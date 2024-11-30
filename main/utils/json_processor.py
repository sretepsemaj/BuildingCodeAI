"""Module for processing text files into JSON format."""

import json
import logging
import os
import re
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TEXT_FILE_EXT = ".txt"


def process_file(file_path: str) -> Dict[str, Any]:
    """Process a single text file and extract data.

    Args:
        file_path: Path to text file to process.

    Returns:
        Dictionary containing processed file data.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If file cannot be processed.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            raw_text = file.read()

        # Initialize data structure
        data = {
            "file_path": file_path,
            "raw_text": raw_text,
            "sections": [],
            "metadata": {},
        }

        # Split text into sections
        current_section = ""
        current_content = []

        for line in raw_text.split("\n"):
            # Check if line starts with a section number (e.g., "101.1", "102", etc.)
            if re.match(r"^\d+\.?\d*\.?\d*\s+", line):
                # Save previous section if it exists
                if current_section and current_content:
                    data["sections"].append(
                        {
                            "section": current_section,
                            "content": "\n".join(current_content),
                        }
                    )
                # Start new section
                current_section = line
                current_content = []
            else:
                # Add line to current section content
                if line.strip():  # Only add non-empty lines
                    current_content.append(line)

        # Add last section
        if current_section and current_content:
            data["sections"].append(
                {"section": current_section, "content": "\n".join(current_content)}
            )

        return data

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        raise ValueError(f"Failed to process file: {str(e)}")


def get_chapter_from_filename(filename: str) -> str:
    """Extract chapter number from filename and create new filename.

    Example: NYCP2ch_1pg.txt -> NYCP2CH.json
    """
    # Extract chapter number from filename (e.g., NYCP2ch_1pg.txt -> 2)
    match = re.match(r"NYCP(\d+)ch_", filename)
    if match:
        chapter_num = match.group(1)
        return f"NYCP{chapter_num}CH.json"
    return "text_data.json"  # fallback name


def process_directory(directory_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Process all text files in a directory, skipping subdirectories.

    Args:
        directory_path: Path to directory containing text files.

    Returns:
        Dictionary of chapter filenames and their file data.

    Raises:
        NotADirectoryError: If directory_path is not a directory.
    """
    if not os.path.isdir(directory_path):
        raise NotADirectoryError(f"Not a directory: {directory_path}")

    # Group files by chapter
    chapter_files = {}

    # Get all items in directory
    items = os.listdir(directory_path)
    for item in items:
        item_path = os.path.join(directory_path, item)

        # Skip if it's a directory
        if os.path.isdir(item_path):
            logger.info(f"Skipping directory: {item}")
            continue

        # Skip if not a text file
        if not item.endswith(TEXT_FILE_EXT):
            logger.info(f"Skipping non-text file: {item}")
            continue

        try:
            data = process_file(item_path)

            # Get chapter from filename
            chapter_filename = get_chapter_from_filename(item)

            # Group by chapter
            if chapter_filename not in chapter_files:
                chapter_files[chapter_filename] = []
            chapter_files[chapter_filename].append(data)

            logger.info(f"Successfully processed file: {item}")
        except Exception as e:
            logger.error(f"Failed to process file {item}: {str(e)}")
            continue

    return chapter_files


def save_json(data: Dict[str, List[Dict[str, Any]]], output_dir: str) -> None:
    """Save the extracted data to JSON files by chapter.

    Args:
        data: Dictionary of chapter filenames and their file data.
        output_dir: Directory where JSON files will be saved.

    Raises:
        OSError: If the output files cannot be written.
    """
    os.makedirs(output_dir, exist_ok=True)

    for chapter_filename, chapter_data in data.items():
        output_file = os.path.join(output_dir, chapter_filename)
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(chapter_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved JSON to: {output_file}")
        except OSError as e:
            logger.error(f"Failed to save JSON to {output_file}: {str(e)}")
            raise


def main() -> None:
    """Process text files and generate JSON output."""
    try:
        # Set up paths
        base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"
        input_dir = os.path.join(base_path, "text")
        output_dir = os.path.join(base_path, "json")

        # Process files and save by chapter
        data = process_directory(input_dir)
        save_json(data, output_dir)

        # Log processing summary
        total_files = sum(len(files) for files in data.values())
        logger.info(f"Processed {total_files} files. Results saved to {output_dir}")

    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        raise


if __name__ == "__main__":
    main()
