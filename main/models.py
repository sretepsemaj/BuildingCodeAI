"""Models for the main application."""

import os
import uuid

from django.contrib.auth.models import User
from django.db import models


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
    """Represents a processed document."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DocumentBatch, on_delete=models.CASCADE, related_name="documents")
    original_filename = models.CharField(max_length=255)
    processed_file = models.FileField(upload_to="processed_documents/", null=True, blank=True)
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
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        """Return a string representation of the ProcessedDocument."""
        return f"{self.original_filename} ({self.status})"

    class Meta:
        """Meta options for ProcessedDocument model."""

        ordering = ["-created_at"]


class ProcessedImage(models.Model):
    """Represents a processed image from a document."""

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
        doc_name = self.document.original_filename if self.document else "Unknown Document"
        return f"Page {self.page_number or 'Unknown'} of {doc_name}"

    class Meta:
        """Meta options for ProcessedImage model."""

        ordering = ["page_number"]
