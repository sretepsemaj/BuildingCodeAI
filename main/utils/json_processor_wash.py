"""Script to process JSON files and extract metadata from all chapters."""

import json
import logging
import os
import re
from typing import Any, Dict, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_chapter_info(filename: str, raw_text: str) -> tuple[str, str]:
    """Extract chapter number from filename and title from raw text."""
    # Look for chapter number in filename
    filename_pattern = r"NYCP(\d+)CH"
    match = re.search(filename_pattern, filename)
    if not match:
        return None, None

    chapter_num = match.group(1)

    # Get chapter title from first non-empty line
    text_lines = raw_text.split("\n")
    for line in text_lines:
        line = line.strip()
        if line and not line.startswith("$") and line.isupper():
            return chapter_num, line

    return chapter_num, None


def process_section(section_text: str, content: str) -> Dict[str, str]:
    """Process a section into id and text."""
    # Extract section ID (e.g., "312.5" from "312.5 Water supply system test")
    id_pattern = r"^(\d+\.\d+(?:\.\d+)?)"
    match = re.search(id_pattern, section_text)
    if match:
        section_id = match.group(1)
        # Get the title (everything after the ID)
        title = section_text[len(match.group(0)) :].strip()
        if title.startswith("."):
            title = title[1:].strip()

        # Combine section text and content, removing any section headers
        full_text = section_text
        if content:
            full_text += "\n" + content

        # Remove any "SECTION PC XXX" headers from the text
        full_text = re.sub(r"SECTION PC \d+\n[A-Z\s]+\n+", "", full_text)

        return {"i": section_id, "t": full_text.strip()}  # id  # text
    else:
        # Handle special cases like numbered lists
        return None


def get_ocr_path(file_path: str, base_path: str) -> str:
    """Generate corresponding OCR image path from text file path."""
    # Extract chapter and page info from file path
    path_pattern = r"NYCP(\d+)ch_(\d+)pg\.txt$"
    match = re.search(path_pattern, file_path)
    if match:
        chapter_num = match.group(1)
        page_num = match.group(2)
        ocr_path = os.path.join(
            base_path, "optimized", "OCR", f"NYCP{chapter_num}ch_{page_num}pg.jpg"
        )
        return ocr_path
    return None


def process_json_data(input_file: str, output_file: str) -> None:
    """Process JSON data to create optimized format."""
    try:
        # Load input data
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            logger.warning("No data found in input file")
            return

        # Get chapter info from first document's raw text
        first_doc = data[0]
        chapter_num, chapter_title = extract_chapter_info(input_file, first_doc["raw_text"])

        if not chapter_num:
            logger.error(f"Could not extract chapter info from {input_file}")
            return

        if not chapter_title:
            # Use first line of raw text as chapter title
            chapter_title = first_doc["raw_text"].split("\n")[0].strip()

        # Create new optimized structure
        optimized_data = {
            "m": {  # metadata
                "c": chapter_num,  # chapter
                "t": "NYCPC",  # title
                "ct": chapter_title,  # chapter title
            },
            "f": [],  # files
            "r": [],  # raw text
            "s": [],  # sections
        }

        # Get base path for OCR images
        base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"

        # Process all documents
        for idx, doc in enumerate(data):
            # Add file path and OCR path
            file_path = doc.get("file_path")
            if file_path:
                file_entry = {
                    "i": idx,  # index
                    "p": file_path,  # text path
                }

                # Add OCR path if available
                ocr_path = get_ocr_path(file_path, base_path)
                if ocr_path:
                    file_entry["o"] = ocr_path  # OCR image path

                optimized_data["f"].append(file_entry)

            # Add raw text
            raw_text = doc.get("raw_text")
            if raw_text:
                optimized_data["r"].append({"i": idx, "t": raw_text})  # index  # text

            # Process sections
            for section in doc.get("sections", []):
                processed_section = process_section(section["section"], section["content"])
                if processed_section:  # Only add valid sections
                    processed_section["f"] = idx  # Add file index reference
                    optimized_data["s"].append(processed_section)

        # Sort sections by ID numerically
        def section_key(section):
            # Split the ID into parts and convert to float for proper numerical sorting
            parts = section["i"].split(".")
            return tuple(float(p) for p in parts)

        optimized_data["s"].sort(key=section_key)

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(optimized_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully processed {input_file} and saved to {output_file}")

    except Exception as e:
        logger.error(f"Error processing {input_file}: {str(e)}")
        raise


def process_directory(input_dir: str, output_dir: str) -> None:
    """Process all JSON files in a directory."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Process each JSON file
    for root, _, files in os.walk(input_dir):
        for filename in files:
            if filename.endswith(".json"):
                input_file = os.path.join(root, filename)
                # Keep the same relative path structure in output directory
                rel_path = os.path.relpath(root, input_dir)
                output_subdir = os.path.join(output_dir, rel_path)
                os.makedirs(output_subdir, exist_ok=True)
                output_file = os.path.join(output_subdir, filename)
                process_json_data(input_file, output_file)


if __name__ == "__main__":
    # Define input and output paths
    base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"
    input_dir = os.path.join(base_path, "json")
    output_dir = os.path.join(base_path, "json_processed")

    # Process all files
    process_directory(input_dir, output_dir)
