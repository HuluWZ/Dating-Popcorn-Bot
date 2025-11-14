"""
AWS S3 upload utilities for Dating Popcorn Bot

This implementation works with S3 buckets that have:
- ACLs disabled (AccessControlListNotSupported)
- Block Public Access enabled (AccessDenied with BlockPublicAcls)

Files are uploaded privately and accessed via Cloudflare Workers URLs.
This approach is more secure, doesn't expose S3 bucket names, and provides
free CDN benefits with Cloudflare's 50k free requests per day.
"""

import os
import uuid
import logging
from io import BytesIO
from typing import Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config.settings import AWS_REGION, S3_BUCKET_NAME, CLOUDFLARE_WORKER_URL

logger = logging.getLogger(__name__)

class S3UploadError(Exception):
    """Custom exception for S3 upload errors"""
    pass

async def upload_to_s3(file_data: BytesIO, file_extension: str, folder: str = "reviews") -> str:
    """
    Upload file data to S3 and return Cloudflare Worker URL for private access
    
    Args:
        file_data: BytesIO object containing file data
        file_extension: File extension (e.g., 'jpg', 'png')
        folder: S3 folder path (default: 'reviews')
    
    Returns:
        Cloudflare Worker URL for accessing the uploaded file
    
    Raises:
        S3UploadError: If upload fails
    """
    try:
        # Log configuration for testing
        logger.info("=" * 60)
        logger.info("S3 UPLOAD - Starting upload process")
        logger.info(f"Configuration check:")
        logger.info(f"  - Cloudflare Worker URL: {CLOUDFLARE_WORKER_URL}")
        logger.info(f"  - S3 Bucket: {S3_BUCKET_NAME}")
        logger.info(f"  - AWS Region: {AWS_REGION}")
        logger.info(f"  - File extension: {file_extension}")
        logger.info(f"  - Folder: {folder}")
        
        # Verify Cloudflare Worker URL is configured
        if not CLOUDFLARE_WORKER_URL:
            error_msg = "CLOUDFLARE_WORKER_URL is not configured. Please set it in your .env file."
            logger.error(error_msg)
            raise S3UploadError(error_msg)
        
        # Verify URL doesn't contain S3 bucket name (security check)
        if 's3.amazonaws.com' in CLOUDFLARE_WORKER_URL:
            logger.warning(f"WARNING: Cloudflare Worker URL contains 's3.amazonaws.com' - this may be incorrect!")
            logger.warning(f"Expected format: https://your-worker.workers.dev")
            logger.warning(f"Actual URL: {CLOUDFLARE_WORKER_URL}")
        
        # Generate unique key
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        s3_key = f"{folder}/{unique_filename}"
        
        logger.info(f"Generated S3 key: {s3_key}")
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Reset file pointer to beginning
        file_data.seek(0)
        file_size = len(file_data.getvalue())
        logger.info(f"File size: {file_size} bytes")
        
        # Upload file to S3 (private upload, no ACL)
        logger.info(f"Uploading file to S3: bucket={S3_BUCKET_NAME}, key={s3_key}")
        
        s3_client.upload_fileobj(
            file_data,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': f'image/{file_extension.lower()}'
            }
        )
        
        logger.info("✅ S3 upload completed successfully")
        
        # Generate Cloudflare Worker URL instead of presigned URL
        # This avoids exposing S3 bucket names and provides free CDN benefits
        cloudflare_url = f"{CLOUDFLARE_WORKER_URL.rstrip('/')}/{s3_key}"
        
        # Log URL format verification for testing
        logger.info("=" * 60)
        logger.info("URL GENERATION - Cloudflare Worker URL")
        logger.info(f"✅ Generated URL: {cloudflare_url}")
        logger.info(f"URL format verification:")
        logger.info(f"  - Contains 's3.amazonaws.com': {'❌ YES (ERROR!)' if 's3.amazonaws.com' in cloudflare_url else '✅ NO (Good!)'}")
        logger.info(f"  - Contains 'workers.dev': {'✅ YES' if 'workers.dev' in cloudflare_url else '⚠️  NO (may be custom domain)'}")
        logger.info(f"  - Contains 'X-Amz-Algorithm': {'❌ YES (ERROR!)' if 'X-Amz-Algorithm' in cloudflare_url else '✅ NO (Good!)'}")
        logger.info(f"  - Starts with Cloudflare URL: {'✅ YES' if cloudflare_url.startswith(CLOUDFLARE_WORKER_URL.rstrip('/')) else '❌ NO (ERROR!)'}")
        logger.info(f"S3 details:")
        logger.info(f"  - S3 Bucket: {S3_BUCKET_NAME}")
        logger.info(f"  - S3 Key: {s3_key}")
        logger.info(f"  - Content Type: image/{file_extension.lower()}")
        logger.info("=" * 60)
        
        return cloudflare_url
        
    except NoCredentialsError:
        error_msg = "AWS credentials not found. Please check your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
        logger.error(error_msg)
        raise S3UploadError(error_msg)
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        # Handle specific ACL-related errors
        if error_code == 'AccessControlListNotSupported':
            logger.error(f"AWS S3 error ({error_code}): {error_msg}")
            logger.error("This bucket does not allow ACLs. The upload was attempted without ACL settings.")
            raise S3UploadError(f"S3 bucket does not support ACLs: {error_msg}")
        elif error_code == 'AccessDenied' and 'BlockPublicAcls' in error_msg:
            logger.error(f"AWS S3 error ({error_code}): {error_msg}")
            logger.error("This bucket has Block Public Access enabled. Files are uploaded privately and served via Cloudflare Workers.")
            raise S3UploadError(f"S3 bucket blocks public access: {error_msg}")
        else:
            logger.error(f"AWS S3 error ({error_code}): {error_msg}")
            raise S3UploadError(f"AWS S3 error ({error_code}): {error_msg}")
    
    except Exception as e:
        error_msg = f"Unexpected error uploading to S3: {str(e)}"
        logger.error(error_msg)
        raise S3UploadError(error_msg)

