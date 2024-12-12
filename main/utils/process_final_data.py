#!/usr/bin/env python3
"""Script to process and import plumbing code data into the database."""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from django.core.files import File

# Add project root to Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

# Configure Django settings first
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django  # noqa: E402

django.setup()

# Import Django settings and models after setup
from django.conf import settings  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402

from main.models import PlumbingDocument, PlumbingImage, PlumbingTable  # noqa: E402

# Configure logger
logger = logging.getLogger("main.utils.process_final_data")


def extract_page_number(filename: str) -> Optional[int]:
    """Extract page number from filenames like NYCP3ch_1pg.jpg or NYCP3ch_4pg.csv"""
    try:
        # Find the part between '_' and 'pg'
        parts = filename.split("_")
        if len(parts) < 2:
            return None
        page_num = parts[1].split("pg")[0]
        return int(page_num)
    except (ValueError, IndexError):
        return None


def process_json_files(user: User, json_dir: str = "media/plumbing_code/json_final") -> None:
    """Process JSON files and create PlumbingDocument records."""
    json_path = os.path.join(settings.BASE_DIR, json_dir)
    logger.info(f"Processing JSON files from: {json_path}")

    for filename in os.listdir(json_path):
        if not filename.endswith(".json"):
            continue

        file_path = os.path.join(json_path, filename)
        try:
            with open(file_path, "r") as f:
                json_content = json.load(f)

            # Check if document already exists
            doc_title = filename.replace(".json", "")
            doc, created = PlumbingDocument.objects.get_or_create(
                title=doc_title, user=user, defaults={"json_content": json_content}
            )

            if created:
                logger.info(f"Created new document: {doc.title}")
            else:
                # Update existing document
                doc.json_content = json_content
                doc.save()
                logger.info(f"Updated existing document: {doc.title}")

            # Process related images and tables for this document
            process_images_for_document(doc)
            process_tables_for_document(doc)

        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")


def process_images_for_document(
    doc: PlumbingDocument,
) -> None:
    """Process images for a given document."""
    image_path = settings.PLUMBING_CODE_PATHS["optimizer"]
    doc_prefix = doc.title.split("_")[0].replace("CH", "ch")

    logger.info(f"Processing images from: {image_path}")
    logger.info(f"Looking for images with prefix: {doc_prefix}")

    # First, get existing images for this document
    existing_images = {img.page_number: img for img in doc.images.all()}

    # Track which files we've found for each page
    page_files = {}

    # First pass: catalog all files by page number
    for filename in os.listdir(image_path):
        if not filename.endswith(".jpg") or not filename.lower().startswith(doc_prefix.lower()):
            continue

        page_number = extract_page_number(filename)
        if page_number is None:
            continue

        # Prefer files without random suffixes
        if page_number not in page_files or "_" not in filename:
            page_files[page_number] = filename

    # Second pass: process files
    for page_number, source_filename in page_files.items():
        source_path = os.path.join(image_path, source_filename)
        if not os.path.exists(source_path):
            logger.warning(f"Source file not found: {source_path}")
            continue

        try:
            with open(source_path, "rb") as f:
                # If image for this page already exists, update it
                if page_number in existing_images:
                    img = existing_images[page_number]
                    # Delete old file if it exists
                    if img.image:
                        storage = img.image.storage
                        if storage.exists(img.image.name):
                            storage.delete(img.image.name)
                    # Let Django handle the file naming
                    img.image.save(source_filename, File(f), save=True)
                    logger.info(f"Updated existing image for page {page_number}")
                else:
                    # Create new image record
                    img = PlumbingImage(document=doc, page_number=page_number)
                    # Let Django handle the file naming
                    img.image.save(source_filename, File(f), save=True)
                    logger.info(f"Created new image for page {page_number}")

        except Exception as e:
            logger.error(f"Error processing image {source_filename}: {str(e)}")


def process_tables_for_document(doc: PlumbingDocument) -> None:
    """Process CSV tables for a given document."""
    table_path = settings.PLUMBING_CODE_PATHS["tables"]
    doc_prefix = doc.title.split("_")[0].replace("CH", "ch")

    logger.info(f"Processing tables from: {table_path}")
    logger.info(f"Looking for tables with prefix: {doc_prefix}")

    # Track which pages we've processed
    page_files = {}
    processed_pages = set()

    # First pass: catalog all files by page number
    for filename in os.listdir(table_path):
        if not filename.endswith(".csv") or not filename.lower().startswith(doc_prefix.lower()):
            continue

        page_number = extract_page_number(filename)
        if page_number is None:
            continue

        # Prefer files without random suffixes
        if page_number not in page_files or "_" not in filename:
            page_files[page_number] = filename

    # Second pass: process files
    for page_number, source_filename in page_files.items():
        file_path = os.path.join(table_path, source_filename)
        if not os.path.exists(file_path):
            logger.warning(f"Source file not found: {file_path}")
            continue

        try:
            with open(file_path, "r") as f:
                csv_content = f.read()

            # Try to get existing table first
            try:
                table = PlumbingTable.objects.get(document=doc, page_number=page_number)
                logger.info(f"Updating existing table for page {page_number}")
            except PlumbingTable.DoesNotExist:
                table = PlumbingTable(document=doc, page_number=page_number)
                logger.info(f"Creating new table for page {page_number}")

            # Update the content and save
            table.csv_content = csv_content
            table.save()
            processed_pages.add(page_number)

        except Exception as e:
            logger.error(f"Error processing table {source_filename}: {str(e)}")

    # Clean up any tables in database that weren't in source files
    for table in doc.tables.all():
        if table.page_number not in processed_pages:
            logger.info(f"Removing obsolete table for page {table.page_number}")
            table.delete()


def process_all_data(user: User) -> None:
    """Process all plumbing code data for a given user."""
    try:
        # Start with JSON files, which will trigger processing of related images and tables
        process_json_files(user)
        logger.info("Data processing completed successfully!")
    except Exception as e:
        logger.error(f"Error during data processing: {str(e)}")


def main():
    """Main entry point for the script."""
    try:
        # Get the default user from settings
        default_user = User.objects.get(username=settings.DEFAULT_USERNAME)
        process_json_files(default_user)
    except User.DoesNotExist:
        logger.error(f"Error: User '{settings.DEFAULT_USERNAME}' not found in database")
    except Exception as e:
        logger.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
