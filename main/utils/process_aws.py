"""Script to upload processed JSON and image files to AWS."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = Path("/Users/aaronjpeters/PlumbingCodeAi/BuildingCodeai")
MEDIA_ROOT = BASE_DIR / "media"
PLUMBING_CODE_DIR = MEDIA_ROOT / "plumbing_code"
PLUMBING_CODE_DIRS = {
    "json_final": PLUMBING_CODE_DIR / "json_final",
    "optimizer": PLUMBING_CODE_DIR / "optimizer",
}

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "buildingcodeai-media")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
    raise ValueError(
        "AWS credentials not found. Please set AWS_ACCESS_KEY_ID and "
        "AWS_SECRET_ACCESS_KEY environment variables."
    )


def get_aws_client():
    """Get AWS S3 client."""
    try:
        s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        return s3_client
    except Exception as e:
        logger.error(f"Error creating AWS client: {str(e)}")
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
        logger.info(f"Successfully uploaded {file_path} to {bucket}/{object_name}")
        return True
    except ClientError as e:
        logger.error(f"Error uploading file {file_path}: {str(e)}")
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
        logger.error(f"Error processing JSON file {json_path}: {str(e)}")
        return []


def upload_files():
    """Upload JSON and image files to AWS S3."""
    try:
        # Process each *_groq.json file
        for json_file in PLUMBING_CODE_DIRS["json_final"].glob("*_groq.json"):
            logger.info(f"Processing {json_file}")

            # Upload JSON file
            json_s3_path = f"json/{json_file.name}"
            if not upload_file(str(json_file), AWS_BUCKET_NAME, json_s3_path):
                raise Exception(f"Failed to upload JSON file: {json_file}")

            # Get referenced image paths and upload them
            image_paths = process_json_file(json_file)
            for img_path in image_paths:
                # Create S3 path maintaining directory structure
                img_s3_path = f"images/{os.path.basename(img_path)}"
                if not upload_file(img_path, AWS_BUCKET_NAME, img_s3_path):
                    logger.warning(f"Failed to upload image: {img_path}")

        logger.info("Successfully completed file upload process")

    except Exception as e:
        logger.error(f"Error in upload process: {str(e)}")
        raise


def main():
    """Main function to handle AWS uploads."""
    try:
        # Check if bucket exists
        s3_client = get_aws_client()
        s3_client.head_bucket(Bucket=AWS_BUCKET_NAME)

        # Upload files
        upload_files()
        logger.info("Successfully completed AWS upload process")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404":
            logger.error(f"Bucket {AWS_BUCKET_NAME} does not exist")
        elif error_code == "403":
            logger.error(f"Access denied to bucket {AWS_BUCKET_NAME}")
        else:
            logger.error(f"Error accessing bucket {AWS_BUCKET_NAME}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise


if __name__ == "__main__":
    main()
