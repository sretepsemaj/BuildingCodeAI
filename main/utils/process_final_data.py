#!/usr/bin/env python3
"""Script to process and import plumbing code data into the database."""

import json
import logging
import os
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
    doc: PlumbingDocument, image_dir: str = "media/plumbing_code/optimizer"
) -> None:
    """Process images for a given document."""
    image_path = os.path.join(settings.BASE_DIR, image_dir)
    doc_prefix = doc.title.split("_")[0].replace("CH", "ch")  # Get document prefix and match case
    logger.info(f"Processing images from: {image_path}")
    logger.info(f"Looking for images with prefix: {doc_prefix}")

    # First, get existing images for this document
    existing_images = {img.page_number: img for img in doc.images.all()}

    for filename in os.listdir(image_path):
        logger.debug(f"Checking file: {filename}")
        if not filename.endswith(".jpg") or not filename.lower().startswith(doc_prefix.lower()):
            logger.debug(f"Skipping {filename} - not a matching jpg file")
            continue

        page_number = extract_page_number(filename)
        if page_number is None:
            logger.warning(f"Skipping {filename} - could not extract page number")
            continue

        file_path = os.path.join(image_path, filename)
        try:
            with open(file_path, "rb") as f:
                # If image for this page already exists, update it
                if page_number in existing_images:
                    img = existing_images[page_number]
                    # Delete old file if it exists
                    if img.image:
                        img.image.delete(save=False)
                    img.image = File(f, name=filename)
                    img.save()
                    logger.info(f"Updated existing image: {filename} (Page {page_number})")
                else:
                    # Create new image record
                    img = PlumbingImage.objects.create(
                        document=doc, page_number=page_number, image=File(f, name=filename)
                    )
                    logger.info(f"Created new image: {filename} (Page {page_number})")
        except Exception as e:
            logger.error(f"Error processing image {filename}: {str(e)}")


def process_tables_for_document(
    doc: PlumbingDocument, table_dir: str = "media/plumbing_code/tables"
) -> None:
    """Process CSV tables for a given document."""
    table_path = os.path.join(settings.BASE_DIR, table_dir)
    doc_prefix = doc.title.split("_")[0].replace("CH", "ch")  # Get document prefix and match case
    logger.info(f"Processing tables from: {table_path}")
    logger.info(f"Looking for tables with prefix: {doc_prefix}")

    # First, get existing tables for this document
    existing_tables = {table.page_number: table for table in doc.tables.all()}

    for filename in os.listdir(table_path):
        logger.debug(f"Checking file: {filename}")
        if not filename.endswith(".csv") or not filename.lower().startswith(doc_prefix.lower()):
            logger.debug(f"Skipping {filename} - not a matching csv file")
            continue

        page_number = extract_page_number(filename)
        if page_number is None:
            logger.warning(f"Skipping {filename} - could not extract page number")
            continue

        file_path = os.path.join(table_path, filename)
        try:
            with open(file_path, "r") as f:
                csv_content = f.read()

            # If table for this page already exists, update it
            if page_number in existing_tables:
                table = existing_tables[page_number]
                table.csv_content = csv_content
                table.save()
                logger.info(f"Updated existing table: {filename} (Page {page_number})")
            else:
                # Create new table record
                table = PlumbingTable.objects.create(
                    document=doc, page_number=page_number, csv_content=csv_content
                )
                logger.info(f"Created new table: {filename} (Page {page_number})")
        except Exception as e:
            logger.error(f"Error processing table {filename}: {str(e)}")


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
