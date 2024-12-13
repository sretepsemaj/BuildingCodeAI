#!/usr/bin/env python3
"""Process OCR module for handling OCR operations."""

import logging
import os
import re
import shutil
import sys
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple

import django
import pytesseract
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from PIL import Image

# Django settings configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.base"),
)

django.setup()

# Get logger from Django's configuration
logger = logging.getLogger("main.utils.process_ocr")

# Set up logging if not already configured
if not logger.handlers:
    # Use settings for directory paths
    try:
        logs_dir = settings.LOGS_DIR
    except AttributeError:
        # Fallback to default logs directory
        logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Add file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "process_ocr.log",
        maxBytes=10485760,  # 10MB
        backupCount=3,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
        style="{",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.setLevel(logging.INFO)


def analyze_text_patterns(text: str) -> Tuple[bool, float]:
    """Analyze text patterns to detect table-like structures."""
    logger.info("Analyzing text patterns to detect table-like structures")

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return False, 0.0

    # Pattern scores
    scores = []

    # 1. Check for measurement patterns
    measurement_pattern = r"\d+(?:\.\d+)?\s*(?:feet|foot|ft|inches|inch|mm|meters|m|\'|\")"
    measurements = sum(1 for line in lines if re.search(measurement_pattern, line, re.IGNORECASE))
    measurement_score = measurements / len(lines)
    scores.append(measurement_score * 2)  # Weight measurements heavily

    # 2. Analyze indentation patterns
    if len(lines) >= 3:
        indents = [len(line) - len(line.lstrip()) for line in lines]
        try:
            indent_consistency = 1.0 / (1.0 + stdev(indents))
            scores.append(indent_consistency)
        except (ValueError, ZeroDivisionError):
            scores.append(0.0)

    # 3. Check for consistent word spacing
    word_counts = [len(line.split()) for line in lines]
    if len(word_counts) >= 3:
        try:
            spacing_consistency = 1.0 / (1.0 + stdev(word_counts))
            scores.append(spacing_consistency)
        except (ValueError, ZeroDivisionError):
            scores.append(0.0)

    # 4. Look for numbered lists or bullet points
    numbered_pattern = r"^\s*(?:\d+\.|\(\d+\)|\w\.|\-|\•)\s"
    numbered_lines = sum(1 for line in lines if re.match(numbered_pattern, line))
    numbered_score = numbered_lines / len(lines)
    scores.append(numbered_score)

    # 5. Check for column-like structure
    spaces_pattern = r"\s{2,}"
    consistent_spaces = sum(1 for line in lines if len(re.findall(spaces_pattern, line)) >= 2)
    column_score = consistent_spaces / len(lines)
    scores.append(column_score * 2)  # Weight column structure heavily

    # Calculate final score
    final_score = mean(scores) if scores else 0.0
    logger.info(f"Text pattern analysis completed with score: {final_score:.2f}")
    return final_score > 0.3, final_score  # Threshold of 0.3 for table detection


def process_tables(text: str, image_path: str, tables_dir: str) -> Dict:
    """Extract tables from text using pattern analysis."""
    logger.info(f"Processing tables for image: {image_path}")

    try:
        # Ensure tables directory exists
        if not os.path.exists(tables_dir):
            os.makedirs(tables_dir)
            logger.info(f"Created tables directory: {tables_dir}")

        # Analyze text patterns
        is_table, confidence = analyze_text_patterns(text)

        if not is_table:
            logger.info("No table detected in the text")
            return {
                "success": True,
                "table_path": None,
                "df_path": None,
                "error": "No table detected",
                "confidence": confidence,
            }

        # Convert text to CSV format
        csv_lines = []
        for line in text.split("\n"):
            if line.strip():
                # Replace multiple spaces with a single comma
                csv_line = re.sub(r"\s{2,}", ",", line.strip())
                csv_lines.append(csv_line)

        # Create CSV content
        csv_content = "\n".join(csv_lines)

        try:
            # Get base name for the file
            base_name = os.path.splitext(os.path.basename(image_path))[0]

            # Extract document title and page number from filename
            match = re.search(r"(.+?)_(\d+)pg", base_name)
            if not match:
                raise ValueError(f"Invalid filename format: {base_name}")

            doc_title = match.group(1)
            page_number = int(match.group(2))

            # Get or create the document
            from main.models import PlumbingDocument, PlumbingImage, PlumbingTable

            doc, _ = PlumbingDocument.objects.get_or_create(title=doc_title)

            # Create or update the table
            table, created = PlumbingTable.objects.get_or_create(
                document=doc,
                page_number=page_number,
            )

            # Generate filename for CSV
            base_prefix = doc_title.split("_")[0].replace("CH", "ch")
            csv_filename = f"{base_prefix}_{page_number}pg.csv"

            # Save the CSV content to the model
            table.csv_file.save(csv_filename, ContentFile(csv_content.encode("utf-8")), save=True)

            logger.info(f"Table saved to database: {table}")
            return {
                "success": True,
                "table_path": table.csv_file.path if table.csv_file else None,
                "df_path": None,
                "error": None,
                "confidence": confidence,
            }

        except (ValueError, AttributeError, IndexError) as e:
            logger.error(f"Error processing filename or database: {e}")
            return {
                "success": False,
                "table_path": None,
                "df_path": None,
                "error": str(e),
                "confidence": confidence,
            }

    except Exception as e:
        logger.error(f"Error processing tables: {e}")
        return {
            "success": False,
            "table_path": None,
            "df_path": None,
            "error": str(e),
            "confidence": 0.0,
        }


