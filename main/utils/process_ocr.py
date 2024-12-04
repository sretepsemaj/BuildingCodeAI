import os
import shutil
from typing import Dict, List

import pytesseract
from PIL import Image


def ensure_directories(base_dir: str) -> Dict[str, str]:
    """Ensure all required directories exist."""
    dirs = {
        "uploads": os.path.join(base_dir, "uploads"),
        "ocr": os.path.join(base_dir, "OCR"),
        "original": os.path.join(base_dir, "original"),
    }

    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    return dirs


def process_image(image_path: str, output_path: str) -> Dict:
    """Process a single image with OCR."""
    try:
        # Open and process image
        with Image.open(image_path) as img:
            # Extract text using OCR
            text = pytesseract.image_to_string(img)

            # Save OCR text
            text_path = output_path.rsplit(".", 1)[0] + ".txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)

            return {"success": True, "text_path": text_path, "error": None}
    except Exception as e:
        return {"success": False, "text_path": None, "error": str(e)}


def main():
    """Process images from uploads directory, save OCR results, and move originals."""
    # Setup directories
    base_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "media", "plumbing_code"
    )
    dirs = ensure_directories(base_dir)

    # Get list of files to process
    files = [
        f
        for f in os.listdir(dirs["uploads"])
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
    ]

    results = {
        "processed": [],
        "failed": [],
        "stats": {"total": len(files), "success": 0, "failed": 0},
    }

    # Process each file
    for filename in files:
        input_path = os.path.join(dirs["uploads"], filename)
        ocr_output_path = os.path.join(dirs["ocr"], filename)
        original_dest_path = os.path.join(dirs["original"], filename)

        print(f"Processing {filename}...")

        # Process the image
        result = process_image(input_path, ocr_output_path)

        if result["success"]:
            # Move original file to original directory
            shutil.move(input_path, original_dest_path)
            results["processed"].append(
                {
                    "filename": filename,
                    "ocr_path": result["text_path"],
                    "original_path": original_dest_path,
                }
            )
            results["stats"]["success"] += 1
        else:
            results["failed"].append({"filename": filename, "error": result["error"]})
            results["stats"]["failed"] += 1

    # Print summary
    print("\nProcessing Summary:")
    print(f"Total files: {results['stats']['total']}")
    print(f"Successfully processed: {results['stats']['success']}")
    print(f"Failed: {results['stats']['failed']}")

    if results["processed"]:
        print("\nSuccessfully Processed Files:")
        for item in results["processed"]:
            print(f"\nFile: {item['filename']}")
            print(f"OCR output: {item['ocr_path']}")
            print(f"Original moved to: {item['original_path']}")

    if results["failed"]:
        print("\nFailed Files:")
        for item in results["failed"]:
            print(f"\nFile: {item['filename']}")
            print(f"Error: {item['error']}")


if __name__ == "__main__":
    main()
