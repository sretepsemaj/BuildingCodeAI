"""Script to process images in JSON files using Groq API."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from image_groq import GroqImageProcessor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = Path("/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai")
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
JSON_PROCESSED_DIR = PLUMBING_CODE_DIR / "json_processed"


def process_json_file(json_path: str) -> None:
    """Process a JSON file and add Groq analysis results.

    Args:
        json_path: Path to the JSON file to process
    """
    try:
        # Read the JSON file
        with open(json_path, "r") as f:
            data = json.load(f)

        # Initialize Groq processor
        processor = GroqImageProcessor()

        # Process each chapter
        for chapter_key, chapter_data in data.items():
            if "tb" not in chapter_data:
                continue

            # Process each table entry
            for table in chapter_data["tb"]:
                if "io" not in table:
                    continue

                image_path = table["io"]
                logger.info(f"Processing image: {image_path}")

                try:
                    # Process the image with Groq
                    result = processor.process_image(image_path)

                    # Add the analysis result to the table entry
                    if result and "choices" in result and result["choices"]:
                        analysis = result["choices"][0]["message"]["content"]
                        table["tg"] = analysis
                        logger.info(f"Successfully processed image for page {table['i']}")
                    else:
                        logger.warning(f"No analysis result for image on page {table['i']}")

                except Exception as e:
                    logger.error(f"Error processing image {image_path}: {str(e)}")
                    continue

        # Save the updated JSON
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Successfully updated {json_path} with Groq analysis results")

    except Exception as e:
        logger.error(f"Error processing JSON file {json_path}: {str(e)}")
        raise


def process_all_json_files() -> None:
    """Process all JSON files in the processed directory."""
    try:
        # Process each JSON file
        for json_file in JSON_PROCESSED_DIR.glob("*.json"):
            logger.info(f"Processing {json_file}")
            process_json_file(str(json_file))

    except Exception as e:
        logger.error(f"Error processing JSON files: {str(e)}")
        raise


def main() -> None:
    """Main function to process all JSON files."""
    try:
        process_all_json_files()
        logger.info("Successfully processed all JSON files")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
