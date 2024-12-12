"""Django management command to clean up intermediate processing directories."""

import logging
import os
import shutil
from typing import Dict, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/process_broom.log"),
    ],
)
logger = logging.getLogger(__name__)


def get_directory_size(path: str) -> int:
    """Get total size of directory in bytes."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):  # Skip if it's a symbolic link
                total += os.path.getsize(fp)
    return total


def format_size(size_bytes: int) -> str:
    """Format bytes into human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def clean_directory(path: str) -> Tuple[bool, int]:
    """Clean a directory and return success status and space freed."""
    if not os.path.exists(path):
        logger.warning(f"Directory does not exist: {path}")
        return True, 0

    try:
        size_before = get_directory_size(path)
        shutil.rmtree(path)
        logger.info(f"Successfully cleaned directory: {path}")
        return True, size_before
    except Exception as e:
        logger.error(f"Error cleaning directory {path}: {str(e)}")
        return False, 0


class Command(BaseCommand):
    """Django management command to clean up intermediate processing directories."""

    help = "Clean up intermediate processing directories"

    def handle(self, *args, **options):
        """Execute the command."""
        # Directories to clean
        dirs_to_clean = [
            "original",
            "optimizer",
            "OCR",
            "json_processed",
            "json",
        ]

        total_space_freed = 0
        success_count = 0
        error_count = 0

        logger.info("Starting cleanup of intermediate directories")
        self.stdout.write("Starting cleanup of intermediate directories...")

        # Get sizes before cleanup
        sizes_before: Dict[str, int] = {}
        for dir_name in dirs_to_clean:
            path = os.path.join(settings.MEDIA_ROOT, "plumbing_code", dir_name)
            if os.path.exists(path):
                sizes_before[dir_name] = get_directory_size(path)
                msg = f"{dir_name}: Current size {format_size(sizes_before[dir_name])}"
                logger.info(msg)
                self.stdout.write(msg)

        # Clean directories
        for dir_name in dirs_to_clean:
            path = os.path.join(settings.MEDIA_ROOT, "plumbing_code", dir_name)
            msg = f"Cleaning directory: {dir_name}"
            logger.info(msg)
            self.stdout.write(msg)

            success, space_freed = clean_directory(path)
            if success:
                success_count += 1
                total_space_freed += space_freed
                if space_freed > 0:
                    msg = f"Freed {format_size(space_freed)} from {dir_name}"
                    logger.info(msg)
                    self.stdout.write(self.style.SUCCESS(msg))
            else:
                error_count += 1

        # Summary
        logger.info("\nCleanup Summary:")
        self.stdout.write("\nCleanup Summary:")

        msg = f"Total space freed: {format_size(total_space_freed)}"
        logger.info(msg)
        self.stdout.write(self.style.SUCCESS(msg))

        msg = f"Successful cleanups: {success_count}"
        logger.info(msg)
        self.stdout.write(self.style.SUCCESS(msg))

        msg = f"Failed cleanups: {error_count}"
        logger.info(msg)
        self.stdout.write(self.style.ERROR(msg) if error_count > 0 else self.style.SUCCESS(msg))
