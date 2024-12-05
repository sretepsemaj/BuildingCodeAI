"""Script to process text files and tables into optimized JSON format."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = Path("/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai")
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = {
    "ocr": PLUMBING_CODE_DIR / "OCR",
    "json": PLUMBING_CODE_DIR / "json",
    "json_final": PLUMBING_CODE_DIR / "json_final",
    "json_processed": PLUMBING_CODE_DIR / "json_processed",
    "tables": PLUMBING_CODE_DIR / "tables",
    "analytics": PLUMBING_CODE_DIR / "analytics",
    "optimized": PLUMBING_CODE_DIR / "optimized",
    "uploads": PLUMBING_CODE_DIR / "uploads",
}


def read_table_data(table_path: str) -> Optional[Dict]:
    """Read and parse table data from file."""
    try:
        if not os.path.exists(table_path):
            return None

        with open(table_path, "r", encoding="utf-8") as f:
            table_content = f.read()

        return {
            "table_content": table_content,
            "table_path": table_path,
        }
    except Exception as e:
        logger.error(f"Error reading table data from {table_path}: {str(e)}")
        return None


def process_file(text_path: str) -> Dict:
    """Process a single text file and its associated table data."""
    try:
        # Read OCR text
        with open(text_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        # Get filename without extension
        filename = Path(text_path).stem

        # Extract page number from filename (e.g., NYCP1ch_9pg.txt -> 9)
        try:
            pg_num = int("".join(filter(str.isdigit, filename.split("_")[-1])))
        except (IndexError, ValueError):
            pg_num = 0
            logger.warning(f"Could not extract page number from filename: {filename}")

        # Check for associated table files
        table_file = PLUMBING_CODE_DIRS["tables"] / f"{filename}.txt"
        analytics_file = PLUMBING_CODE_DIRS["analytics"] / f"{filename}.png"

        table_data = None
        if table_file.exists():
            table_data = read_table_data(str(table_file))

        # Create optimized file entry
        file_entry = {
            "i": pg_num,
            "p": str(text_path),
            "o": str(PLUMBING_CODE_DIRS["original"] / f"{filename}.jpg"),
            "pg": pg_num,
            "t": text_content,
        }

        if table_data:
            file_entry["tb"] = table_data["table_content"]
            file_entry["tb_data"] = str(table_file)
        if analytics_file.exists():
            file_entry["tb_img"] = str(analytics_file)

        return file_entry

    except Exception as e:
        logger.error(f"Error processing file {text_path}: {str(e)}")
        raise


def process_directory(base_dir: str) -> Dict[str, Dict]:
    """Process all text files in the OCR directory."""
    try:
        processed_data = {}

        # Process each text file in the OCR directory
        for file_path in PLUMBING_CODE_DIRS["ocr"].glob("*.txt"):
            try:
                # Extract chapter number from filename (e.g., NYCP1CH -> 1)
                chapter_match = re.search(r"NYCP(\d+)CH", file_path.stem, re.IGNORECASE)
                if not chapter_match:
                    logger.warning(
                        f"Could not extract chapter number from filename: {file_path.name}"
                    )
                    continue

                chapter_num = chapter_match.group(1)
                chapter_key = f"NYCP{chapter_num}CH"

                # Initialize chapter data if not exists
                if chapter_key not in processed_data:
                    processed_data[chapter_key] = {
                        "m": {
                            "c": chapter_num,
                            "t": "NYCPC",
                            "ct": "",  # Will be filled from content
                        },
                        "f": [],
                        "r": [],
                        "s": [],
                        "tb": [],
                    }

                # Process the file
                file_entry = process_file(str(file_path))
                processed_data[chapter_key]["f"].append(file_entry)

                # Add raw text
                if "t" in file_entry:
                    processed_data[chapter_key]["r"].append(
                        {"i": file_entry["i"], "t": file_entry["t"]}
                    )

                # Add table if exists
                if "tb" in file_entry:
                    table_entry = {
                        "i": file_entry["i"],
                        "t": file_entry["tb"],
                        "f": file_entry["i"],
                    }
                    if "tb_data" in file_entry:
                        table_entry["d"] = file_entry["tb_data"]
                    if "tb_img" in file_entry:
                        table_entry["img"] = file_entry["tb_img"]
                    processed_data[chapter_key]["tb"].append(table_entry)

                # Process sections from text content
                if "t" in file_entry:
                    sections = []
                    current_section = None
                    for line in file_entry["t"].split("\n"):
                        line = line.strip()
                        if not line:
                            continue

                        # Check for section header (e.g., "308.5 Interval of support")
                        section_match = re.match(r"^(\d+\.\d+(?:\.\d+)?)\s+(.+)$", line)
                        if section_match:
                            if current_section:
                                sections.append(current_section)
                            section_id = section_match.group(1)
                            current_section = {
                                "i": section_id,
                                "t": line,
                                "c": "",
                                "f": file_entry["i"],
                            }
                        elif current_section:
                            current_section["c"] += line + "\n"

                    if current_section:
                        sections.append(current_section)

                    # Add processed sections
                    processed_data[chapter_key]["s"].extend(sections)

            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                continue

        # Sort sections by ID numerically
        for chapter_data in processed_data.values():

            def section_key(section):
                parts = section["i"].split(".")
                return tuple(float(p) for p in parts)

            chapter_data["s"].sort(key=section_key)

        return processed_data

    except Exception as e:
        logger.error(f"Error processing directory: {str(e)}")
        raise


def save_json(data: Dict[str, Dict], output_dir: str) -> None:
    """Save processed data to JSON files."""
    try:
        os.makedirs(output_dir, exist_ok=True)

        for filename, chapter_data in data.items():
            output_file = os.path.join(output_dir, f"{filename}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(chapter_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved processed data to {output_file}")

    except Exception as e:
        logger.error(f"Error saving JSON files: {str(e)}")
        raise


def main():
    """Process all files and create optimized JSON output."""
    try:
        # Process all files
        processed_data = process_directory(str(PLUMBING_CODE_DIR))

        # Save to JSON files
        save_json(processed_data, str(PLUMBING_CODE_DIRS["json_processed"]))

        logger.info("Successfully processed all files")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()
