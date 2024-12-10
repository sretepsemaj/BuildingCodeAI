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


def extract_chapter_info(filename: str) -> Tuple[str, str]:
    """Extract chapter number and type from filename."""
    match = re.match(r"NYCP(\d+)ch_.*", filename)
    if match:
        chapter = match.group(1)
        return chapter, "NYCPC"
    return "", ""


def find_matching_table(file_entry: Dict, tables_dir: Path) -> Optional[Path]:
    """Find matching table file for a given file entry."""
    # Get all table files in the directory
    table_files = list(tables_dir.glob("*.csv"))

    # Extract page number from the file entry
    page_num = file_entry.get("i", 1)

    # Try to find a matching table file
    for table_file in table_files:
        # Extract page number from table filename
        table_match = re.search(r"_(\d+)pg\.csv$", table_file.name)
        if table_match:
            table_page = int(table_match.group(1))
            if table_page == page_num:
                return table_file

    return None


def find_table_file(chapter_num: str, tables_dir: Path) -> Optional[Path]:
    """Find corresponding table file in tables directory."""
    pattern = f"NYCP{chapter_num}ch_*pg.csv"
    table_files = list(tables_dir.glob(pattern))
    return table_files[0] if table_files else None


def process_files(input_files: List[Path], output_dir: Path) -> bool:
    """Process multiple text files and save as single JSON."""
    try:
        if not input_files:
            logger.warning("No input files found")
            return False

        # Extract chapter info from first file
        chapter, doc_type = extract_chapter_info(input_files[0].name)

        # Get tables directory
        tables_dir = Path(settings.PLUMBING_CODE_PATHS["tables"])

        # Create files array
        files_data = []
        for i, input_file in enumerate(sorted(input_files), 1):
            try:
                logger.info(f"Processing file: {input_file}")

                # Read the input file
                with open(input_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract page number from filename
                page_match = re.search(r"_(\d+)pg\.txt$", input_file.name)
                page_num = int(page_match.group(1)) if page_match else i

                # Create optimizer path
                optimizer_path = (
                    str(input_file).replace("/OCR/", "/optimizer/").replace(".txt", ".jpg")
                )

                # Create initial file entry
                file_data = {
                    "i": page_num,
                    "o": optimizer_path,
                    "t": content,
                }

                # Find matching table file
                table_file = find_matching_table(file_data, tables_dir)
                file_data["p"] = str(table_file) if table_file else None

                files_data.append(file_data)
                logger.info(f"Successfully processed: {input_file.name}")
                if table_file:
                    logger.info(f"Found matching table file: {table_file.name}")
                else:
                    logger.info("No matching table file found")

            except Exception as e:
                logger.error(f"Error processing file {input_file}: {str(e)}")
                continue

        # Create final JSON structure
        data = {"m": {"c": chapter, "t": doc_type, "ct": ""}, "f": files_data}

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save as JSON
        output_file = output_dir / f"NYCP{chapter}CH_.json"
        logger.info(f"Saving JSON to: {output_file}")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        logger.error(f"Error in process_files: {str(e)}")
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

        # Group files by chapter
        files_by_chapter = {}
        for file in text_files:
            chapter, _ = extract_chapter_info(file.name)
            if chapter:
                if chapter not in files_by_chapter:
                    files_by_chapter[chapter] = []
                files_by_chapter[chapter].append(file)

        successful = 0
        failed = 0

        # Process each chapter's files
        for chapter_files in files_by_chapter.values():
            if process_files(chapter_files, json_dir):
                successful += 1
            else:
                failed += 1

        logger.info("JSON processing complete")
        logger.info(f"Successfully processed chapters: {successful}")
        logger.info(f"Failed to process chapters: {failed}")
        logger.info("=" * 50)

        return successful > 0 or len(files_by_chapter) == 0

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return False


if __name__ == "__main__":
    main()
