"""Script to process text files and tables into JSON format."""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import django

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

# Define paths
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = {
    "ocr": PLUMBING_CODE_DIR / "OCR",
    "json": PLUMBING_CODE_DIR / "json",
    "tables": PLUMBING_CODE_DIR / "tables",
    "text": PLUMBING_CODE_DIR / "text",
    "uploads": PLUMBING_CODE_DIR / "uploads",
}


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
    try:
        logger.info("Starting JSON processing")

        # Setup directories
        text_dir = PLUMBING_CODE_DIRS["text"]
        json_dir = PLUMBING_CODE_DIRS["json"]
        os.makedirs(json_dir, exist_ok=True)

        logger.info(f"Processing files from: {text_dir}")
        logger.info(f"Output directory: {json_dir}")

        # Process each text file
        processed_count = 0
        error_count = 0
        for filename in os.listdir(text_dir):
            if filename.endswith(".txt"):
                input_file = os.path.join(text_dir, filename)
                try:
                    process_file(input_file, str(json_dir))
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process {filename}: {str(e)}")
                    error_count += 1
                    continue

        logger.info(f"Processing complete. Successful: {processed_count}, Failed: {error_count}")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("Fatal error in JSON processing", exc_info=True)
        raise
