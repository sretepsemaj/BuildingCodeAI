#!/usr/bin/env python3

import logging
import os

from main.utils.text_processor import TextProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def process_images_to_text():
    """Process all images in the OCR directory and extract text."""
    # Define input and output directories
    base_dir = "/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai/main/media/plumbing_code"
    input_dir = os.path.join(base_dir, "optimized/OCR")
    output_dir = os.path.join(base_dir, "text")

    # Ensure input directory exists
    if not os.path.exists(input_dir):
        logger.error(f"Input directory does not exist: {input_dir}")
        return

    # Create text processor
    processor = TextProcessor(input_dir, output_dir)
    logger.info(f"Processing images from: {input_dir}")
    logger.info(f"Saving text files to: {output_dir}")

    # Process all images
    results = processor.process_all_images()

    # Print detailed results
    print("\n" + "=" * 50)
    print("Processing Results Summary")
    print("=" * 50)
    print(f"Total files processed: {results['stats']['total']}")
    print(f"Successfully processed: {results['stats']['success']}")
    print(f"Failed: {results['stats']['failed']}")

    if results["processed_files"]:
        print("\nSuccessfully Processed Files:")
        print("-" * 30)
        for file in results["processed_files"]:
            print(f"\nImage: {file['image_file']}")
            print(f"Text File: {file['text_file']}")

            # Read and display first few lines of extracted text
            text_path = os.path.join(output_dir, file["text_file"])
            try:
                with open(text_path, "r", encoding="utf-8") as f:
                    text_preview = f.read(200)  # Read first 200 characters
                print("\nText Preview:")
                print(f"{text_preview}...")
            except Exception as e:
                print(f"Could not read text file: {str(e)}")

    if results["failed_files"]:
        print("\nFailed Files:")
        print("-" * 30)
        for file in results["failed_files"]:
            print(f"\nFilename: {file['filename']}")
            print(f"Error: {file['error']}")

    print("\n" + "=" * 50)
    return results


def main():
    """Main entry point for the script."""
    try:
        process_images_to_text()
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise


if __name__ == "__main__":
    main()
