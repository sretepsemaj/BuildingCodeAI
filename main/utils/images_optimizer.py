#!/usr/bin/env python3
"""Image optimizer for processing original images into optimized versions."""

import logging
from pathlib import Path
from typing import Tuple

from PIL import Image

# Configure logger
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = Path("/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai")
MEDIA_ROOT = BASE_DIR / "media"
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
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directory exists: {OPTIMIZED_DIR}")


def optimize_image(image: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    """Resize and optimize an image while maintaining aspect ratio."""
    try:
        # Convert to RGB if necessary
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Get original dimensions
        orig_width, orig_height = image.size

        # Calculate new dimensions maintaining aspect ratio
        width_ratio = max_size[0] / orig_width
        height_ratio = max_size[1] / orig_height
        ratio = min(width_ratio, height_ratio)

        if ratio < 1:  # Only resize if image is larger than target size
            new_size = (int(orig_width * ratio), int(orig_height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(
                f"Resized image from {orig_width}x{orig_height} to {new_size[0]}x{new_size[1]}"
            )
        else:
            logger.info(f"Image size {orig_width}x{orig_height} within limits, no resize needed")

        return image
    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        raise


def process_image(input_path: Path) -> None:
    """Process a single image file."""
    try:
        # Check if file extension is allowed
        if input_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            logger.warning(f"Skipping unsupported file type {input_path.suffix}: {input_path}")
            return

        logger.info(f"Processing image: {input_path}")

        # Open the image
        with Image.open(input_path) as img:
            # Log original image info
            logger.info(f"Original image: {input_path.name}, Mode: {img.mode}, Size: {img.size}")

            # Create optimized version for document viewing
            optimized = optimize_image(img, DOCUMENT_MAX_SIZE)

            # Save optimized version
            output_path = OPTIMIZED_DIR / f"{input_path.stem}.jpg"
            optimized.save(
                output_path,
                "JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,  # Makes images load progressively in web browsers
            )
            logger.info(f"Saved optimized image: {output_path}")

    except (IOError, OSError) as e:
        logger.error(f"File error processing {input_path}: {str(e)}")
    except Image.DecompressionBombError:
        logger.error(f"Image too large to process: {input_path}")
    except Exception as e:
        logger.error(f"Unexpected error processing {input_path}: {str(e)}")


def main() -> None:
    """Main function to process all images in the original directory."""
    try:
        logger.info("Starting image optimization process")
        create_dirs()

        # Process all images in original directory
        files_processed = 0
        files_skipped = 0

        for file_path in ORIGINAL_DIR.glob("*"):
            if file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                process_image(file_path)
                files_processed += 1
            else:
                files_skipped += 1
                logger.info(f"Skipped non-image file: {file_path}")

        logger.info(
            f"Image optimization complete. Processed: {files_processed}, Skipped: {files_skipped}"
        )

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")


if __name__ == "__main__":
    main()
