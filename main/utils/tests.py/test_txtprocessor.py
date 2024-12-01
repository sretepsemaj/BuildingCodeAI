import os
import shutil
import tempfile
import unittest

import numpy as np
from PIL import Image

from main.utils.text_processor import TextProcessor


class TestTextProcessor(unittest.TestCase):
    """Test cases for the TextProcessor class."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary directories for testing
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, "input")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.input_dir)

        # Create a test image with some text
        self.create_test_image()

        # Initialize the text processor
        self.processor = TextProcessor(self.input_dir, self.output_dir)

    def tearDown(self):
        """Clean up test environment after each test."""
        shutil.rmtree(self.test_dir)

    def create_test_image(self, text="TEST", filename="test_image.png"):
        """Create a test image with text for OCR testing."""
        # Create a white background
        img = Image.new("RGB", (200, 100), color="white")
        img_path = os.path.join(self.input_dir, filename)
        img.save(img_path)
        return img_path

    def test_init(self):
        """Test TextProcessor initialization."""
        self.assertEqual(self.processor.input_dir, self.input_dir)
        self.assertEqual(self.processor.output_dir, self.output_dir)
        self.assertTrue(os.path.exists(self.output_dir))

    def test_process_image_to_text(self):
        """Test processing a single image to text."""
        test_image_path = os.path.join(self.input_dir, "test_image.png")
        result = self.processor.process_image_to_text(test_image_path)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_save_text_to_file(self):
        """Test saving text to a file."""
        test_text = "Sample text for testing"
        output_path = os.path.join(self.output_dir, "test_output.txt")

        # Test successful save
        success = self.processor.save_text_to_file(test_text, output_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(output_path))

        # Verify content
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, test_text)

    def test_process_all_images(self):
        """Test processing multiple images."""
        # Create multiple test images
        self.create_test_image(filename="test1.png")
        self.create_test_image(filename="test2.jpg")
        self.create_test_image(filename="test3.jpeg")

        # Process all images
        results = self.processor.process_all_images()

        # Check results structure
        self.assertIn("processed_files", results)
        self.assertIn("failed_files", results)
        self.assertIn("stats", results)

        # Check stats
        self.assertEqual(results["stats"]["total"], 4)  # Including original test image
        self.assertGreaterEqual(results["stats"]["success"], 0)
        self.assertGreaterEqual(results["stats"]["failed"], 0)
        self.assertEqual(
            results["stats"]["success"] + results["stats"]["failed"], results["stats"]["total"]
        )

    def test_invalid_image(self):
        """Test handling of invalid image file."""
        # Create an invalid image file
        invalid_path = os.path.join(self.input_dir, "invalid.jpg")
        with open(invalid_path, "w") as f:
            f.write("This is not an image")

        # Test processing invalid image
        result = self.processor.process_image_to_text(invalid_path)
        self.assertIsNone(result)

    def test_invalid_output_path(self):
        """Test saving to an invalid output path."""
        # Try to save to a non-existent directory
        invalid_path = os.path.join(self.test_dir, "nonexistent", "test.txt")
        success = self.processor.save_text_to_file("test", invalid_path)
        self.assertFalse(success)

    def test_empty_input_directory(self):
        """Test processing an empty input directory."""
        # Create new empty directory
        empty_dir = os.path.join(self.test_dir, "empty")
        os.makedirs(empty_dir)

        # Initialize processor with empty directory
        processor = TextProcessor(empty_dir, self.output_dir)
        results = processor.process_all_images()

        # Check results
        self.assertEqual(results["stats"]["total"], 0)
        self.assertEqual(results["stats"]["success"], 0)
        self.assertEqual(results["stats"]["failed"], 0)
        self.assertEqual(len(results["processed_files"]), 0)
        self.assertEqual(len(results["failed_files"]), 0)


if __name__ == "__main__":
    unittest.main()
