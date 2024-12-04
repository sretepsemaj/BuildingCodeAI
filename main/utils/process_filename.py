import os
import re
import shutil
from pathlib import Path

# Define base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = {
    "ocr": PLUMBING_CODE_DIR / "OCR",
    "base64": PLUMBING_CODE_DIR / "base64",
    "embeddings": PLUMBING_CODE_DIR / "embeddings",
    "json": PLUMBING_CODE_DIR / "json",
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
    # Only process image files
    valid_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff")

    try:
        files = os.listdir(directory)
    except Exception as e:
        print(f"Error accessing directory {directory}: {e}")
        return

    for filename in files:
        # Skip system files
        if filename.startswith("."):
            continue

        # Skip if not a file or doesn't have valid extension
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext not in valid_extensions:
            continue

        # Extract chapter and page numbers
        chapter, page = extract_chapter_page(filename)
        if not chapter or not page:
            print(f"Warning: Could not extract chapter/page from {filename}")
            continue

        # Generate new name
        new_name = generate_nycp_name(chapter, page, ext)
        new_path = os.path.join(directory, new_name)

        # Skip if file already has correct name
        if filename == new_name:
            continue

        # Rename file
        try:
            shutil.move(filepath, new_path)
            print(f"Renamed: {filename} -> {new_name}")
        except Exception as e:
            print(f"Error renaming {filename}: {e}")


def main():
    """Main function to run the renaming process."""
    # Ensure uploads directory exists
    uploads_dir = PLUMBING_CODE_DIRS["uploads"]
    if not uploads_dir.exists():
        print(f"Creating uploads directory: {uploads_dir}")
        uploads_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing files in: {uploads_dir}")
    rename_files(str(uploads_dir))


if __name__ == "__main__":
    main()
    print(
        "\nTo use with a specific directory, modify script to pass directory path to rename_files()"
    )
