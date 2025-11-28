"""Website analysis service using Playwright."""

from playwright.async_api import async_playwright, Browser, Page
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio
import json
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebsiteAnalyzer:
    """Analyze website structure, styles, and capture screenshots using Playwright."""
    
    def __init__(self, timeout: int = 30000):
        """
        Initialize website analyzer.
        
        Args:
            timeout: Default timeout in milliseconds
        """
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def capture_screenshot(self, url: str, output_path: str, 
                                 viewport: Optional[Dict] = None,
                                 wait_for_selector: Optional[str] = None,
                                 full_page: bool = True) -> str:
        """
        Capture screenshot of a webpage.
        
        Args:
            url: Website URL
            output_path: Path to save screenshot
            viewport: Viewport dimensions {width, height}
            wait_for_selector: CSS selector to wait for before screenshot
            full_page: Capture full page or just viewport
            
        Returns:
            Path to saved screenshot
        """
        page = await self.browser.new_page(
            viewport=viewport or {"width": 1920, "height": 1080}
        )
        
        try:
            # Navigate to URL
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            # Wait for specific selector if provided
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=self.timeout)
            
            # Additional wait for any animations
            await page.wait_for_timeout(1000)
            
            # Take screenshot
            await page.screenshot(path=output_path, full_page=full_page)
            
            logger.info(f"Screenshot saved: {output_path}")
            return output_path
            
        finally:
            await page.close()
    
    async def extract_dom_structure(self, url: str, 
                                    viewport: Optional[Dict] = None) -> Dict:
        """
        Extract DOM structure and computed styles.
        
        Args:
            url: Website URL
            viewport: Viewport dimensions
            
        Returns:
            DOM structure with computed styles
        """
        page = await self.browser.new_page(
            viewport=viewport or {"width": 1920, "height": 1080}
        )
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            await page.wait_for_timeout(1000)
            
            # Extract complete DOM with computed styles
            dom_data = await page.evaluate("""
                () => {
                    function extractElement(element) {
                        if (element.nodeType !== Node.ELEMENT_NODE) {
                            return null;
                        }
                        
                        const computedStyle = window.getComputedStyle(element);
                        const rect = element.getBoundingClientRect();
                        
                        return {
                            tagName: element.tagName.toLowerCase(),
                            id: element.id || null,
                            classes: Array.from(element.classList),
                            bounds: {
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            },
                            styles: {
                                color: computedStyle.color,
                                backgroundColor: computedStyle.backgroundColor,
                                fontSize: computedStyle.fontSize,
                                fontFamily: computedStyle.fontFamily,
                                fontWeight: computedStyle.fontWeight,
                                lineHeight: computedStyle.lineHeight,
                                letterSpacing: computedStyle.letterSpacing,
                                margin: {
                                    top: computedStyle.marginTop,
                                    right: computedStyle.marginRight,
                                    bottom: computedStyle.marginBottom,
                                    left: computedStyle.marginLeft
                                },
                                padding: {
                                    top: computedStyle.paddingTop,
                                    right: computedStyle.paddingRight,
                                    bottom: computedStyle.paddingBottom,
                                    left: computedStyle.paddingLeft
                                },
                                border: {
                                    width: computedStyle.borderWidth,
                                    style: computedStyle.borderStyle,
                                    color: computedStyle.borderColor,
                                    radius: computedStyle.borderRadius
                                },
                                display: computedStyle.display,
                                position: computedStyle.position,
                                flexDirection: computedStyle.flexDirection,
                                justifyContent: computedStyle.justifyContent,
                                alignItems: computedStyle.alignItems,
                                gap: computedStyle.gap
                            },
                            textContent: element.textContent ? element.textContent.trim().substring(0, 100) : null,
                            children: Array.from(element.children).map(child => extractElement(child)).filter(Boolean)
                        };
                    }
                    
                    return extractElement(document.body);
                }
            """)
            
            return dom_data
            
        finally:
            await page.close()
    
    async def extract_colors(self, url: str, viewport: Optional[Dict] = None) -> List[str]:
        """
        Extract all colors used on the page.
        
        Args:
            url: Website URL
            viewport: Viewport dimensions
            
        Returns:
            List of unique colors (hex format)
        """
        page = await self.browser.new_page(
            viewport=viewport or {"width": 1920, "height": 1080}
        )
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            colors = await page.evaluate("""
                () => {
                    const colors = new Set();
                    
                    function rgbToHex(rgb) {
                        const match = rgb.match(/^rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*[\\d.]+)?\\)$/);
                        if (!match) return rgb;
                        
                        const r = parseInt(match[1]);
                        const g = parseInt(match[2]);
                        const b = parseInt(match[3]);
                        
                        return '#' + [r, g, b].map(x => {
                            const hex = x.toString(16);
                            return hex.length === 1 ? '0' + hex : hex;
                        }).join('');
                    }
                    
                    document.querySelectorAll('*').forEach(element => {
                        const style = window.getComputedStyle(element);
                        
                        // Extract color
                        if (style.color && style.color !== 'rgba(0, 0, 0, 0)') {
                            colors.add(rgbToHex(style.color));
                        }
                        
                        // Extract background color
                        if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                            colors.add(rgbToHex(style.backgroundColor));
                        }
                        
                        // Extract border color
                        if (style.borderColor && style.borderColor !== 'rgba(0, 0, 0, 0)') {
                            colors.add(rgbToHex(style.borderColor));
                        }
                    });
                    
                    return Array.from(colors).filter(c => c.startsWith('#'));
                }
            """)
            
            return colors
            
        finally:
            await page.close()
    
    async def extract_fonts(self, url: str, viewport: Optional[Dict] = None) -> List[Dict]:
        """
        Extract all fonts used on the page.
        
        Args:
            url: Website URL
            viewport: Viewport dimensions
            
        Returns:
            List of font information
        """
        page = await self.browser.new_page(
            viewport=viewport or {"width": 1920, "height": 1080}
        )
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            fonts = await page.evaluate("""
                () => {
                    const fontMap = new Map();
                    
                    document.querySelectorAll('*').forEach(element => {
                        const style = window.getComputedStyle(element);
                        const fontFamily = style.fontFamily;
                        const fontSize = style.fontSize;
                        const fontWeight = style.fontWeight;
                        
                        if (fontFamily) {
                            const key = `${fontFamily}|${fontSize}|${fontWeight}`;
                            if (!fontMap.has(key)) {
                                fontMap.set(key, {
                                    family: fontFamily,
                                    size: fontSize,
                                    weight: fontWeight,
                                    count: 0
                                });
                            }
                            fontMap.get(key).count++;
                        }
                    });
                    
                    return Array.from(fontMap.values())
                        .sort((a, b) => b.count - a.count);
                }
            """)
            
            return fonts
            
        finally:
            await page.close()
    
    async def capture_element_screenshot(self, url: str, selector: str,
                                        output_path: str,
                                        viewport: Optional[Dict] = None) -> Optional[str]:
        """
        Capture screenshot of a specific element.
        
        Args:
            url: Website URL
            selector: CSS selector for the element
            output_path: Path to save screenshot
            viewport: Viewport dimensions
            
        Returns:
            Path to saved screenshot or None if element not found
        """
        page = await self.browser.new_page(
            viewport=viewport or {"width": 1920, "height": 1080}
        )
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            element = await page.query_selector(selector)
            if not element:
                logger.warning(f"Element not found: {selector}")
                return None
            
            await element.screenshot(path=output_path)
            logger.info(f"Element screenshot saved: {output_path}")
            return output_path
            
        finally:
            await page.close()
    
    async def analyze_website(self, url: str, 
                             output_dir: Path,
                             viewport: Optional[Dict] = None,
                             wait_for_selector: Optional[str] = None) -> Dict:
        """
        Complete website analysis pipeline.
        
        Args:
            url: Website URL
            output_dir: Directory for outputs
            viewport: Viewport dimensions
            wait_for_selector: Selector to wait for
            
        Returns:
            Complete analysis results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        viewport = viewport or {"width": 1920, "height": 1080}
        
        logger.info(f"Analyzing website: {url}")
        
        # Capture screenshot
        screenshot_path = output_dir / "website_screenshot.png"
        await self.capture_screenshot(
            url, 
            str(screenshot_path), 
            viewport=viewport,
            wait_for_selector=wait_for_selector
        )
        
        # Extract DOM structure
        dom_structure = await self.extract_dom_structure(url, viewport=viewport)
        
        # Extract colors
        colors = await self.extract_colors(url, viewport=viewport)
        
        # Extract fonts
        fonts = await self.extract_fonts(url, viewport=viewport)
        
        # Save analysis data
        analysis_data = {
            "url": url,
            "viewport": viewport,
            "screenshot": str(screenshot_path),
            "dom_structure": dom_structure,
            "colors": colors,
            "fonts": fonts,
            "metadata": {
                "total_elements": self._count_elements(dom_structure),
                "unique_colors": len(colors),
                "unique_fonts": len(fonts)
            }
        }
        
        # Save to JSON
        json_path = output_dir / "website_analysis.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2)
        
        logger.info(f"Website analysis complete. Results saved to {output_dir}")
        
        return analysis_data
    
    def _count_elements(self, node: Dict) -> int:
        """Recursively count DOM elements."""
        if not node:
            return 0
        count = 1
        for child in node.get("children", []):
            count += self._count_elements(child)
        return count


async def analyze_website_async(url: str, output_dir: Path, 
                               viewport: Optional[Dict] = None,
                               wait_for_selector: Optional[str] = None,
                               timeout: int = 30000) -> Dict:
    """
    Async helper function to analyze a website.
    
    Args:
        url: Website URL
        output_dir: Output directory
        viewport: Viewport configuration
        wait_for_selector: Selector to wait for
        timeout: Timeout in milliseconds
        
    Returns:
        Analysis results
    """
    async with WebsiteAnalyzer(timeout=timeout) as analyzer:
        return await analyzer.analyze_website(
            url, 
            output_dir, 
            viewport=viewport,
            wait_for_selector=wait_for_selector
        )
