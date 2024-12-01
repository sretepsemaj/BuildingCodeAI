"""Test module for image_groq.py."""

import os
import sys
import unittest

from main.utils.image_groq import GroqImageProcessor

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ANSI color codes
class Colors:
    """Class for ANSI color codes."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class TestGroqImageProcessor(unittest.TestCase):
    """Test cases for GroqImageProcessor class."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.processor = GroqImageProcessor()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.test_image = os.path.join(
            base_dir, "static", "images", "png_files", "1732664257.2506502_6Screenshot4.png"
        )

    def test_process_image(self) -> None:
        """Test processing a single image."""
        if not os.path.exists(self.test_image):
            self.skipTest("Test image not found")

        result = self.processor.process_image(self.test_image)
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("content", result)

        if "error" in result:
            print(f"{Colors.FAIL}Error:{Colors.ENDC} {result['error']}")

        if result["success"]:
            print(f"\n{Colors.BOLD}Content Analysis:{Colors.ENDC}")
            print("=" * 50)

            content = result["content"]
            print(f"\n{Colors.HEADER}Extracted Content:{Colors.ENDC}")
            print("-" * 50)
            print(content)

            # Print content statistics
            print(f"\n{Colors.HEADER}Content Statistics:{Colors.ENDC}")
            print("-" * 50)
            print(f"Total characters: {len(content)}")
            print(f"Approximate words: {len(content.split())}")
            print(f"Number of sections: {content.count('#')}")
            print(f"Number of tables: {content.count('|') // 2}")  # Rough estimate of table rows

    def test_process_directory(self) -> None:
        """Test processing a directory of images."""
        test_dir = os.path.join(os.path.dirname(__file__), "..", "static", "test")
        output_dir = os.path.join(test_dir, "output")

        if not os.path.exists(test_dir):
            self.skipTest("Test directory not found")

        results, error = self.processor.process_directory(test_dir, output_dir)
        self.assertIsInstance(results, list)
        self.assertIsNone(error)


if __name__ == "__main__":
    unittest.main()
