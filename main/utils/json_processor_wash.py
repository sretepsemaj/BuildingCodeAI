"""Script to process JSON files and extract metadata from all chapters."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_chapter_info(raw_text: str) -> tuple[Optional[int], Optional[str]]:
    """Extract chapter number and title from raw text.

    Args:
        raw_text: Raw text content to process

    Returns:
        Tuple of (chapter_number, chapter_title) or (None, None) if not found
    """
    # Look for chapter number and title in the raw text
    # Pattern matches "CHAPTER X" followed by an all-caps title on the next line
    chapter_match = re.search(r"CHAPTER\s+(\d+)\s*\n([A-Z][A-Z\s]+?)(?:\s*\n|$)", raw_text)
    if chapter_match:
        chapter_num = int(chapter_match.group(1))
        chapter_title = chapter_match.group(2).strip()
        return chapter_num, chapter_title
    return None, None


def extract_metadata(data: List[Dict[str, Any]], chapter_num: int) -> Optional[Dict[str, Any]]:
    """Find chapter and extract its metadata.

    Args:
        data: List of document dictionaries
        chapter_num: Chapter number to process

    Returns:
        Dict containing metadata from the chapter, or None if not found
    """
    chapter_pattern = f"NYCP{chapter_num}ch_"

    # First find the first page (ending with _1pg.txt)
    first_page = None
    for doc in data:
        if f"{chapter_pattern}1pg.txt" in doc["file_path"]:
            first_page = doc
            break

    if not first_page:
        logger.warning(f"First page not found for Chapter {chapter_num}")
        return None

    # Extract chapter number and title from raw text of first page
    chapter_num, chapter_title = extract_chapter_info(first_page["raw_text"])
    if not chapter_num or not chapter_title:
        logger.warning(f"Could not extract chapter info from first page of Chapter {chapter_num}")
        return None

    # Extract title from section X01.1 where X is the chapter number
    title = None
    for section in first_page.get("sections", []):
        # Look for title in section X01.1
        if f"{chapter_num}01.1" in section["section"]:
            # Extract the title from the quoted text
            title_match = re.search(r'"([^"]*)"', section["content"])
            if title_match:
                title = title_match.group(1).strip()
                break

    # Create metadata
    metadata = {
        "chapter": chapter_num,
        "title": "New York City Plumbing Code",  # Simplified title without chapter number
        "chapter_title": chapter_title,
    }
    return metadata


def update_metadata(data: List[Dict[str, Any]], chapter_num: int) -> List[Dict[str, Any]]:
    """Update metadata for all documents in a chapter.

    Args:
        data: List of document dictionaries
        chapter_num: Chapter number to process

    Returns:
        Updated list of document dictionaries
    """
    # Extract metadata from the chapter
    metadata = extract_metadata(data, chapter_num)
    if not metadata:
        logger.warning(f"No metadata found for Chapter {chapter_num}")
        return data

    # Update all documents in this chapter
    chapter_pattern = f"NYCP{chapter_num}ch_"
    updated_data = []
    for doc in data:
        if chapter_pattern in doc["file_path"]:
            doc["metadata"] = metadata
        updated_data.append(doc)

    return updated_data


def process_json_data(input_file: str, output_file: str) -> None:
    """Process JSON data to update metadata for all chapters.

    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file
    """
    try:
        # Load input data
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            logger.warning("No data found in input file")
            return

        # Find all unique chapter numbers
        chapter_nums = set()
        for doc in data:
            match = re.search(r"NYCP(\d+)ch_", doc["file_path"])
            if match:
                chapter_nums.add(int(match.group(1)))

        # Process each chapter
        for chapter_num in sorted(chapter_nums):
            data = update_metadata(data, chapter_num)

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully processed {input_file} and saved to {output_file}")

    except Exception as e:
        logger.error(f"Error processing {input_file}: {str(e)}")
        raise


def process_directory(input_dir: str, output_dir: str) -> None:
    """Process all JSON files in a directory and save to output directory.

    Args:
        input_dir: Path to directory containing input JSON files
        output_dir: Path to directory where processed JSON files will be saved
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Process each JSON file
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            input_file = os.path.join(input_dir, filename)
            output_file = os.path.join(output_dir, filename)
            process_json_data(input_file, output_file)


if __name__ == "__main__":
    # Define input and output paths
    base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"
    input_dir = os.path.join(base_path, "json")
    output_dir = os.path.join(base_path, "optimized", "json")

    # Process all files
    process_directory(input_dir, output_dir)
