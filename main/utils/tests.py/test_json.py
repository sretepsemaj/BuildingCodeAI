import json
import os
import shutil
import tempfile
import unittest

from main.utils.json_processor import process_directory, save_json


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

        # Create a sample text file
        self.sample_text = """
        SECTION PC 101
        GENERAL

        101.1 Title. This code shall be known and may be cited as the “New York City Plumbing Code,” “NYCPC” or “PC.”
        All section numbers in this code shall be deemed to be preceded by the designation “PC.”

        SECTION PC 102
        APPLICABILITY

        102.1 General. Where there is a conflict between a general requirement and a specific requirement, the specific
        requirement shall govern.

        107.6.2.2 Connection not feasible or not available. Where a public combined or storm sewer is not available,
        or where connection thereto is not feasible, applicants shall submit:

        1. Department of Environmental Protection or applicant certification of unavailability or non-feasi-
        bility. (i) Certification issued by the Department of Environmental Protection that a public storm or com-
        bined sewer is not available or that connection thereto is not feasible. Such certification shall be on forms
        specified by such department (Department of Environmental Protection “house/site connection proposal
        application” or other form as specified in the rules of such department); or (ii) Certification submitted by
        the applicant to the Department of Environmental Protection that a public storm or combined sewer is not
        available or that connection thereto is not feasible, in such cases where the availability and feasibility of
        connection to a public storm or combined sewer are allowed to be certified by the applicant pursuant to
        rules of such department. Certification shall be on forms specified by such department (Department of
        Environmental Protection “house/site connection proposal application” or other form as specified in the
        rules of such department); and

        nv

        . On-site disposal. A proposal for the design and construction of a system for the on-site disposal of storm-
        water conforming to the provisions of this code and other applicable laws and rules including but not
        limited to minimum required distances from lot lines or structures and subsoil conditions. Construction
        documents for such system shall be subject to the approval of the department.

        107.6.3 Post-construction stormwater management facilities. A post-construction stormwater management fa-

        """
        self.sample_file_path = os.path.join(self.input_dir, "sample.txt")
        with open(self.sample_file_path, "w", encoding="utf-8") as f:
            f.write(self.sample_text)

    def tearDown(self):
        """Clean up test environment after each test."""
        shutil.rmtree(self.test_dir)

    def test_process_directory(self):
        """Test processing a directory of text files."""
        data = process_directory(self.input_dir)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["file_path"], self.sample_file_path)

        # We now expect 7 sections: SECTION PC 101, 101.1, SECTION PC 102, 102.1, 107.6.2.2, numbered list item, and 107.6.3
        self.assertEqual(len(data[0]["sections"]), 7)

        # Test some specific sections
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


if __name__ == "__main__":
    unittest.main()
