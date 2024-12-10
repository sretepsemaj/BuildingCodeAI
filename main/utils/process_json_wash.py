#!/usr/bin/env python3
"""Script to add table file paths to JSON files."""

import json
import logging
import os
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
        logger.info(f"Processing JSON file: {json_file}")

        # Read the JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        modified = False

        # Process each file entry
        for file_entry in data.get("f", []):
            # Get the OCR file path and base name
            ocr_path = Path(file_entry["p"]) if file_entry.get("p") else None
            if ocr_path:
                base_name = ocr_path.stem

                # Look for corresponding table file
                table_file = find_table_file(base_name, tables_dir)

                if table_file:
                    logger.info(f"Found table file for {base_name}: {table_file}")
                    file_entry["p"] = str(table_file)
                    modified = True
                else:
                    logger.debug(f"No table file found for {base_name}")

        if modified:
            # Save updated JSON
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Updated JSON file: {json_file}")
            return True

        logger.info(f"No changes needed for: {json_file}")
        return True

    except Exception as e:
        logger.error(f"Error processing JSON file {json_file}: {str(e)}")
        return False


def main() -> bool:
    """Process all JSON files and update with table information."""
    try:
        logger.info("=" * 50)
        logger.info("Starting JSON washing process")

        # Get paths from Django settings
        json_dir = Path(settings.PLUMBING_CODE_PATHS["json"])
        tables_dir = Path(settings.PLUMBING_CODE_PATHS["tables"])

        logger.info(f"JSON directory: {json_dir}")
        logger.info(f"Tables directory: {tables_dir}")

        # Get list of JSON files to process
        json_files = list(json_dir.glob("NYCP*CH_.json"))
        logger.info(f"Found {len(json_files)} JSON files to process")

        successful = 0
        failed = 0

        # Process each JSON file
        for json_file in json_files:
            if process_json_file(json_file, tables_dir):
                successful += 1
            else:
                failed += 1

        logger.info("JSON washing complete")
        logger.info(f"Successfully processed: {successful}")
        logger.info(f"Failed to process: {failed}")
        logger.info("=" * 50)

        return successful > 0 or len(json_files) == 0

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return False


if __name__ == "__main__":
    main()
