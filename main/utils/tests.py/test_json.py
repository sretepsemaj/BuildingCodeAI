"""Tests for json processor."""

import json
import os
import unittest
from unittest.mock import mock_open, patch

from ..json_processor_wash import (
    extract_chapter_info,
    extract_metadata,
    process_directory,
    process_json_data,
    update_metadata,
)


class TestJsonProcessor(unittest.TestCase):
    """Test cases for json processor functions."""

    def setUp(self):
        """Set up test data."""
        self.test_data = [
            {
                "file_path": "/path/to/NYCP1ch_1pg.txt",
                "base64_file_path": None,
                "metadata": {"chapter": None, "title": None, "chapter_title": None},
                "raw_text": (
                    "CHAPTER 1\nADMINISTRATION\n\nSECTION PC 101\n"
                    '101.1 Title. This code shall be known as the "NYC Plumbing Code"'
                ),
                "sections": [
                    {
                        "section": "101.1 Title",
                        "content": 'This code shall be known as the "NYC Plumbing Code"',
                    }
                ],
            }
        ]

    def test_extract_chapter_info(self):
        """Test extracting chapter info from raw text."""
        raw_text = (
            "CHAPTER 1\nADMINISTRATION\n\nSECTION PC 101\n"
            '101.1 Title. This code shall be known as the "NYC Plumbing Code"'
        )
        chapter_num, chapter_title = extract_chapter_info(raw_text)
        self.assertEqual(chapter_num, 1)
        self.assertEqual(chapter_title, "ADMINISTRATION")

    def test_extract_metadata(self):
        """Test metadata extraction from chapter data."""
        metadata = extract_metadata(self.test_data, 1)
        expected = {
            "chapter": 1,
            "title": "New York City Plumbing Code",
            "chapter_title": "ADMINISTRATION",
        }
        self.assertEqual(metadata, expected)

    def test_update_metadata(self):
        """Test updating metadata for all documents in a chapter."""
        updated_data = update_metadata(self.test_data, 1)
        expected_metadata = {
            "chapter": 1,
            "title": "New York City Plumbing Code",
            "chapter_title": "ADMINISTRATION",
        }
        self.assertEqual(updated_data[0]["metadata"], expected_metadata)

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("json.dump")
    @patch("os.makedirs")
    def test_process_json_data(self, mock_makedirs, mock_dump, mock_load, mock_file):
        """Test processing JSON data end-to-end."""
        mock_load.return_value = self.test_data
        process_json_data("input.json", "output.json")
        mock_makedirs.assert_called_once()
        mock_dump.assert_called_once()

    @patch("os.makedirs")
    @patch("os.listdir")
    @patch("json_processor_wash.process_json_data")
    def test_process_directory(self, mock_process, mock_listdir, mock_makedirs):
        """Test processing all JSON files in a directory."""
        mock_listdir.return_value = ["test1.json", "test2.txt", "test3.json"]
        process_directory("input_dir", "output_dir")
        self.assertEqual(mock_process.call_count, 2)
        mock_makedirs.assert_called_once_with("output_dir", exist_ok=True)


if __name__ == "__main__":
    unittest.main()
