"""Models for the main application."""

import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, cast

# Django settings configuration
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.base")
)

from django.conf import settings  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.db import models  # noqa: E402
from django.db.models.signals import post_delete, pre_delete  # noqa: E402
from django.dispatch import receiver  # noqa: E402

# Get logger
logger = logging.getLogger(__name__)


class Chapter(models.Model):
    """Represents a NYC Plumbing Code chapter."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter_number = models.CharField(max_length=10)
    code_type = models.CharField(max_length=10, default="NYCPC")
    title = models.CharField(max_length=255)
    content_json = models.FileField(upload_to="plumbing_code/json_final/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a string representation of the Chapter."""
        return f"{self.code_type} Chapter {self.chapter_number}: {self.title}"

    @property
    def json_filename(self):
        """Generate the expected JSON filename."""
        return f"NYCP{self.chapter_number}CH_groq.json"

    class Meta:
        """Meta options for Chapter model."""

        ordering = ["chapter_number"]
        verbose_name_plural = "Chapters"


class ChapterPage(models.Model):
    """Represents a single page within a chapter."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="pages")
    page_number = models.IntegerField()
    text_content = models.TextField()
    image_file = models.FileField(upload_to="plumbing_code/optimizer/")
    table_file = models.FileField(upload_to="plumbing_code/tables/", null=True, blank=True)

    def __str__(self):
        """Return a string representation of the ChapterPage."""
        return f"Chapter {self.chapter.chapter_number} - Page {self.page_number}"

    @property
    def image_filename(self):
        """Generate the expected image filename."""
        return f"NYCP{self.chapter.chapter_number}ch_{self.page_number}pg.jpg"

    @property
    def table_filename(self):
        """Generate the expected table filename if this page has a table."""
        if self.table_file:
            return f"NYCP{self.chapter.chapter_number}ch_{self.page_number}pg.csv"
        return None

    class Meta:
        """Meta options for ChapterPage model."""

        unique_together = ["chapter", "page_number"]
        ordering = ["chapter", "page_number"]
        verbose_name_plural = "Chapter Pages"


class DocumentBatch(models.Model):
    """Represents a batch of documents to be processed."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )

    def __str__(self):
        """Return a string representation of the DocumentBatch."""
        return f"Batch {self.id} by {self.user.username} ({self.status})"

    class Meta:
        """Meta options for DocumentBatch model."""

        verbose_name_plural = "Document Batches"


class ProcessedDocument(models.Model):
    """Represents a single processed document."""

    id: models.UUIDField = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch: models.ForeignKey = models.ForeignKey(
        DocumentBatch, on_delete=models.CASCADE, related_name="documents"
    )
    filename: models.CharField = models.CharField(max_length=255)
    original_path: models.CharField = models.CharField(max_length=255, null=True, blank=True)
    text_path: models.CharField = models.CharField(max_length=255, null=True, blank=True)
    status: models.CharField = models.CharField(
        max_length=20, choices=[("success", "Success"), ("failed", "Failed")]
    )
    error_message: models.TextField = models.TextField(null=True, blank=True)
    processed_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, Dict[str, int]]:
        """Override delete to ensure all files are cleaned up."""
        result: tuple[int, Dict[str, int]] = (0, {})

        # Delete the physical files
        if self.original_path and os.path.exists(self.original_path):
            try:
                os.remove(self.original_path)
            except Exception as e:
                print(f"Error deleting original file: {e}")

        if self.text_path and os.path.exists(self.text_path):
            try:
                os.remove(self.text_path)
            except Exception as e:
                print(f"Error deleting text file: {e}")

        # Call the parent delete method
        result = super().delete(*args, **kwargs)
        return result

    @property
    def original_url(self) -> Optional[str]:
        """Get the URL for the original file."""
        if self.original_path:
            # Ensure the path starts with media/
            path = self.original_path.lstrip("/")
            if not path.startswith("media/"):
                path = f"media/{path}"
            return f"/{path}"
        return None

    @property
    def text_url(self) -> Optional[str]:
        """Get the URL for the processed text file."""
        if self.text_path:
            # Ensure the path starts with media/
            path = self.text_path.lstrip("/")
            if not path.startswith("media/"):
                path = f"media/{path}"
            return f"/{path}"
        return None

    def get_text_content(self) -> Optional[str]:
        """Get the extracted text content."""
        try:
            if self.text_path:
                full_path = os.path.join(settings.MEDIA_ROOT, self.text_path.lstrip("/"))
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        return f.read()
                return f"Error: Text file not found at {full_path}"
            return None
        except Exception as e:
            return f"Error reading text content: {str(e)}"

    def __str__(self) -> str:
        """String representation of the document."""
        return f"Document {self.filename} ({self.status})"

    class Meta:
        """Model metadata for ProcessedDocument."""

        ordering = ["-processed_at"]


class ProcessedImage(models.Model):
    """Represents a processed image with analysis results."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ProcessedDocument, on_delete=models.CASCADE, related_name="images", null=True, blank=True
    )
    image_file = models.FileField(upload_to="processed_images/", null=True, blank=True)
    page_number = models.IntegerField(null=True, blank=True, default=1)
    ocr_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a string representation of the ProcessedImage."""
        doc_name = self.document.filename if self.document else "Unknown Document"
        return f"Page {self.page_number or 'Unknown'} of {doc_name}"

    class Meta:
        """Model metadata for ProcessedImage."""

        verbose_name = "Processed Image"
        verbose_name_plural = "Processed Images"
        ordering = ["-created_at"]

    def __str__(self):
        """Return a string representation of the processed image."""
        return f"{self.image_file.name} ({self.status})"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, Dict[str, int]]:
        """Override delete to ensure all files are cleaned up."""
        # Delete the physical files
        if self.image_file:
            if os.path.exists(self.image_file.path):
                os.remove(self.image_file.path)

        # Delete the model instance
        return super().delete(*args, **kwargs)


