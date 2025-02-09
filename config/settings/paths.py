"""Path configuration for Django settings.

This module defines all the important directory paths used throughout the application.
It ensures consistent file organization and creates necessary directories on startup.
All paths should be defined here to maintain a single source of truth.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Core directories
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"
LOGS_DIR = BASE_DIR / "logs"

# Create core directories
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Plumbing code directory
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIR.mkdir(exist_ok=True)

# Define paths relative to MEDIA_ROOT
PLUMBING_CODE_PATHS = {
    # Image processing paths
    "images": PLUMBING_CODE_DIR / "images",  # Processed images
    "uploads": PLUMBING_CODE_DIR / "uploads",  # User uploaded files
    "ocr": PLUMBING_CODE_DIR / "ocr",  # OCR processing results
    "original": PLUMBING_CODE_DIR / "original",  # Original unmodified files
    # Data processing paths
    "final_csv": PLUMBING_CODE_DIR / "final_csv",  # Final CSV exports
    "embeddings": PLUMBING_CODE_DIR / "embeddings",  # Vector embeddings for search
    # JSON processing paths
    "json": PLUMBING_CODE_DIR / "json",  # Initial JSON data
    "json_final": PLUMBING_CODE_DIR / "json_final",  # Final processed JSON
    "json_processed": PLUMBING_CODE_DIR / "json_processed",  # Intermediate JSON
    "optimizer": PLUMBING_CODE_DIR / "optimizer",  # Optimization results
}

# Create all plumbing code directories
for path in PLUMBING_CODE_PATHS.values():
    path.mkdir(parents=True, exist_ok=True)

# Temporary files directory
TEMP_DIR = MEDIA_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)
