#!/usr/bin/env python3
"""Process images by running the image optimizer."""

import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path before importing Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Django imports
import django  # noqa: E402

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Local imports
from main.utils import images_optimizer  # noqa: E402

# Configure logger
logger = logging.getLogger("main.utils.process_image")


def main() -> None:
    """Run the image optimization process."""
    try:
        logger.info("=" * 50)
        logger.info("Starting image processing")

        # Run the optimizer
        images_optimizer.main()

        logger.info("Image processing complete")
        logger.info("=" * 50)
        return True  # Return True on success for process_start.py

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        return False  # Return False on failure for process_start.py


if __name__ == "__main__":
    main()
