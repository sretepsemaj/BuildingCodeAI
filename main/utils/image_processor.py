import base64
import logging
import os
import re
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any, Dict, List, Optional

import pytesseract
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageProcessorBase(ABC):
    """Abstract base class for image processing."""

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path

    @abstractmethod
    def process_image(self, image_path: str, new_filename: str) -> Dict[str, Any]:
        """Process a single image."""
        pass

    def validate_image(self, image_path: str) -> bool:
        """Validate if the file is a valid image."""
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception as e:
            logger.error(f"Invalid image file {image_path}: {str(e)}")
            return False


class OCRImageProcessor(ImageProcessorBase):
    """Processor for OCR-optimized images."""

    def __init__(self, input_path: str, output_path: str):
        super().__init__(input_path, output_path)
        os.makedirs(output_path, exist_ok=True)

    def process_image(self, image_path: str, new_filename: str) -> Dict[str, Any]:
        """Process image for OCR optimization."""
        if not self.validate_image(image_path):
            return {"success": False, "error": "Invalid image file"}

        try:
            # Open and process image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Enhance image for OCR
                processed = img.copy()
                # Resize if too large while maintaining aspect ratio
                if max(processed.size) > 2000:
                    processed.thumbnail((2000, 2000), Image.Resampling.LANCZOS)

                # Create output path with .jpg extension
                output_filename = os.path.join(self.output_path, f"{new_filename}.jpg")

                # Save processed image as JPG
                processed.save(output_filename, "JPEG", quality=95)

                return {
                    "success": True,
                    "output_path": output_filename,
                    "original_size": img.size,
                    "processed_size": processed.size,
                }

        except Exception as e:
            logger.error(f"Error processing image {image_path} for OCR: {str(e)}")
            return {"success": False, "error": str(e)}


class Base64ImageProcessor(ImageProcessorBase):
    """Processor for base64-optimized images."""

    def __init__(self, input_path: str, output_path: str, max_size: int = 800):
        super().__init__(input_path, output_path)
        self.max_size = max_size
        os.makedirs(output_path, exist_ok=True)

    def process_image(self, image_path: str, new_filename: str) -> Dict[str, Any]:
        """Process image for base64 optimization."""
        if not self.validate_image(image_path):
            return {"success": False, "error": "Invalid image file"}

        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize image while maintaining aspect ratio
                processed = img.copy()
                if max(processed.size) > self.max_size:
                    processed.thumbnail((self.max_size, self.max_size), Image.Resampling.LANCZOS)

                # Create output path with .jpg extension
                output_filename = os.path.join(self.output_path, f"{new_filename}.jpg")

                # Save processed image as JPG
                processed.save(output_filename, "JPEG", quality=85, optimize=True)

                # Generate base64 string
                buffered = BytesIO()
                processed.save(buffered, format="JPEG", quality=85, optimize=True)
                img_str = base64.b64encode(buffered.getvalue()).decode()

                return {
                    "success": True,
                    "output_path": output_filename,
                    "original_size": img.size,
                    "processed_size": processed.size,
                    "base64_length": len(img_str),
                }

        except Exception as e:
            logger.error(f"Error processing image {image_path} for base64: {str(e)}")
            return {"success": False, "error": str(e)}


class ImageProcessor:
    """Main image processor that handles both OCR and base64 optimization."""

    def __init__(self, input_dir: str, ocr_output_dir: str, base64_output_dir: str):
        self.input_dir = input_dir
        self.ocr_processor = OCRImageProcessor(input_dir, ocr_output_dir)
        self.base64_processor = Base64ImageProcessor(input_dir, base64_output_dir)

    def get_new_filename(self, original_filename: str) -> str:
        """Convert original filename to the new NYCP format."""
        # Remove file extension
        name_without_ext = os.path.splitext(original_filename)[0]

        # Extract chapter number and page info
        # Expected format: chapter_X_Xpage
        parts = name_without_ext.split("_")
        if len(parts) >= 3 and parts[0].lower() == "chapter":
            chapter_num = parts[1]
            # Extract just the number from 'Xpage'
            page_info = parts[2].lower().replace("page", "")
            # Create new filename in format NYCPXch_Xpg
            new_filename = f"NYCP{chapter_num}ch_{page_info}pg"
            return new_filename

        # If filename doesn't match expected format, return original name without extension
        return name_without_ext

    def process_images(self) -> Dict[str, Any]:
        """Process all images in the input directory, skipping subdirectories."""
        if not os.path.exists(self.input_dir):
            return {"success": False, "error": "Input directory does not exist"}

        results = {
            "success": True,
            "processed_files": [],
            "failed_files": [],
            "stats": {"total": 0, "success": 0, "failed": 0},
        }

        # Get all items in directory
        items = os.listdir(self.input_dir)
        for item in items:
            item_path = os.path.join(self.input_dir, item)

            # Skip if it's a directory
            if os.path.isdir(item_path):
                logger.info(f"Skipping directory: {item}")
                continue

            # Skip if not an image file
            if not item.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")):
                logger.info(f"Skipping non-image file: {item}")
                continue

            results["stats"]["total"] += 1

            # Get the new filename first
            new_filename = self.get_new_filename(item)

            # Process for both OCR and base64 with the same new filename
            ocr_result = self.ocr_processor.process_image(item_path, new_filename)
            base64_result = self.base64_processor.process_image(item_path, new_filename)

            if ocr_result["success"] and base64_result["success"]:
                results["processed_files"].append(
                    {
                        "original_filename": item,
                        "new_filename": new_filename,
                        "ocr_output": ocr_result["output_path"],
                        "base64_output": base64_result["output_path"],
                    }
                )
                results["stats"]["success"] += 1
            else:
                results["failed_files"].append(
                    {
                        "filename": item,
                        "ocr_error": None if ocr_result["success"] else ocr_result.get("error"),
                        "base64_error": (
                            None if base64_result["success"] else base64_result.get("error")
                        ),
                    }
                )
                results["stats"]["failed"] += 1

        return results
