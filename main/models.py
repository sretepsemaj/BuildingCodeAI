"""Models for the main application."""

import os
import shutil
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver


class DocumentBatch(models.Model):
    """Represents a batch of processed documents."""

    id: uuid.UUID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name: str = models.CharField(max_length=255)
    user: User = models.ForeignKey(User, on_delete=models.CASCADE, related_name="document_batches")
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    status: str = models.CharField(
        max_length=20,
        choices=[
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="processing",
    )

    @property
    def batch_directory(self) -> str:
        """Get the directory path for this batch's files."""
        return os.path.join(settings.MEDIA_ROOT, "indexes", "doc_classic", str(self.id))

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Override delete to ensure all files are cleaned up."""
        result: tuple[int, dict[str, int]] = (0, {})
        
        # Delete all associated documents first
        for doc in self.documents.all():
            if hasattr(doc, "original_file") and doc.original_file:
                try:
                    doc.original_file.delete()
                except Exception as e:
                    print(f"Error deleting original file: {e}")

            if hasattr(doc, "text_file") and doc.text_file:
                try:
                    doc.text_file.delete()
                except Exception as e:
                    print(f"Error deleting text file: {e}")

        # Delete the batch directory if it exists
        batch_dir = self.batch_directory
        if os.path.exists(batch_dir):
            try:
                shutil.rmtree(batch_dir)
            except Exception as e:
                print(f"Error deleting batch directory: {e}")

        # Call the parent delete method
        result = super().delete(*args, **kwargs)
        return result

    def __str__(self) -> str:
        """String representation of the batch."""
        return f"Batch {self.id} ({self.status})"


class ProcessedDocument(models.Model):
    """Represents a single processed document."""

    id: uuid.UUID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch: DocumentBatch = models.ForeignKey(DocumentBatch, on_delete=models.CASCADE, related_name="documents")
    filename: str = models.CharField(max_length=255)
    original_path: str = models.CharField(max_length=255, null=True, blank=True)
    text_path: Optional[str] = models.CharField(max_length=255, null=True, blank=True)
    status: str = models.CharField(max_length=20, choices=[("success", "Success"), ("failed", "Failed")])
    error_message: Optional[str] = models.TextField(null=True, blank=True)
    processed_at: Optional[datetime] = models.DateTimeField(auto_now_add=True)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Override delete to ensure all files are cleaned up."""
        result: tuple[int, dict[str, int]] = (0, {})
        
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


T = TypeVar("T", bound=models.Model)
SignalCallback = Callable[[Type[T], T, Dict[str, Any]], None]

@receiver(pre_delete, sender=DocumentBatch)  # type: ignore[misc]
def delete_batch_files(sender: Type[DocumentBatch], instance: DocumentBatch, **kwargs: Dict[str, Any]) -> None:
    """Delete all files associated with a batch before deleting the batch."""
    batch_dir = os.path.join(settings.MEDIA_ROOT, f"batches/{instance.id}")
    if os.path.exists(batch_dir):
        shutil.rmtree(batch_dir)


@receiver(post_delete, sender=ProcessedDocument)  # type: ignore[misc]
def delete_document_files(sender: Type[ProcessedDocument], instance: ProcessedDocument, **kwargs: Dict[str, Any]) -> None:
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
