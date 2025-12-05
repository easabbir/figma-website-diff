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
                                 full_page: bool = True,
                                 scroll_to_load: bool = True,
                                 wait_for_animations: bool = True) -> str:
        """
        Capture screenshot of a webpage with full content loading.
        
        Args:
            url: Website URL
            output_path: Path to save screenshot
            viewport: Viewport dimensions {width, height}
            wait_for_selector: CSS selector to wait for before screenshot
            full_page: Capture full page or just viewport
            scroll_to_load: Scroll through page to trigger lazy loading
            wait_for_animations: Wait for CSS animations/transitions to complete
            
        Returns:
            Path to saved screenshot
        """
        page = await self.browser.new_page(
            viewport=viewport or {"width": 1920, "height": 1080}
        )
        
        try:
            # Navigate to URL and wait for initial load
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            # Wait for specific selector if provided
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=self.timeout)
            
            # Wait for DOM content to be fully painted
            await self._wait_for_dom_stable(page)
            
            # Scroll through the page to trigger lazy loading
            if scroll_to_load and full_page:
                await self._scroll_to_load_content(page)
            
            # Wait for all images to load
            await self._wait_for_images(page)
            
            # Wait for animations/transitions to complete
            if wait_for_animations:
                await self._wait_for_animations(page)
            
            # Final wait for any remaining renders
            await page.wait_for_timeout(500)
            
            # Take screenshot
            await page.screenshot(path=output_path, full_page=full_page)
            
            logger.info(f"Screenshot saved: {output_path}")
            return output_path
            
        finally:
            await page.close()
    
    async def _wait_for_dom_stable(self, page: Page, timeout_ms: int = 5000):
        """
        Wait for DOM to stabilize (no more mutations).
        """
        try:
            await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        let timeout;
                        let lastMutationTime = Date.now();
                        
                        const observer = new MutationObserver(() => {
                            lastMutationTime = Date.now();
                        });
                        
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true,
                            attributes: true
                        });
                        
                        // Check every 100ms if DOM has been stable for 300ms
                        const checkStable = () => {
                            if (Date.now() - lastMutationTime > 300) {
                                observer.disconnect();
                                resolve();
                            } else {
                                timeout = setTimeout(checkStable, 100);
                            }
                        };
                        
                        // Start checking after initial delay
                        setTimeout(checkStable, 200);
                        
                        // Timeout after 5 seconds
                        setTimeout(() => {
                            observer.disconnect();
                            clearTimeout(timeout);
                            resolve();
                        }, 5000);
                    });
                }
            """)
        except Exception as e:
            logger.warning(f"DOM stability check failed: {e}")
            await page.wait_for_timeout(1000)
    
    async def _scroll_to_load_content(self, page: Page):
        """
        Scroll through the entire page to trigger lazy loading.
        """
        try:
            await page.evaluate("""
                async () => {
                    const scrollHeight = document.body.scrollHeight;
                    const viewportHeight = window.innerHeight;
                    const scrollStep = viewportHeight * 0.8;
                    let currentPosition = 0;
                    
                    // Scroll down through the page
                    while (currentPosition < scrollHeight) {
                        window.scrollTo(0, currentPosition);
                        await new Promise(r => setTimeout(r, 150));
                        currentPosition += scrollStep;
                        
                        // Check if page height increased (infinite scroll)
                        const newScrollHeight = document.body.scrollHeight;
                        if (newScrollHeight > scrollHeight + viewportHeight) {
                            break; // Stop if page keeps growing
                        }
                    }
                    
                    // Scroll to bottom
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(r => setTimeout(r, 300));
                    
                    // Scroll back to top
                    window.scrollTo(0, 0);
                    await new Promise(r => setTimeout(r, 200));
                }
            """)
        except Exception as e:
            logger.warning(f"Scroll to load failed: {e}")
    
    async def _wait_for_images(self, page: Page):
        """
        Wait for all images to be fully loaded.
        """
        try:
            await page.evaluate("""
                () => {
                    return Promise.all(
                        Array.from(document.images)
                            .filter(img => !img.complete)
                            .map(img => new Promise((resolve) => {
                                img.onload = resolve;
                                img.onerror = resolve;
                                // Timeout for individual images
                                setTimeout(resolve, 5000);
                            }))
                    );
                }
            """)
            
            # Also wait for background images in CSS
            await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('*');
                    const bgImages = [];
                    
                    elements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        const bgImage = style.backgroundImage;
                        if (bgImage && bgImage !== 'none' && bgImage.includes('url(')) {
                            const urlMatch = bgImage.match(/url\\(["']?([^"')]+)["']?\\)/);
                            if (urlMatch && urlMatch[1]) {
                                bgImages.push(urlMatch[1]);
                            }
                        }
                    });
                    
                    return Promise.all(
                        bgImages.map(url => new Promise((resolve) => {
                            const img = new Image();
                            img.onload = resolve;
                            img.onerror = resolve;
                            img.src = url;
                            setTimeout(resolve, 3000);
                        }))
                    );
                }
            """)
        except Exception as e:
            logger.warning(f"Wait for images failed: {e}")
            await page.wait_for_timeout(1000)
    
    async def _wait_for_animations(self, page: Page):
        """
        Wait for CSS animations and transitions to complete.
        """
        try:
            await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        // Get all elements with animations or transitions
                        const elements = document.querySelectorAll('*');
                        const animatedElements = [];
                        
                        elements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            const animDuration = parseFloat(style.animationDuration) || 0;
                            const transDuration = parseFloat(style.transitionDuration) || 0;
                            
                            if (animDuration > 0 || transDuration > 0) {
                                animatedElements.push({
                                    element: el,
                                    duration: Math.max(animDuration, transDuration) * 1000
                                });
                            }
                        });
                        
                        if (animatedElements.length === 0) {
                            resolve();
                            return;
                        }
                        
                        // Wait for the longest animation (max 3 seconds)
                        const maxWait = Math.min(
                            Math.max(...animatedElements.map(a => a.duration)),
                            3000
                        );
                        
                        setTimeout(resolve, maxWait + 100);
                    });
                }
            """)
        except Exception as e:
            logger.warning(f"Wait for animations failed: {e}")
            await page.wait_for_timeout(500)
    
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
    
    async def extract_colors_with_elements(self, url: str, viewport: Optional[Dict] = None) -> List[Dict]:
        """
        Extract all colors with their element information.
        
        Args:
            url: Website URL
            viewport: Viewport dimensions
            
        Returns:
            List of color info with element details
        """
        page = await self.browser.new_page(
            viewport=viewport or {"width": 1920, "height": 1080}
        )
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            
            color_elements = await page.evaluate("""
                () => {
                    const colorMap = new Map();
                    
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
                    
                    function getSelector(element) {
                        if (element.id) return '#' + element.id;
                        
                        let selector = element.tagName.toLowerCase();
                        if (element.className && typeof element.className === 'string') {
                            const classes = element.className.trim().split(/\\s+/).filter(c => c).slice(0, 2);
                            if (classes.length > 0) {
                                selector += '.' + classes.join('.');
                            }
                        }
                        return selector;
                    }
                    
                    function getElementName(element) {
                        // Try to get a meaningful name
                        if (element.id) return element.id;
                        if (element.getAttribute('aria-label')) return element.getAttribute('aria-label');
                        if (element.getAttribute('name')) return element.getAttribute('name');
                        if (element.getAttribute('alt')) return element.getAttribute('alt');
                        
                        // Use text content if short
                        const text = element.textContent?.trim();
                        if (text && text.length <= 30) return text;
                        if (text && text.length > 30) return text.substring(0, 30) + '...';
                        
                        // Fall back to tag + class
                        const classes = element.className && typeof element.className === 'string' 
                            ? element.className.trim().split(/\\s+/).filter(c => c).slice(0, 2).join(' ')
                            : '';
                        return element.tagName.toLowerCase() + (classes ? ' (' + classes + ')' : '');
                    }
                    
                    document.querySelectorAll('*').forEach(element => {
                        const style = window.getComputedStyle(element);
                        const rect = element.getBoundingClientRect();
                        
                        // Skip invisible elements
                        if (rect.width === 0 || rect.height === 0) return;
                        if (style.display === 'none' || style.visibility === 'hidden') return;
                        
                        const selector = getSelector(element);
                        const elementName = getElementName(element);
                        const coords = { x: Math.round(rect.x), y: Math.round(rect.y) };
                        
                        // Extract text color
                        if (style.color && style.color !== 'rgba(0, 0, 0, 0)') {
                            const hex = rgbToHex(style.color);
                            if (hex.startsWith('#')) {
                                const key = hex + '|text';
                                if (!colorMap.has(key)) {
                                    colorMap.set(key, {
                                        color: hex,
                                        type: 'text',
                                        elements: []
                                    });
                                }
                                colorMap.get(key).elements.push({
                                    selector: selector,
                                    name: elementName,
                                    coordinates: coords
                                });
                            }
                        }
                        
                        // Extract background color
                        if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                            const hex = rgbToHex(style.backgroundColor);
                            if (hex.startsWith('#')) {
                                const key = hex + '|background';
                                if (!colorMap.has(key)) {
                                    colorMap.set(key, {
                                        color: hex,
                                        type: 'background',
                                        elements: []
                                    });
                                }
                                colorMap.get(key).elements.push({
                                    selector: selector,
                                    name: elementName,
                                    coordinates: coords
                                });
                            }
                        }
                        
                        // Extract border color
                        if (style.borderColor && style.borderColor !== 'rgba(0, 0, 0, 0)' && 
                            style.borderWidth !== '0px') {
                            const hex = rgbToHex(style.borderColor);
                            if (hex.startsWith('#')) {
                                const key = hex + '|border';
                                if (!colorMap.has(key)) {
                                    colorMap.set(key, {
                                        color: hex,
                                        type: 'border',
                                        elements: []
                                    });
                                }
                                colorMap.get(key).elements.push({
                                    selector: selector,
                                    name: elementName,
                                    coordinates: coords
                                });
                            }
                        }
                    });
                    
                    return Array.from(colorMap.values());
                }
            """)
            
            return color_elements
            
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
        
        # Extract colors with element info for detailed comparison
        colors_with_elements = await self.extract_colors_with_elements(url, viewport=viewport)
        
        # Extract fonts
        fonts = await self.extract_fonts(url, viewport=viewport)
        
        # Save analysis data
        analysis_data = {
            "url": url,
            "viewport": viewport,
            "screenshot": str(screenshot_path),
            "dom_structure": dom_structure,
            "colors": colors,
            "colors_with_elements": colors_with_elements,
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
