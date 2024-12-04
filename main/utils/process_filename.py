import os
import re
from pathlib import Path


def get_numbers_from_filename(filename: str) -> tuple:
    """Extract chapter and page numbers from filename using various patterns."""
    # Remove file extension
    name = os.path.splitext(filename)[0]

    # Pattern 1: XScreenshotY (e.g., 8Screenshot1)
    match = re.match(r"(\d+)Screenshot(\d+)", name)
    if match:
        return match.groups()

    # Pattern 2: chapter_X_Ypage or chapterX_Ypage (e.g., chapter_2_1page or chapter2_1page)
    match = re.search(r"chapter[_]?(\d+)[_](\d+)page", name, re.IGNORECASE)
    if match:
        return match.groups()

    # Pattern 3: X...Y (e.g., 3......12)
    match = re.match(r"(\d+)[.]+(\d+)", name)
    if match:
        return match.groups()

    # Pattern 4: Just look for first two numbers in the filename
    numbers = re.findall(r"\d+", name)
    if len(numbers) >= 2:
        return numbers[0], numbers[1]

    return None


def rename_files(directory_path: str):
    """Rename files in directory to NYCP format in place."""
    # Ensure directory exists
    directory = Path(directory_path)
    if not directory.exists():
        print(f"Directory not found: {directory_path}")
        return

    # Get all files in directory
    files = sorted(os.listdir(directory))

    for filename in files:
        if filename in [".DS_Store", ".gitkeep"]:
            continue

        # Get file path
        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
            continue

        # Get file extension
        _, ext = os.path.splitext(filename)

        # Extract numbers from filename
        result = get_numbers_from_filename(filename)

        if result:
            chapter, page = result
            new_name = f"NYCP{chapter}ch_{page}pg{ext}"

            # Create new file path in same directory
            new_path = os.path.join(directory, new_name)

            # Rename file in place
            os.rename(file_path, new_path)
            print(f"Renamed: {filename} -> {new_name}")
        else:
            print(f"Warning: Could not process {filename} - unknown format")


if __name__ == "__main__":
    # Use current directory if no path provided
    current_dir = os.getcwd()
    rename_files(current_dir)
    print(
        "To use with a specific directory, modify the script to pass your directory "
        "path to rename_files()"
    )
