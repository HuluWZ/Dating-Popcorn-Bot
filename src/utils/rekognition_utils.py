"""
AWS Rekognition utilities for face detection and comparison
"""

import os
import logging
from typing import List, Dict, Optional, Tuple, BinaryIO
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from config.settings import AWS_REGION

logger = logging.getLogger(__name__)

# Minimum face size in pixels (width or height)
MIN_FACE_SIZE = 80
# Minimum confidence for face detection
MIN_FACE_CONFIDENCE = 90.0
# Default match threshold (90%)
DEFAULT_MATCH_THRESHOLD = 90.0


class RekognitionError(Exception):
    """Custom exception for Rekognition errors"""
    pass


class FaceDetectionError(RekognitionError):
    """Error when face detection fails"""
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(message)


class FaceComparisonError(RekognitionError):
    """Error when face comparison fails"""
    pass


def get_rekognition_client():
    """Get AWS Rekognition client"""
    try:
        return boto3.client(
            'rekognition',
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
    except Exception as e:
        logger.error(f"Failed to create Rekognition client: {e}")
        raise RekognitionError(f"Failed to initialize Rekognition client: {e}")


def detect_faces(image_bytes: bytes) -> Dict:
    """
    Detect faces in an image using AWS Rekognition
    
    Args:
        image_bytes: Image data as bytes
        
    Returns:
        Dictionary with face detection results:
        {
            'faces': List of face details,
            'face_count': Number of faces detected,
            'has_faces': Boolean
        }
        
    Raises:
        FaceDetectionError: If detection fails or no faces found
    """
    try:
        rekognition = get_rekognition_client()
        
        logger.info(f"Detecting faces in image ({len(image_bytes)} bytes)")
        
        response = rekognition.detect_faces(
            Image={'Bytes': image_bytes},
            Attributes=['ALL']
        )
        
        faces = response.get('FaceDetails', [])
        face_count = len(faces)
        
        logger.info(f"Detected {face_count} face(s) in image")
        
        # Validate faces
        valid_faces = []
        for i, face in enumerate(faces):
            # Check face quality/confidence
            confidence = face.get('Confidence', 0)
            bounding_box = face.get('BoundingBox', {})
            
            # Calculate face size
            width = bounding_box.get('Width', 0)
            height = bounding_box.get('Height', 0)
            
            # Assume image dimensions (we'll need to get actual dimensions)
            # For now, use relative size - if width/height are very small, face is too small
            # Rekognition returns normalized coordinates (0-1), so we need image dimensions
            # For validation, we'll check if the bounding box is too small
            # A face that's less than ~5% of image width/height is likely too small
            
            if confidence < MIN_FACE_CONFIDENCE:
                logger.warning(f"Face {i+1} has low confidence: {confidence:.1f}% (min: {MIN_FACE_CONFIDENCE}%)")
                continue
            
            # Check if face bounding box is too small (normalized coordinates)
            # If width or height is less than ~0.1 (10% of image), it's likely too small
            # This is approximate - ideally we'd have actual image dimensions
            if width < 0.1 or height < 0.1:
                logger.warning(f"Face {i+1} bounding box too small: {width:.3f} x {height:.3f}")
                continue
            
            valid_faces.append({
                'index': i,
                'confidence': confidence,
                'bounding_box': bounding_box,
                'quality': face.get('Quality', {}),
                'face_details': face
            })
        
        if not valid_faces:
            if face_count == 0:
                raise FaceDetectionError("NO_FACE", "No face detected in the image. Please upload a clear photo with a visible face.")
            else:
                raise FaceDetectionError(
                    "FACE_TOO_SMALL_OR_LOW_QUALITY",
                    "Face too small or low quality. Please upload a clearer, higher resolution photo."
                )
        
        return {
            'faces': valid_faces,
            'face_count': len(valid_faces),
            'has_faces': True,
            'raw_response': response
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Rekognition error ({error_code}): {error_message}")
        
        if error_code == 'InvalidImageFormatException':
            raise FaceDetectionError("INVALID_IMAGE", "Invalid image format. Please upload a JPG or PNG image.")
        elif error_code == 'ImageTooLargeException':
            raise FaceDetectionError("IMAGE_TOO_LARGE", "Image is too large. Maximum size is 15MB.")
        else:
            raise FaceDetectionError("DETECTION_FAILED", f"Face detection failed: {error_message}")
    
    except BotoCoreError as e:
        logger.error(f"AWS service error: {e}")
        raise FaceDetectionError("SERVICE_ERROR", f"AWS service error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in face detection: {e}")
        raise FaceDetectionError("UNEXPECTED_ERROR", f"Unexpected error: {str(e)}")


def compare_faces(source_image_bytes: bytes, target_image_bytes: bytes, similarity_threshold: float = DEFAULT_MATCH_THRESHOLD) -> Dict:
    """
    Compare faces between two images using AWS Rekognition
    
    Args:
        source_image_bytes: Source image data as bytes
        target_image_bytes: Target image data as bytes
        similarity_threshold: Minimum similarity score (0-100)
        
    Returns:
        Dictionary with comparison results:
        {
            'similarity': Similarity score (0-100),
            'is_match': Boolean indicating if similarity >= threshold,
            'face_matches': List of face match details
        }
    """
    try:
        # Validate source image
        is_valid, error_msg = validate_image_bytes(source_image_bytes)
        if not is_valid:
            raise FaceComparisonError(f"Invalid source image: {error_msg}")
        
        # Validate target image
        is_valid, error_msg = validate_image_bytes(target_image_bytes)
        if not is_valid:
            raise FaceComparisonError(f"Invalid target image: {error_msg}")
        
        rekognition = get_rekognition_client()
        
        logger.info(f"Comparing faces (threshold: {similarity_threshold}%) - source: {len(source_image_bytes)} bytes, target: {len(target_image_bytes)} bytes")
        
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source_image_bytes},
            TargetImage={'Bytes': target_image_bytes},
            SimilarityThreshold=similarity_threshold
        )
        
        face_matches = response.get('FaceMatches', [])
        unmatched_faces = response.get('UnmatchedFaces', [])
        
        # Get the highest similarity score
        max_similarity = 0.0
        if face_matches:
            max_similarity = max(match.get('Similarity', 0) for match in face_matches)
        
        is_match = max_similarity >= similarity_threshold
        
        logger.info(f"Face comparison result: similarity={max_similarity:.2f}%, is_match={is_match}, matches={len(face_matches)}")
        
        return {
            'similarity': max_similarity,
            'is_match': is_match,
            'face_matches': face_matches,
            'unmatched_faces': unmatched_faces,
            'raw_response': response
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Rekognition error ({error_code}): {error_message}")
        raise FaceComparisonError(f"Face comparison failed: {error_message}")
    
    except BotoCoreError as e:
        logger.error(f"AWS service error: {e}")
        raise FaceComparisonError(f"AWS service error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in face comparison: {e}")
        raise FaceComparisonError(f"Unexpected error: {str(e)}")


def validate_image_bytes(image_bytes: bytes) -> Tuple[bool, Optional[str]]:
    """
    Validate image bytes for AWS Rekognition compatibility
    
    Args:
        image_bytes: Image data as bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not image_bytes or len(image_bytes) == 0:
        return False, "Image is empty"
    
    # AWS Rekognition max size is 15MB
    MAX_SIZE = 15 * 1024 * 1024  # 15MB
    if len(image_bytes) > MAX_SIZE:
        return False, f"Image too large: {len(image_bytes)} bytes (max: {MAX_SIZE})"
    
    # Minimum size check (at least 4 bytes for magic number check)
    if len(image_bytes) < 4:
        return False, "Image too small"
    
    # Check magic numbers for JPEG and PNG (Rekognition only supports these)
    # JPEG: FF D8 FF
    is_jpeg = image_bytes[:3] == b'\xff\xd8\xff'
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    is_png = len(image_bytes) >= 8 and image_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    if not (is_jpeg or is_png):
        return False, f"Invalid image format. Only JPEG and PNG are supported. Detected magic bytes: {image_bytes[:8].hex()}"
    
    return True, None


def download_image_from_url(image_url: str) -> bytes:
    """
    Download image from URL (Cloudflare Worker URL or S3 URL)
    
    Args:
        image_url: URL of the image
        
    Returns:
        Image data as bytes
        
    Raises:
        Exception: If download fails or image is invalid
    """
    import requests
    
    try:
        logger.info(f"Downloading image from URL: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if content_type and not any(ct in content_type for ct in ['image/jpeg', 'image/jpg', 'image/png']):
            logger.warning(f"Unexpected content type: {content_type}")
        
        image_bytes = response.content
        logger.info(f"Downloaded image: {len(image_bytes)} bytes, content-type: {content_type}")
        
        # Validate image bytes
        is_valid, error_msg = validate_image_bytes(image_bytes)
        if not is_valid:
            logger.error(f"Invalid image from {image_url}: {error_msg}")
            raise Exception(f"Invalid image: {error_msg}")
        
        return image_bytes
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download image from {image_url}: {e}")
        raise Exception(f"Failed to download image: {str(e)}")

