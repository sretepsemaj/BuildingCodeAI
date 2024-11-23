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
        """Preprocess image to reduce size."""
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
            max_size = 200  
            ratio = min(max_size/img.width, max_size/img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            
            # Resize image
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to grayscale
            img = img.convert('L')
            
            # Increase contrast to make text more readable at low quality
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            
            # Save with extreme compression
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=10, optimize=True)
            
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
            
            # Minimal prompt
            prompt = (
                "Table analysis:{\"table_headers\":[...],\"table_data\":[[...]],\"table_summary\":\"...\"}\n"
                f"data:image/jpeg;base64,{base64_image}"
            )
            
            logger.info("Making API request to Groq")
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": "Table analyzer"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            logger.info("Received response from Groq API")
            
            try:
                if hasattr(response.choices[0].message, 'content'):
                    logger.info("Parsing API response content")
                    result = json.loads(response.choices[0].message.content)
                    
                    required_keys = ['table_headers', 'table_data', 'table_summary']
                    if not all(key in result for key in required_keys):
                        logger.error("Missing required keys in JSON response")
                        raise ValueError("Missing required keys in JSON response")
                    
                    if not isinstance(result['table_headers'], list):
                        logger.warning("table_headers is not a list, setting to empty list")
                        result['table_headers'] = []
                    
                    if not isinstance(result['table_data'], list):
                        logger.warning("table_data is not a list, setting to empty list")
                        result['table_data'] = []
                    
                    if not isinstance(result['table_summary'], str):
                        logger.warning("table_summary is not a string, setting default message")
                        result['table_summary'] = "No summary available"
                    
                    logger.info(f"Successfully processed image. Result: {result}")
                    return result
                else:
                    logger.error("No content in API response")
                    raise ValueError("No content in API response")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}", exc_info=True)
            raise

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process all PNG files in a directory."""
        logger.info(f"Processing directory: {directory_path}")
        results = []
        
        # Get all PNG files
        png_files = Path(directory_path).glob('*.png')
        
        for image_path in png_files:
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
