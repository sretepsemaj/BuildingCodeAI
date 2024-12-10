#!/usr/bin/env python3
"""Script to process images using Groq AI and update JSON files."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Configure Django settings first
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django  # noqa: E402

django.setup()

# Import Django settings and other dependencies
from django.conf import settings  # noqa: E402

from main.utils.image_groq import GroqImageProcessor  # noqa: E402

# Configure logger after Django setup
logger = logging.getLogger("main.utils.process_groq")

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is required")

# Initialize Groq processor
groq_processor = GroqImageProcessor()


def analyze_image_with_groq(image_path: str) -> Optional[str]:
    """Analyze image using Groq AI API."""
    try:
        logger.info(f"Analyzing image: {image_path}")

        # Process the image using GroqImageProcessor
        result = groq_processor.process_image(image_path)
        if result:
            # Extract relevant information from the result
            analysis = result.get("analysis", "No analysis available")
            return analysis

        return None

    except Exception as e:
        logger.error(f"Error analyzing image {image_path}: {str(e)}")
        return None


def process_json_file(json_file: Path) -> bool:
    """Process a single JSON file and update with Groq analysis."""
    try:
        logger.info(f"Processing JSON file: {json_file}")

        # Read the JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        modified = False

        # Process each file entry
        for file_entry in data.get("f", []):
            # Skip entries without table path
            if not file_entry.get("p"):
                logger.debug(f"Skipping entry {file_entry.get('i')}: no table path")
                continue

            # Get the image path from 'o' field
            image_path = file_entry.get("o")
            if not image_path:
                logger.warning(f"No image path for entry {file_entry.get('i')}")
                continue

            # Check if image exists
            if not Path(image_path).exists():
                logger.warning(f"Image not found: {image_path}")
                continue

            # Analyze image with Groq
            analysis = analyze_image_with_groq(image_path)
            if analysis:
                # Update the text content
                file_entry["t"] = analysis
                modified = True
                logger.info(f"Updated entry {file_entry.get('i')} with Groq analysis")

        # Create output filename with _groq suffix in json_final directory
        output_dir = Path(settings.PLUMBING_CODE_PATHS["json_final"])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{json_file.stem}_groq.json"

        # Save the file (whether modified or not)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if modified:
            logger.info(f"Successfully saved results to {output_file}")
        else:
            logger.info(f"No changes needed, copied original file to {output_file}")

        return True

    except Exception as e:
        logger.error(f"Error processing JSON file {json_file}: {str(e)}")
        return False


def main() -> bool:
    """Process all JSON files with Groq analysis."""
    try:
        logger.info("=" * 50)
        logger.info("Starting Groq processing")

        # Get paths from Django settings
        json_dir = Path(settings.PLUMBING_CODE_PATHS["json_processed"])
        logger.info(f"JSON directory: {json_dir}")

        # Get list of JSON files to process
        json_files = list(json_dir.glob("NYCP*CH.json"))
        logger.info(f"Found {len(json_files)} JSON files to process")

        successful = 0
        failed = 0

        # Process each JSON file
        for json_file in json_files:
            if process_json_file(json_file):
                successful += 1
            else:
                failed += 1

        logger.info("Groq processing complete")
        logger.info(f"Successfully processed: {successful}")
        logger.info(f"Failed to process: {failed}")
        logger.info("=" * 50)

        return successful > 0 or len(json_files) == 0

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return False


if __name__ == "__main__":
    main()
