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
    def process_image(self, image_path: str) -> Dict[str, Any]:
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

    def convert_filename(self, original_filename: str) -> str:
        """Convert chapter-based filename to NYCPcode format."""
        # Remove file extension
        base_name = os.path.splitext(original_filename)[0].lower()

        # Match pattern like chapter1_1page or similar
        match = re.match(r"chapter(\d+)_(\d+)page", base_name)
        if match:
            chapter_num = int(match.group(1))
            page_num = int(match.group(2))
            return f"NYCP{chapter_num}ch_{page_num}pg.jpg"

        # If filename doesn't match expected pattern, keep original name but ensure jpg extension
        return f"{base_name}.jpg"


class OCRImageProcessor(ImageProcessorBase):
    """Processor for OCR-optimized images."""

    def __init__(self, input_path: str, output_path: str):
        super().__init__(input_path, output_path)
        os.makedirs(output_path, exist_ok=True)

    def process_image(self, image_path: str) -> Dict[str, Any]:
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

                # Convert filename to NYCPcode format
                new_filename = self.convert_filename(os.path.basename(image_path))
                output_filename = os.path.join(self.output_path, new_filename)

                # Save processed image as JPG
                processed.save(output_filename, "JPEG", quality=95)

                return {
                    "success": True,
                    "output_path": output_filename,
                    "original_size": img.size,
                    "processed_size": processed.size,
                    "new_filename": new_filename,
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

    def process_image(self, image_path: str) -> Dict[str, Any]:
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

                # Convert filename to NYCPcode format
                new_filename = self.convert_filename(os.path.basename(image_path))
                output_filename = os.path.join(self.output_path, new_filename)

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
                    "new_filename": new_filename,
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

    def process_images(self) -> Dict[str, Any]:
        """Process all images in the input directory."""
        if not os.path.exists(self.input_dir):
            return {"success": False, "error": "Input directory does not exist"}

        results = {
            "success": True,
            "processed_files": [],
            "failed_files": [],
            "stats": {"total": 0, "success": 0, "failed": 0},
        }

        # Process all image files (including various formats)
        for filename in os.listdir(self.input_dir):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")):
                file_path = os.path.join(self.input_dir, filename)

                # Process for both OCR and base64
                ocr_result = self.ocr_processor.process_image(file_path)
                base64_result = self.base64_processor.process_image(file_path)

                results["stats"]["total"] += 1

                if ocr_result["success"] and base64_result["success"]:
                    results["processed_files"].append(
                        {
                            "original_filename": filename,
                            "new_filename": ocr_result["new_filename"],
                            "ocr_output": ocr_result["output_path"],
                            "base64_output": base64_result["output_path"],
                        }
                    )
                    results["stats"]["success"] += 1
                else:
                    results["failed_files"].append(
                        {
                            "filename": filename,
                            "ocr_error": None if ocr_result["success"] else ocr_result.get("error"),
                            "base64_error": (
                                None if base64_result["success"] else base64_result.get("error")
                            ),
                        }
                    )
                    results["stats"]["failed"] += 1

        return results
