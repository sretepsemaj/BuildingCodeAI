from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import uuid
import os
import shutil

class DocumentBatch(models.Model):
    """Represents a batch of processed documents."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_batches')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ])

    @property
    def batch_directory(self):
        """Get the directory path for this batch's files."""
        return os.path.join(settings.MEDIA_ROOT, 'indexes', 'doc_classic', str(self.id))

    def delete(self, *args, **kwargs):
        """Override delete to ensure all files are cleaned up."""
        # Delete all associated documents first
        for doc in self.documents.all():
            if hasattr(doc, 'original_file') and doc.original_file:
                try:
                    doc.original_file.delete()
                except Exception as e:
                    print(f"Error deleting original file: {e}")
            
            if hasattr(doc, 'processed_file') and doc.processed_file:
                try:
                    doc.processed_file.delete()
                except Exception as e:
                    print(f"Error deleting processed file: {e}")
            
            if hasattr(doc, 'text_file') and doc.text_file:
                try:
                    doc.text_file.delete()
                except Exception as e:
                    print(f"Error deleting text file: {e}")

        # Delete the batch directory
        batch_dir = os.path.join(settings.MEDIA_ROOT, f'batches/{self.id}')
        if os.path.exists(batch_dir):
            try:
                shutil.rmtree(batch_dir)
            except Exception as e:
                print(f"Error deleting batch directory: {e}")

        # Call the parent delete method
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Batch {self.id} ({self.status})"

class ProcessedDocument(models.Model):
    """Represents a single processed document."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DocumentBatch, on_delete=models.CASCADE, related_name='documents')
    filename = models.CharField(max_length=255)
    original_path = models.CharField(max_length=255, null=True, blank=True)
    text_path = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('failed', 'Failed')
    ])
    error_message = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        """Override delete to ensure all files are cleaned up."""
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
        super().delete(*args, **kwargs)

    @property
    def original_url(self):
        """Get the URL for the original file."""
        if self.original_path:
            # Ensure the path starts with media/
            path = self.original_path.lstrip('/')
            if not path.startswith('media/'):
                path = os.path.join('media', path)
            return f"/{path}"
        return None

    @property
    def text_url(self):
        """Get the URL for the processed text file."""
        if self.text_path:
            # Ensure the path starts with media/
            path = self.text_path.lstrip('/')
            if not path.startswith('media/'):
                path = os.path.join('media', path)
            return f"/{path}"
        return None

    def get_text_content(self):
        """Get the extracted text content."""
        try:
            if self.text_path:
                full_path = os.path.join(settings.MEDIA_ROOT, self.text_path.lstrip('/'))
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                else:
                    return f"Error: Text file not found at {full_path}"
            return None
        except Exception as e:
            return f"Error reading text content: {str(e)}"

    def delete(self, *args, **kwargs):
        try:
            if self.original_path:
                full_path = os.path.join(settings.MEDIA_ROOT, self.original_path.lstrip('/'))
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            if self.text_path:
                full_path = os.path.join(settings.MEDIA_ROOT, self.text_path.lstrip('/'))
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            super().delete(*args, **kwargs)
        except Exception as e:
            print(f"Error in document deletion: {e}")
            raise

    def __str__(self):
        return f"Document {self.filename} ({self.status})"
