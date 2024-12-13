#!/usr/bin/env python3
"""Main processing script for the plumbing code pipeline."""

import importlib
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import django
from django.conf import settings

# Django settings configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings.base")
)

django.setup()

# Get logger from Django's configuration
logger = logging.getLogger("main.utils.process_start")

# Use settings for directory paths
try:
    logs_dir = settings.LOGS_DIR
except AttributeError:
    # Fallback to default logs directory
    logs_dir = Path(__file__).resolve().parent.parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Set up logging
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add file handler
file_handler = logging.handlers.RotatingFileHandler(
    filename=logs_dir / "process_start.log",
    maxBytes=10485760,  # 10MB
    backupCount=3,
    encoding="utf-8",
)
formatter = logging.Formatter(
    "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
    style="{",
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Add console handler for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# List of processes to run in order
PROCESS_ORDER = [
    "process_filename",
    "process_ocr",
    "process_json",
    # Add other processes here
]


def import_module(module_name: str) -> Optional[object]:
    """Safely import a module from the current directory."""
    try:
        # Add the parent directory to sys.path if not already there
        parent_dir = str(Path(__file__).resolve().parent.parent)
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)

        # Import the module from utils package
        module = importlib.import_module(f"utils.{module_name}")
        return module
    except ImportError as e:
        logger.error(f"Could not import {module_name}: {e}")
        return None


def run_process(module_name: str) -> bool:
    """Run a single process module."""
    try:
        module = import_module(module_name)
        if module is None:
            return False

        if hasattr(module, "main"):
            logger.info(f"Running {module_name}")
            result = module.main()
            if result is None or result is True:
                logger.info(f"{module_name} completed successfully")
                return True
            else:
                logger.error(f"{module_name} failed with result: {result}")
                return False
        else:
            logger.error(f"{module_name} has no main function")
            return False

    except Exception as e:
        logger.error(f"Error in {module_name}: {str(e)}", exc_info=True)
        return False


def main():
    """Run all processes in the specified order."""
    logger.info("Starting processing pipeline")

    try:
        # Ensure all required directories exist
        if hasattr(settings, "PLUMBING_CODE_PATHS"):
            for path in settings.PLUMBING_CODE_PATHS.values():
                Path(path).mkdir(parents=True, exist_ok=True)
                logger.info(f"Ensured directory exists: {path}")
    except Exception as e:
        logger.error(f"Error creating directories: {e}", exc_info=True)

    successful = 0
    total = len(PROCESS_ORDER)

    for module_name in PROCESS_ORDER:
        logger.info(f"Starting {module_name}")

        if run_process(module_name):
            successful += 1

        # Wait between processes to ensure proper sequencing
        if module_name != PROCESS_ORDER[-1]:
            logger.info("Waiting 2 seconds before next process...")
            time.sleep(2)

    logger.info(f"Pipeline completed. {successful}/{total} processes successful")
    return successful == total


if __name__ == "__main__":
    main()
