"""Image processing and comparison utilities."""

from PIL import Image, ImageDraw, ImageChops, ImageFilter
import numpy as np
from typing import Tuple, Optional, Dict
import cv2
from skimage.metrics import structural_similarity as ssim
import imagehash


class ImageComparator:
    """Compare images using various methods."""
    
    def __init__(self, threshold: float = 0.95):
        """
        Initialize image comparator.
        
        Args:
            threshold: SSIM threshold for considering images similar (0-1)
        """
        self.threshold = threshold
    
    def calculate_ssim(self, img1_path: str, img2_path: str) -> float:
        """
        Calculate Structural Similarity Index (SSIM) between two images.
        
        Returns:
            SSIM score (0-1, where 1 is identical)
        """
        # Load images
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        
        if img1 is None or img2 is None:
            raise ValueError("Could not load one or both images")
        
        # Resize to same dimensions
        if img1.shape != img2.shape:
            height = min(img1.shape[0], img2.shape[0])
            width = min(img1.shape[1], img2.shape[1])
            img1 = cv2.resize(img1, (width, height))
            img2 = cv2.resize(img2, (width, height))
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Calculate SSIM
        score, _ = ssim(gray1, gray2, full=True)
        return float(score)
    
    def calculate_mse(self, img1_path: str, img2_path: str) -> float:
        """Calculate Mean Squared Error between two images."""
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        
        if img1.shape != img2.shape:
            height = min(img1.shape[0], img2.shape[0])
            width = min(img1.shape[1], img2.shape[1])
            img1 = cv2.resize(img1, (width, height))
            img2 = cv2.resize(img2, (width, height))
        
        mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
        return float(mse)
    
    def calculate_perceptual_hash(self, img_path: str, hash_size: int = 8) -> str:
        """Calculate perceptual hash of an image."""
        img = Image.open(img_path)
        return str(imagehash.phash(img, hash_size=hash_size))
    
    def compare_hashes(self, hash1: str, hash2: str) -> int:
        """Compare two perceptual hashes (lower is more similar)."""
        return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)
    
    def find_differences(self, img1_path: str, img2_path: str, 
                        sensitivity: int = 50) -> Optional[Image.Image]:
        """
        Find pixel-level differences between two images.
        
        Args:
            img1_path: Path to first image
            img2_path: Path to second image
            sensitivity: Threshold for difference detection (0-255)
        
        Returns:
            PIL Image highlighting differences
        """
        img1 = Image.open(img1_path).convert('RGB')
        img2 = Image.open(img2_path).convert('RGB')
        
        # Resize to match
        if img1.size != img2.size:
            width = min(img1.width, img2.width)
            height = min(img1.height, img2.height)
            img1 = img1.resize((width, height))
            img2 = img2.resize((width, height))
        
        # Calculate difference
        diff = ImageChops.difference(img1, img2)
        
        # Convert to grayscale and threshold
        diff_gray = diff.convert('L')
        threshold_diff = diff_gray.point(lambda x: 255 if x > sensitivity else 0)
        
        return threshold_diff


def create_visual_diff(img1_path: str, img2_path: str, output_path: str, 
                      mode: str = "side-by-side") -> str:
    """
    Create a visual difference image.
    
    Args:
        img1_path: Path to first image (Figma)
        img2_path: Path to second image (Website)
        output_path: Path to save the diff image
        mode: "side-by-side", "overlay", or "highlight"
    
    Returns:
        Path to the created diff image
    """
    img1 = Image.open(img1_path).convert('RGB')
    img2 = Image.open(img2_path).convert('RGB')
    
    # Resize to match
    max_height = max(img1.height, img2.height)
    img1 = img1.resize((int(img1.width * max_height / img1.height), max_height))
    img2 = img2.resize((int(img2.width * max_height / img2.height), max_height))
    
    if mode == "side-by-side":
        # Create side-by-side comparison
        total_width = img1.width + img2.width + 4  # 4px separator
        result = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        result.paste(img1, (0, 0))
        result.paste(img2, (img1.width + 4, 0))
        
        # Add labels
        draw = ImageDraw.Draw(result)
        draw.text((10, 10), "Figma Design", fill=(255, 0, 0))
        draw.text((img1.width + 14, 10), "Website", fill=(0, 0, 255))
        
    elif mode == "overlay":
        # Create overlay with transparency
        result = Image.blend(img1, img2, alpha=0.5)
        
    else:  # highlight
        # Highlight differences in red
        diff = ImageChops.difference(img1, img2)
        diff_gray = diff.convert('L')
        
        # Create mask for differences
        threshold = 30
        mask = diff_gray.point(lambda x: 255 if x > threshold else 0)
        
        # Create result with highlighted differences
        result = img2.copy()
        highlight = Image.new('RGB', img2.size, (255, 0, 0))
        result.paste(highlight, mask=mask)
    
    result.save(output_path, 'PNG', quality=95)
    return output_path


def calculate_similarity(img1_path: str, img2_path: str) -> Dict[str, float]:
    """
    Calculate various similarity metrics between two images.
    
    Returns:
        Dictionary with different similarity scores
    """
    comparator = ImageComparator()
    
    try:
        ssim_score = comparator.calculate_ssim(img1_path, img2_path)
    except:
        ssim_score = 0.0
    
    try:
        mse_score = comparator.calculate_mse(img1_path, img2_path)
    except:
        mse_score = float('inf')
    
    try:
        hash1 = comparator.calculate_perceptual_hash(img1_path)
        hash2 = comparator.calculate_perceptual_hash(img2_path)
        hash_distance = comparator.compare_hashes(hash1, hash2)
    except:
        hash_distance = 999
    
    # Normalize scores to 0-100 percentage
    ssim_percentage = ssim_score * 100
    # MSE: lower is better, convert to similarity percentage (assuming max MSE of 10000)
    mse_percentage = max(0, 100 - (mse_score / 100))
    # Hash: 0 is identical, normalize (assuming max distance of 64 for 8x8 hash)
    hash_percentage = max(0, 100 - (hash_distance * 100 / 64))
    
    return {
        "ssim": round(ssim_percentage, 2),
        "mse": round(mse_percentage, 2),
        "perceptual_hash": round(hash_percentage, 2),
        "overall": round((ssim_percentage + mse_percentage + hash_percentage) / 3, 2)
    }


def resize_for_comparison(img1_path: str, img2_path: str, 
                         output1_path: str, output2_path: str) -> Tuple[str, str]:
    """Resize two images to the same dimensions for comparison."""
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    
    # Use the smaller dimensions
    target_width = min(img1.width, img2.width)
    target_height = min(img1.height, img2.height)
    
    img1_resized = img1.resize((target_width, target_height), Image.Resampling.LANCZOS)
    img2_resized = img2.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    img1_resized.save(output1_path)
    img2_resized.save(output2_path)
    
    return output1_path, output2_path
