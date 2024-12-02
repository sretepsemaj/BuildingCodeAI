"""Module for processing text files and extracting structured data."""

import logging
import os
import re
from typing import Dict, List, Optional

import pytesseract
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SECTION_PATTERN = r"(SECTION PC \d+|\d+(\.\d+)*|\d+\.?\s+[A-Za-z])"


class TextProcessor:
    """Class for processing images and extracting text."""

    def __init__(self, input_dir: str, output_dir: str):
        """Initialize TextProcessor.

        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save output text files
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def process_image(self, image_path: str) -> Optional[str]:
        """Process a single image and extract text.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text if successful, None otherwise
        """
        try:
            # Open and process image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Extract text using OCR
                text = pytesseract.image_to_string(img)
                return text.strip() if text else None

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            return None

    def process_all_images(self) -> Dict[str, any]:
        """Process all images in the input directory.

        Returns:
            Dictionary containing processing results
        """
        results = {
            "processed_files": [],
            "failed_files": [],
            "stats": {"total": 0, "success": 0, "failed": 0},
        }

        # Process each image in directory
        for filename in os.listdir(self.input_dir):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
                continue

            results["stats"]["total"] += 1
            image_path = os.path.join(self.input_dir, filename)

            # Extract text from image
            text = self.process_image(image_path)

            if text:
                # Create output text file
                text_filename = os.path.splitext(filename)[0] + ".txt"
                text_path = os.path.join(self.output_dir, text_filename)

                try:
                    # Save extracted text
                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(text)

                    results["processed_files"].append(
                        {"image_file": filename, "text_file": text_filename}
                    )
                    results["stats"]["success"] += 1
                    logger.info(f"Successfully processed {filename}")

                except Exception as e:
                    logger.error(f"Error saving text file for {filename}: {str(e)}")
                    results["failed_files"].append({"file": filename, "error": str(e)})
                    results["stats"]["failed"] += 1
            else:
                results["failed_files"].append({"file": filename, "error": "No text extracted"})
                results["stats"]["failed"] += 1
                logger.warning(f"No text extracted from {filename}")

        return results


def extract_sections(text: str) -> List[Dict[str, str]]:
    """Extract sections from text content.

    Args:
        text: Raw text content to process.

    Returns:
        List of dictionaries containing section and content pairs.
    """
    sections = []
    current_section = None
    current_content = []

    for line in text.splitlines():
        section_match = re.match(SECTION_PATTERN, line.strip())
        if section_match:
            if current_section:
                sections.append(
                    {
                        "section": current_section,
                        "content": "\n".join(current_content).strip(),
                    }
                )
            current_section = line.strip()
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections.append({"section": current_section, "content": "\n".join(current_content).strip()})

    return sections


def extract_metadata(text: str) -> Dict[str, Optional[str]]:
    """Extract metadata from text content.

    Args:
        text: Raw text content to analyze.

    Returns:
        Dictionary containing metadata like chapter, title, etc.
    """
    metadata = {"chapter": None, "title": None, "chapter_title": None}

    # Extract chapter number
    chapter_match = re.search(r"CHAPTER\s+(\d+)", text)
    if chapter_match:
        metadata["chapter"] = chapter_match.group(1)

    # Extract title (e.g., "New York City Plumbing Code")
    title_match = re.search(r'"([^"]*City Plumbing Code[^"]*)"', text)
    if title_match:
        metadata["title"] = title_match.group(1).rstrip('."')

    # Extract chapter title (e.g., "ADMINISTRATION")
    chapter_title_match = re.search(r"CHAPTER\s+\d+\s*\n\s*([A-Z][A-Z\s]+)(?:\n|$)", text)
    if chapter_title_match:
        metadata["chapter_title"] = chapter_title_match.group(1).strip()

    return metadata


def process_file(file_path: str) -> Dict[str, any]:
    """Process a single text file and extract structured data.

    Args:
        file_path: Path to the text file to process.

    Returns:
        Dictionary containing file data, including path and sections.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except UnicodeDecodeError as e:
        logger.error(f"Failed to decode file {file_path}: {str(e)}")
        raise

    metadata = extract_metadata(content)
    sections = extract_sections(content)

    data = {
        "file_path": file_path,
        "metadata": metadata,
        "raw_text": content,
        "sections": sections,
    }

    return data


def process_directory(directory_path: str) -> List[Dict[str, any]]:
    """Process all text files in a directory.

    Args:
        directory_path: Path to directory containing text files.

    Returns:
        List of dictionaries containing file data.

    Raises:
        NotADirectoryError: If directory_path is not a directory.
    """
    if not os.path.isdir(directory_path):
        raise NotADirectoryError(f"Not a directory: {directory_path}")

    processed_data = []
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            try:
                data = process_file(file_path)
                processed_data.append(data)
                logger.info(f"Successfully processed file: {filename}")
            except Exception as e:
                logger.error(f"Failed to process file {filename}: {str(e)}")
                continue

    return processed_data


if __name__ == "__main__":
    try:
        # Set up paths
        base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"
        input_dir = os.path.join(base_path, "text")

        # Process all files in directory
        data = process_directory(input_dir)
        logger.info(f"Successfully processed {len(data)} files")

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise
