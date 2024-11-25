import os
import pytesseract
from PIL import Image
from django.conf import settings
import uuid
import shutil
import logging
import imghdr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocClassicProcessor:
    def __init__(self):
        self.media_root = settings.MEDIA_ROOT
        self.source_dir = os.path.join(self.media_root, 'uploads', 'doc_classic', str(uuid.uuid4()))
        self.output_dir = os.path.join(self.media_root, 'processed', 'doc_classic', str(uuid.uuid4()))
        
        # Create directories if they don't exist
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("DocClassicProcessor initialized successfully")
    
    def validate_image(self, file):
        """Validate that the file is a valid image."""
        try:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValueError("File size too large. Maximum size is 10MB.")
            
            # Save temporarily to check format
            temp_path = os.path.join(self.source_dir, "temp_" + file.name)
            with open(temp_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            # Check if it's a valid image
            img_type = imghdr.what(temp_path)
            if img_type not in ['png', 'jpeg', 'jpg']:
                os.remove(temp_path)
                raise ValueError(f"Invalid image format. Got {img_type}, expected png, jpeg, or jpg.")
            
            # Clean up temp file
            os.remove(temp_path)
            return True
            
        except Exception as e:
            logger.error(f"Validation error for {file.name}: {str(e)}")
            raise ValueError(f"File validation failed: {str(e)}")
    
    def process_single(self, uploaded_file):
        """Process a single uploaded file and return paths to the original and processed files."""
        try:
            # Validate the file first
            self.validate_image(uploaded_file)
            
            # Save the uploaded file
            original_filename = uploaded_file.name
            original_path = os.path.join(self.source_dir, original_filename)
            
            print(f"Saving file to: {original_path}")  # Debug print
            
            with open(original_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Process the image and extract text
            print("Extracting text from image...")  # Debug print
            text = self._extract_text_from_image(original_path)
            print(f"Extracted text: {text[:100]}...")  # Debug print first 100 chars
            
            # Save the extracted text
            text_filename = os.path.splitext(original_filename)[0] + '.txt'
            text_path = os.path.join(self.output_dir, text_filename)
            
            print(f"Saving text to: {text_path}")  # Debug print
            
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.info(f"Successfully processed {original_path} and saved text to {text_path}")
            
            # Verify files exist
            if not os.path.exists(original_path):
                raise ValueError("Original file not found after processing")
            if not os.path.exists(text_path):
                raise ValueError("Text file not found after processing")
                
            return {
                'original_path': original_path,
                'text_path': text_path,
                'text': text
            }
        except ValueError as e:
            logger.error(f"ValueError in process_single: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing {uploaded_file.name}: {str(e)}")
            raise Exception(f"Error processing file: {str(e)}")
    
    def _extract_text_from_image(self, image_path):
        """Extract text from an image using OCR."""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            text = text.strip()
            if not text:
                raise ValueError("No text could be extracted from the image.")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            raise Exception(f"Error extracting text from image: {str(e)}")
    
    def cleanup(self):
        """Clean up temporary files and directories."""
        try:
            if os.path.exists(self.source_dir):
                shutil.rmtree(self.source_dir)
            if os.path.exists(self.output_dir):
                shutil.rmtree(self.output_dir)
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

def main():
    """Main function to demonstrate usage."""
    processor = DocClassicProcessor()
    # Add code to call process_single and cleanup methods

if __name__ == "__main__":
    main()