@receiver(pre_delete, sender=DocumentBatch)
def delete_batch_files(
    sender: Type[DocumentBatch], instance: DocumentBatch, **kwargs: Dict[str, Any]
) -> None:
    """Delete all files associated with a batch before deleting the batch."""
    batch_dir = os.path.join(settings.MEDIA_ROOT, f"batches/{instance.id}")
    if os.path.exists(batch_dir):
        shutil.rmtree(batch_dir)


@receiver(post_delete, sender=ProcessedDocument)
def delete_document_files(
    sender: Type[ProcessedDocument],
    instance: ProcessedDocument,
    **kwargs: Dict[str, Any],
) -> None:
    """Delete files associated with a document after deleting the document."""
    # Delete the original file if it exists
    if instance.original_path and os.path.exists(instance.original_path):
        os.remove(instance.original_path)

    # Delete the text file if it exists
    if instance.text_path and os.path.exists(instance.text_path):
        os.remove(instance.text_path)

    # Delete the parent directory if it's empty
    parent_dir = os.path.dirname(instance.original_path)
    if os.path.exists(parent_dir) and not os.listdir(parent_dir):
        shutil.rmtree(parent_dir)


@receiver(pre_delete, sender=ProcessedImage)
def delete_image_files(
    sender: Type[ProcessedImage],
    instance: ProcessedImage,
    **kwargs: Dict[str, Any],
) -> None:
    """Delete files associated with a processed image before deleting the image."""
    try:
        # Delete the original file if it exists
        if instance.image_file:
            if os.path.exists(instance.image_file.path):
                os.remove(instance.image_file.path)

    except Exception as e:
        print(f"Error deleting image files: {e}")


def get_image_upload_path(instance, filename):
    """Get the upload path for plumbing images."""
    base_prefix = instance.document.title.split("_")[0].replace("CH", "ch")
    new_filename = f"{base_prefix}_{instance.page_number}pg.jpg"
    return f"plumbing_code/final_jpg/{new_filename}"


def get_csv_upload_path(instance, filename):
    """Get the upload path for plumbing tables."""
    try:
        # Get the path from settings or use a default
        tables_path = getattr(settings, "PLUMBING_CODE_PATHS", {}).get(
            "tables", "plumbing_code/tables"
        )
        return str(Path(tables_path) / filename)
    except Exception as e:
        logger.error("Error getting CSV upload path: %s", str(e))
        return str(Path("plumbing_code/tables") / filename)


class PlumbingDocument(models.Model):
    """Main document model that holds the chapter information"""

    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    json_content = models.JSONField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="plumbing_documents")

    def __str__(self):
        return self.title

    class Meta:
        """Model metadata for PlumbingDocument."""

        verbose_name = "Plumbing Document"
        verbose_name_plural = "Plumbing Documents"
        ordering = ["title"]


class PlumbingImage(models.Model):
    """Model to store images from the final_jpg directory."""

    document = models.ForeignKey(PlumbingDocument, on_delete=models.CASCADE, related_name="images")
    page_number = models.IntegerField()
    image = models.ImageField(upload_to=get_image_upload_path)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Model metadata for PlumbingImage."""

        unique_together = ("document", "page_number")
        ordering = ["page_number"]

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, Dict[str, int]]:
        """Override delete to ensure image file is cleaned up."""
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.document.title} - Page {self.page_number}"


class PlumbingTable(models.Model):
    """Model to store CSV tables"""

    document = models.ForeignKey(PlumbingDocument, on_delete=models.CASCADE, related_name="tables")
    page_number = models.IntegerField()
    csv_file = models.FileField(upload_to=get_csv_upload_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Ensure the upload directory exists before saving."""
        if not self.id and not self.csv_file:
            # This is a new instance without a file
            # Create the directory if it doesn't exist
            upload_dir = os.path.join(settings.MEDIA_ROOT, "plumbing_code", "final_csv")
            os.makedirs(upload_dir, exist_ok=True)
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, Dict[str, int]]:
        """Override delete to ensure CSV file is cleaned up."""
        if self.csv_file:
            try:
                # Delete the file from storage
                self.csv_file.delete(save=False)
            except Exception as e:
                print(f"Error deleting CSV file: {e}")
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        """Return a string representation of the table."""
        return f"Table {self.page_number} from {self.document.title}"

    class Meta:
        """Model metadata."""

        verbose_name = "Plumbing Table"
        verbose_name_plural = "Plumbing Tables"
        ordering = ["document", "page_number"]
        unique_together = ("document", "page_number")


@receiver(pre_delete, sender=PlumbingImage)
def delete_plumbing_image_files(
    sender: Type[PlumbingImage],
    instance: PlumbingImage,
    **kwargs: Dict[str, Any],
) -> None:
    """Delete image file before deleting the PlumbingImage instance."""
    if instance.image:
        try:
            instance.image.delete(False)
        except Exception as e:
            print(f"Error deleting plumbing image file: {e}")
