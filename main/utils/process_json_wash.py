"""Script to process JSON files and extract metadata from all chapters."""

import json
import logging
import os

from json_processor_wash import process_directory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Process all JSON files in the directory."""
    try:
        # Define paths
        base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"
        input_dir = os.path.join(base_path, "json")
        output_dir = os.path.join(base_path, "optimized/json")

        # Process JSON files
        process_directory(input_dir, output_dir)

        logger.info(f"Successfully processed all JSON files in {input_dir}")

    except Exception as e:
        logger.error(f"Error processing JSON files: {str(e)}")
        raise


if __name__ == "__main__":
    main()
