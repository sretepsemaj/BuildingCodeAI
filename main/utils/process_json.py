"""Module for processing and searching JSON data from plumbing code documents."""

import json
import logging
import os
from typing import Dict, List, Optional

from main.utils.json_processor import process_directory, save_json

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JsonProcessor:
    """Class for processing and searching JSON data from plumbing code documents.

    This class provides functionality to:
    - Extract sections from text files
    - Process and save JSON data
    - Search through sections by content or section number
    - Load existing JSON data
    """

    def __init__(self, input_dir: str, output_dir: str):
        """Initialize the JsonProcessor with input and output directories.

        Args:
            input_dir: Directory containing text files to process
            output_dir: Directory where JSON output will be saved
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.json_data = None
        self.output_json = os.path.join(self.output_dir, "text_data.json")

    def run_extraction(self) -> None:
        """Run the text extraction process and save results."""
        try:
            os.makedirs(self.output_dir, exist_ok=True)

            # Process all text files and extract sections
            data = process_directory(self.input_dir)
            if not data:
                logger.warning("No files were processed")
                return

            save_json(data, self.output_json)
            self.json_data = data
            logger.info(f"Processed {len(data)} files. Results saved to {self.output_json}")
        except Exception as e:
            logger.error(f"Failed to run extraction: {str(e)}")
            raise

    def load_json(self, json_file: str) -> None:
        """Load existing JSON data from file.

        Args:
            json_file: Path to JSON file to load

        Raises:
            FileNotFoundError: If JSON file doesn't exist
            json.JSONDecodeError: If JSON file is invalid
        """
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                self.json_data = json.load(f)
            logger.info(f"Loaded data from {json_file}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load JSON file: {str(e)}")
            raise

    def find_sections_by_number(self, section_number: str) -> List[Dict]:
        """Find all sections matching a specific section number.

        Args:
            section_number: Section number to search for

        Returns:
            List of matching sections with file and content information
        """
        self._ensure_data_loaded()

        matching_sections = []
        for file_data in self.json_data:
            for section in file_data["sections"]:
                if section_number in section["section"]:
                    matching_sections.append(
                        {
                            "file": file_data["file_path"],
                            "section": section["section"],
                            "content": section["content"],
                        }
                    )
        return matching_sections

    def get_section_numbers(self) -> List[str]:
        """Get a list of all unique section numbers.

        Returns:
            Sorted list of unique section numbers
        """
        self._ensure_data_loaded()

        section_numbers = set()
        for file_data in self.json_data:
            for section in file_data["sections"]:
                section_numbers.add(section["section"])
        return sorted(list(section_numbers))

    def search_content(self, keyword: str) -> List[Dict]:
        """Search for sections containing specific keywords.

        Args:
            keyword: Term to search for in section content

        Returns:
            List of matching sections with file and content information
        """
        self._ensure_data_loaded()

        results = []
        for file_data in self.json_data:
            for section in file_data["sections"]:
                if keyword.lower() in section["content"].lower():
                    results.append(
                        {
                            "file": file_data["file_path"],
                            "section": section["section"],
                            "content": section["content"],
                        }
                    )
        return results

    def _ensure_data_loaded(self) -> None:
        """Ensure JSON data is loaded before operations.

        Raises:
            ValueError: If no JSON data is loaded
        """
        if not self.json_data:
            # Try to load from default location if exists
            if os.path.exists(self.output_json):
                self.load_json(self.output_json)
            else:
                raise ValueError("No JSON data loaded. Run extraction or load JSON first.")


def main() -> None:
    """Main function to demonstrate usage."""
    try:
        input_dir = (
            "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/text"
        )
        output_dir = (
            "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/json"
        )

        # Create processor instance
        processor = JsonProcessor(input_dir, output_dir)

        # Run extraction
        processor.run_extraction()

        # Example: Find sections containing "storm"
        results = processor.search_content("storm")
        if results:
            logger.info("\nSections containing 'storm':")
            for result in results:
                logger.info(f"\nFile: {os.path.basename(result['file'])}")
                logger.info(f"Section: {result['section']}")
                logger.info(f"Content preview: {result['content'][:200]}...")
        else:
            logger.info("No sections found containing 'storm'")

        # Example: Get all section numbers
        section_numbers = processor.get_section_numbers()
        if section_numbers:
            logger.info("\nFirst 10 unique section numbers:")
            for section in section_numbers[:10]:
                logger.info(section)
        else:
            logger.info("No section numbers found")

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()
