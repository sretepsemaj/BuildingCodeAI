import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS Settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "buildingcode-assets")

# EC2 Settings
AWS_EC2_KEY_PATH = os.getenv("AWS_EC2_KEY_PATH")

# Resource Names
DYNAMODB_TABLE = "plumbing_code_sections"


def get_aws_credentials():
    """Get AWS credentials from environment variables."""
    return {
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "region_name": AWS_REGION,
    }


def get_s3_bucket():
    """Get the S3 bucket name."""
    return AWS_S3_BUCKET


def get_dynamodb_table():
    """Get the DynamoDB table name."""
    return DYNAMODB_TABLE


def get_ec2_key_path():
    """Get the path to the EC2 key file."""
    return AWS_EC2_KEY_PATH
