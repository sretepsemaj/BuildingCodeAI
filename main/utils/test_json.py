import json
import os
import shutil
import tempfile
import unittest

from json_processor import process_directory, process_file, save_json


class TestTextJson(unittest.TestCase):
    """Test cases for the text_json.py script."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, "text")
        self.output_dir = os.path.join(self.test_dir, "json")
        os.makedirs(self.input_dir)
        os.makedirs(self.output_dir)

        # Create test file content
        test_content = """
        SECTION PC 101
        GENERAL

        101.1 Title.
        This code shall be known as the "New York City Plumbing
        Code." All section numbers in this code shall be preceded
        by "PC."

        SECTION PC 102
        APPLICABILITY

        102.1 General.
        Where there is a conflict between requirements, the specific
        requirement shall govern.

        107.6.2.2 Connection not feasible or not available.
        Where a public combined or storm sewer is not available, or
        where connection is not feasible:

        1. Department of Environmental Protection certification:
        (i) Certification by DEP that a public storm/combined sewer
        is not available. Such certification shall be on specified
        forms.
        (ii) Applicant certification to DEP about sewer
        unavailability/infeasibility. Certification must be on forms
        specified by the department.

        nv

        On-site disposal:
        A proposal for storm-water disposal system design meeting
        code requirements. Construction documents require department
        approval.

        107.6.3 Post-construction stormwater management facilities.
        """
        self.sample_file_path = os.path.join(self.input_dir, "sample.txt")
        with open(self.sample_file_path, "w", encoding="utf-8") as f:
            f.write(test_content)

    def tearDown(self):
        """Clean up test environment after each test."""
        shutil.rmtree(self.test_dir)

    def test_process_directory(self):
        """Test processing a directory of text files."""
        data = process_directory(self.input_dir)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["file_path"], self.sample_file_path)

        # Verify number of sections
        expected_sections = 7  # PC 101, 101.1, PC 102, 102.1, 107.6.2.2, list item, 107.6.3
        self.assertEqual(len(data[0]["sections"]), expected_sections)

        # Test specific sections
        sections = data[0]["sections"]
        self.assertEqual(sections[0]["section"], "SECTION PC 101")
        self.assertTrue(any(s["section"].startswith("107.6.2.2") for s in sections))
        self.assertTrue(any(s["section"].startswith("1. Department") for s in sections))

    def test_save_json(self):
        """Test saving extracted data to a JSON file."""
        data = process_directory(self.input_dir)
        output_json_path = os.path.join(self.output_dir, "text_data.json")
        save_json(data, output_json_path)

        # Verify JSON file creation
        self.assertTrue(os.path.exists(output_json_path))
        with open(output_json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        self.assertEqual(len(json_data), 1)
        self.assertEqual(json_data[0]["file_path"], self.sample_file_path)

    def test_metadata_extraction(self):
        """Test extraction of metadata from text content."""
        test_content = """
        CHAPTER 1
        ADMINISTRATION

        101.1 Title.
        This code shall be known as the "New York City Plumbing Code."
        All section numbers in this code shall be preceded by "PC."
        """

        with open(os.path.join(self.input_dir, "metadata_test.txt"), "w") as f:
            f.write(test_content)

        data = process_file(os.path.join(self.input_dir, "metadata_test.txt"))

        # Verify metadata
        self.assertEqual(data["metadata"]["chapter"], 1)
        self.assertEqual(data["metadata"]["title"], "New York City Plumbing Code")
        self.assertEqual(data["metadata"]["chapter_title"], "ADMINISTRATION")


if __name__ == "__main__":
    unittest.main()
