"""Script to process images in JSON files using Groq API."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to the Python path
root_path = str(Path(__file__).parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from config.settings.base import BASE_DIR, MEDIA_ROOT, PLUMBING_CODE_DIR  # noqa: E402
from main.utils.image_groq import GroqImageProcessor  # noqa: E402

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define additional paths
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

        # Track if any changes were made
        changes_made = False

        # Process fields at root level
        for field in data.get("f", []):
            # Only process fields that have a CSV file (p is not null)
            if not field.get("p"):
                continue

            # Look for image path in 'o' field
            image_path = field.get("o", "")
            if not image_path or not image_path.endswith(".jpg"):
                continue

            # Check if image exists
            if not os.path.exists(image_path):
                logger.warning(f"Image not found: {image_path}")
                continue

            logger.info(f"Processing image for CSV file {field['p']}: {image_path}")

            try:
                # Process the image with Groq
                result = processor.process_image(image_path)

                if result and "error" not in result:
                    # Update the 't' field with Groq analysis
                    field["t"] = result.get("raw_response", "")
                    changes_made = True
                    logger.info(f"Successfully processed image: {image_path}")
                else:
                    logger.error(f"Error in Groq response for {image_path}: {result}")

            except Exception as e:
                logger.error(f"Error processing image {image_path}: {str(e)}")
                continue

        # Save the updated JSON if changes were made
        if changes_made:
            output_path = (
                str(json_path)
                .replace("/json_processed/", "/json_final/")
                .replace(".json", "_groq.json")
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully saved results to {output_path}")
        else:
            logger.info(f"No changes made to {json_path}")

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
            logger.info(f"Processing file: {json_file}")
            process_json_file(str(json_file))

    except Exception as e:
        logger.error(f"Error processing JSON files: {str(e)}")
        raise


def main() -> None:
    """Main function to process all JSON files."""
    process_all_json_files()


if __name__ == "__main__":
    main()
