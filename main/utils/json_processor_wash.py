"""Script to process JSON files and extract metadata from Chapter 1."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_chapter1_metadata(data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find Chapter 1 and extract its metadata.

    Args:
        data: List of document dictionaries

    Returns:
        Dict containing metadata from Chapter 1, or None if not found
    """
    # Find Chapter 1
    for doc in data:
        if "NYCP1ch_1pg" in doc["file_path"]:
            # Extract title from section 101.1
            title = None
            for section in doc.get("sections", []):
                if "101.1 Title" in section["section"]:
                    # Extract the title from the quoted text
                    title_match = re.search(r'"([^"]*)"', section["section"])
                    if title_match:
                        title = title_match.group(1).strip()
                        break

            # Create metadata
            metadata = {
                "chapter": 1,
                "title": title or "New York City Plumbing Code",
                "chapter_title": "ADMINISTRATION",
            }
            return metadata

    return None


def extract_chapter_number(raw_text: str) -> Optional[int]:
    """Extract chapter number from the raw text content.

    Args:
        raw_text: Raw text content of the document

    Returns:
        Chapter number if found, None otherwise
    """
    # Look for chapter number in text
    chapter_patterns = [
        r"CHAPTER\s+(\d+)",  # Matches "CHAPTER 1"
        r"SECTION\s+PC\s+(\d+)",  # Matches "SECTION PC 101"
    ]

    for pattern in chapter_patterns:
        match = re.search(pattern, raw_text)
        if match:
            chapter_num = int(match.group(1))
            # If we find a section number like 101, extract just the first digit
            if chapter_num > 20:  # Assuming no more than 20 chapters
                chapter_num = int(str(chapter_num)[0])
            return chapter_num

    # If we haven't found a chapter number but we see "ADMINISTRATION", it's Chapter 1
    if "ADMINISTRATION" in raw_text.split("\n")[0:3]:  # Check first few lines
        return 1

    return None


def update_metadata(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update metadata for all documents using Chapter 1 information.

    Args:
        data: List of document dictionaries

    Returns:
        Updated list of document dictionaries
    """
    # First get Chapter 1 metadata
    ch1_metadata = extract_chapter1_metadata(data)
    if not ch1_metadata:
        logger.warning("Chapter 1 metadata not found!")
        return data

    # Update all documents
    for doc in data:
        # Extract chapter number from text content
        chapter = extract_chapter_number(doc["raw_text"])

        # Create metadata using Chapter 1 as base
        new_metadata = ch1_metadata.copy()

        # Update chapter number from content
        if chapter is not None:
            new_metadata["chapter"] = chapter

        # Keep existing chapter title if present
        if doc["metadata"].get("chapter_title"):
            new_metadata["chapter_title"] = doc["metadata"]["chapter_title"]

        # Update document metadata
        doc["metadata"] = new_metadata

    return data


def process_json_data(input_file: str, output_file: str) -> None:
    """Process JSON data to update metadata using Chapter 1 information.

    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file
    """
    try:
        # Read input JSON
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Update metadata
        updated_data = update_metadata(data)

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, indent=4)

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
