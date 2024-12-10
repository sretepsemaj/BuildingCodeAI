#!/usr/bin/env python3
"""Script to add table file paths to JSON files."""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

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
    table_file = tables_dir / f"{base_name}.csv"
    if table_file.exists():
        return table_file
    return None


def process_json_file(json_file: Path, tables_dir: Path) -> bool:
    """Process a single JSON file and update with table information."""
    try:
        logger.info("Processing JSON file: %s", json_file)

        # Read the JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Process each file entry if "f" exists
        if "f" in data and isinstance(data["f"], list):
            for file_entry in data["f"]:
                if isinstance(file_entry, dict) and "o" in file_entry:
                    # Get the optimizer file path and base name
                    optimizer_path = Path(file_entry["o"])
                    # Get base name without _pg suffix
                    base_name = optimizer_path.stem.split("_")[0]

                    # Look for corresponding table file
                    table_file = find_table_file(base_name, tables_dir)

                    # Set p field to table path or null
                    file_entry["p"] = str(table_file) if table_file else None
                    if table_file:
                        logger.info("Found table file for %s: %s", base_name, table_file)
                    else:
                        logger.debug("No table file found for %s", base_name)

        # Save to json_processed directory
        processed_dir = settings.PLUMBING_CODE_PATHS["json_processed"]
        processed_file = processed_dir / json_file.name

        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
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

        # Get paths from Django settings
        json_dir = Path(settings.PLUMBING_CODE_PATHS["json"])
        tables_dir = Path(settings.PLUMBING_CODE_PATHS["tables"])

        logger.info("JSON directory: %s", json_dir)
        logger.info("Tables directory: %s", tables_dir)

        # Get list of JSON files to process
        json_files = list(json_dir.glob("NYCP*CH_.json"))
        logger.info("Found %s JSON files to process", len(json_files))

        successful = 0
        failed = 0

        # Process each JSON file
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
    # Specific input and output files
    input_file = (
        "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/media/plumbing_code/json/NYCP1CH_.json"
    )
    output_file = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/media/plumbing_code/json_processed/NYCP1CH_.json"

    try:
        # Read input JSON
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Create the output JSON structure
        output_data = {"m": {"c": "1", "t": "NYCPC", "ct": "ADMINISTRATION"}, "f": [], "s": []}

        # Process each file entry if it exists
        if "f" in data and isinstance(data["f"], list):
            output_data["f"] = [
                {
                    "i": entry.get("i"),
                    "p": None,  # Set p to null
                    "o": entry.get("o"),
                    "pg": entry.get("pg"),
                    "t": entry.get("t", ""),
                }
                for entry in data["f"]
            ]

            # Extract sections from text content
            for entry in output_data["f"]:
                text = entry.get("t", "")
                lines = text.split("\n")
                current_section = None
                current_content = []

                for line in lines:
                    # Look for section headers like "101.1 Title."
                    section_match = re.match(
                        r"^(?:SECTION PC )?(\d+(?:\.\d+)?)\s+" r"([^.]+)\.?(.*)$",
                        line.strip(),
                    )
                    if section_match:
                        # If we have a previous section, save it
                        if current_section:
                            current_section["c"] = "\n".join(current_content).strip()
                            output_data["s"].append(current_section)
                            current_content = []

                        # Start new section
                        section_num = section_match.group(1)
                        section_title = section_match.group(2).strip()
                        first_content = section_match.group(3).strip()

                        current_section = {
                            "i": section_num,
                            "t": section_title,
                            "f": entry.get("pg", 1),
                        }
                        if first_content:
                            current_content.append(first_content)
                    elif current_section and line.strip():
                        current_content.append(line.strip())

                # Save the last section
                if current_section:
                    current_section["c"] = "\n".join(current_content).strip()
                    output_data["s"].append(current_section)

        # Add sections after files
        # Copy over any existing definitions and terms
        if "s" in data:
            if "d" in data["s"]:
                output_data["s"] = {
                    "d": data["s"]["d"],
                    "t": data["s"]["t"] if "t" in data["s"] else [],
                    "sections": output_data["s"],
                }
            else:
                output_data["s"] = {
                    "d": [],
                    "t": data["s"]["t"] if "t" in data["s"] else [],
                    "sections": output_data["s"],
                }

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Write the processed JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        msg = "Successfully processed %s and saved to %s"
        logger.info(msg, input_file, output_file)

    except Exception as e:
        logger.error("Error processing file: %s", str(e))
