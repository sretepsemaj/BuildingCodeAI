#!/usr/bin/env python3
"""Script to add table file paths to JSON files."""

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


def find_table_file(base_name: str, tables_dir: Path) -> Optional[Path]:
    """Find corresponding table file in tables directory."""
    chapter_match = re.match(r"NYCP(\d+)CH", base_name)
    if not chapter_match:
        return None

    chapter_num = chapter_match.group(1)
    pattern = f"NYCP{chapter_num}ch_*pg.csv"
    table_files = list(tables_dir.glob(pattern))

    return table_files[0] if table_files else None


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

        chapter_match = re.match(r"NYCP(\d+)CH", json_file.stem)
        if not chapter_match:
            logger.error("Invalid filename format: %s", json_file.name)
            return False

        chapter_num = chapter_match.group(1)

        # Extract chapter title from the first page's text
        chapter_title = "GENERAL REGULATIONS"  # Default title for Chapter 3
        if data.get("f"):
            # Sort pages by page number
            pages = sorted(data["f"], key=lambda x: x.get("i", 0))
            # Look for the title in each page until found
            for page in pages:
                if "t" in page:
                    title = extract_chapter_title(page["t"])
                    if title:
                        chapter_title = title
                        break

        output_data = {
            "m": {"c": chapter_num, "t": "NYCPC", "ct": chapter_title},
            "f": [],
            "s": [],
        }

        # Copy over file entries with their p field
        for file_entry in data.get("f", []):
            output_entry = {
                "i": file_entry.get("i"),
                "p": file_entry.get("p"),  # Copy over the p field
                "o": file_entry.get("o"),
                "t": file_entry.get("t"),
            }
            output_data["f"].append(output_entry)

        all_sections = []
        if "f" in data and isinstance(data["f"], list):
            for file_entry in data["f"]:
                if isinstance(file_entry, dict):
                    optimizer_path = Path(file_entry.get("o", ""))
                    base_name = optimizer_path.stem.split("_")[0]
                    table_file = find_table_file(base_name, tables_dir)

                    new_entry = {
                        "i": file_entry.get("i", 1),  # Page number from file entry
                        "p": str(table_file) if table_file else None,
                        "o": file_entry.get("o", ""),
                        "t": file_entry.get("t", ""),
                    }
                    output_data["f"].append(new_entry)

                    # Extract sections from text content with file entry context
                    sections = extract_sections(file_entry.get("t", ""), file_entry)
                    all_sections.extend(sections)

        # Sort sections by their identifiers
        all_sections.sort(key=lambda x: [int(n) for n in x["i"].split(".")])

        # Structure the sections properly
        if "s" in data:
            output_data["s"] = {
                "d": data["s"].get("d", []),
                "t": data["s"].get("t", []),
                "sections": all_sections,
            }
        else:
            output_data["s"] = {"d": [], "t": [], "sections": all_sections}

        processed_dir = settings.PLUMBING_CODE_PATHS["json_processed"]
        processed_file = processed_dir / json_file.name

        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info("Saved processed JSON file to: %s", processed_file)

        return True

    except Exception as e:
        logger.error("Error processing JSON file %s: %s", json_file, str(e))
        return False


def main() -> bool:
    """Process all JSON files and update with table information."""
    try:
        logger.info("=" * 50)
        logger.info("Starting JSON washing process")

        json_dir = Path(settings.PLUMBING_CODE_PATHS["json"])
        tables_dir = Path(settings.PLUMBING_CODE_PATHS["tables"])

        logger.info("JSON directory: %s", json_dir)
        logger.info("Tables directory: %s", tables_dir)

        json_files = list(json_dir.glob("NYCP*CH_.json"))
        logger.info("Found %s JSON files to process", len(json_files))

        successful = 0
        failed = 0

        for json_file in json_files:
            if process_json_file(json_file, tables_dir):
                successful += 1
            else:
                failed += 1

        logger.info("JSON washing complete")
        logger.info("Successfully processed: %s", successful)
        logger.info("Failed to process: %s", failed)
        logger.info("=" * 50)

        return successful > 0 or len(json_files) == 0

    except Exception as e:
        logger.error("Error in main process: %s", str(e))
        return False


if __name__ == "__main__":
    main()
