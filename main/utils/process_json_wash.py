#!/usr/bin/env python3
"""Script to add table file paths to JSON files."""

import glob
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402

# Configure logger
logger = logging.getLogger("main.utils.process_json_wash")


def find_table_file(base_name: str, tables_dir: Path, page_num: int) -> Optional[str]:
    """Find corresponding table file in tables directory."""
    chapter_match = re.match(r"NYCP(\d+)CH", base_name)
    if not chapter_match:
        return None

    chapter_num = chapter_match.group(1)
    pattern = f"NYCP{chapter_num}ch_{page_num}pg.csv"

    # Convert to string paths for consistent handling
    tables_dir_str = str(tables_dir)
    table_path = os.path.join(tables_dir_str, pattern)

    # Check if file exists
    if os.path.exists(table_path):
        # Return relative path from media directory
        return os.path.join("media/plumbing_code/tables", pattern)
    return None


def extract_sections(text: str, file_entry: Dict[str, Any]) -> List[Dict]:
    """Extract sections from text content."""
    lines = text.split("\n")
    sections = []
    current_section = None
    current_content = []

    for line in lines:
        # Look for section headers like "101.1 Title." or "SECTION PC 101.1 Title"
        section_match = re.match(
            r"^(?:SECTION PC )?(\d+(?:\.\d+)?)\s+" r"([^.]+)\.?(.*)$",
            line.strip(),
        )
        if section_match:
            if current_section:
                current_section["c"] = "\n".join(current_content).strip()
                sections.append(current_section)
                current_content = []

            section_num = section_match.group(1)
            section_title = section_match.group(2).strip()
            first_content = section_match.group(3).strip()

            current_section = {
                "i": section_num,
                "t": section_title,
                "f": file_entry.get("i", 1),  # Use the page number from the file entry
                "o": file_entry.get("o", ""),  # Add original file reference
            }
            if first_content:
                current_content.append(first_content)
        elif current_section and line.strip():
            current_content.append(line.strip())

    if current_section:
        current_section["c"] = "\n".join(current_content).strip()
        sections.append(current_section)

    return sections


def extract_chapter_title(text: str) -> Optional[str]:
    """Extract chapter title from text content."""
    # Split into lines and clean them
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Find the chapter line
    chapter_line_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("CHAPTER"):
            chapter_line_idx = i
            break

    if chapter_line_idx >= 0:
        # Look for title in the next non-empty line
        for i in range(chapter_line_idx + 1, len(lines)):
            line = lines[i].strip()
            if line and not line.startswith("SECTION"):
                return line

    return None


def process_json_file(json_file: Path, tables_dir: Path) -> bool:
    """Process a single JSON file and update with table information."""
    try:
        logger.info("Processing JSON file: %s", json_file)

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        chapter_match = re.match(r"NYCP(\d+)CH", json_file.stem.replace("_", ""))
        if not chapter_match:
            logger.error("Invalid filename format: %s", json_file.name)
            return False

        chapter_num = chapter_match.group(1)

        # Initialize output structure with fixed metadata
        output_data = {
            "m": {"c": chapter_num, "t": "NYCPC", "ct": "GENERAL REGULATIONS"},
            "f": [],
            "s": [],  # Will be populated with sections
        }

        # Process files and extract sections
        if "f" in data and isinstance(data["f"], list):
            for file_entry in data["f"]:
                if isinstance(file_entry, dict):
                    # Get page number and find corresponding table file
                    page_num = file_entry.get("i")
                    base_name = f"NYCP{chapter_num}CH"
                    table_path = (
                        find_table_file(base_name, tables_dir, page_num) if page_num else None
                    )

                    # Copy file entry with all fields
                    output_entry = {
                        "i": page_num,
                        "p": table_path,  # Use found table path or None
                        "o": file_entry.get("o", ""),
                        "t": file_entry.get("t", ""),  # Keep the original text
                    }
                    output_data["f"].append(output_entry)

                    # Extract sections from this file's text
                    if "t" in file_entry:
                        sections = extract_sections(file_entry["t"], file_entry)
                        for section in sections:
                            section_entry = {
                                "i": section["i"],
                                "t": section["t"],
                                "f": file_entry.get("i", 1),
                                "o": file_entry.get("o", ""),
                                "c": section["c"],
                            }
                            output_data["s"].append(section_entry)

        # Sort sections by their identifiers
        output_data["s"].sort(key=lambda x: [int(n) for n in x["i"].split(".")])

        # Save to json_processed directory
        processed_dir = settings.PLUMBING_CODE_PATHS["json_processed"]
        os.makedirs(processed_dir, exist_ok=True)
        output_filename = f"NYCP{chapter_num}CH.json"
        processed_file = os.path.join(processed_dir, output_filename)

        logger.info(f"Saving processed JSON to: {processed_file}")
        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved processed JSON to: {processed_file}")

        return True

    except Exception as e:
        logger.error("Error processing JSON file %s: %s", json_file, str(e))
        return False


def main() -> bool:
    """Process all JSON files and update with table information."""
    try:
        logger.info("=" * 50)
        logger.info("Starting JSON washing process")

        # Get paths from Django settings
        json_dir = settings.PLUMBING_CODE_PATHS["json"]
        json_processed_dir = settings.PLUMBING_CODE_PATHS["json_processed"]
        tables_dir = settings.PLUMBING_CODE_PATHS["tables"]

        # Create output directory if it doesn't exist
        os.makedirs(json_processed_dir, exist_ok=True)

        logger.info("Input JSON directory: %s", json_dir)
        logger.info("Output JSON directory: %s", json_processed_dir)
        logger.info("Tables directory: %s", tables_dir)

        # Look for input files (with underscore)
        pattern = os.path.join(json_dir, "NYCP*CH_.json")
        json_files = glob.glob(pattern)
        logger.info("Found %s JSON files to process", len(json_files))

        successful = 0
        failed = 0

        # Process each JSON file
        for json_file in json_files:
            if process_json_file(Path(json_file), Path(tables_dir)):
                successful += 1
            else:
                failed += 1

        logger.info("Processing complete")
        logger.info(f"Successfully processed: {successful}")
        logger.info(f"Failed to process: {failed}")
        logger.info("=" * 50)

        return successful > 0

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return False


if __name__ == "__main__":
    main()
