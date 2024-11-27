"""Base class for image processing."""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from django.conf import settings
from PIL import Image


class ImageProcessor(ABC):
    """Abstract base class for image processing."""

    def __init__(self):
        """Initialize the image processor."""
        pass

    @abstractmethod
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process a single image.

        Args:
            image_path: Path to the image file.

        Returns:
            Dictionary containing the processing results.
        """
        pass

    @abstractmethod
    def process_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple images.

        Args:
            image_paths: List of paths to image files.

        Returns:
            List of dictionaries containing the processing results.
        """
        pass

    def resize_image(self, image_path: str, max_size: int = 800) -> str:
        """Resize an image if it's too large.

        Args:
            image_path: Path to the image file.
            max_size: Maximum dimension (width or height) for the image.

        Returns:
            Path to the resized image.
        """
        with Image.open(image_path) as img:
            # Convert image to RGB if it's not
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Check if resizing is needed
            width, height = img.size
            if width <= max_size and height <= max_size:
                return image_path

            # Calculate new dimensions
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))

            # Resize image
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save resized image
            output_dir = os.path.join(settings.MEDIA_ROOT, "resized")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, os.path.basename(image_path))
            resized.save(output_path, quality=95)

            return output_path
