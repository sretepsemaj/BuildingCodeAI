"""Unit tests for json_wash.py module."""

import json
import os
import tempfile
import unittest

from process_json_wash import extract_metadata_from_raw_text, process_json_data


class TestJsonWash(unittest.TestCase):
    """Test cases for json_wash.py functionality."""

    def setUp(self):
        """Set up test data for each test case."""
        # Sample text data for testing
        self.sample_text_1 = """CHAPTER 1
ADMINISTRATION
This is some content from the "New York City Plumbing Code" document."""

        self.sample_text_2 = """CHAPTER 2
DEFINITIONS
Reference to the "NYC Plumbing Code" standards."""

        self.sample_text_3 = "Just some random text without metadata"

    def test_extract_metadata_chapter_number(self):
        """Test extraction of chapter numbers from text."""
        metadata = extract_metadata_from_raw_text(self.sample_text_1)
        self.assertEqual(metadata["chapter"], 1)

        metadata = extract_metadata_from_raw_text(self.sample_text_2)
        self.assertEqual(metadata["chapter"], 2)

        metadata = extract_metadata_from_raw_text(self.sample_text_3)
        self.assertIsNone(metadata["chapter"])

    def test_extract_metadata_title(self):
        """Test extraction of document titles from text."""
        metadata = extract_metadata_from_raw_text(self.sample_text_1)
        self.assertIsNotNone(metadata["title"])
        self.assertEqual(metadata["title"], "New York City Plumbing Code")

        metadata = extract_metadata_from_raw_text(self.sample_text_2)
        self.assertIsNotNone(metadata["title"])
        self.assertEqual(metadata["title"], "NYC Plumbing Code")

        metadata = extract_metadata_from_raw_text(self.sample_text_3)
        self.assertIsNone(metadata["title"])

    def test_extract_metadata_chapter_title(self):
        """Test extraction of chapter titles from text."""
        metadata = extract_metadata_from_raw_text(self.sample_text_1)
        self.assertEqual(metadata["chapter_title"], "ADMINISTRATION")

        metadata = extract_metadata_from_raw_text(self.sample_text_2)
        self.assertEqual(metadata["chapter_title"], "DEFINITIONS")

        metadata = extract_metadata_from_raw_text(self.sample_text_3)
        self.assertIsNone(metadata["chapter_title"])

    def test_process_json_data(self):
        """Test processing of JSON data and metadata extraction."""
        # Create temporary test files
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as input_file:
            test_data = [
                {
                    "raw_text": self.sample_text_1,
                    "metadata": {"chapter": None, "title": None, "chapter_title": None},
                },
                {
                    "raw_text": self.sample_text_2,
                    "metadata": {"chapter": None, "title": None, "chapter_title": None},
                },
            ]
            json.dump(test_data, input_file)
            input_path = input_file.name

        output_path = input_path + "_processed.json"

        try:
            # Process the test data
            process_json_data(input_path, output_path)

            # Verify the processed output
            with open(output_path, "r", encoding="utf-8") as f:
                processed_data = json.load(f)

            # Check first document
            self.assertEqual(processed_data[0]["metadata"]["chapter"], 1)
            self.assertEqual(processed_data[0]["metadata"]["chapter_title"], "ADMINISTRATION")
            self.assertEqual(processed_data[0]["metadata"]["title"], "New York City Plumbing Code")

            # Check second document
            self.assertEqual(processed_data[1]["metadata"]["chapter"], 2)
            self.assertEqual(processed_data[1]["metadata"]["chapter_title"], "DEFINITIONS")
            self.assertEqual(processed_data[1]["metadata"]["title"], "NYC Plumbing Code")

        finally:
            # Clean up temporary files
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
