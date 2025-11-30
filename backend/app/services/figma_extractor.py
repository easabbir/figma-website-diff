"""Figma design data extraction service."""

import requests
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
import logging
import hashlib
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Global cache for Figma API responses
# Structure: {cache_key: {"data": response_data, "timestamp": datetime, "file_key": str}}
_figma_cache: Dict[str, Dict] = {}
CACHE_DURATION_MINUTES = 30  # Cache responses for 30 minutes


def get_cache_key(file_key: str, node_id: Optional[str] = None, endpoint: str = "file") -> str:
    """Generate a cache key for Figma API requests."""
    key_parts = [file_key, endpoint]
    if node_id:
        key_parts.append(node_id)
    return hashlib.md5(":".join(key_parts).encode()).hexdigest()


def get_cached_response(cache_key: str) -> Optional[Dict]:
    """Get cached response if valid."""
    if cache_key in _figma_cache:
        cached = _figma_cache[cache_key]
        if datetime.now() - cached["timestamp"] < timedelta(minutes=CACHE_DURATION_MINUTES):
            logger.info(f"Using cached Figma response (key: {cache_key[:8]}...)")
            return cached["data"]
        else:
            # Cache expired
            del _figma_cache[cache_key]
    return None


def set_cached_response(cache_key: str, data: Dict, file_key: str):
    """Cache a Figma API response."""
    _figma_cache[cache_key] = {
        "data": data,
        "timestamp": datetime.now(),
        "file_key": file_key
    }
    logger.info(f"Cached Figma response (key: {cache_key[:8]}..., expires in {CACHE_DURATION_MINUTES} min)")


def clear_cache_for_file(file_key: str):
    """Clear all cached responses for a specific file."""
    keys_to_delete = [k for k, v in _figma_cache.items() if v.get("file_key") == file_key]
    for key in keys_to_delete:
        del _figma_cache[key]
    logger.info(f"Cleared {len(keys_to_delete)} cached responses for file {file_key}")