def validate_image_file(file_path: str, max_size_mb: int = 5) -> tuple[bool, str]:
    """
    Validate image file
    
    Args:
        file_path: Path to the file
        max_size_mb: Maximum file size in MB
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    allowed_extensions = {'.jpg', '.jpeg', '.png'}
    file_ext = os.path.splitext(file_path.lower())[1]
    
    if file_ext not in allowed_extensions:
        return False, f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            return False, f"File too large. Maximum size: {max_size_mb}MB"
        
        return True, ""
    
    except OSError as e:
        return False, f"Error checking file size: {str(e)}"

def get_file_extension_from_path(file_path: str) -> str:
    """
    Extract file extension from file path
    
    Args:
        file_path: Path to the file
    
    Returns:
        File extension without dot (e.g., 'jpg', 'png')
    """
    return os.path.splitext(file_path.lower())[1].lstrip('.')

def generate_cloudflare_url(s3_key: str) -> str:
    """
    Generate a Cloudflare Worker URL for an existing S3 object
    
    Args:
        s3_key: S3 object key (e.g., 'reviews/uuid.jpg')
    
    Returns:
        Cloudflare Worker URL for accessing the object
    
    Raises:
        S3UploadError: If URL generation fails
    """
    try:
        # Log configuration for testing
        logger.info("=" * 60)
        logger.info("URL GENERATION - Generating Cloudflare Worker URL")
        logger.info(f"Input S3 key: {s3_key}")
        logger.info(f"Cloudflare Worker URL: {CLOUDFLARE_WORKER_URL}")
        
        # Verify Cloudflare Worker URL is configured
        if not CLOUDFLARE_WORKER_URL:
            error_msg = "CLOUDFLARE_WORKER_URL is not configured. Please set it in your .env file."
            logger.error(error_msg)
            raise S3UploadError(error_msg)
        
        # Generate Cloudflare Worker URL
        cloudflare_url = f"{CLOUDFLARE_WORKER_URL.rstrip('/')}/{s3_key}"
        
        # Log URL format verification for testing
        logger.info(f"✅ Generated URL: {cloudflare_url}")
        logger.info(f"URL format verification:")
        logger.info(f"  - Contains 's3.amazonaws.com': {'❌ YES (ERROR!)' if 's3.amazonaws.com' in cloudflare_url else '✅ NO (Good!)'}")
        logger.info(f"  - Contains 'workers.dev': {'✅ YES' if 'workers.dev' in cloudflare_url else '⚠️  NO (may be custom domain)'}")
        logger.info(f"  - Contains 'X-Amz-Algorithm': {'❌ YES (ERROR!)' if 'X-Amz-Algorithm' in cloudflare_url else '✅ NO (Good!)'}")
        logger.info("=" * 60)
        
        return cloudflare_url
        
    except Exception as e:
        error_msg = f"Error generating Cloudflare Worker URL for {s3_key}: {str(e)}"
        logger.error(error_msg)
        raise S3UploadError(error_msg)


def extract_s3_key_from_url(cloudflare_url: str) -> Optional[str]:
    """
    Extract S3 key from Cloudflare Worker URL
    
    Args:
        cloudflare_url: Cloudflare Worker URL (e.g., 'https://worker.workers.dev/reviews/uuid.jpg')
    
    Returns:
        S3 key (e.g., 'reviews/uuid.jpg') or None if URL format is invalid
    """
    try:
        if not cloudflare_url or not CLOUDFLARE_WORKER_URL:
            return None
        
        # Remove Cloudflare Worker URL prefix
        if cloudflare_url.startswith(CLOUDFLARE_WORKER_URL.rstrip('/')):
            s3_key = cloudflare_url[len(CLOUDFLARE_WORKER_URL.rstrip('/')):].lstrip('/')
            return s3_key
        
        return None
    except Exception as e:
        logger.error(f"Error extracting S3 key from URL {cloudflare_url}: {e}")
        return None


async def delete_from_s3(cloudflare_url: str) -> bool:
    """
    Delete file from S3 using Cloudflare Worker URL
    
    Args:
        cloudflare_url: Cloudflare Worker URL of the file to delete
    
    Returns:
        True if deletion succeeded, False otherwise
    """
    try:
        # Extract S3 key from URL
        s3_key = extract_s3_key_from_url(cloudflare_url)
        if not s3_key:
            logger.warning(f"Could not extract S3 key from URL: {cloudflare_url}")
            return False
        
        logger.info(f"Deleting S3 object: bucket={S3_BUCKET_NAME}, key={s3_key}")
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Delete object
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        
        logger.info(f"✅ Successfully deleted S3 object: {s3_key}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            logger.warning(f"S3 object not found (may already be deleted): {s3_key}")
            return True  # Consider it success if already deleted
        else:
            logger.error(f"AWS S3 error deleting object: {error_code} - {e.response['Error']['Message']}")
            return False
    
    except Exception as e:
        logger.error(f"Unexpected error deleting from S3: {e}")
        return False
