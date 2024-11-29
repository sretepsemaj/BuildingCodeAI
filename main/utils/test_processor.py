import os
import shutil
import unittest
from io import BytesIO

from PIL import Image

from main.utils.image_processor import Base64ImageProcessor, ImageProcessor, OCRImageProcessor


class TestImageProcessor(unittest.TestCase):
    """Test suite for the ImageProcessor class and its components."""

    def setUp(self):
        """Set up test environment before each test case."""
        # Create test directories
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_images")
        self.ocr_output_dir = os.path.join(self.test_dir, "ocr_output")
        self.base64_output_dir = os.path.join(self.test_dir, "base64_output")

        # Create directories if they don't exist
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.ocr_output_dir, exist_ok=True)
        os.makedirs(self.base64_output_dir, exist_ok=True)

        # Create test images
        self.create_test_images()

        # Initialize processor
        self.processor = ImageProcessor(self.test_dir, self.ocr_output_dir, self.base64_output_dir)

    def create_test_images(self):
        """Create test images with different formats and names."""
        # Create a simple test image
        img = Image.new("RGB", (100, 100), color="red")

        # Save with different names and formats
        test_images = [
            "chapter1_1page.png",
            "chapter2_3page.jpg",
            "chapter10_5page.jpeg",
            "regular_image.png",
            "test.gif",
        ]

        for filename in test_images:
            img.save(os.path.join(self.test_dir, filename))

    def tearDown(self):
        """Clean up test directories after tests."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_filename_conversion(self):
        """Test filename conversion logic."""
        ocr_processor = OCRImageProcessor(self.test_dir, self.ocr_output_dir)

        test_cases = [
            ("chapter1_1page.png", "NYCP1ch_1pg.jpg"),
            ("chapter2_3page.jpg", "NYCP2ch_3pg.jpg"),
            ("chapter10_5page.jpeg", "NYCP10ch_5pg.jpg"),
            ("regular_image.png", "regular_image.jpg"),
            ("test.gif", "test.jpg"),
        ]

        for input_name, expected_output in test_cases:
            result = ocr_processor.convert_filename(input_name)
            self.assertEqual(result, expected_output)

    def test_image_processing(self):
        """Test full image processing pipeline."""
        # Process all images
        results = self.processor.process_images()

        # Verify success
        self.assertTrue(results["success"])
        self.assertEqual(results["stats"]["total"], 5)  # We created 5 test images
        self.assertEqual(results["stats"]["success"], 5)
        self.assertEqual(results["stats"]["failed"], 0)

        # Check if all processed files exist
        for processed_file in results["processed_files"]:
            # Check OCR output
            self.assertTrue(os.path.exists(processed_file["ocr_output"]))
            self.assertTrue(processed_file["ocr_output"].endswith(".jpg"))

            # Check base64 output
            self.assertTrue(os.path.exists(processed_file["base64_output"]))
            self.assertTrue(processed_file["base64_output"].endswith(".jpg"))

            # Verify filename conversion
            if processed_file["original_filename"].startswith("chapter"):
                self.assertTrue("ch_" in processed_file["new_filename"])
                self.assertTrue("pg.jpg" in processed_file["new_filename"])

    def test_image_formats(self):
        """Test if all image formats are processed correctly."""
        results = self.processor.process_images()

        # Verify all images were processed
        processed_filenames = [f["original_filename"] for f in results["processed_files"]]
        self.assertIn("chapter1_1page.png", processed_filenames)
        self.assertIn("chapter2_3page.jpg", processed_filenames)
        self.assertIn("chapter10_5page.jpeg", processed_filenames)
        self.assertIn("regular_image.png", processed_filenames)
        self.assertIn("test.gif", processed_filenames)

        # Check if all output files are JPG
        for processed_file in results["processed_files"]:
            self.assertTrue(processed_file["ocr_output"].endswith(".jpg"))
            self.assertTrue(processed_file["base64_output"].endswith(".jpg"))

    def test_output_image_quality(self):
        """Test if output images meet quality requirements."""
        results = self.processor.process_images()

        for processed_file in results["processed_files"]:
            # Check OCR output image
            with Image.open(processed_file["ocr_output"]) as img:
                self.assertEqual(img.format, "JPEG")
                self.assertEqual(img.mode, "RGB")
                # Verify size constraints for OCR (max 2000px)
                self.assertLessEqual(max(img.size), 2000)

            # Check base64 output image
            with Image.open(processed_file["base64_output"]) as img:
                self.assertEqual(img.format, "JPEG")
                self.assertEqual(img.mode, "RGB")
                # Verify size constraints for base64 (max 800px)
                self.assertLessEqual(max(img.size), 800)


if __name__ == "__main__":
    unittest.main()
