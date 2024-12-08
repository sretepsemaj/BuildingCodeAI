#!/usr/bin/env python3
import importlib
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import django

# Add project root to Python path first
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# Create logs directory if it doesn't exist
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

# Set up logging first, before Django setup
logger = logging.getLogger("main.utils.process_start")
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

# Now set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from django.conf import settings  # noqa: E402

# List of processes to run in order
PROCESS_ORDER = [
    "process_filename",
    "process_ocr",
    "process_image",
    "process_json",
    "process_json_wash",
    "process_groq",
]

# Time to wait between processes (in seconds)
WAIT_TIME = 2


def import_module(module_name: str) -> Optional[object]:
    """
    Safely import a module from the current directory.
    """
    try:
        return importlib.import_module(f".{module_name}", package="main.utils")
    except ImportError as e:
        logger.error(f"Failed to import {module_name}: {e}")
        return None


def run_process(module_name: str) -> bool:
    """
    Run a single process module.
    """
    logger.info(f"Starting {module_name}")
    module = import_module(module_name)

    if not module:
        return False

    try:
        # Most modules should have a main() function
        if hasattr(module, "main"):
            module.main()
        # Fallback to other common function names
        elif hasattr(module, "run"):
            module.run()
        elif hasattr(module, "process"):
            module.process()
        else:
            logger.error(f"No entry point found in {module_name}")
            return False

        logger.info(f"Completed {module_name}")
        return True
    except Exception as e:
        logger.error(f"Error running {module_name}: {e}")
        return False


def main():
    """
    Run all processes in the specified order.
    """
    logger.info("Starting processing pipeline")

    success_count = 0
    for process in PROCESS_ORDER:
        if run_process(process):
            success_count += 1
        else:
            logger.warning(f"Process {process} failed or was skipped")

        # Wait between processes
        logger.info(f"Waiting {WAIT_TIME} seconds before next process...")
        time.sleep(WAIT_TIME)

    logger.info(f"Pipeline completed. {success_count}/{len(PROCESS_ORDER)} processes successful")


if __name__ == "__main__":
    main()
