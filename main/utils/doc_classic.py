import imghdr
import logging
import operator
import os
import re
import shutil
import uuid
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List, Optional, Tuple

import pytesseract
from django.conf import settings
from django.db.models import Q
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocClassicProcessor:
    """A class for processing documents using OCR and metadata extraction."""

    def __init__(self) -> None:
        """Initialize the DocClassicProcessor."""
        self.media_root = settings.MEDIA_ROOT
        self.source_dir = os.path.join(self.media_root, "uploads", "doc_classic", str(uuid.uuid4()))
        self.output_dir = os.path.join(
            self.media_root, "processed", "doc_classic", str(uuid.uuid4())
        )

        # Create directories if they don't exist
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info("DocClassicProcessor initialized successfully")

    def validate_image(self, file: Any) -> None:
        """Validate that the file is a valid image."""
        try:
            # Save temporarily to check format and size
            temp_path = os.path.join(
                self.source_dir, "temp_" + os.path.basename(getattr(file, "name", "temp.png"))
            )
            file_size = 0

            # Handle both Django UploadedFile and regular file objects
            with open(temp_path, "wb+") as destination:
                if hasattr(file, "chunks"):
                    # Django UploadedFile
                    for chunk in file.chunks():
                        file_size += len(chunk)
                        destination.write(chunk)
                else:
                    # Regular file object
                    content = file.read()
                    file_size = len(content)
                    destination.write(content)
                    file.seek(0)  # Reset file pointer

            # Check file size (max 10MB)
            if file_size > 10 * 1024 * 1024:
                os.remove(temp_path)
                raise ValueError("File size too large. Maximum size is 10MB.")

            # Check if it's a valid image
            try:
                with Image.open(temp_path) as img:
                    format = img.format.lower()
                    if format not in ["png", "jpeg"]:
                        raise ValueError(
                            f"Invalid image format. Got {format}, expected png or jpeg."
                        )
            except Exception as e:
                raise ValueError(f"Invalid image file: {str(e)}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"Validation error for {getattr(file, 'name', 'unknown file')}: {str(e)}")
            raise ValueError(f"File validation failed: {str(e)}")

    def extract_metadata(self, text: str) -> Dict[str, Optional[str]]:
        """Extract metadata from OCR text."""
        logger.info(f"Starting metadata extraction from text:\n{text}")

        metadata = {
            "title": None,
            "chapter": None,
            "section_pc": None,
            "section": None,
            "subsection": None,
        }

        # Clean up text by removing extra whitespace and normalizing newlines
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        lines = text.split("\n")
        logger.info(f"Cleaned text lines: {lines}")

        # Extract chapter first
        chapter_patterns = [r"CHAPTER\s+(\d+)", r"ARTICLE\s+(\d+)", r"Section\s+(\d+)"]
        for pattern in chapter_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["chapter"] = match.group(1)
                break

        # Extract section identifiers
        section_patterns = [
            r"PC[- ](\d+(?:\.\d+)?)",
            r"Section\s+(\d+(?:\.\d+)?)",
            r"§\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in section_patterns:
            match = re.search(pattern, text)
            if match:
                metadata["section_pc"] = f"PC-{match.group(1)}"
                break

        # Extract title (look for "BUILDING CODE REQUIREMENTS")
        for line in lines:
            logger.info(f"Looking for title in line: {line}")
            if "BUILDING CODE REQUIREMENTS" in line.upper().rstrip("."):
                metadata["title"] = line.strip()
                logger.info(f"Found title: {metadata['title']}")
                break

        # Extract section
        for line in lines:
            logger.info(f"Looking for section in line: {line}")
            section_patterns = [
                r"^(\d+\.\d+)\s+",  # Start of line
                r"Section\s+(\d+\.\d+)",  # Explicit section
                r"(?<!\d)(\d+\.\d+)(?!\d)",  # Numbers with dot, not part of larger number
                r"(?<!\d)(\d+)\.(\d+)(?!\d)",  # Split numbers with dot
                r"(?<!\d)(\d)(?!\d).*?(?<!\d)(\d)(?!\d)",  # Single digits with content between
            ]
            for pattern in section_patterns:
                match = re.search(pattern, line)
                if match:
                    if len(match.groups()) == 2:
                        # Handle split numbers
                        metadata["section"] = f"{match.group(1)}.{match.group(2)}"
                    else:
                        metadata["section"] = match.group(1)
                    logger.info(f"Found section: {metadata['section']}")
                    break
            if metadata["section"]:
                break

        logger.info(f"Final metadata: {metadata}")
        return metadata

    def process_single(self, file_obj) -> Dict[str, Any]:
        """Process a single image file and extract metadata."""
        try:
            # Validate the image
            self.validate_image(file_obj)

            # Convert file object to PIL Image
            image = Image.open(file_obj)

            # Extract text using OCR
            extracted_text = pytesseract.image_to_string(image)
            logger.info(f"OCR Extracted Text:\n{extracted_text}")

            # Extract metadata from text
            metadata = self.extract_metadata(extracted_text)
            logger.info(f"Extracted Metadata: {metadata}")

            # Calculate OCR confidence
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [float(conf) for conf in ocr_data["conf"] if conf != "-1"]
            ocr_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Combine results
            result = {
                "extracted_text": extracted_text,
                "ocr_confidence": ocr_confidence,
                "ocr_version": pytesseract.get_tesseract_version(),
                "processing_params": {"tesseract_config": "", "preprocessing": "none"},
                **metadata,
            }

            return result

        except Exception as e:
            logger.error(f"Error processing single image: {str(e)}")
            raise

    def process_folder(self, folder_path: str, batch_name: str = None, user=None) -> Dict[str, Any]:
        """Process all images in a folder."""
        try:
            from django.core.files import File

            from main.models import DocumentBatch, ProcessedDocument

            # Create a new batch
            batch = DocumentBatch.objects.create(
                name=batch_name or f"Batch {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                user=user,
                status="processing",
            )

            successful = 0
            total_documents = 0

            # Process each image in the folder
            for filename in os.listdir(folder_path):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    total_documents += 1
                    file_path = os.path.join(folder_path, filename)

                    try:
                        # Calculate content hash for duplicate detection
                        content_hash = ProcessedDocument.calculate_content_hash(file_path)

                        # Check for duplicates
                        duplicate = ProcessedDocument.objects.filter(
                            content_hash=content_hash
                        ).first()

                        # Process the image
                        with open(file_path, "rb") as img_file:
                            # Get file size
                            img_file.seek(0, 2)  # Seek to end
                            file_size = img_file.tell()
                            img_file.seek(0)  # Back to start

                            # Process the image
                            result = self.process_single(img_file)

                            # Create ProcessedDocument
                            doc = ProcessedDocument.objects.create(
                                batch=batch,
                                filename=filename,
                                content_hash=content_hash,
                                is_duplicate=duplicate is not None,
                                duplicate_of=duplicate,
                                title=result.get("title"),
                                chapter=result.get("chapter"),
                                section_pc=result.get("section_pc"),
                                section=result.get("section"),
                                subsection=result.get("subsection"),
                                extracted_text=result.get("extracted_text"),
                                ocr_version=result.get("ocr_version"),
                                ocr_confidence=result.get("ocr_confidence"),
                                processing_params=result.get("processing_params"),
                                status="success",
                            )

                            # Save the original file
                            with open(file_path, "rb") as f:
                                doc.original_file.save(filename, File(f), save=True)

                            # Create text content file
                            text_filename = f"{os.path.splitext(filename)[0]}.txt"
                            text_content = result.get("extracted_text", "")

                            # Save text content
                            from django.core.files.base import ContentFile

                            doc.text_content.save(
                                text_filename, ContentFile(text_content.encode("utf-8")), save=True
                            )

                            successful += 1

                    except Exception as e:
                        logger.error(f"Error processing {filename}: {str(e)}")
                        # Create error document
                        ProcessedDocument.objects.create(
                            batch=batch,
                            filename=filename,
                            content_hash=ProcessedDocument.calculate_content_hash(file_path),
                            status="failed",
                            error_message=str(e),
                        )

            # Update batch status and statistics
            batch.total_documents = total_documents
            batch.successful_documents = (
                (successful / total_documents * 100) if total_documents > 0 else 0
            )
            batch.status = "completed"
            batch.save()

            return {
                "batch_id": batch.id,
                "successful": successful,
                "total_documents": total_documents,
            }

        except Exception as e:
            if "batch" in locals():
                batch.status = "failed"
                batch.save()
            logger.error(f"Error in batch processing: {str(e)}")
            raise

    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about processed documents."""
        from main.models import ProcessedDocument

        try:
            total_docs = ProcessedDocument.objects.count()
            successful_docs = ProcessedDocument.objects.filter(status="success").count()
            error_docs = ProcessedDocument.objects.filter(status="error").count()
            duplicate_docs = ProcessedDocument.objects.filter(is_duplicate=True).count()

            # Get average OCR confidence
            avg_confidence = ProcessedDocument.objects.filter(
                status="success", ocr_confidence__isnull=False
            ).values_list("ocr_confidence", flat=True)
            avg_confidence = sum(avg_confidence) / len(avg_confidence) if avg_confidence else 0

            return {
                "total_documents": total_docs,
                "successful_documents": successful_docs,
                "error_documents": error_docs,
                "duplicate_documents": duplicate_docs,
                "average_ocr_confidence": avg_confidence,
            }
        except Exception as e:
            logger.error(f"Error getting document stats: {str(e)}")
            raise

    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """Search for documents based on metadata or content."""
        from main.models import ProcessedDocument

        try:
            # Search in metadata and content
            query_filters = [
                Q(title__icontains=query),
                Q(chapter__icontains=query),
                Q(section_pc__icontains=query),
                Q(section__icontains=query),
                Q(subsection__icontains=query),
                Q(extracted_text__icontains=query),
            ]
            docs = ProcessedDocument.objects.filter(
                reduce(operator.or_, query_filters)
            ).select_related("batch")

            results = []
            for doc in docs:
                results.append(
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "title": doc.title,
                        "chapter": doc.chapter,
                        "section_pc": doc.section_pc,
                        "section": doc.section,
                        "subsection": doc.subsection,
                        "batch_name": doc.batch.name,
                        "created_at": doc.created_at,
                        "status": doc.status,
                        "ocr_confidence": doc.ocr_confidence,
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Clean up temporary files and directories."""
        try:
            # Only clean up temporary validation files
            temp_files = [f for f in os.listdir(self.source_dir) if f.startswith("temp_")]
            for f in temp_files:
                os.remove(os.path.join(self.source_dir, f))
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


def main() -> None:
    """Main function to demonstrate usage."""
    processor = DocClassicProcessor()
    # Add code to call process_single and cleanup methods


if __name__ == "__main__":
    main()
