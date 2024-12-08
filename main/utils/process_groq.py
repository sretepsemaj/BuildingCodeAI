"""Script to process images in JSON files using Groq API."""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to the Python path
root_path = str(Path(__file__).parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

import django  # noqa: E402
from django.conf import settings  # noqa: E402

# Initialize Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from config.settings.base import BASE_DIR, MEDIA_ROOT, PLUMBING_CODE_DIR  # noqa: E402
from main.utils.image_groq import GroqImageProcessor  # noqa: E402

# Set up logging
logger = logging.getLogger("main.utils.process_groq")


# Define additional paths
JSON_PROCESSED_DIR = PLUMBING_CODE_DIR / "json_processed"
JSON_FINAL_DIR = PLUMBING_CODE_DIR / "json_final"


def process_json_file(json_path: str) -> None:
    """Process a JSON file and add Groq analysis results.

    Args:
        json_path: Path to the JSON file to process
    """
    logger.info(f"Starting to process JSON file: {json_path}")
    try:
        # Read the JSON file
        logger.debug(f"Reading JSON file: {json_path}")
        with open(json_path, "r") as f:
            data = json.load(f)

        # Initialize Groq processor
        logger.debug("Initializing Groq processor")
        processor = GroqImageProcessor()

        # Track if any changes were made
        changes_made = False
        has_valid_fields = False

        # Process fields at root level
        logger.debug("Processing fields at root level")
        for field in data.get("f", []):
            # Only process fields that have a CSV file (p is not null)
            if not field.get("p"):
                continue

            has_valid_fields = True
            logger.debug(f"Processing field with path: {field.get('p')}")

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

        # Get the output path
        output_path = (
            str(json_path)
            .replace("/json_processed/", "/json_final/")
            .replace(".json", "_groq.json")
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if changes_made:
            # Save the updated JSON with changes
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully saved results to {output_path}")
        elif not has_valid_fields:
            # If no valid fields were found, just copy the original file
            shutil.copy2(json_path, output_path)
            logger.info(f"No valid fields found, copied original file to {output_path}")
        else:
            # If there were valid fields but no changes made, still save the file
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"No changes made, saved original data to {output_path}")

    except Exception as e:
        logger.error(f"Error processing JSON file {json_path}: {str(e)}")
        raise


def process_all_json_files() -> None:
    """Process all JSON files in the processed directory."""
    logger.info(f"Starting to process all JSON files in: {JSON_PROCESSED_DIR}")

    # Create final directory if it doesn't exist
    if not JSON_FINAL_DIR.exists():
        logger.debug(f"Creating final directory: {JSON_FINAL_DIR}")
        JSON_FINAL_DIR.mkdir(parents=True, exist_ok=True)

    # Get list of JSON files
    json_files = list(JSON_PROCESSED_DIR.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files to process")

    # Process each file
    for json_path in json_files:
        try:
            logger.debug(f"Processing file: {json_path}")
            process_json_file(str(json_path))
        except Exception as e:
            logger.error(f"Error processing {json_path}: {str(e)}", exc_info=True)

    logger.info("Finished processing all JSON files")


def main() -> None:
    """Main function to process all JSON files."""
    logger.info("Starting Groq processing")
    try:
        process_all_json_files()
        logger.info("Groq processing completed successfully")
    except Exception as e:
        logger.error(f"Fatal error in Groq processing: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
