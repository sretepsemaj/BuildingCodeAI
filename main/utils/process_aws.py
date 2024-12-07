"""Script to upload processed JSON and image files to AWS."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import boto3
import django
from botocore.exceptions import ClientError
from django.conf import settings
from dotenv import load_dotenv

# Set up logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Load environment variables first
env_path = os.path.join(project_root, ".env")
logger.info("Loading environment variables from: %s", env_path)
logger.info("File exists: %s", os.path.exists(env_path))
load_dotenv(env_path, override=True)

# Then set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

# Define paths
BASE_DIR = Path(project_root)
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = {
    "json_final": PLUMBING_CODE_DIR / "json_final",
    "optimizer": PLUMBING_CODE_DIR / "optimizer",
}

# AWS Configuration from Django settings
logger.info("Loading AWS Configuration from Django settings...")
logger.info("Settings AWS dict: %s", settings.AWS)
AWS_ACCESS_KEY_ID = settings.AWS["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = settings.AWS["AWS_SECRET_ACCESS_KEY"]
AWS_BUCKET_NAME = settings.AWS["AWS_S3_BUCKET"]
AWS_REGION = settings.AWS["AWS_REGION"]

logger.info("AWS Configuration loaded:")
logger.info("Access Key ID: %s", AWS_ACCESS_KEY_ID)
logger.info("Secret Key length: %s", len(AWS_SECRET_ACCESS_KEY))
logger.info("Region: %s", AWS_REGION)
logger.info("Bucket: %s", AWS_BUCKET_NAME)


def get_aws_client():
    """Get AWS S3 client."""
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        logger.info("Using AWS credentials from Django settings")
        return s3_client
    except Exception as e:
        logger.error("Error creating AWS client: %s", str(e))
        raise


def upload_file(file_path: str, bucket: str, object_name: str = None) -> bool:
    """Upload a file to an S3 bucket.

    Args:
        file_path: Path to file to upload
        bucket: Bucket to upload to
        object_name: S3 object name (if different from local file name)

    Returns:
        True if file was uploaded, else False
    """
    # If S3 object_name not specified, use file_path
    if object_name is None:
        object_name = os.path.basename(file_path)

    s3_client = get_aws_client()

    try:
        s3_client.upload_file(file_path, bucket, object_name)
        logger.info("Successfully uploaded %s to %s/%s", file_path, bucket, object_name)
        return True
    except ClientError as e:
        logger.error("Error uploading file %s: %s", file_path, str(e))
        return False


def process_json_file(json_path: Path) -> List[str]:
    """Process a JSON file and return list of referenced image paths.

    Args:
        json_path: Path to JSON file

    Returns:
        List of image paths referenced in the JSON
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract image paths from 'o' field in 'f' entries
        image_paths = []
        for entry in data.get("f", []):
            if "o" in entry and entry["o"]:
                img_path = entry["o"]
                if os.path.exists(img_path):
                    image_paths.append(img_path)

        return image_paths
    except Exception as e:
        logger.error("Error processing JSON file %s: %s", json_path, str(e))
        return []


def upload_files():
    """Upload JSON and image files to AWS S3."""
    try:
        # Process each *_groq.json file
        for json_file in PLUMBING_CODE_DIRS["json_final"].glob("*_groq.json"):
            logger.info("Processing %s", json_file)

            # Upload JSON file
            json_s3_path = "json/%s" % json_file.name
            if not upload_file(str(json_file), AWS_BUCKET_NAME, json_s3_path):
                raise Exception("Failed to upload JSON file: %s" % json_file)

            # Get referenced image paths and upload them
            image_paths = process_json_file(json_file)
            for img_path in image_paths:
                # Create S3 path maintaining directory structure
                img_s3_path = "images/%s" % os.path.basename(img_path)
                if not upload_file(img_path, AWS_BUCKET_NAME, img_s3_path):
                    logger.warning("Failed to upload image: %s", img_path)

        logger.info("Successfully completed file upload process")

    except Exception as e:
        logger.error("Error in upload process: %s", str(e))
        raise


def main():
    """Main function to handle AWS uploads."""
    try:
        # Debug: Print environment variables
        logger.info("Checking environment variables:")
        logger.info("AWS_REGION: %s", AWS_REGION)
        logger.info("AWS_S3_BUCKET: %s", AWS_BUCKET_NAME)

        s3_client = get_aws_client()

        # List all available buckets
        logger.info("Listing all available S3 buckets:")
        response = s3_client.list_buckets()
        for bucket in response["Buckets"]:
            logger.info("Found bucket: %s", bucket["Name"])

        logger.info("\nAttempting to access target bucket: %s", AWS_BUCKET_NAME)
        try:
            s3_client.head_bucket(Bucket=AWS_BUCKET_NAME)
            logger.info("Successfully accessed bucket: %s", AWS_BUCKET_NAME)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.error(
                "Failed to access bucket %s. Error code: %s, Message: %s",
                AWS_BUCKET_NAME,
                error_code,
                error_message,
            )
            if error_code == "404":
                logger.error("Bucket %s does not exist", AWS_BUCKET_NAME)
            elif error_code == "403":
                logger.error("Access denied. Please check your AWS credentials and permissions")
            raise

        # Upload files
        upload_files()
        logger.info("Successfully completed AWS upload process")

    except Exception as e:
        logger.error("Error in main process: %s", str(e))
        raise


if __name__ == "__main__":
    main()
