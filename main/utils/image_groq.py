"""Module for processing images using the Groq API."""

import base64
import io
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypedDict, Union, cast

# Third-party imports
import groq  # type: ignore
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from dotenv import load_dotenv  # type: ignore
from fpdf import FPDF  # type: ignore
from PIL import Image  # type: ignore

# Add the project root to the Python path
root_path = str(Path(__file__).parent.parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

# Local imports
from config.settings.base import BASE_DIR, MEDIA_ROOT, PLUMBING_CODE_DIR  # noqa: E402

# Set up logging
logger = logging.getLogger(__name__)


class ChatMessage(TypedDict):
    """Type for chat message content."""

    role: str
    content: Dict[str, Any]


class GroqImageProcessor:
    """Class for processing images using the Groq API."""

    def __init__(self) -> None:
        """Initialize the GroqImageProcessor."""
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = groq.Groq(api_key=self.api_key)
        # Rate limiting settings
        self.max_retries = 3
        self.initial_retry_delay = 1.0  # seconds
        self.max_retry_delay = 8.0  # seconds
        self.batch_size = 5
        self.prompt_template = (
            "You are an expert plumbing code analyst. Please analyze this "
            "plumbing code document and provide a structured response in "
            "the following format:\n\n"
            "1. SECTION NUMBERS:\n"
            "- List all section numbers mentioned (e.g., 301.1, 302.4)\n\n"
            "2. TABLE DATA:\n"
            "- Extract any table data in a structured format\n"
            "- Include table numbers, headers, and values\n\n"
            "3. CODE REQUIREMENTS:\n"
            "- Identify specific code requirements and regulations\n"
            "- Note any numerical values, measurements, or specifications\n\n"
            "4. CONTEXT SUMMARY:\n"
            "- Provide a brief summary of the main topics covered\n"
            "- Highlight key terms for semantic search\n\n"
            "5. CROSS-REFERENCES:\n"
            "- Note any references to other code sections or standards\n\n"
            "Format your response with clear section headers and bullet "
            "points for easy parsing. Use multiple lines for each "
            "section to improve readability."
        )

    def encode_image(self, image_path: str, max_size: int = 800) -> str:
        """
        Encode an image file to base64, resizing if necessary to reduce token size.

        Args:
            image_path: Path to the image file.
            max_size: Maximum dimension (width or height) for the image.

        Returns:
            Base64 encoded string of the image.
        """
        # Open and resize the image if necessary
        with Image.open(image_path) as img:
            # Convert to RGB if image is in RGBA mode
            if img.mode == "RGBA":
                img = img.convert("RGB")

            # Calculate new dimensions while maintaining aspect ratio
            width, height = img.size
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG", quality=85, optimize=True)
            img_byte_arr_value = img_byte_arr.getvalue()

            return base64.b64encode(img_byte_arr_value).decode("utf-8")

    def _encode_image(self, image_path: str) -> str:
        """
        Encode an image file to base64.

        Args:
            image_path: Path to the image file.

        Returns:
            Base64 encoded string of the image.
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return {"error": "Image file not found", "success": False}

        # Read and encode the image
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Error reading image file {image_path}: {str(e)}")
            return {"error": f"Error reading image: {str(e)}", "success": False}

        return image_data

    def _process_image_batch(self, image_paths: List[str]) -> List[str]:
        """Process a batch of images and return their base64 encodings.

        Args:
            image_paths: List of paths to image files.

        Returns:
            List of base64 encoded strings.
        """
        base64_images = []
        for path in image_paths:
            try:
                base64_str = self._encode_image(path)
                if isinstance(base64_str, dict) and not base64_str.get("success", True):
                    logger.error(f"Failed to encode image {path}: {base64_str['error']}")
                    continue
                base64_images.append(base64_str)
            except Exception as e:
                logger.error(f"Error in batch processing for {path}: {e}")
                continue
        return base64_images

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process a single image using Groq API with Llama vision model.

        This method handles rate limiting and retries with exponential backoff.

        Args:
            image_path: Path to the image file to process.

        Returns:
            Dict containing the processed results or error information.
        """
        retry_count = 0
        retry_delay = self.initial_retry_delay

        try:
            # Encode the image
            base64_image = self._encode_image(image_path)
            if isinstance(base64_image, dict) and not base64_image.get("success", True):
                return base64_image

            # Prepare the messages for the API
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                        {
                            "type": "text",
                            "text": self.prompt_template,
                        },
                    ],
                }
            ]

            logger.info(f"Processing image: {image_path}")
            completion = self.client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=messages,
                temperature=0.1,
                max_tokens=2000,
            )

            if completion.choices:
                response = completion.choices[0].message.content
                logger.info(f"Successfully processed image: {image_path}")

                # Create a structured response dictionary
                structured_response = {
                    "sections": [],
                    "tables": [],
                    "requirements": [],
                    "context": "",
                    "references": [],
                    "raw_response": response,
                    "success": True,
                }

                # Parse the response into sections
                current_section = None
                for line in response.split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    # Check for section headers
                    if "SECTION NUMBERS:" in line or "1." in line:
                        current_section = "sections"
                        continue
                    elif "TABLE DATA:" in line or "2." in line:
                        current_section = "tables"
                        continue
                    elif "CODE REQUIREMENTS:" in line or "3." in line:
                        current_section = "requirements"
                        continue
                    elif "CONTEXT SUMMARY:" in line or "4." in line:
                        current_section = "context"
                        continue
                    elif "CROSS-REFERENCES:" in line or "5." in line:
                        current_section = "references"
                        continue

                    # Process content based on section
                    if current_section:
                        if current_section == "context":
                            structured_response[current_section] += line + " "
                        elif line.startswith("-") or line.startswith("•"):
                            content = line.lstrip("- •").strip()
                            if current_section in [
                                "sections",
                                "tables",
                                "requirements",
                                "references",
                            ]:
                                structured_response[current_section].append(content)

                # Clean up the context
                structured_response["context"] = structured_response["context"].strip()
                return structured_response

            logger.warning(f"No response from model for image: {image_path}")
            return {"error": "No response from model", "success": False}

        except groq.error.RateLimitError as e:
            retry_count += 1
            if retry_count <= self.max_retries:
                logger.warning(
                    f"Rate limit hit for {image_path}. "
                    f"Attempt {retry_count} of {self.max_retries}. "
                    f"Retrying in {retry_delay} seconds..."
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, self.max_retry_delay)  # Exponential backoff
            else:
                logger.error(
                    f"Rate limit exceeded after {self.max_retries} retries for {image_path}"
                )
                return {"error": f"Rate limit exceeded: {str(e)}", "success": False}

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}", exc_info=True)
            return {"error": str(e), "success": False}

    def process_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple images using Groq API with batch processing and rate limiting.

        Args:
            image_paths: List of paths to image files.

        Returns:
            List of dictionaries containing API responses.
        """
        results, error = self.batch_process_images(
            image_paths=image_paths,
            output_dir=None,  # Not needed for this method
            batch_size=self.batch_size,
            delay=self.initial_retry_delay,
        )

        if error:
            logger.error(f"Batch processing error: {error}")
            return [{"error": error, "success": False}]

        return results

    def process_uploaded_file(self, uploaded_file: UploadedFile, output_dir: str) -> Dict[str, Any]:
        """
        Process an uploaded file using Groq API.

        Args:
            uploaded_file: The uploaded file object.
            output_dir: Directory to save processed files.

        Returns:
            Dictionary containing the processing results.
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)

            # Save the uploaded file
            if uploaded_file.name:
                image_path = os.path.join(output_dir, uploaded_file.name)
                with open(image_path, "wb+") as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)

                # Process the image
                result = self.process_image(image_path)

                # Save the text output
                if result["success"] and result["content"] and uploaded_file.name:
                    text_filename = f"{os.path.splitext(uploaded_file.name)[0]}.txt"
                    text_path = os.path.join(output_dir, text_filename)
                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(result["content"])
                    result["text_path"] = text_path

                return result

            return {"success": False, "content": None, "error": "No filename provided"}

        except Exception as e:
            return {"success": False, "content": None, "error": str(e)}

    def process_uploaded_files(
        self, files: List[UploadedFile], output_dir: str
    ) -> List[Dict[str, Any]]:
        """
        Process multiple uploaded files using Groq API.

        Args:
            files: List of uploaded file objects.
            output_dir: Directory to save processed files.

        Returns:
            List of dictionaries containing processing results.
        """
        results = []
        for uploaded_file in files:
            result = self.process_uploaded_file(uploaded_file, output_dir)
            results.append(result)
        return results

    def create_pdf_report(self, results: List[Dict[str, Any]], output_path: str) -> Optional[str]:
        """
        Create a PDF report from processing results.

        Args:
            results: List of processing results.
            output_path: Path to save the PDF file.

        Returns:
            Path to the created PDF file or None if creation fails.
        """
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            # Add title
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, text="Image Processing Report", ln=True, align="C")
            pdf.ln(10)

            # Reset font for content
            pdf.set_font("Arial", size=12)

            for i, result in enumerate(results, 1):
                # Add section header
                pdf.set_font("Arial", "B", 14)
                pdf.cell(200, 10, text=f"Image {i}", ln=True)
                pdf.ln(5)

                # Reset font for content
                pdf.set_font("Arial", size=12)

                if result["success"]:
                    # Add the analysis text
                    text = result.get("content", "No analysis available")
                    pdf.multi_cell(0, 10, text=text)
                else:
                    # Add error message
                    error = result.get("error", "Unknown error")
                    pdf.set_text_color(255, 0, 0)  # Red color for errors
                    pdf.multi_cell(0, 10, text=f"Error: {error}")
                    pdf.set_text_color(0, 0, 0)  # Reset text color

                pdf.ln(10)

            # Save the PDF
            pdf.output(output_path)
            return output_path

        except Exception as e:
            print(f"Error creating PDF report: {e}")
            return None

    def process_directory(
        self, input_dir: str, output_dir: str
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Process all images in a directory and save results.

        Args:
            input_dir: Directory containing images to process
            output_dir: Directory to save processed results

        Returns:
            Tuple containing list of processing results and optional error message
        """
        try:
            # Get list of image files in directory
            image_paths = []
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if file.lower().endswith((".png", ".jpg", ".jpeg")):
                        image_paths.append(os.path.join(root, file))

            if not image_paths:
                return [], "No image files found in directory"

            # Process images in batches
            results, error = self.batch_process_images(image_paths, output_dir)
            if error:
                return [], error

            return results, None

        except Exception as e:
            error_msg = f"Error processing directory: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return [], error_msg

    def batch_process_images(
        self, image_paths, output_dir, batch_size=5, delay=1.0
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Process multiple images in batches to handle API rate limits.

        Args:
            image_paths: List of paths to image files.
            output_dir: Directory to save processed files.
            batch_size: Number of images to process in each batch.
            delay: Delay between batches in seconds.

        Returns:
            Tuple containing list of results and optional error message.
        """
        try:
            results = []
            for i in range(0, len(image_paths), batch_size):
                batch = image_paths[i : i + batch_size]
                batch_results = self.process_images(batch)
                results.extend(batch_results)
                if i + batch_size < len(image_paths):
                    time.sleep(delay)
            return results, None
        except Exception as e:
            error_msg = f"Error in batch processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return [], error_msg

    def get_image_description(self, image_path: str) -> Dict[str, Any]:
        """Get a description of an image.

        Args:
            image_path: Path to the image file.

        Returns:
            Dictionary containing the image description.
        """
        encoded_image = self._encode_image(image_path)
        return {"success": True, "content": f"Image description for {image_path}", "error": None}


def main() -> None:
    """Main function to process images and generate report."""
    try:
        # Initialize processor
        processor = GroqImageProcessor()

        # Set up paths
        base_dir = Path(__file__).resolve().parent.parent
        input_dir = base_dir / "static" / "images" / "png_files"
        output_dir = base_dir / "static" / "reports"
        output_path = output_dir / f'table_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Process images
        logger.info("Starting image processing")
        results, pdf_path = processor.process_directory(str(input_dir), str(output_dir))

        if pdf_path:
            logger.info("Process completed successfully")
        else:
            logger.error("Failed to generate PDF report")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()