class FigmaExtractor:
    """Extract design data from Figma using the Figma API."""
    
    def __init__(self, api_base_url: str = "https://api.figma.com/v1"):
        """
        Initialize Figma extractor.
        
        Args:
            api_base_url: Base URL for Figma API
        """
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.use_cache = True  # Enable caching by default
    
    def set_access_token(self, token: str):
        """Set the Figma API access token."""
        self.session.headers.update({
            "X-Figma-Token": token
        })
    
    def extract_file_key(self, figma_url: str) -> Optional[str]:
        """
        Extract file key from Figma URL.
        
        Supports both old and new Figma URL formats:
        - https://www.figma.com/file/ABC123/Design-Name -> ABC123
        - https://www.figma.com/design/ABC123/Design-Name -> ABC123
        """
        try:
            # Handle both /file/ and /design/ URL formats
            if "/file/" in figma_url:
                parts = figma_url.split("/file/")[1].split("/")
                return parts[0]
            elif "/design/" in figma_url:
                parts = figma_url.split("/design/")[1].split("/")
                return parts[0]
        except Exception as e:
            logger.error(f"Error extracting file key from URL: {e}")
        return None
    
    def get_file_data(self, file_key: str, force_refresh: bool = False) -> Dict:
        """
        Fetch file data from Figma API with caching.
        
        Args:
            file_key: Figma file key
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            Complete file data from Figma API
        """
        # Check cache first
        cache_key = get_cache_key(file_key, endpoint="file")
        if self.use_cache and not force_refresh:
            cached = get_cached_response(cache_key)
            if cached:
                return cached
        
        url = f"{self.api_base_url}/files/{file_key}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            if self.use_cache:
                set_cached_response(cache_key, data, file_key)
            
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Figma API rate limit exceeded. Please wait a minute and try again.")
                raise ValueError("Figma API rate limit exceeded. Please wait 1-2 minutes and try again. Personal tokens are limited to 2 requests per minute. TIP: The same design is cached for 30 minutes - try again with the same URL!")
            logger.error(f"HTTP error fetching Figma file: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Figma file: {e}")
            raise
    
    def get_node_data(self, file_key: str, node_id: str, force_refresh: bool = False) -> Dict:
        """
        Fetch specific node data from Figma API with caching.
        
        Args:
            file_key: Figma file key
            node_id: Node ID to fetch
            force_refresh: If True, bypass cache
            
        Returns:
            Node data
        """
        # Check cache first
        cache_key = get_cache_key(file_key, node_id=node_id, endpoint="node")
        if self.use_cache and not force_refresh:
            cached = get_cached_response(cache_key)
            if cached:
                return cached
        
        url = f"{self.api_base_url}/files/{file_key}/nodes"
        params = {"ids": node_id}
        
        try:
            response = self._make_request_with_retry(url, params=params)
            data = response.json()
            
            # Cache the response
            if self.use_cache:
                set_cached_response(cache_key, data, file_key)
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Figma node: {e}")
            raise
    
    def _make_request_with_retry(self, url: str, params: Optional[Dict] = None, 
                                  max_retries: int = 3, base_delay: float = 30.0) -> requests.Response:
        """
        Make a request with exponential backoff retry on rate limit.
        
        Args:
            url: Request URL
            params: Query parameters
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds (will be multiplied for each retry)
            
        Returns:
            Response object
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, params=params)
                
                if response.status_code == 429:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Rate limited. Waiting {delay:.0f}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(delay)
                        continue
                    else:
                        response.raise_for_status()
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.HTTPError as e:
                last_exception = e
                if e.response.status_code == 429 and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited. Waiting {delay:.0f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay)
                else:
                    raise
        
        raise last_exception
    
    def export_image(self, file_key: str, node_ids: List[str], 
                    scale: int = 2, format: str = "png", 
                    output_dir: Optional[Path] = None) -> Dict[str, str]:
        """
        Export images for specific nodes with caching.
        
        Args:
            file_key: Figma file key
            node_ids: List of node IDs to export
            scale: Export scale (1x, 2x, etc.)
            format: Image format (png, jpg, svg, pdf)
            output_dir: Directory to save images (if None, returns URLs only)
            
        Returns:
            Dictionary mapping node IDs to image URLs or paths
        """
        # Check cache for image URLs
        cache_key = get_cache_key(file_key, node_id=",".join(sorted(node_ids)), endpoint=f"images_{scale}_{format}")
        
        cached_urls = None
        if self.use_cache:
            cached_urls = get_cached_response(cache_key)
        
        if cached_urls:
            image_urls = cached_urls
        else:
            url = f"{self.api_base_url}/images/{file_key}"
            params = {
                "ids": ",".join(node_ids),
                "scale": scale,
                "format": format
            }
            
            try:
                response = self._make_request_with_retry(url, params=params)
                data = response.json()
                image_urls = data.get("images", {})
                
                # Cache the URLs
                if self.use_cache:
                    set_cached_response(cache_key, image_urls, file_key)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Error exporting Figma images: {e}")
                raise
        
        # Download images if output directory specified
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            result = {}
            for node_id, img_url in image_urls.items():
                if img_url:
                    # Check if image already exists locally
                    safe_id = node_id.replace(":", "_").replace(";", "_")
                    img_path = output_dir / f"{safe_id}.{format}"
                    
                    if img_path.exists():
                        logger.info(f"Using cached image: {img_path}")
                        result[node_id] = str(img_path)
                        continue
                    
                    img_response = requests.get(img_url)
                    img_response.raise_for_status()
                    
                    with open(img_path, "wb") as f:
                        f.write(img_response.content)
                    
                    result[node_id] = str(img_path)
            
            return result
        
        return image_urls
    
    def extract_design_tokens(self, node: Dict) -> Dict:
        """
        Extract design tokens (colors, typography, spacing) from a Figma node.
        
        Args:
            node: Figma node object
            
        Returns:
            Extracted design tokens
        """
        tokens = {
            "type": node.get("type"),
            "name": node.get("name"),
            "bounds": self._extract_bounds(node),
            "fills": self._extract_fills(node),
            "strokes": self._extract_strokes(node),
            "effects": self._extract_effects(node),
            "typography": self._extract_typography(node),
            "layout": self._extract_layout(node),
        }
        
        return tokens
    
    def _extract_bounds(self, node: Dict) -> Optional[Dict]:
        """Extract bounding box information."""
        absolute_bounds = node.get("absoluteBoundingBox")
        if absolute_bounds:
            return {
                "x": absolute_bounds.get("x", 0),
                "y": absolute_bounds.get("y", 0),
                "width": absolute_bounds.get("width", 0),
                "height": absolute_bounds.get("height", 0)
            }
        return None
    
    def _extract_fills(self, node: Dict) -> List[Dict]:
        """Extract fill information (colors, gradients, images)."""
        fills = node.get("fills", [])
        extracted = []
        
        for fill in fills:
            if not fill.get("visible", True):
                continue
            
            fill_data = {
                "type": fill.get("type"),
                "opacity": fill.get("opacity", 1.0)
            }
            
            if fill.get("type") == "SOLID":
                color = fill.get("color", {})
                fill_data["color"] = self._rgba_to_hex(
                    color.get("r", 0),
                    color.get("g", 0),
                    color.get("b", 0),
                    color.get("a", 1.0)
                )
            
            extracted.append(fill_data)
        
        return extracted
    
    def _extract_strokes(self, node: Dict) -> List[Dict]:
        """Extract stroke information."""
        strokes = node.get("strokes", [])
        extracted = []
        
        for stroke in strokes:
            if not stroke.get("visible", True):
                continue
            
            stroke_data = {
                "type": stroke.get("type"),
                "weight": node.get("strokeWeight", 0),
                "opacity": stroke.get("opacity", 1.0)
            }
            
            if stroke.get("type") == "SOLID":
                color = stroke.get("color", {})
                stroke_data["color"] = self._rgba_to_hex(
                    color.get("r", 0),
                    color.get("g", 0),
                    color.get("b", 0),
                    color.get("a", 1.0)
                )
            
            extracted.append(stroke_data)
        
        return extracted
    
    def _extract_effects(self, node: Dict) -> List[Dict]:
        """Extract effects (shadows, blurs, etc.)."""
        effects = node.get("effects", [])
        extracted = []
        
        for effect in effects:
            if not effect.get("visible", True):
                continue
            
            extracted.append({
                "type": effect.get("type"),
                "radius": effect.get("radius", 0),
                "offset": effect.get("offset", {}),
                "color": effect.get("color", {})
            })
        
        return extracted
    
    def _extract_typography(self, node: Dict) -> Optional[Dict]:
        """Extract typography information for text nodes."""
        if node.get("type") != "TEXT":
            return None
        
        style = node.get("style", {})
        return {
            "font_family": style.get("fontFamily"),
            "font_size": style.get("fontSize"),
            "font_weight": style.get("fontWeight"),
            "line_height": style.get("lineHeightPx"),
            "letter_spacing": style.get("letterSpacing"),
            "text_align": style.get("textAlignHorizontal"),
            "text_content": node.get("characters", "")
        }
    
    def _extract_layout(self, node: Dict) -> Dict:
        """Extract layout information (auto-layout, constraints)."""
        return {
            "layout_mode": node.get("layoutMode"),
            "padding_left": node.get("paddingLeft", 0),
            "padding_right": node.get("paddingRight", 0),
            "padding_top": node.get("paddingTop", 0),
            "padding_bottom": node.get("paddingBottom", 0),
            "item_spacing": node.get("itemSpacing", 0),
            "constraints": node.get("constraints", {})
        }
    
    def _rgba_to_hex(self, r: float, g: float, b: float, a: float = 1.0) -> str:
        """Convert RGBA (0-1) to hex color."""
        r_int = int(r * 255)
        g_int = int(g * 255)
        b_int = int(b * 255)
        
        if a < 1.0:
            a_int = int(a * 255)
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}{a_int:02x}"
        else:
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}"
    
    def traverse_and_extract(self, node: Dict, depth: int = 0, max_depth: int = 10) -> List[Dict]:
        """
        Recursively traverse Figma node tree and extract design tokens.
        
        Args:
            node: Starting node
            depth: Current depth
            max_depth: Maximum traversal depth
            
        Returns:
            List of extracted design tokens for all nodes
        """
        if depth > max_depth:
            return []
        
        tokens = []
        
        # Extract current node
        node_tokens = self.extract_design_tokens(node)
        tokens.append(node_tokens)
        
        # Traverse children
        children = node.get("children", [])
        for child in children:
            child_tokens = self.traverse_and_extract(child, depth + 1, max_depth)
            tokens.extend(child_tokens)
        
        return tokens
    
    def extract_from_url(self, figma_url: str, access_token: str, 
                        node_id: Optional[str] = None, 
                        output_dir: Optional[Path] = None) -> Dict:
        """
        Complete extraction pipeline from Figma URL.
        
        Args:
            figma_url: Figma file URL
            access_token: Figma API token
            node_id: Specific node to extract (optional)
            output_dir: Directory for exported images
            
        Returns:
            Complete extraction result
        """
        # Set access token
        self.set_access_token(access_token)
        
        # Extract file key
        file_key = self.extract_file_key(figma_url)
        if not file_key:
            raise ValueError(f"Could not extract file key from URL: {figma_url}")
        
        # Fetch file data
        logger.info(f"Fetching Figma file: {file_key}")
        file_data = self.get_file_data(file_key)
        
        # Extract design tokens
        document = file_data.get("document", {})
        
        if node_id:
            # Find specific node
            target_node = self._find_node_by_id(document, node_id)
            if not target_node:
                raise ValueError(f"Node {node_id} not found in file")
            nodes_to_process = [target_node]
            export_ids = [node_id]
        else:
            # Process all top-level canvases/frames
            nodes_to_process = document.get("children", [])
            export_ids = [node.get("id") for node in nodes_to_process if node.get("id")]
        
        # Extract design tokens from all nodes
        all_tokens = []
        for node in nodes_to_process:
            tokens = self.traverse_and_extract(node)
            all_tokens.extend(tokens)
        
        # Export images
        image_paths = {}
        if output_dir and export_ids:
            logger.info(f"Exporting {len(export_ids)} images")
            image_paths = self.export_image(file_key, export_ids, output_dir=output_dir)
        
        return {
            "file_key": file_key,
            "file_name": file_data.get("name"),
            "design_tokens": all_tokens,
            "image_exports": image_paths,
            "metadata": {
                "version": file_data.get("version"),
                "last_modified": file_data.get("lastModified")
            }
        }
    
    def _find_node_by_id(self, node: Dict, target_id: str) -> Optional[Dict]:
        """Recursively find a node by ID."""
        if node.get("id") == target_id:
            return node
        
        for child in node.get("children", []):
            result = self._find_node_by_id(child, target_id)
            if result:
                return result
        
        return None
