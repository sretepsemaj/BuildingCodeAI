import imghdr
import logging
import os
import shutil
import uuid

import pytesseract
from django.conf import settings
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocClassicProcessor:
    def __init__(self):
        self.media_root = settings.MEDIA_ROOT
        self.source_dir = os.path.join(self.media_root, "uploads", "doc_classic", str(uuid.uuid4()))
        self.output_dir = os.path.join(
            self.media_root, "processed", "doc_classic", str(uuid.uuid4())
        )

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
            with open(temp_path, "wb+") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # Check if it's a valid image
            img_type = imghdr.what(temp_path)
            if img_type not in ["png", "jpeg", "jpg"]:
                os.remove(temp_path)
                raise ValueError(
                    f"Invalid image format. Got {img_type}, expected png, jpeg, or jpg."
                )

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

            # Create permanent directories
            batch_id = str(uuid.uuid4())

            # Create full paths
            full_permanent_dir = os.path.join(
                settings.MEDIA_ROOT, "uploads", "doc_classic", batch_id
            )
            full_text_dir = os.path.join(settings.MEDIA_ROOT, "processed", "doc_classic", batch_id)

            os.makedirs(full_permanent_dir, exist_ok=True)
            os.makedirs(full_text_dir, exist_ok=True)

            # Save the uploaded file to permanent location
            original_filename = uploaded_file.name
            relative_original_path = os.path.join(
                "uploads", "doc_classic", batch_id, original_filename
            )
            full_original_path = os.path.join(settings.MEDIA_ROOT, relative_original_path)

            print(f"Saving file to: {full_original_path}")

            with open(full_original_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Process the image and extract text
            print("Extracting text from image...")
            text = self._extract_text_from_image(full_original_path)
            print(f"Extracted text: {text[:100]}...")

            # Save the extracted text
            text_filename = os.path.splitext(original_filename)[0] + ".txt"
            relative_text_path = os.path.join("processed", "doc_classic", batch_id, text_filename)
            full_text_path = os.path.join(settings.MEDIA_ROOT, relative_text_path)

            print(f"Saving text to: {full_text_path}")

            with open(full_text_path, "w", encoding="utf-8") as f:
                f.write(text)

            logger.info(
                f"Successfully processed {full_original_path} and saved text to {full_text_path}"
            )

            # Verify files exist
            if not os.path.exists(full_original_path):
                raise ValueError("Original file not found after processing")

            # Return relative paths for storage in the database
            return {
                "original_path": relative_original_path,
                "text_path": relative_text_path,
                "text": text,
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
            # Only clean up temporary validation files
            temp_files = [f for f in os.listdir(self.source_dir) if f.startswith("temp_")]
            for f in temp_files:
                os.remove(os.path.join(self.source_dir, f))
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def process_folder(self, folder_path, batch_name=None, user=None):
        """Process all image files in a folder and return batch information."""
        try:
            # Create a new batch
            from main.models import DocumentBatch, ProcessedDocument

            batch = DocumentBatch.objects.create(
                name=batch_name or f"Batch {uuid.uuid4()}",
                status="processing",
                user=user,
            )

            successful = 0
            total_documents = 0

            # Process each file in the folder
            for filename in os.listdir(folder_path):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    total_documents += 1
                    file_path = os.path.join(folder_path, filename)

                    try:
                        # Create a file object from the path
                        with open(file_path, "rb") as f:
                            from django.core.files.uploadedfile import InMemoryUploadedFile

                            file = InMemoryUploadedFile(
                                f,
                                None,
                                filename,
                                "image/jpeg",
                                os.path.getsize(file_path),
                                None,
                            )

                            # Process the file
                            result = self.process_single(file)

                            # Create ProcessedDocument - store the full paths
                            ProcessedDocument.objects.create(
                                batch=batch,
                                filename=filename,
                                original_path=result["original_path"],
                                text_path=result["text_path"],
                                status="success",
                            )
                            successful += 1

                    except Exception as e:
                        logger.error(f"Error processing {filename}: {str(e)}")
                        ProcessedDocument.objects.create(
                            batch=batch,
                            filename=filename,
                            status="failed",
                            error_message=str(e),
                        )

            # Update batch status
            batch.status = "completed"
            batch.save()

            return {
                "batch_id": batch.id,
                "successful": successful,
                "total_documents": total_documents,
            }

        except Exception as e:
            logger.error(f"Error processing folder: {str(e)}")
            if "batch" in locals():
                batch.status = "failed"
                batch.save()
            raise Exception(f"Error processing folder: {str(e)}")

    def get_batch_info(self, batch_id):
        """Get information about a specific batch."""
        try:
            from main.models import DocumentBatch

            batch = DocumentBatch.objects.get(id=batch_id)
            documents = batch.documents.all()

            return {
                "batch_id": batch.id,
                "name": batch.name,
                "status": batch.status,
                "created_at": batch.created_at,
                "documents": [
                    {
                        "filename": doc.filename,
                        "status": doc.status,
                        "error_message": doc.error_message,
                    }
                    for doc in documents
                ],
            }
        except DocumentBatch.DoesNotExist:
            raise ValueError(f"Batch {batch_id} not found")
        except Exception as e:
            logger.error(f"Error getting batch info: {str(e)}")
            raise Exception(f"Error getting batch info: {str(e)}")


def main():
    """Main function to demonstrate usage."""
    processor = DocClassicProcessor()
    # Add code to call process_single and cleanup methods


if __name__ == "__main__":
    main()
