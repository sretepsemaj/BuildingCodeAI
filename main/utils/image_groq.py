import base64
import json
import logging
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import groq
from dotenv import load_dotenv
from fpdf import FPDF
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class GroqImageProcessor:
    def __init__(self):
        """Initialize the Groq Image Processor."""
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")

        self.client = groq.Groq(api_key=self.api_key)
        self.model = "llama-3.2-11b-vision-preview"
        logger.info("GroqImageProcessor initialized successfully")

    def preprocess_image(self, image_data: bytes) -> bytes:
        """Preprocess image while maintaining quality for table recognition."""
        logger.info("Preprocessing image data")

        try:
            # Open image from binary data
            with BytesIO(image_data) as data, Image.open(data) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Calculate new size while maintaining aspect ratio
                max_size = 800
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))

                # Resize image using high-quality resampling
                img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Save with good quality for text recognition
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=85, optimize=True)

                # Get the size in bytes
                size_in_bytes = buffer.tell()
                logger.info(f"Image preprocessed. New size: {new_size}, Bytes: {size_in_bytes}")

                return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            raise

    def encode_image(self, image_data: bytes) -> str:
        """Encode image data to base64."""
        logger.debug("Encoding image data to base64")
        try:
            # Preprocess and encode
            processed_data = self.preprocess_image(image_data)
            return base64.b64encode(processed_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Error encoding image: {str(e)}")
            raise

    def process_image(self, image_data: bytes) -> Dict[str, Any]:
        """Process image data using Groq API."""
        try:
            logger.info("Starting to process image data")

            # Encode image to base64
            base64_image = self.encode_image(image_data)
            logger.info("Successfully encoded image to base64")

            logger.info("Making API request to Groq")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this image and extract the first table you find. Format your response as follows:

1. Present the table in markdown format with | separators
2. Provide a brief summary under a 'Summary' heading
3. Do not repeat the table or summary
4. If multiple tables exist, focus only on the first one""",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                temperature=0.7,
                max_tokens=2048,
                top_p=1,
                stream=False,
                stop=None,
            )
            logger.info("Received response from Groq API")

            try:
                if hasattr(response.choices[0].message, "content"):
                    logger.info("Processing API response content")
                    content = response.choices[0].message.content
                    logger.debug(f"Raw API response: {content}")

                    # Process the natural language response
                    processed_result = {
                        "table_headers": [],
                        "table_data": [],
                        "table_summary": "",
                    }

                    # Extract tables from markdown format
                    tables = []
                    current_table = []
                    summary_parts = []
                    in_table = False

                    for line in content.split("\n"):
                        line = line.strip()

                        # Handle table markers
                        if "|" in line and ":--" in line:  # Header separator
                            in_table = True
                            continue

                        if line.startswith("|") and in_table:
                            # Clean up table row
                            row = [cell.strip() for cell in line.strip("|").split("|")]
                            current_table.append(row)
                        elif in_table and not line:  # Empty line after table
                            if current_table:
                                tables.append(current_table)
                                current_table = []
                            in_table = False
                        elif not in_table and line:  # Non-table content
                            if not line.startswith("**"):  # Skip table titles
                                summary_parts.append(line)

                    # Add last table if exists
                    if current_table:
                        tables.append(current_table)

                    # Process tables - remove duplicates
                    unique_tables = []
                    seen = set()
                    for table in tables:
                        table_str = str(table)
                        if table_str not in seen:
                            seen.add(table_str)
                            unique_tables.append(table)

                    # Use the first unique table found
                    if unique_tables:
                        first_table = unique_tables[0]
                        if len(first_table) > 1:  # Has headers and data
                            processed_result["table_headers"] = first_table[0]
                            processed_result["table_data"] = first_table[1:]

                    # Clean up summary
                    summary = " ".join(summary_parts)
                    # Remove duplicate summaries
                    if "Summary" in summary:
                        summary = summary[summary.find("Summary") :].split("\n\n")[0]
                    processed_result["table_summary"] = summary.strip()

                    logger.info(f"Successfully processed image. Result: {processed_result}")
                    return processed_result
                else:
                    logger.error("No content in API response")
                    return {
                        "table_headers": [],
                        "table_data": [],
                        "table_summary": "No content in API response",
                    }

            except Exception as e:
                # Check if this is a Groq API error with failed_generation
                if hasattr(e, "response") and hasattr(e.response, "json"):
                    error_json = e.response.json()
                    if isinstance(error_json, dict) and "error" in error_json:
                        error_data = error_json["error"]
                        if "failed_generation" in error_data:
                            try:
                                # Try to parse the failed_generation as JSON
                                failed_gen = json.loads(error_data["failed_generation"])
                                logger.info("Successfully extracted data from failed_generation")
                                return {
                                    "table_headers": failed_gen.get("table_headers", []),
                                    "table_data": failed_gen.get("table_data", []),
                                    "table_summary": failed_gen.get(
                                        "table_summary", "No summary available"
                                    ),
                                }
                            except json.JSONDecodeError:
                                logger.error("Failed to parse failed_generation JSON")

                logger.error(f"Error processing image: {str(e)}", exc_info=True)
                return {
                    "table_headers": [],
                    "table_data": [],
                    "table_summary": f"Error processing image: {str(e)}",
                }

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}", exc_info=True)
            return {
                "table_headers": [],
                "table_data": [],
                "table_summary": f"Error processing image: {str(e)}",
            }

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process all image files in a directory."""
        logger.info(f"Processing directory: {directory_path}")
        results = []

        # Get all supported image files
        supported_extensions = ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp")
        image_files = []
        for ext in supported_extensions:
            image_files.extend(Path(directory_path).glob(ext))

        for image_path in image_files:
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()
                result = self.process_image(image_data)
                results.append({"filename": image_path.name, "data": result})
                logger.info(f"Successfully processed {image_path.name}")
            except Exception as e:
                logger.error(f"Failed to process {image_path.name}: {str(e)}")
                results.append(
                    {
                        "filename": image_path.name,
                        "data": {
                            "table_headers": [],
                            "table_data": [],
                            "table_summary": f"Failed to process: {str(e)}",
                        },
                    }
                )

        return results

    def generate_pdf_report(self, results: List[Dict[str, Any]], output_path: str):
        """Generate a PDF report from the processed image data."""
        logger.info("Generating PDF report")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Add title page
        pdf.add_page()
        pdf.set_font("Arial", "B", 24)
        pdf.cell(0, 20, "Table Analysis Report", ln=True, align="C")
        pdf.set_font("Arial", size=12)
        pdf.cell(
            0,
            10,
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ln=True,
            align="C",
        )

        # Process each image result
        for result in results:
            pdf.add_page()

            # Add image filename as header
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Image: {result['filename']}", ln=True)

            table_data = result["data"]

            # Add table summary
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Table Summary", ln=True)
            pdf.set_font("Arial", size=12)
            summary = table_data.get("table_summary", "No summary available")
            pdf.multi_cell(0, 10, str(summary))

            # Add table content if available
            headers = table_data.get("table_headers", [])
            rows = table_data.get("table_data", [])

            if headers and rows:
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)

                # Calculate column widths
                col_width = 190 / len(headers)

                # Add headers
                for header in headers:
                    pdf.cell(col_width, 10, str(header)[:20], 1)
                pdf.ln()

                # Add rows
                pdf.set_font("Arial", size=10)
                for row in rows:
                    for cell in row:
                        pdf.cell(col_width, 10, str(cell)[:20], 1)
                    pdf.ln()

            pdf.ln(10)

        # Save the PDF
        pdf.output(output_path)
        logger.info(f"PDF report generated successfully: {output_path}")


def main():
    """Main function to process images and generate report."""
    try:
        # Initialize processor
        processor = GroqImageProcessor()

        # Set up paths
        base_dir = Path(__file__).resolve().parent.parent
        input_dir = base_dir / "static" / "images" / "png_files"
        output_path = (
            base_dir
            / "static"
            / "reports"
            / f'table_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Process images
        logger.info("Starting image processing")
        results = processor.process_directory(str(input_dir))

        # Generate report
        processor.generate_pdf_report(results, str(output_path))
        logger.info("Process completed successfully")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()
