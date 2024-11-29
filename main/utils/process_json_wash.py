"""Module for processing and updating JSON metadata from raw text content."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_metadata_from_raw_text(text: str) -> Dict[str, Any]:
    """Extract metadata from raw text content.

    Args:
        text: Raw text content to analyze

    Returns:
        dict: Dictionary containing metadata fields:
            - chapter: Chapter number as integer
            - title: Document title as string
            - chapter_title: Chapter title as string
    """
    metadata = {"chapter": None, "title": None, "chapter_title": None}

    # Extract chapter number from text or filename
    chapter_patterns = [
        r"NYCP1ch_(\d+)pg",  # From filename
        r"CHAPTER\s+(\d+)",  # Regular chapter number
        r"Chapter\s+(\d+)",  # Case-insensitive chapter
    ]

    for pattern in chapter_patterns:
        chapter_match = re.search(pattern, text, re.IGNORECASE)
        if chapter_match:
            metadata["chapter"] = int(chapter_match.group(1))
            break

    # Extract title from various patterns
    title_patterns = [
        r'known and may be cited as the\s+"([^"]*)"',  # From formal title declaration
        r'"([^"]*(?:New York City Plumbing Code|NYC Plumbing Code)[^"]*)"',  # Quoted title
        r'([^"]*(?:New York City Plumbing Code|NYC Plumbing Code)[^"]*)',  # Unquoted title
    ]

    for pattern in title_patterns:
        title_match = re.search(pattern, text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip().rstrip('."')
            if "plumbing code" in title.lower():
                metadata["title"] = title
                break

    # Set default title if none found
    if not metadata["title"]:
        metadata["title"] = "New York City Plumbing Code"

    # Extract chapter title with improved patterns
    chapter_title_patterns = [
        r"CHAPTER\s+\d+\s*\n\s*([A-Z][A-Z\s]+)(?:\n|$)",  # After chapter number
        r"^([A-Z][A-Z\s]+)(?:\n|$)",  # At start of text
        r"\n([A-Z][A-Z\s]+)(?:\n|$)",  # After newline
    ]

    # First try to find a chapter title after the chapter number
    if metadata["chapter"]:
        chapter_header = f"CHAPTER {metadata['chapter']}"
        text_after_chapter = text[text.find(chapter_header) :] if chapter_header in text else text
        for pattern in chapter_title_patterns:
            match = re.search(pattern, text_after_chapter)
            if match:
                title = match.group(1).strip()
                if (
                    len(title) >= 3 and title != "CHAPTER"
                ):  # Avoid short matches and the word CHAPTER
                    metadata["chapter_title"] = title
                    break

    # If no chapter title found yet, try the general patterns
    if not metadata["chapter_title"]:
        for pattern in chapter_title_patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                if (
                    len(title) >= 3 and title != "CHAPTER"
                ):  # Avoid short matches and the word CHAPTER
                    metadata["chapter_title"] = title
                    break

    # If we still don't have a chapter title but have "ADMINISTRATION" in the text, use it
    if not metadata["chapter_title"] and "ADMINISTRATION" in text:
        metadata["chapter_title"] = "ADMINISTRATION"

    return metadata


def process_json_data(input_file: str, output_file: str) -> None:
    """Process JSON data to fill in missing metadata.

    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file

    Raises:
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If input file is not valid JSON
        IOError: If there are issues reading/writing files
    """
    try:
        # Read input JSON
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Process each document
        for doc in data:
            if not doc.get("metadata") or all(v is None for v in doc["metadata"].values()):
                # Extract metadata from both raw text and file path
                raw_text = doc.get("raw_text", "") + "\n" + doc.get("file_path", "")
                metadata = extract_metadata_from_raw_text(raw_text)
                doc["metadata"] = metadata

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        logger.info(f"Successfully processed JSON data and saved to {output_file}")

    except Exception as e:
        logger.error(f"Error processing JSON data: {str(e)}")
        raise


if __name__ == "__main__":
    # Define input and output paths
    base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/json"
    input_path = os.path.join(base_path, "text_data.json")
    output_path = os.path.join(base_path, "text_data_processed.json")

    # Process the data
    process_json_data(input_path, output_path)
