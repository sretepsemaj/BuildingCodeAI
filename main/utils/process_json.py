"""Script to process text files and tables into JSON format."""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import django
from django.conf import settings

# Add the project root to the Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Set up logging
logger = logging.getLogger("main.utils.process_json")

# Ensure we have a console handler if running standalone
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

# Use paths from Django settings
PLUMBING_CODE_PATHS = settings.PLUMBING_CODE_PATHS


def read_table_data(table_path: str) -> Optional[Dict]:
    """Read table data from a file."""
    try:
        if not os.path.exists(table_path):
            logger.warning(f"Table file not found: {table_path}")
            return None

        with open(table_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading table data from {table_path}: {str(e)}", exc_info=True)
        return None


def process_file(input_file: str, output_dir: str) -> None:
    """Process a single text file and save as JSON."""
    try:
        logger.info(f"Processing file: {input_file}")

        # Read the text file
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()
        logger.debug(f"Successfully read file: {input_file}")

        # Process the text into sections
        sections = text.split("\n\n")
        processed_data = {
            "sections": sections,
            "metadata": {
                "source_file": os.path.basename(input_file),
                "section_count": len(sections),
            },
        }
        logger.debug(f"Processed {len(sections)} sections")

        # Create output filename
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_dir, f"{base_name}.json")

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2)

        logger.info(f"Saved processed data to {output_file}")

    except Exception as e:
        logger.error(f"Error processing file {input_file}: {str(e)}", exc_info=True)
        raise


def main():
    """Process all text files and convert to JSON format."""
    logger.info("Starting JSON processing")

    # Use OCR directory for input files since that's where the OCR output is stored
    input_dir = str(PLUMBING_CODE_PATHS["ocr"])
    output_dir = str(PLUMBING_CODE_PATHS["json"])

    logger.info(f"Processing files from: {input_dir}")
    logger.info(f"Output directory: {output_dir}")

    successful = 0
    failed = 0

    try:
        for filename in os.listdir(input_dir):
            if filename.endswith(".txt"):  # Only process text files
                input_file = os.path.join(input_dir, filename)
                try:
                    process_file(input_file, output_dir)
                    successful += 1
                except Exception as e:
                    logger.error(f"Error processing {filename}: {e}")
                    failed += 1
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise

    logger.info(f"Processing complete. Successful: {successful}, Failed: {failed}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("Fatal error in JSON processing", exc_info=True)
        raise
