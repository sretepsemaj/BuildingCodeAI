import logging
import os
import re
import shutil
import sys
from pathlib import Path

import django

# Add the project root to the Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Set up logging
logger = logging.getLogger("main.utils.process_filename")

# Ensure we have a console handler if running standalone
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

# Define base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = {
    "ocr": PLUMBING_CODE_DIR / "OCR",
    "optimizer": PLUMBING_CODE_DIR / "optimizer",
    "embeddings": PLUMBING_CODE_DIR / "embeddings",
    "json": PLUMBING_CODE_DIR / "json",
    "json_final": PLUMBING_CODE_DIR / "json_final",
    "json_processed": PLUMBING_CODE_DIR / "json_processed",
    "original": PLUMBING_CODE_DIR / "original",
    "tables": PLUMBING_CODE_DIR / "tables",
    "text": PLUMBING_CODE_DIR / "text",
    "uploads": PLUMBING_CODE_DIR / "uploads",
}


def extract_chapter_page(filename: str) -> tuple:
    """Extract chapter and page numbers from filename."""
    # Remove file extension
    name = os.path.splitext(filename)[0]

    # Try different patterns
    patterns = [
        r"(\d+).*?(\d+)",  # matches "5Screenshot3" or "8...12"
        r"chapter[_]?(\d+)[_]?(\d+)page",  # matches "chapter_2_1page" or "chapter2_1page"
        r"NYCP(\d+)ch[_](\d+)pg",  # matches existing NYCP format
    ]

    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)

    return None, None


def generate_nycp_name(chapter: str, page: str, ext: str) -> str:
    """Generate filename in NYCP format."""
    return f"NYCP{chapter}ch_{page}pg{ext}"


def rename_files(directory: str) -> None:
    """Rename files in the specified directory to NYCP format."""
    logger.info(f"Starting file renaming in directory: {directory}")

    try:
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        # Get list of files in directory (excluding hidden files)
        files = [
            f
            for f in os.listdir(directory)
            if not f.startswith(".") and os.path.isfile(os.path.join(directory, f))
        ]
        logger.info(f"Found {len(files)} files to process")

        for filename in files:
            try:
                logger.info(f"Processing file: {filename}")
                filepath = os.path.join(directory, filename)

                # Extract chapter and page numbers
                chapter, page = extract_chapter_page(filename)
                if not chapter or not page:
                    logger.warning(f"Could not extract chapter/page from filename: {filename}")
                    continue

                # Generate new filename
                ext = os.path.splitext(filename)[1]
                new_name = generate_nycp_name(chapter, page, ext)
                new_filepath = os.path.join(directory, new_name)

                # Rename file
                shutil.move(filepath, new_filepath)
                logger.info(f"Renamed {filename} to {new_name}")

            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}", exc_info=True)
                continue

        logger.info("File renaming completed successfully")

    except Exception as e:
        logger.error(f"Error during file renaming: {str(e)}", exc_info=True)
        raise


def main():
    """Main function to run the renaming process."""
    logger.info("Starting file renaming process")

    try:
        # Ensure uploads directory exists
        uploads_dir = PLUMBING_CODE_DIRS["uploads"]
        os.makedirs(uploads_dir, exist_ok=True)
        logger.info(f"Uploads directory ensured: {uploads_dir}")

        # Process files in uploads directory
        rename_files(uploads_dir)
        logger.info("File renaming process completed successfully")

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
    print(
        "\nTo use with a specific directory, modify script to pass directory path to rename_files()"
    )
