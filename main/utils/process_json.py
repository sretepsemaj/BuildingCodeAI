"""Script to process text files into JSON format."""

import json
import logging
import os
import sys
from typing import Dict, List, Optional

from main.utils.json_processor import process_directory, save_json

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Process text files into JSON format."""
    try:
        # Set up input and output directories
        base_path = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"
        input_dir = os.path.join(base_path, "text")
        output_dir = os.path.join(base_path, "json")

        # Process files
        data = process_directory(input_dir)
        save_json(data, output_dir)

        # Log processing summary
        total_files = sum(len(files) for files in data.values())
        logger.info(f"Processed {total_files} files. Results saved to {output_dir}")

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
