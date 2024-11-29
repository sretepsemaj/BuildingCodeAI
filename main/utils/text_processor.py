import logging
import os
from typing import Dict, List, Optional

import pytesseract
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TextProcessor:
    """Process optimized images using OCR to extract text content."""

    def __init__(self, input_dir: str, output_dir: str):
        """Initialize the TextProcessor.

        Args:
            input_dir: Directory containing optimized images for OCR
            output_dir: Directory to save extracted text files
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def process_image_to_text(self, image_path: str) -> Optional[str]:
        """Convert a single image to text using OCR.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text if successful, None otherwise
        """
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            return None

    def save_text_to_file(self, text: str, output_path: str) -> bool:
        """Save extracted text to a file.

        Args:
            text: Extracted text content
            output_path: Path to save the text file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception as e:
            logger.error(f"Error saving text to {output_path}: {str(e)}")
            return False

    def process_all_images(self) -> Dict:
        """Process all images in the input directory and save text files.

        Returns:
            Dictionary containing processing statistics and results
        """
        results = {
            "processed_files": [],
            "failed_files": [],
            "stats": {"total": 0, "success": 0, "failed": 0},
        }

        # Get all image files
        image_files = [
            f for f in os.listdir(self.input_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        results["stats"]["total"] = len(image_files)

        for image_file in image_files:
            image_path = os.path.join(self.input_dir, image_file)
            output_path = os.path.join(self.output_dir, os.path.splitext(image_file)[0] + ".txt")

            logger.info(f"Processing {image_file}")

            # Extract text from image
            text = self.process_image_to_text(image_path)
            if text is None:
                results["failed_files"].append(
                    {"filename": image_file, "error": "OCR extraction failed"}
                )
                results["stats"]["failed"] += 1
                continue

            # Save text to file
            if self.save_text_to_file(text, output_path):
                results["processed_files"].append(
                    {"image_file": image_file, "text_file": os.path.basename(output_path)}
                )
                results["stats"]["success"] += 1
            else:
                results["failed_files"].append(
                    {"filename": image_file, "error": "Failed to save text file"}
                )
                results["stats"]["failed"] += 1

        return results


def main():
    """Main function to run the text processor."""
    # Define directories
    input_dir = (
        "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/optimized/OCR"
    )
    output_dir = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code/text"

    # Initialize and run the processor
    processor = TextProcessor(input_dir, output_dir)
    results = processor.process_all_images()

    # Print results
    print("\nProcessing Results:")
    print(f"Total files processed: {results['stats']['total']}")
    print(f"Successfully processed: {results['stats']['success']}")
    print(f"Failed: {results['stats']['failed']}")

    print("\nProcessed Files:")
    for file in results["processed_files"]:
        print(f"\nImage: {file['image_file']}")
        print(f"Text: {file['text_file']}")

    if results["failed_files"]:
        print("\nFailed Files:")
        for file in results["failed_files"]:
            print(f"\nFilename: {file['filename']}")
            print(f"Error: {file['error']}")


if __name__ == "__main__":
    main()
