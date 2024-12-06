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
JSON_FINAL_DIR = PLUMBING_CODE_DIR / "json_final"


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

        # Initialize output list
        output_data = []

        # Process table entries
        if "tb" in data:
            for table in data["tb"]:
                # Get page number and text
                page_num = table.get("i")
                text = table.get("t", "")

                # Get image and table paths
                table_path = table.get("t", "")
                image_path = table.get("io", "")

                # Convert image path to analytics path
                analytics_path = (
                    str(image_path).replace("/optimizer/", "/analytics/").replace(".jpg", ".png")
                )

                if os.path.exists(image_path):
                    logger.info(f"Processing image: {image_path}")

                    try:
                        # Process the image with Groq
                        result = processor.process_image(image_path)

                        # Create entry in output format
                        entry = {
                            "page_num": page_num,
                            "text": text,
                            "table_path": table_path,
                            "image_path": analytics_path,
                            "groq_result": {
                                "content": (
                                    result.get("raw_response", "")
                                    if result and "error" not in result
                                    else ""
                                )
                            },
                        }

                        output_data.append(entry)
                        logger.info(f"Successfully processed image: {image_path}")

                    except Exception as e:
                        logger.error(f"Error processing image {image_path}: {str(e)}")
                        continue
                else:
                    logger.warning(f"Image not found: {image_path}")

        # Save the output JSON
        output_path = (
            str(json_path)
            .replace("/json_processed/", "/json_final/")
            .replace(".json", "_groq.json")
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Successfully saved results to {output_path}")

    except Exception as e:
        logger.error(f"Error processing JSON file {json_path}: {str(e)}")
        raise


def process_all_json_files() -> None:
    """Process all JSON files in the processed directory."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(JSON_FINAL_DIR, exist_ok=True)

        # Process each JSON file
        for json_file in JSON_PROCESSED_DIR.glob("*.json"):
            logger.info(f"Processing {json_file}")
            process_json_file(str(json_file))

        logger.info("Successfully processed all JSON files")

    except Exception as e:
        logger.error(f"Error processing JSON files: {str(e)}")
        raise


def main():
    """Main function to process all JSON files."""
    process_all_json_files()


if __name__ == "__main__":
    main()
