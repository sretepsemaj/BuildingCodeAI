#!/usr/bin/env python3
"""Script to process text files and tables into JSON format."""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the project root to the Python path before importing Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Django imports
import django  # noqa: E402
from django.conf import settings  # noqa: E402

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Configure logger
logger = logging.getLogger("main.utils.process_json")

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Add file handler if not already present
if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
    log_file = LOGS_DIR / "process_json.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter(
            "{levelname} {asctime} {module} {process:d} {thread:d} {message}", style="{"
        )
    )
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)


def read_table_data(table_path: Path) -> Optional[Dict]:
    """Read table data from a file."""
    try:
        if not table_path.exists():
            logger.warning(f"Table file not found: {table_path}")
            return None

        logger.info(f"Reading table data from: {table_path}")
        with open(table_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Successfully loaded table data from {table_path}")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in table file {table_path}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error reading table file {table_path}: {str(e)}")
        return None


def process_file(input_file: Path, output_dir: Path) -> bool:
    """Process a single text file and save as JSON."""
    try:
        logger.info(f"Processing file: {input_file}")

        # Read the input file
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract filename without extension
        base_name = input_file.stem

        # Look for associated table file
        table_path = Path(str(input_file).replace(".txt", "_table.json"))
        table_data = read_table_data(table_path) if table_path.exists() else None

        # Create JSON structure
        data = {
            "filename": input_file.name,
            "content": content,
            "tables": table_data,
            "metadata": {
                "processed_date": datetime.now().isoformat(),
                "version": "1.0",
            },
        }

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        output_file = output_dir / f"{base_name}.json"
        logger.info(f"Saving JSON to: {output_file}")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully processed: {input_file.name}")
        return True

    except Exception as e:
        logger.error(f"Error processing file {input_file}: {str(e)}")
        return False


def main() -> bool:
    """Process all text files and convert to JSON format."""
    try:
        logger.info("=" * 50)
        logger.info("Starting JSON processing")

        # Get paths from Django settings
        ocr_dir = Path(settings.PLUMBING_CODE_PATHS["ocr"])
        json_dir = Path(settings.PLUMBING_CODE_PATHS["json"])

        # Create output directory if it doesn't exist
        json_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Input directory: {ocr_dir}")
        logger.info(f"Output directory: {json_dir}")

        # Get list of text files to process
        text_files = list(ocr_dir.glob("*.txt"))
        logger.info(f"Found {len(text_files)} text files to process")

        successful = 0
        failed = 0

        # Process each file
        for text_file in text_files:
            if process_file(text_file, json_dir):
                successful += 1
            else:
                failed += 1

        logger.info("JSON processing complete")
        logger.info(f"Successfully processed: {successful}")
        logger.info(f"Failed to process: {failed}")
        logger.info("=" * 50)

        return successful > 0 or len(text_files) == 0

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return False


if __name__ == "__main__":
    main()
