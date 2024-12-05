#!/usr/bin/env python3
"""Process images by running the image optimizer."""

import logging
from pathlib import Path

from . import images_optimizer

# Configure logger
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the image optimization process."""
    try:
        logger.info("=" * 50)
        logger.info("Starting image processing")

        # Run the optimizer
        images_optimizer.main()

        logger.info("Image processing complete")
        logger.info("=" * 50)
    except Exception as e:
        logger.error(f"Error in image processing: {str(e)}", exc_info=True)
        logger.info("=" * 50)


if __name__ == "__main__":
    main()
