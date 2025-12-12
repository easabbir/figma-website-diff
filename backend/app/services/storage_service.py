"""Storage service for profile images - local filesystem for dev, S3 for production."""

import os
import uuid
import base64
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import boto3 to avoid errors if not installed
_s3_client = None


def _get_s3_client():
    """Get or create S3 client (lazy initialization)."""
    global _s3_client
    if _s3_client is None:
        import boto3
        from app.config import get_settings
        settings = get_settings()
        _s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
    return _s3_client


def _is_production() -> bool:
    """Check if running in production environment."""
    from app.config import get_settings
    settings = get_settings()
    # Production if ENVIRONMENT is 'production' or DEBUG is False
    env = getattr(settings, 'ENVIRONMENT', 'development')
    return env.lower() == 'production' or not settings.DEBUG


def _decode_base64_image(base64_string: str) -> tuple[bytes, str]:
    """
    Decode base64 image data URL.
    
    Args:
        base64_string: Base64 encoded image (data:image/png;base64,...)
        
    Returns:
        Tuple of (image_bytes, extension)
    """
    # Handle data URL format: data:image/png;base64,iVBORw0KGgo...
    if base64_string.startswith('data:'):
        # Extract mime type and base64 data
        header, data = base64_string.split(',', 1)
        # Get extension from mime type (e.g., data:image/png;base64 -> png)
        mime_type = header.split(':')[1].split(';')[0]
        ext = mime_type.split('/')[-1]
        if ext == 'jpeg':
            ext = 'jpg'
    else:
        # Assume raw base64, default to png
        data = base64_string
        ext = 'png'
    
    image_bytes = base64.b64decode(data)
    return image_bytes, ext


def save_profile_image(user_id: str, image_data: str) -> Optional[str]:
    """
    Save profile image and return the URL.
    
    - In development: saves to local uploads/profile/ folder
    - In production: uploads to S3 bucket
    
    Args:
        user_id: User ID for naming the file
        image_data: Base64 encoded image data URL
        
    Returns:
        URL to access the saved image, or None on failure
    """
    # If it's already a URL (http/https), just return it
    if image_data.startswith('http://') or image_data.startswith('https://'):
        return image_data
    
    try:
        # Decode base64 image
        image_bytes, ext = _decode_base64_image(image_data)
        
        # Generate unique filename
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
        
        if _is_production():
            return _save_to_s3(filename, image_bytes, ext)
        else:
            return _save_to_local(filename, image_bytes)
            
    except Exception as e:
        logger.error(f"Failed to save profile image: {e}")
        return None


def _save_to_local(filename: str, image_bytes: bytes) -> str:
    """Save image to local filesystem."""
    from app.config import get_settings
    settings = get_settings()
    
    # Create profile images directory
    profile_dir = Path(settings.UPLOAD_DIR) / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = profile_dir / filename
    with open(file_path, 'wb') as f:
        f.write(image_bytes)
    
    logger.info(f"Saved profile image locally: {file_path}")
    
    # Return URL path (will be served via /uploads/profile/...)
    return f"/uploads/profile/{filename}"


def _save_to_s3(filename: str, image_bytes: bytes, ext: str) -> str:
    """Upload image to S3 bucket."""
    from app.config import get_settings
    settings = get_settings()
    
    s3_client = _get_s3_client()
    
    # Determine content type
    content_type_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    content_type = content_type_map.get(ext, 'image/png')
    
    # S3 key (path in bucket)
    s3_key = f"profile-images/{filename}"
    
    # Upload to S3
    s3_client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=s3_key,
        Body=image_bytes,
        ContentType=content_type,
        ACL='public-read'  # Make publicly readable
    )
    
    logger.info(f"Uploaded profile image to S3: {s3_key}")
    
    # Return public URL
    # Use custom domain if configured, otherwise use S3 URL
    if settings.AWS_S3_CUSTOM_DOMAIN:
        return f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{s3_key}"
    else:
        return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"


def delete_profile_image(image_url: str) -> bool:
    """
    Delete a profile image.
    
    Args:
        image_url: URL of the image to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    if not image_url:
        return True
    
    try:
        if image_url.startswith('/uploads/profile/'):
            # Local file
            from app.config import get_settings
            settings = get_settings()
            filename = image_url.split('/')[-1]
            file_path = Path(settings.UPLOAD_DIR) / "profile" / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted local profile image: {file_path}")
            return True
            
        elif 's3.' in image_url and 'amazonaws.com' in image_url:
            # S3 file
            from app.config import get_settings
            settings = get_settings()
            s3_client = _get_s3_client()
            
            # Extract key from URL
            # URL format: https://bucket.s3.region.amazonaws.com/profile-images/filename
            s3_key = '/'.join(image_url.split('/')[-2:])
            
            s3_client.delete_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key
            )
            logger.info(f"Deleted S3 profile image: {s3_key}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to delete profile image: {e}")
        
    return False
