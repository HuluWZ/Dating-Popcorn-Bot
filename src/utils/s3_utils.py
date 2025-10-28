"""
AWS S3 upload utilities for Dating Popcorn Bot

This implementation works with S3 buckets that have:
- ACLs disabled (AccessControlListNotSupported)
- Block Public Access enabled (AccessDenied with BlockPublicAcls)

Files are uploaded privately and accessed via presigned URLs that expire in 1 year.
This approach is more secure and works with modern S3 bucket configurations.
"""

import os
import uuid
import logging
from io import BytesIO
from typing import Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from config.settings import AWS_REGION, S3_BUCKET_NAME

logger = logging.getLogger(__name__)

class S3UploadError(Exception):
    """Custom exception for S3 upload errors"""
    pass

async def upload_to_s3(file_data: BytesIO, file_extension: str, folder: str = "reviews") -> str:
    """
    Upload file data to S3 and return presigned URL for private access
    
    Args:
        file_data: BytesIO object containing file data
        file_extension: File extension (e.g., 'jpg', 'png')
        folder: S3 folder path (default: 'reviews')
    
    Returns:
        Presigned URL for accessing the uploaded file
    
    Raises:
        S3UploadError: If upload fails
    """
    try:
        # Generate unique key
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        s3_key = f"{folder}/{unique_filename}"
        
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Reset file pointer to beginning
        file_data.seek(0)
        
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
        
        # Generate presigned URL for private access (expires in 1 year)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=31536000  # 1 year in seconds
        )
        
        logger.info(f"Successfully uploaded file to S3: {presigned_url}")
        logger.info(f"S3 upload details: bucket={S3_BUCKET_NAME}, key={s3_key}, content_type=image/{file_extension.lower()}")
        return presigned_url
        
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
            logger.error("This bucket has Block Public Access enabled. Files are uploaded privately with presigned URLs.")
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

def generate_presigned_url(s3_key: str, expiration: int = 31536000) -> str:
    """
    Generate a presigned URL for an existing S3 object
    
    Args:
        s3_key: S3 object key
        expiration: URL expiration time in seconds (default: 1 year)
    
    Returns:
        Presigned URL for accessing the object
    
    Raises:
        S3UploadError: If URL generation fails
    """
    try:
        s3_client = boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=expiration
        )
        
        logger.info(f"Generated presigned URL for S3 key: {s3_key}")
        return presigned_url
        
    except Exception as e:
        error_msg = f"Error generating presigned URL for {s3_key}: {str(e)}"
        logger.error(error_msg)
        raise S3UploadError(error_msg)
