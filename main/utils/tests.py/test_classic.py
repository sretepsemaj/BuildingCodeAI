"""Test cases for the DocClassicProcessor class."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image, ImageDraw, ImageFont

from .doc_classic import DocClassicProcessor


class TestDocClassicProcessor(TestCase):
    """Test cases for the DocClassicProcessor class."""

    def setUp(self):
        """Set up test environment before each test."""
        super().setUp()  # Important: call parent's setUp
        self.temp_dir = tempfile.mkdtemp()
        self.processor = DocClassicProcessor()
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_files")
        os.makedirs(self.test_dir, exist_ok=True)

        # Create a test user
        self.test_user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

        self.test_images = self.create_test_images()

    def tearDown(self):
        """Clean up after each test."""
        super().tearDown()  # Important: call parent's tearDown
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        print("=== Test completed ===\n")

    def create_test_images(self):
        """Create test images with metadata patterns."""
        # Create test images with metadata patterns
        image1_path = os.path.join(self.test_dir, "chapter1.png")
        image2_path = os.path.join(self.test_dir, "chapter2.png")

        # Create image with metadata
        img1 = Image.new("RGB", (1200, 800), color="white")
        d1 = ImageDraw.Draw(img1)

        # Text properties
        text_color = "black"
        bg_color = "white"
        spacing = 200  # Increased spacing
        font_size = 48  # Larger font
        try:
            font = ImageFont.truetype("Arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        def draw_text_with_background(draw, pos, text):
            # Draw white background for better contrast
            text_bbox = draw.textbbox(pos, text, font=font)
            # Add extra padding around text
            padding = 10
            draw.rectangle(
                [
                    text_bbox[0] - padding,
                    text_bbox[1] - padding,
                    text_bbox[2] + padding,
                    text_bbox[3] + padding,
                ],
                fill="white",
                outline="black",
            )
            # Draw text
            draw.text(pos, text, fill="black", font=font)

        # Draw text with consistent spacing and clear formatting
        draw_text_with_background(d1, (100, 100), "CHAPTER 1")
        draw_text_with_background(d1, (100, 100 + spacing), "SECTION PC-101")
        draw_text_with_background(d1, (100, 100 + spacing * 2), "BUILDING CODE REQUIREMENTS")
        draw_text_with_background(d1, (100, 100 + spacing * 3), "1.2 General Requirements")

        # Save with high quality
        img1.save(image1_path, quality=100, dpi=(600, 600))
        print(f"Created test image at: {image1_path}")

        # Create second test image
        img2 = Image.new("RGB", (1200, 800), color="white")
        d2 = ImageDraw(img2)

        # Chapter 2 content
        draw_text_with_background(d2, (100, 100), "CHAPTER 2")
        draw_text_with_background(d2, (100, 100 + spacing), "SECTION PC-201")
        draw_text_with_background(d2, (100, 100 + spacing * 2), "BUILDING CODE REQUIREMENTS")
        draw_text_with_background(d2, (100, 100 + spacing * 3), "2.1 Definitions")

        img2.save(image2_path, quality=100, dpi=(600, 600))
        print(f"Created test image at: {image2_path}")

        return [image1_path, image2_path]

    def test_initialization(self) -> None:
        """Test if the processor initializes correctly."""
        print("\nTesting initialization...")
        self.assertIsNotNone(self.processor)
        self.assertTrue(os.path.exists(self.processor.source_dir))
        self.assertTrue(os.path.exists(self.processor.output_dir))
        print("Initialization successful")

    def test_metadata_extraction(self):
        """Test metadata extraction from text."""
        print("\n=== Starting new test ===\n")
        print("Testing metadata extraction...")

        test_text = """BUILDING CODE REQUIREMENTS
