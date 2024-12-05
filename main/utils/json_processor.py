"""Module for processing text files into JSON format."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TEXT_FILE_EXT = ".txt"
TABLE_FILE_EXT = "_data.csv"
ANALYTICS_FILE_EXT = ".png"


def get_table_data(file_path: str) -> Optional[str]:
    """Get the path to the table data file if it exists."""
    base_path = str(Path(file_path).parent.parent / "tables" / Path(file_path).stem)
    table_path = f"{base_path}{TABLE_FILE_EXT}"
    return table_path if os.path.exists(table_path) else None


def get_analytics_image(file_path: str) -> Optional[str]:
    """Get the path to the analytics image if it exists."""
    base_path = str(Path(file_path).parent.parent / "analytics" / Path(file_path).stem)
    analytics_path = f"{base_path}{ANALYTICS_FILE_EXT}"
    return analytics_path if os.path.exists(analytics_path) else None


def process_file(file_path: str, original_path: str) -> Dict[str, Any]:
    """Process a single text file and extract data.

    Args:
        file_path: Path to text file to process.
        original_path: Path to original image file.

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

        # Get page number from filename
        match = re.search(r"ch_(\d+)pg", file_path)
        page_num = int(match.group(1)) if match else 0

        # Get table data and analytics image if they exist
        table_path = get_table_data(file_path)
        analytics_path = get_analytics_image(file_path)

        # Create file data structure
        file_data = {
            "i": page_num,
            "p": file_path,
            "o": original_path,
            "pg": page_num,
            "t": raw_text,
        }

        # Add table and analytics info if they exist
        if table_path:
            file_data["tb"] = table_path
        if analytics_path:
            file_data["ti"] = analytics_path

        return file_data

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        raise ValueError(f"Failed to process file {file_path}: {str(e)}")


def get_chapter_from_filename(filename: str) -> tuple:
    """Extract chapter info from filename.

    Example: NYCP2ch_1pg.txt -> (2, "NYCPC", "")
    """
    match = re.match(r"NYCP(\d+)ch_\d+pg", filename)
    if match:
        chapter = match.group(1)
        return chapter, "NYCPC", ""
    return "", "", ""


def process_directory(text_dir: str, original_dir: str) -> Dict[str, Dict[str, Any]]:
    """Process all text files in a directory.

    Args:
        text_dir: Path to directory containing text files.
        original_dir: Path to directory containing original images.

    Returns:
        Dictionary of chapter data.
    """
    if not os.path.isdir(text_dir):
        raise NotADirectoryError(f"Directory not found: {text_dir}")

    chapter_files = {}

    # Process all text files
    for filename in sorted(os.listdir(text_dir)):
        if not filename.endswith(TEXT_FILE_EXT):
            continue

        file_path = os.path.join(text_dir, filename)
        chapter, code_type, code_title = get_chapter_from_filename(filename)

        if not chapter:
            logger.warning(f"Skipping file with invalid format: {filename}")
            continue

        # Get corresponding original image path
        original_filename = f"{filename[:-4]}.jpg"  # Replace .txt with .jpg
        original_path = os.path.join(original_dir, original_filename)

        # Process the file
        try:
            file_data = process_file(file_path, original_path)

            # Create or update chapter data
            chapter_key = f"{code_type}{chapter}CH_"
            if chapter_key not in chapter_files:
                chapter_files[chapter_key] = {
                    "m": {"c": chapter, "t": code_type, "ct": code_title},
                    "f": [],
                }
            chapter_files[chapter_key]["f"].append(file_data)

        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            continue

    return chapter_files


def save_json(data: Dict[str, Dict[str, Any]], output_dir: str) -> None:
    """Save the extracted data to JSON files by chapter.

    Args:
        data: Dictionary of chapter data.
        output_dir: Directory where JSON files will be saved.

    Raises:
        OSError: If the output files cannot be written.
    """
    os.makedirs(output_dir, exist_ok=True)

    for chapter_key, chapter_data in data.items():
        output_file = os.path.join(output_dir, f"{chapter_key}.json")
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
        base_path = Path("/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/media/plumbing_code")
        text_dir = base_path / "OCR"
        original_dir = base_path / "optimizer"
        output_dir = base_path / "json"

        # Process files and save by chapter
        data = process_directory(str(text_dir), str(original_dir))
        save_json(data, str(output_dir))

        # Log processing summary
        total_files = sum(len(chapter["f"]) for chapter in data.values())
        logger.info(f"Processed {total_files} files. Results saved to {output_dir}")

    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        raise


if __name__ == "__main__":
    main()
