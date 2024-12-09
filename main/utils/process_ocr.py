"""Script to process images with OCR and detect tables."""

import logging
import os
import re
import shutil
import sys
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List, Tuple

# Add the project root to the Python path before importing Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Django imports
import django  # noqa: E402

# Third-party imports
import pytesseract  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.exceptions import ImproperlyConfigured  # noqa: E402
from PIL import Image  # noqa: E402

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Get logger from Django's configuration
logger = logging.getLogger("main.utils.process_ocr")


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

        # Save table text to CSV
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        table_path = os.path.join(tables_dir, f"{base_name}.csv")

        # Convert text to CSV format
        csv_lines = []
        for line in text.split("\n"):
            if line.strip():
                # Replace multiple spaces with a single comma
                csv_line = re.sub(r"\s{2,}", ",", line.strip())
                csv_lines.append(csv_line)

        # Write CSV file
        with open(table_path, "w", encoding="utf-8") as f:
            f.write("\n".join(csv_lines))

        logger.info(f"Table saved to CSV: {table_path}")
        return {
            "success": True,
            "table_path": table_path,
            "df_path": None,
            "error": None,
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

            return {
                "success": True,
                "text_path": text_path,
                "table_result": table_result,
                "error": None,
            }

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return {
            "success": False,
            "text_path": None,
            "table_result": None,
            "error": str(e),
        }


def main():
    """Process images from uploads directory, save OCR results, and detect tables."""
    logger.info("Starting OCR processing")

    try:
        # Get paths from Django settings
        paths = settings.PLUMBING_CODE_PATHS
        uploads_dir = paths["uploads"]
        ocr_dir = paths["ocr"]
        tables_dir = paths["tables"]
        original_dir = paths["original"]

        # Get list of image files to process
        files = [
            f
            for f in os.listdir(uploads_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
        ]
        logger.info(f"Found {len(files)} images to process")

        # Process each file
        successful = 0
        failed = 0

        for filename in files:
            input_path = os.path.join(uploads_dir, filename)
            output_path = os.path.join(ocr_dir, filename)

            try:
                # Process the image
                result = process_image(input_path, output_path, tables_dir)

                if result["success"]:
                    # Move original to original directory
                    original_path = os.path.join(original_dir, filename)
                    shutil.move(input_path, original_path)
                    logger.info(f"Moved original file to: {original_path}")

                    # Log table detection results
                    if result["table_result"]["table_path"]:
                        logger.info(
                            f"Table detected in {filename} "
                            f"(confidence: {result['table_result']['confidence']:.2f})"
                        )

                    successful += 1
                else:
                    logger.error(f"Failed to process {filename}: {result['error']}")
                    failed += 1

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                failed += 1
                continue

        logger.info(f"OCR processing complete. Successful: {successful}, Failed: {failed}")

    except Exception as e:
        logger.error(f"Error in main process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