CHAPTER 1
SECTION PC-101
1.2 General Requirements"""

        metadata = self.processor.extract_metadata(test_text)

        self.assertEqual(metadata["title"], "BUILDING CODE REQUIREMENTS")
        self.assertEqual(metadata["chapter"], "1")
        self.assertEqual(metadata["section_pc"], "PC-101")
        self.assertEqual(metadata["section"], "1.2")

    def test_process_single_image(self):
        """Test processing a single document."""
        print("\n=== Starting new test ===\n")
        print("Testing single image processing...")

        try:
            # Process the first test image
            with open(self.test_images[0], "rb") as img_file:
                result = self.processor.process_single(img_file)

            self.assertIsNotNone(result)
            self.assertIn("title", result)
            self.assertEqual(result["title"], "BUILDING CODE REQUIREMENTS")
            self.assertEqual(result["chapter"], "1")
            self.assertEqual(result["section_pc"], "PC-101")

        except Exception as e:
            self.fail(f"Processing failed with error: {str(e)}")

    def test_process_folder_success(self):
        """Test successful processing of a folder of documents."""
        print("\n=== Starting new test ===\n")
        print("Testing batch processing...")

        try:
            results = self.processor.process_folder(
                folder_path=self.test_dir, batch_name="Test Batch", user=self.test_user
            )

            self.assertIsNotNone(results)
            self.assertIn("batch_id", results)
            self.assertIn("successful", results)
            self.assertIn("total_documents", results)
            self.assertEqual(results["total_documents"], 2)  # We created 2 test images

        except Exception as e:
            self.fail(f"Error in batch processing: {str(e)}")

    def test_process_folder_empty(self):
        """Test processing an empty folder."""
        print("\n=== Starting new test ===\n")
        print("Testing empty folder processing...")

        try:
            empty_dir = os.path.join(self.temp_dir, "empty_folder")
            os.makedirs(empty_dir, exist_ok=True)

            results = self.processor.process_folder(
                folder_path=empty_dir, batch_name="Empty Batch", user=self.test_user
            )

            self.assertIsNotNone(results)
            self.assertIn("batch_id", results)
            self.assertIn("successful", results)
            self.assertIn("total_documents", results)
            self.assertEqual(results["total_documents"], 0)  # Empty folder

        except Exception as e:
            self.fail(f"Error in empty folder processing: {str(e)}")

    def test_process_folder_invalid_files(self):
        """Test processing a folder with invalid file types."""
        print("\n=== Starting new test ===\n")
        print("Testing invalid file processing...")

        try:
            invalid_dir = os.path.join(self.temp_dir, "invalid_folder")
            os.makedirs(invalid_dir, exist_ok=True)

            # Create an invalid file (not an image)
            with open(os.path.join(invalid_dir, "invalid_file.txt"), "w") as f:
                f.write("This is not an image.")

            results = self.processor.process_folder(
                folder_path=invalid_dir, batch_name="Invalid Batch", user=self.test_user
            )

            self.assertIsNotNone(results)
            self.assertIn("batch_id", results)
            self.assertIn("successful", results)
            self.assertIn("total_documents", results)
            self.assertEqual(results["total_documents"], 0)  # Invalid file

        except Exception as e:
            self.fail(f"Error in invalid file processing: {str(e)}")

    def test_batch_processing(self):
        """Test batch processing functionality."""
        print("\n=== Starting new test ===\n")
        print("Testing batch processing...")

        try:
            results = self.processor.process_folder(
                folder_path=self.test_dir, batch_name="Test Batch", user=self.test_user
            )

            self.assertIsNotNone(results)
            self.assertIn("batch_id", results)
            self.assertIn("successful", results)
            self.assertIn("total_documents", results)
            self.assertEqual(results["total_documents"], 2)  # We created 2 test images

        except Exception as e:
            self.fail(f"Error in batch processing: {str(e)}")

    def test_search_documents(self):
        """Test document search functionality."""
        pass

    def test_get_document_stats(self):
        """Test document statistics retrieval."""
        pass


if __name__ == "__main__":
    print("Starting DocClassicProcessor tests...")
    unittest.main(verbosity=2)
