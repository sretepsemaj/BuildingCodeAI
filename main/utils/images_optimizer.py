#!/usr/bin/env python3
"""Image optimizer for processing original images into optimized versions."""

import logging
import os
import sys
from pathlib import Path
from typing import Tuple

# Add the project root to the Python path before importing Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Django imports
import django  # noqa: E402
from django.conf import settings  # noqa: E402
from PIL import Image  # noqa: E402

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Configure logger
logger = logging.getLogger("main.utils.images_optimizer")

# Define paths
MEDIA_ROOT = Path(settings.MEDIA_ROOT)
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
ORIGINAL_DIR = PLUMBING_CODE_DIR / "original"
OPTIMIZED_DIR = PLUMBING_CODE_DIR / "optimizer"  # Changed from 'optimized' to 'optimizer'

# Image settings
THUMBNAIL_SIZE = (300, 300)  # Max dimensions for thumbnails
DOCUMENT_MAX_SIZE = (1920, 1080)  # Max dimensions for document view
JPEG_QUALITY = 85  # JPEG quality (1-100)
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
}  # Expanded format support


def create_dirs() -> None:
    """Create necessary directories if they don't exist."""
    logger.info("Creating necessary directories")
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Original directory: {ORIGINAL_DIR}")
    logger.info(f"Optimized directory: {OPTIMIZED_DIR}")


def optimize_image(image: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    """Resize and optimize an image while maintaining aspect ratio."""
    logger.debug(f"Original image size: {image.size}")

    # Calculate aspect ratio
    width_ratio = max_size[0] / image.size[0]
    height_ratio = max_size[1] / image.size[1]
    ratio = min(width_ratio, height_ratio)

    # Only resize if image is larger than max_size
    if ratio < 1:
        new_size = tuple(int(dim * ratio) for dim in image.size)
        logger.info(f"Resizing image from {image.size} to {new_size}")
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        logger.info("Image is already within size limits, no resizing needed")

    return image


def process_image(input_path: Path) -> None:
    """Process a single image file."""
    try:
        logger.info(f"Processing image: {input_path}")

        # Open and process image
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode == "RGBA":
                logger.info("Converting RGBA image to RGB")
                img = img.convert("RGB")

            # Optimize the image
            optimized = optimize_image(img, DOCUMENT_MAX_SIZE)

            # Prepare output path
            output_path = OPTIMIZED_DIR / f"{input_path.stem}.jpg"
            logger.info(f"Saving optimized image to: {output_path}")

            # Save optimized image
            optimized.save(output_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
            logger.info(f"Successfully optimized image: {input_path.name}")

    except Exception as e:
        logger.error(f"Error processing image {input_path}: {str(e)}")
        raise


def main() -> None:
    """Main function to process all images in the original directory."""
    try:
        logger.info("=" * 50)
        logger.info("Starting image optimization process")
        create_dirs()

        # Get list of images to process
        image_files = list(ORIGINAL_DIR.glob("*"))
        logger.info(f"Found {len(image_files)} images to process")

        successful = 0
        failed = 0

        # Process each image
        for image_path in image_files:
            if image_path.suffix.lower() in ALLOWED_EXTENSIONS:
                try:
                    process_image(image_path)
                    successful += 1
                except Exception as e:
                    logger.error(f"Failed to process {image_path}: {str(e)}")
                    failed += 1
            else:
                logger.info(f"Skipped non-image file: {image_path}")

        logger.info("Image optimization complete")
        logger.info(f"Successfully processed: {successful}")
        logger.info(f"Failed to process: {failed}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()