def process_image(image_path: str, output_path: str, tables_dir: str) -> Dict:
    """Process a single image with OCR and table detection."""
    logger.info(f"Processing image: {image_path}")

    try:
        # Extract text using OCR
        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img)
            logger.info("Text extracted from image using OCR")

            # Save OCR text
            text_path = os.path.join(
                settings.PLUMBING_CODE_PATHS["ocr"],
                os.path.splitext(os.path.basename(image_path))[0] + ".txt",
            )
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"OCR text saved to: {text_path}")

            # Process tables if text contains table-like patterns
            table_result = process_tables(text, image_path, tables_dir)

            # Create or update PlumbingImage
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            doc_title = "_".join(base_name.split("_")[:-1])  # Remove page number part
            page_number = int(re.search(r"(\d+)pg", base_name).group(1))

            # Get or create the document
            from main.models import PlumbingDocument, PlumbingImage, PlumbingTable

            doc, _ = PlumbingDocument.objects.get_or_create(title=doc_title)

            # Create or update the image
            plumbing_image, created = PlumbingImage.objects.get_or_create(
                document=doc,
                page_number=page_number,
            )

            # Generate filename for image
            base_prefix = doc_title.split("_")[0].replace("CH", "ch")
            image_filename = f"{base_prefix}_{page_number}pg.jpg"

            # Save the image file
            with open(image_path, "rb") as img_file:
                plumbing_image.image.save(
                    image_filename,
                    ContentFile(img_file.read()),
                    save=True,  # Provide the filename
                )

            return {
                "success": True,
                "text_path": text_path,
                "table_result": table_result,
                "error": None,
                "image_path": (plumbing_image.image.path if plumbing_image.image else None),
            }

    except Exception as e:
        logger.error("Error processing image %s: %s", image_path, str(e))
        return {
            "success": False,
            "text_path": None,
            "table_result": None,
            "error": str(e),
            "image_path": None,
        }


def process_image(image_path: str) -> Dict[str, Any]:
    """Process an image with OCR and detect tables."""
    try:
        # Convert image to text using OCR
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)

        # Save text to file
        text_path = image_path.replace(".jpg", ".txt")
        with open(text_path, "w") as f:
            f.write(text)

        return {"success": True, "text_path": text_path, "error": None}

    except Exception as e:
        logger.error("Error processing image %s: %s", image_path, str(e))
        return {"success": False, "text_path": None, "error": str(e)}


def process_all_images():
    """Process all images in the uploads directory."""
    try:
        # Get paths from settings
        uploads_dir = str(settings.PLUMBING_CODE_PATHS["uploads"])
        ocr_dir = str(settings.PLUMBING_CODE_PATHS["ocr"])
        original_dir = str(settings.PLUMBING_CODE_PATHS["original"])

        # Get list of image files to process
        image_files = [
            f
            for f in os.listdir(uploads_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
        ]

        if not image_files:
            logger.info("No image files found in uploads directory")
            return

        logger.info("Found %d images to process", len(image_files))

        for image_file in image_files:
            image_path = os.path.join(uploads_dir, image_file)
            result = process_image(image_path)

            if result["success"]:
                # Move processed image to original directory
                shutil.move(image_path, os.path.join(original_dir, image_file))
                logger.info("Successfully processed %s", image_file)
            else:
                logger.error("Failed to process %s: %s", image_file, result["error"])

    except Exception as e:
        logger.error("Error processing images: %s", str(e))
        raise


def main():
    """Process images from uploads directory, save OCR results, and detect tables."""
    try:
        logger.info("Starting OCR processing")
        process_all_images()
    except Exception as e:
        logger.error("Error in main OCR processing: %s", str(e))


if __name__ == "__main__":
    main()
