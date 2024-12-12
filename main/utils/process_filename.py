"""Script to rename uploaded files to NYCP format."""

import logging
import os
import re
import sys
from pathlib import Path

import django
from django.conf import settings

# Add the project root to the Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Get the Django settings module from environment variable or default to base
DJANGO_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.base")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)

# Set up Django environment
django.setup()

# Set up logging using Django's configuration
logger = logging.getLogger("main.utils.process_filename")


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


def rename_files() -> None:
    """Rename files in the uploads directory to NYCP format."""
    uploads_dir = settings.PLUMBING_CODE_PATHS["uploads"]
    logger.info(f"Starting file renaming in directory: {uploads_dir}")

    try:
        # Create directory if it doesn't exist
        os.makedirs(uploads_dir, exist_ok=True)
        logger.info(f"Uploads directory ensured: {uploads_dir}")

        # Get list of files in directory (excluding hidden files)
        files = [
            f
            for f in os.listdir(uploads_dir)
            if not f.startswith(".") and os.path.isfile(os.path.join(uploads_dir, f))
        ]
        logger.info(f"Found {len(files)} files to process")

        for filename in files:
            try:
                logger.info(f"Processing file: {filename}")
                filepath = os.path.join(uploads_dir, filename)

                # Extract chapter and page numbers
                chapter, page = extract_chapter_page(filename)
                if not chapter or not page:
                    logger.warning(f"Could not extract chapter/page from filename: {filename}")
                    continue

                # Generate new filename
                ext = os.path.splitext(filename)[1]
                new_filename = generate_nycp_name(chapter, page, ext)
                new_filepath = os.path.join(uploads_dir, new_filename)

                # Rename file
                if filename != new_filename:
                    os.rename(filepath, new_filepath)
                    logger.info(f"Renamed {filename} to {new_filename}")
                else:
                    logger.info(f"File already in correct format: {filename}")

            except Exception as e:
                logger.error(f"Error processing file {filename}: {e}")
                continue

        logger.info("File renaming completed successfully")

    except Exception as e:
        logger.error(f"Error in rename_files: {e}")
        raise


def main():
    """Main function to run the renaming process."""
    try:
        logger.info("Starting file renaming process")
        rename_files()
        logger.info("File renaming process completed successfully")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
