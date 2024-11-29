"""Module for processing text files and generating structured JSON data.

This module provides functionality to:
1. Extract structured sections from text files
2. Process base64 image paths
3. Generate and save JSON output
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
SECTION_PATTERN = r"(SECTION PC \d+|\d+(\.\d+)*|\d+\.?\s+[A-Za-z])"
TEXT_FILE_EXT = ".txt"
IMAGE_FILE_EXT = ".jpg"
BASE64_DIR = "optimized/base64"


def extract_section_data(file_content: str) -> List[Dict[str, str]]:
    """Extract structured section data from file content.

    Args:
        file_content: Raw text content from the file.

    Returns:
        List of dictionaries containing section and content pairs.
    """
    sections: List[Dict[str, str]] = []
    current_section: Optional[str] = None
    current_content: List[str] = []

    lines = file_content.splitlines()
    for line in lines:
        section_match = re.match(SECTION_PATTERN, line.strip())
        if section_match:
            logger.debug(f"Matched section: {line.strip()}")
            if current_section:
                sections.append(
                    {"section": current_section, "content": "\n".join(current_content).strip()}
                )
            current_section = line.strip()
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections.append({"section": current_section, "content": "\n".join(current_content).strip()})

    return sections


def get_base64_path(text_file_path: str) -> Optional[str]:
    """Get the path to the corresponding base64 image file.

    Args:
        text_file_path: Path to the text file.

    Returns:
        Path to corresponding base64 image file or None if not found.
    """
    try:
        file_name = os.path.basename(text_file_path).replace(TEXT_FILE_EXT, IMAGE_FILE_EXT)
        base_dir = os.path.dirname(os.path.dirname(text_file_path))
        base64_path = os.path.join(base_dir, BASE64_DIR, file_name)

        logger.debug(f"Looking for base64 image at: {base64_path}")

        if os.path.exists(base64_path):
            return base64_path
        logger.warning(f"Base64 image not found at: {base64_path}")
        return None
    except Exception as e:
        logger.error(f"Error getting base64 path: {str(e)}")
        return None


def process_file(file_path: str) -> Dict[str, Any]:
    """Process a single file and extract structured data.

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

    sections = extract_section_data(content)
    base64_path = get_base64_path(file_path)

    data = {
        "file_path": file_path,
        "base64_file_path": base64_path,
        "raw_text": content,
        "sections": sections,
    }

    return data


def process_directory(directory_path: str) -> List[Dict[str, Any]]:
    """Process all text files in a directory.

    Args:
        directory_path: Path to directory containing text files.

    Returns:
        List of dictionaries containing processed file data.

    Raises:
        NotADirectoryError: If directory_path is not a directory.
    """
    if not os.path.isdir(directory_path):
        raise NotADirectoryError(f"Not a directory: {directory_path}")

    json_data = []
    for filename in os.listdir(directory_path):
        if filename.endswith(TEXT_FILE_EXT):
            file_path = os.path.join(directory_path, filename)
            try:
                data = process_file(file_path)
                json_data.append(data)
                logger.info(f"Successfully processed file: {filename}")
            except Exception as e:
                logger.error(f"Failed to process file {filename}: {str(e)}")
                continue

    return json_data


def save_json(data: List[Dict[str, Any]], output_file: str) -> None:
    """Save the extracted data to a JSON file.

    Args:
        data: List of dictionaries containing file data.
        output_file: Path where JSON file will be saved.

    Raises:
        OSError: If the output file cannot be written.
    """
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        logger.info(f"Successfully saved JSON to: {output_file}")
    except OSError as e:
        logger.error(f"Failed to save JSON file: {str(e)}")
        raise


def main() -> None:
    """Main function to process text files and save as JSON."""
    try:
        input_directory = (
            "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/text"
        )
        output_directory = (
            "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/json"
        )
        os.makedirs(output_directory, exist_ok=True)
        output_json = os.path.join(output_directory, "text_data.json")

        data = process_directory(input_directory)
        save_json(data, output_json)
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
