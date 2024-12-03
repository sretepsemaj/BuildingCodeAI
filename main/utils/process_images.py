import os

from django.conf import settings

from main.utils.image_processor import ImageProcessor


def main():
    """Process images from original directory and save optimized versions."""
    # Define the directories using Django settings
    plumbing_dir = os.path.join(settings.MEDIA_ROOT, "plumbing_code")
    input_dir = os.path.join(plumbing_dir, "original")
    ocr_output_dir = os.path.join(plumbing_dir, "optimized", "OCR")
    base64_output_dir = os.path.join(plumbing_dir, "optimized", "base64")

    # Create output directories if they don't exist
    os.makedirs(ocr_output_dir, exist_ok=True)
    os.makedirs(base64_output_dir, exist_ok=True)

    # Initialize and run the processor
    processor = ImageProcessor(input_dir, ocr_output_dir, base64_output_dir)
    results = processor.process_images()

    # Print results
    print("\nProcessing Results:")
    print(f"Total files processed: {results['stats']['total']}")
    print(f"Successfully processed: {results['stats']['success']}")
    print(f"Failed: {results['stats']['failed']}")

    print("\nProcessed Files:")
    for file in results["processed_files"]:
        print(f"\nOriginal: {file['original_filename']}")
        print(f"New name: {file['new_filename']}")
        print(f"OCR output: {file['ocr_output']}")
        print(f"Base64 output: {file['base64_output']}")

    if results["failed_files"]:
        print("\nFailed Files:")
        for file in results["failed_files"]:
            print(f"\nFilename: {file['filename']}")
            if file["ocr_error"]:
                print(f"OCR Error: {file['ocr_error']}")
            if file["base64_error"]:
                print(f"Base64 Error: {file['base64_error']}")


if __name__ == "__main__":
    main()
