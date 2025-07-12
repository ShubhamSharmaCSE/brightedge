"""
HTML parsing and metadata extraction service.
"""

import re
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime
import dateutil.parser
from bs4 import BeautifulSoup, Tag
import structlog

from shared.models import PageMetadata, ImageMetadata, LinkMetadata, ContentType

logger = structlog.get_logger()


class HTMLParser:
    """HTML parser for extracting metadata from web pages."""
    
    def __init__(self):
        self.title_selectors = [
            'title',
            'h1',
            '[property="og:title"]',
            '[name="twitter:title"]',
            '[itemprop="name"]',
        ]
        
        self.description_selectors = [
            '[name="description"]',
            '[property="og:description"]',
            '[name="twitter:description"]',
            '[itemprop="description"]',
        ]
        
        self.keywords_selectors = [
            '[name="keywords"]',
            '[property="article:tag"]',
            '[rel="tag"]',
        ]
        
        self.author_selectors = [
            '[name="author"]',
            '[property="article:author"]',
            '[name="twitter:creator"]',
            '[itemprop="author"]',
            '[rel="author"]',
        ]
        
        self.published_date_selectors = [
            '[property="article:published_time"]',
            '[name="publication_date"]',
            '[itemprop="datePublished"]',
            '[name="date"]',
            'time[datetime]',
        ]
        
    async def extract_metadata(self, soup: BeautifulSoup, url: str) -> PageMetadata:
        """Extract comprehensive metadata from HTML content."""
        
        metadata = PageMetadata(url=url)
        
        # Extract title
        metadata.title = self._extract_title(soup)
        
        # Extract description
        metadata.description = self._extract_description(soup)
        
        # Extract keywords
        metadata.keywords = self._extract_keywords(soup)
        
        # Extract author
        metadata.author = self._extract_author(soup)
        
        # Extract published date
        metadata.published_date = self._extract_published_date(soup)
        
        # Extract canonical URL
        metadata.canonical_url = self._extract_canonical_url(soup, url)
        
        # Extract language
        metadata.language = self._extract_language(soup)
        
        # Extract content type
        metadata.content_type = ContentType.HTML
        
        # Extract word count
        metadata.word_count = self._extract_word_count(soup)
        
        # Extract images
        metadata.images = self._extract_images(soup, url)
        
        # Extract links
        metadata.links = self._extract_links(soup, url)
        
        return metadata
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title."""
        for selector in self.title_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'title':
                    title = element.get_text(strip=True)
                elif element.has_attr('content'):
                    title = element.get('content', '').strip()
                else:
                    title = element.get_text(strip=True)
                
                if title:
                    # Clean up title
                    title = re.sub(r'\s+', ' ', title)
                    return title[:500]  # Limit title length
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page description."""
        for selector in self.description_selectors:
            element = soup.select_one(selector)
            if element:
                if element.has_attr('content'):
                    description = element.get('content', '').strip()
                else:
                    description = element.get_text(strip=True)
                
                if description:
                    # Clean up description
                    description = re.sub(r'\s+', ' ', description)
                    return description[:1000]  # Limit description length
        
        # Fallback: extract from first paragraph
        first_p = soup.find('p')
        if first_p:
            description = first_p.get_text(strip=True)
            if description:
                description = re.sub(r'\s+', ' ', description)
                return description[:1000]
        
        return None
    
    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract keywords from page."""
        keywords = []
        
        for selector in self.keywords_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element.has_attr('content'):
                    content = element.get('content', '').strip()
                    if content:
                        # Split keywords by comma or semicolon
                        page_keywords = re.split(r'[,;]', content)
                        keywords.extend([kw.strip() for kw in page_keywords if kw.strip()])
                else:
                    text = element.get_text(strip=True)
                    if text:
                        keywords.append(text)
        
        # Remove duplicates and limit count
        unique_keywords = list(set(keywords))
        return unique_keywords[:20]  # Limit to 20 keywords
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author information."""
        for selector in self.author_selectors:
            element = soup.select_one(selector)
            if element:
                if element.has_attr('content'):
                    author = element.get('content', '').strip()
                else:
                    author = element.get_text(strip=True)
                
                if author:
                    return author[:200]  # Limit author length
        
        return None
    
    def _extract_published_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract published date."""
        for selector in self.published_date_selectors:
            element = soup.select_one(selector)
            if element:
                date_str = None
                
                if element.has_attr('content'):
                    date_str = element.get('content', '').strip()
                elif element.has_attr('datetime'):
                    date_str = element.get('datetime', '').strip()
                else:
                    date_str = element.get_text(strip=True)
                
                if date_str:
                    try:
                        # Parse various date formats
                        return dateutil.parser.parse(date_str)
                    except (ValueError, TypeError):
                        continue
        
        return None
    
    def _extract_canonical_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract canonical URL."""
        # Check for canonical link
        canonical_link = soup.find('link', rel='canonical')
        if canonical_link and canonical_link.has_attr('href'):
            canonical_url = canonical_link['href']
            return urljoin(base_url, canonical_url)
        
        # Check for og:url
        og_url = soup.find('meta', property='og:url')
        if og_url and og_url.has_attr('content'):
            return og_url['content']
        
        return None
    
    def _extract_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page language."""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.has_attr('lang'):
            return html_tag['lang'][:10]  # Limit language code length
        
        # Check meta http-equiv
        meta_lang = soup.find('meta', {'http-equiv': 'content-language'})
        if meta_lang and meta_lang.has_attr('content'):
            return meta_lang['content'][:10]
        
        return None
    
    def _extract_word_count(self, soup: BeautifulSoup) -> int:
        """Extract word count from page content."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'head', 'title', 'meta']):
            element.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Count words
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[ImageMetadata]:
        """Extract image metadata."""
        images = []
        
        # Find all img tags
        img_tags = soup.find_all('img', src=True)
        
        for img in img_tags:
            src = img.get('src')
            if not src:
                continue
            
            # Convert relative URLs to absolute
            img_url = urljoin(base_url, src)
            
            # Skip data URLs and very small images
            if img_url.startswith('data:') or self._is_small_image(img):
                continue
            
            image_metadata = ImageMetadata(
                url=img_url,
                alt_text=img.get('alt', '').strip() or None,
                title=img.get('title', '').strip() or None,
                width=self._get_int_attr(img, 'width'),
                height=self._get_int_attr(img, 'height'),
            )
            
            images.append(image_metadata)
        
        # Limit number of images
        return images[:50]
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[LinkMetadata]:
        """Extract link metadata."""
        links = []
        
        # Find all a tags with href
        link_tags = soup.find_all('a', href=True)
        
        for link in link_tags:
            href = link.get('href')
            if not href:
                continue
            
            # Convert relative URLs to absolute
            link_url = urljoin(base_url, href)
            
            # Skip internal anchors and javascript links
            if href.startswith('#') or href.startswith('javascript:'):
                continue
            
            link_metadata = LinkMetadata(
                url=link_url,
                text=link.get_text(strip=True)[:200] or None,
                title=link.get('title', '').strip() or None,
                rel=link.get('rel', [''])[0] if link.get('rel') else None,
            )
            
            links.append(link_metadata)
        
        # Limit number of links
        return links[:100]
    
    def _is_small_image(self, img: Tag) -> bool:
        """Check if image is too small to be meaningful."""
        width = self._get_int_attr(img, 'width')
        height = self._get_int_attr(img, 'height')
        
        if width and height:
            return width < 50 or height < 50
        
        return False
    
    def _get_int_attr(self, element: Tag, attr: str) -> Optional[int]:
        """Safely get integer attribute value."""
        try:
            value = element.get(attr)
            if value:
                return int(value)
        except (ValueError, TypeError):
            pass
        
        return None
