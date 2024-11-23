import os
import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from io import BytesIO

import groq
from fpdf import FPDF
from dotenv import load_dotenv
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GroqImageProcessor:
    def __init__(self):
        """Initialize the Groq Image Processor."""
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        
        self.client = groq.Groq(api_key=self.api_key)
        self.model = "llama-3.2-11b-vision-preview"
        logger.info("GroqImageProcessor initialized successfully")

    def preprocess_image(self, image_path: str) -> bytes:
        """Preprocess image while maintaining quality for table recognition."""
        logger.info(f"Preprocessing image: {image_path}")
        
        # Open and convert image to RGB (removing alpha channel if present)
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate new size while maintaining aspect ratio
            max_size = 800  
            ratio = min(max_size/img.width, max_size/img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            
            # Resize image using high-quality resampling
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save with good quality for text recognition
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            
            # Get the size in bytes
            size_in_bytes = buffer.tell()
            logger.info(f"Image preprocessed. New size: {new_size}, Bytes: {size_in_bytes}")
            
            return buffer.getvalue()

    def encode_image(self, image_path: str) -> str:
        """Encode an image file to base64."""
        logger.debug(f"Encoding image: {image_path}")
        # Preprocess and encode
        image_data = self.preprocess_image(image_path)
        return base64.b64encode(image_data).decode('utf-8')

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process a single image using Groq API."""
        try:
            logger.info(f"Starting to process image: {image_path}")
            
            # Encode image to base64
            base64_image = self.encode_image(image_path)
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
                                "text": "Extract the table information from this image. For each table found, list the headers, data rows, and provide a brief summary."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=2048,
                top_p=1,
                stream=False,
                stop=None
            )
            logger.info("Received response from Groq API")
            
            try:
                if hasattr(response.choices[0].message, 'content'):
                    logger.info("Processing API response content")
                    content = response.choices[0].message.content
                    logger.debug(f"Raw API response: {content}")

                    # Process the natural language response
                    processed_result = {
                        'table_headers': [],
                        'table_data': [],
                        'table_summary': content  # Store full response as summary
                    }

                    # Try to extract structured data if available
                    try:
                        # Look for table headers
                        if "headers" in content.lower():
                            headers_section = content[content.lower().find("headers"):].split("\n")[0]
                            headers = [h.strip() for h in headers_section.split(":")[1].split(",") if h.strip()]
                            if headers:
                                processed_result['table_headers'] = headers

                        # Look for table data/rows
                        if "row" in content.lower() or "data" in content.lower():
                            data_lines = [line.strip() for line in content.split("\n") 
                                        if ("row" in line.lower() or "data" in line.lower()) 
                                        and ":" in line]
                            if data_lines:
                                processed_result['table_data'] = [
                                    [cell.strip() for cell in line.split(":")[1].split(",")]
                                    for line in data_lines
                                ]

                    except Exception as e:
                        logger.warning(f"Error extracting structured data: {e}")
                        # Keep the full response as summary if structured extraction fails
                    
                    logger.info(f"Successfully processed image. Result: {processed_result}")
                    return processed_result
                else:
                    logger.error("No content in API response")
                    return {
                        'table_headers': [],
                        'table_data': [],
                        'table_summary': "No content in API response"
                    }
                    
            except Exception as e:
                # Check if this is a Groq API error with failed_generation
                if hasattr(e, 'response') and hasattr(e.response, 'json'):
                    error_json = e.response.json()
                    if isinstance(error_json, dict) and 'error' in error_json:
                        error_data = error_json['error']
                        if 'failed_generation' in error_data:
                            try:
                                # Try to parse the failed_generation as JSON
                                failed_gen = json.loads(error_data['failed_generation'])
                                logger.info("Successfully extracted data from failed_generation")
                                return {
                                    'table_headers': failed_gen.get('table_headers', []),
                                    'table_data': failed_gen.get('table_data', []),
                                    'table_summary': failed_gen.get('table_summary', 'No summary available')
                                }
                            except json.JSONDecodeError:
                                logger.error("Failed to parse failed_generation JSON")

                logger.error(f"Error processing image {image_path}: {str(e)}", exc_info=True)
                return {
                    'table_headers': [],
                    'table_data': [],
                    'table_summary': f"Error processing image: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}", exc_info=True)
            return {
                'table_headers': [],
                'table_data': [],
                'table_summary': f"Error processing image: {str(e)}"
            }

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process all image files in a directory."""
        logger.info(f"Processing directory: {directory_path}")
        results = []
        
        # Get all supported image files
        supported_extensions = ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp')
        image_files = []
        for ext in supported_extensions:
            image_files.extend(Path(directory_path).glob(ext))
        
        for image_path in image_files:
            try:
                result = self.process_image(str(image_path))
                results.append({
                    'filename': image_path.name,
                    'data': result
                })
                logger.info(f"Successfully processed {image_path.name}")
            except Exception as e:
                logger.error(f"Failed to process {image_path.name}: {str(e)}")
                results.append({
                    'filename': image_path.name,
                    'data': {
                        "table_headers": [],
                        "table_data": [],
                        "table_summary": f"Failed to process: {str(e)}"
                    }
                })
        
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
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
        
        # Process each image result
        for result in results:
            pdf.add_page()
            
            # Add image filename as header
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Image: {result['filename']}", ln=True)
            
            table_data = result['data']
            
            # Add table summary
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Table Summary", ln=True)
            pdf.set_font("Arial", size=12)
            summary = table_data.get('table_summary', 'No summary available')
            pdf.multi_cell(0, 10, str(summary))
            
            # Add table content if available
            headers = table_data.get('table_headers', [])
            rows = table_data.get('table_data', [])
            
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
        input_dir = base_dir / 'static' / 'images' / 'png_files'
        output_path = base_dir / 'static' / 'reports' / f'table_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
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
