"""Script to process JSON files and extract metadata from all chapters."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_metadata(data: List[Dict[str, Any]], chapter_num: int) -> Optional[Dict[str, Any]]:
    """Find chapter and extract its metadata.

    Args:
        data: List of document dictionaries
        chapter_num: Chapter number to process

    Returns:
        Dict containing metadata from the chapter, or None if not found
    """
    chapter_pattern = f"NYCP{chapter_num}ch_"

    # Find the chapter
    for doc in data:
        if chapter_pattern in doc["file_path"]:
            # Extract title from section X01.1 where X is the chapter number
            title = None
            chapter_title = None

            for section in doc.get("sections", []):
                # Look for title in section X01.1
                if f"{chapter_num}01.1" in section["section"]:
                    # Extract the title from the quoted text
                    title_match = re.search(r'"([^"]*)"', section["content"])
                    if title_match:
                        title = title_match.group(1).strip()

                # Look for chapter title (usually in all caps at the start)
                if not chapter_title:
                    lines = section["content"].split("\n")
                    for line in lines:
                        if line.isupper() and len(line.strip()) > 0:
                            chapter_title = line.strip()
                            break

                if title and chapter_title:
                    break

            # Create metadata
            metadata = {
                "chapter": chapter_num,
                "title": title or f"New York City Plumbing Code Chapter {chapter_num}",
                "chapter_title": chapter_title or f"CHAPTER {chapter_num}",
            }
            return metadata

    return None


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
    updated_data = []
    for doc in data:
        if f"NYCP{chapter_num}ch_" in doc["file_path"]:
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
            logger.warning(f"No data found in {input_file}")
            return

        # Find all unique chapter numbers
        chapter_nums = set()
        for doc in data:
            match = re.search(r"NYCP(\d+)ch_", doc["file_path"])
            if match:
                chapter_nums.add(int(match.group(1)))

        # Process each chapter
        processed_data = data
        for chapter_num in sorted(chapter_nums):
            processed_data = update_metadata(processed_data, chapter_num)
            logger.info(f"Processed metadata for Chapter {chapter_num}")

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2)
        logger.info(f"Saved processed data to {output_file}")

    except Exception as e:
        logger.error(f"Error processing {input_file}: {str(e)}")
        raise


def process_directory(input_dir: str, output_dir: str) -> None:
    """Process all JSON files in a directory and save to output directory.

    Args:
        input_dir: Path to directory containing input JSON files
        output_dir: Path to directory where processed JSON files will be saved
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Process each JSON file in the directory
        for filename in os.listdir(input_dir):
            if filename.endswith(".json"):
                input_file = os.path.join(input_dir, filename)
                output_file = os.path.join(output_dir, filename)

                logger.info(f"Processing {filename}...")

                # Load and process the file
                try:
                    with open(input_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if not data:
                        logger.warning(f"No data found in {filename}")
                        continue

                    # Find all unique chapter numbers
                    chapter_nums = set()
                    for doc in data:
                        match = re.search(r"NYCP(\d+)ch_", doc["file_path"])
                        if match:
                            chapter_nums.add(int(match.group(1)))

                    # Process each chapter
                    processed_data = data
                    for chapter_num in sorted(chapter_nums):
                        processed_data = update_metadata(processed_data, chapter_num)
                        logger.info(f"Processed metadata for Chapter {chapter_num}")

                    # Save processed data to output directory
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(processed_data, f, indent=2)
                    logger.info(f"Saved processed data to {output_file}")

                except Exception as e:
                    logger.error(f"Error processing {filename}: {str(e)}")
                    continue

    except Exception as e:
        logger.error(f"Error processing directory {input_dir}: {str(e)}")
        raise


if __name__ == "__main__":
    # Define input and output paths
    base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/json"
    input_directory = os.path.join(base_path, "input")
    output_directory = os.path.join(base_path, "output")

    # Process the directory
    process_directory(input_directory, output_directory)
