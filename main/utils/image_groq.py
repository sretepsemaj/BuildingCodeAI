import base64
import io
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypedDict, Union, cast

import groq  # type: ignore
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from dotenv import load_dotenv  # type: ignore
from fpdf import FPDF  # type: ignore
from PIL import Image  # type: ignore

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
        with Image.open(image_path) as img:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG", quality=85, optimize=True)
            img_byte_arr_value = img_byte_arr.getvalue()

            return base64.b64encode(img_byte_arr_value).decode("utf-8")

    def _process_image_batch(self, image_paths: List[str]) -> List[str]:
        """Process a batch of images and return their base64 encodings.

        Args:
            image_paths: List of paths to images to process.

        Returns:
            List of base64 encoded image strings.
        """
        return [self._encode_image(img_path) for img_path in image_paths]

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process a single image using Groq API with Llama vision model.

        Args:
            image_path: Path to the image file.

        Returns:
            Dictionary containing the API response.
        """
        try:
            base64_image = self.encode_image(image_path)

            # Prepare the prompt for the image analysis
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You are an expert plumbing code analyst. "
                                "Please analyze this plumbing diagram or building plan:\n\n"
                                "1. Identify plumbing fixtures, pipes, and components.\n"
                                "2. Check compliance with plumbing codes and regulations.\n"
                                "3. Highlight potential issues or code violations.\n"
                                "4. Provide specific references to relevant code sections.\n"
                                "5. Suggest improvements or corrections if needed.\n"
                                "6. Note any safety concerns or requirements.\n\n"
                                "Format your response in a clear, structured way that can be "
                                "easily parsed for database storage."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ]

            # Create a new client
            client = groq.Groq(api_key=self.api_key)
            completion = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=messages,
                temperature=0.1,  # Lower temperature for more consistent output
                max_tokens=2000,  # Ensure we get detailed responses
            )

            # Extract and structure the response
            response = completion.choices[0].message.content

            # Process the response to make it more suitable for embedding
            processed_response = self._process_response_for_embedding(response)

            return {
                "success": True,
                "content": processed_response,
                "error": None,
            }

        except Exception as e:
            logger.error("Error processing image: %s", str(e), exc_info=True)
            return {"success": False, "content": None, "error": str(e)}

    def _process_response_for_embedding(self, response: str) -> str:
        """Process the LLM response to make it more suitable for embedding.

        Args:
            response: Raw response from the LLM.

        Returns:
            Processed response optimized for embedding.
        """
        # Split the response into sections
        sections = response.split("\n\n")

        # Remove any markdown-style headers while keeping the content
        processed_sections = []
        for section in sections:
            # Remove numbered lists (e.g., "1. ", "2. ")
            section = "\n".join(line.lstrip("123456789. ") for line in section.split("\n"))
            # Remove section headers (e.g., "OVERVIEW:", "TEXTUAL CONTENT:")
            section = section.replace(":\n", "\n").replace(":", "")
            processed_sections.append(section)

        # Join sections with clear separators
        processed_text = " | ".join(processed_sections)

        # Remove multiple spaces and normalize whitespace
        processed_text = " ".join(processed_text.split())

        return processed_text

    def process_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple images using Groq API.

        Args:
            image_paths: List of paths to image files.

        Returns:
            List of dictionaries containing API responses.
        """
        results = []
        for image_path in image_paths:
            result = self.process_image(image_path)
            results.append(result)
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
