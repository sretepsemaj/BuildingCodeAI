"""Script to process JSON files and extract metadata from all chapters."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = Path("/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai")
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = {
    "json": PLUMBING_CODE_DIR / "json",
    "json_processed": PLUMBING_CODE_DIR / "json_processed",
    "tables": PLUMBING_CODE_DIR / "tables",
    "analytics": PLUMBING_CODE_DIR / "analytics",
}


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

        if not data or not data.get("f"):
            logger.warning("No data found in input file")
            return

        # Get metadata from input
        metadata = data.get("m", {})
        chapter_num = metadata.get("c")
        chapter_title = metadata.get("ct", "")

        if not chapter_num:
            logger.error(f"Could not extract chapter info from {input_file}")
            return

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
            "tb": [],  # tables
        }

        # Process all files
        files = data.get("f", [])
        for file_entry in files:
            # Add file information
            optimized_data["f"].append(
                {
                    "i": file_entry["i"],
                    "p": file_entry["p"],
                    "o": file_entry["o"],
                    "pg": file_entry.get("pg", 0),
                }
            )

            # Add raw text
            text_content = file_entry.get("t", "")
            if text_content:
                optimized_data["r"].append({"i": file_entry["i"], "t": text_content})

            # Add table if exists
            if file_entry.get("tb"):
                table_entry = {
                    "i": file_entry["i"],
                    "t": file_entry["tb"],
                    "f": file_entry["i"],  # Reference to source file
                }
                if file_entry.get("tb_data"):
                    table_entry["d"] = str(
                        PLUMBING_CODE_DIRS["tables"] / Path(file_entry["tb_data"]).name
                    )
                if file_entry.get("tb_img"):
                    table_entry["img"] = str(
                        PLUMBING_CODE_DIRS["analytics"] / Path(file_entry["tb_img"]).name
                    )
                optimized_data["tb"].append(table_entry)

            # Process sections from text content
            sections = []
            current_section = None
            for line in text_content.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Check for section header (e.g., "308.5 Interval of support")
                section_match = re.match(r"^(\d+\.\d+(?:\.\d+)?)\s+(.+)$", line)
                if section_match:
                    if current_section:
                        sections.append(current_section)
                    section_id = section_match.group(1)
                    section_title = section_match.group(2)
                    current_section = {"i": section_id, "t": line, "c": "", "f": file_entry["i"]}
                elif current_section:
                    current_section["c"] += line + "\n"

            if current_section:
                sections.append(current_section)

            # Add processed sections
            optimized_data["s"].extend(sections)

        # Sort sections by ID numerically
        def section_key(section):
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
    try:
        os.makedirs(output_dir, exist_ok=True)

        for filename in os.listdir(input_dir):
            if filename.endswith(".json"):
                input_file = os.path.join(input_dir, filename)
                output_file = os.path.join(output_dir, filename)
                process_json_data(input_file, output_file)

    except Exception as e:
        logger.error(f"Error processing directory {input_dir}: {str(e)}")
        raise


if __name__ == "__main__":
    # Define input and output paths
    input_dir = str(PLUMBING_CODE_DIRS["json"])
    output_dir = str(PLUMBING_CODE_DIRS["json_processed"])

    # Process all files
    process_directory(input_dir, output_dir)
