"""
Chomp: A web content parser that converts HTML to clean, structured Markdown.

This module provides tools for converting web content and raw HTML into markdown format,
specifically optimized for consumption by large language models (LLMs).

Main features:
- HTML cleaning and parsing
- Smart content extraction
- Image handling
- Markdown conversion with customizable formatting
"""

import requests
from bs4 import BeautifulSoup
import html2text
import re
from typing import Optional, List, Set, Union
from urllib.parse import urljoin
import logging


def is_valid_image_url(url: str) -> bool:
    """
    Check if a URL points to a valid image file.

    Args:
        url (str): The URL to check

    Returns:
        bool: True if URL is valid image link, False otherwise
    """
    return url and (
        url.startswith(("http://", "https://", "/"))
        and any(
            url.lower().endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        )
    )


def get_raw_html(url: str) -> BeautifulSoup:
    """
    Fetch and parse HTML content from a URL.

    Args:
        url (str): The URL to fetch HTML from

    Returns:
        BeautifulSoup: Parsed HTML content
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Error downloading URL: {e}")
        return ""
    return BeautifulSoup(html_content, "lxml")


def parse_html(
    url_or_html: Optional[str] = None,
    retain_images: bool = False,
    min_word_length: int = 2,
    retain_tags: Optional[List[str]] = None,
    retain_keywords: Optional[List[str]] = None,
    verbose: Optional[bool] = False,
) -> str:
    """
    Parse and clean HTML content from a URL or raw HTML string.
    """
    # Set up logging for both file and console output
    if verbose:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # Create console handler with formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if not url_or_html:
        return ""

    retain_tags = retain_tags or ["p", "strong", "h1", "h2", "h3", "h4", "h5", "h6"]
    retain_keywords = retain_keywords or []
    
    # Initial parsing
    is_url = url_or_html.startswith(("http", "https", "www"))
    print("🌐 Downloading HTML content..." if is_url else "📄 Parsing provided HTML content...")
    initial_soup = get_raw_html(url_or_html) if is_url else BeautifulSoup(f"<div>{url_or_html}</div>", "lxml")
    
    body = initial_soup.find("body") or initial_soup.find("main") or initial_soup
    
    # Remove unwanted elements early - Modified to be more thorough
    def remove_unwanted_elements(soup):
        """Remove unwanted elements from the HTML soup."""
        unwanted_elements = [
            # Direct tag names
            "menu", "search", "nav", "aside", "footer", "script", "style",
            # Elements with specific classes/ids
            {"class": ["menu", "nav"]},
            {"id": ["menu", "nav", "modal"]},
            # Elements with specific roles
            {"role": ["navigation", "menu"]}
        ]
        
        for element in soup.find_all():
            try:
                # Skip None elements or elements without proper attributes
                if not element or not hasattr(element, 'name'):
                    continue

                # Check tag name
                if element.name in unwanted_elements:
                    if verbose:
                        logger.info(f"Removing by tag name: <{element.name}>")
                    element.decompose()
                    continue
                
                # Skip elements without attrs
                if not hasattr(element, 'attrs') or not element.attrs:
                    continue
                    
                # Check classes and IDs
                classes = element.attrs.get("class", [])
                if isinstance(classes, str):
                    classes = [classes]
                
                element_id = element.attrs.get("id", "")
                element_role = element.attrs.get("role", "")
                
                # Check if any class contains menu-related terms
                if any(cls and any(term in cls.lower() for term in ["menu", "nav", "sidebar"]) 
                    for cls in classes):
                    if verbose:
                        logger.info(f"Removing by class: <{element.name} class='{classes}'>")
                    element.decompose()
                    continue
                    
                # Check if ID contains menu-related terms
                if element_id and any(term in element_id.lower() 
                                    for term in ["menu", "nav", "sidebar"]):
                    if verbose:
                        logger.info(f"Removing by ID: <{element.name} id='{element_id}'>")
                    element.decompose()
                    continue

                # Check role attribute
                if element_role and element_role.lower() in ["navigation", "menu"]:
                    if verbose:
                        logger.info(f"Removing by role: <{element.name} role='{element_role}'>")
                    element.decompose()
                    continue

            except AttributeError as e:
                if verbose:
                    logger.warning(f"Skipping element due to AttributeError: {str(e)}")
                continue

    # Apply the removal function
    remove_unwanted_elements(body)

    keywords_regex = re.compile(r"(social|comment(s)?|sidebar|widget|menu|nav)", re.IGNORECASE)
    processed_headers = set()
    processed_content = set()
    processed_images = set()
    cleaned_html_parts = []
    base_url = url_or_html if is_url else None

    def is_unwanted_element(element):
        """Check if an element should be removed."""
        if verbose:
            logger.info(f"Checking element: <{element.name} class='{element.get('class', '')}' id='{element.get('id', '')}>")
        
        classes = element.get("class", [])
        ids = element.get("id", [])
        
        is_unwanted = (
            any(
                keywords_regex.search(str(item))
                for item in (classes if isinstance(classes, list) else [classes])
                + (ids if isinstance(ids, list) else [ids])
                if isinstance(item, str)
            )
            or len(element.get_text(strip=True).split()) < min_word_length
        )
        
        if verbose and is_unwanted:
            logger.info(f"Marked for removal: <{element.name} class='{element.get('class', '')}' id='{element.get('id', '')}'>")
        
        return is_unwanted

    def process_images(element):
        """Handle image processing consistently."""
        if verbose:
            logger.info(f"Processing images in <{element.name}>")
            
        if retain_images:
            for img in element.find_all("img"):
                if img.has_attr("src"):
                    img_src = urljoin(base_url, img["src"])
                    if img_src not in processed_images:
                        if verbose:
                            logger.info(f"Keeping image: {img_src}")
                        img["src"] = img_src
                        processed_images.add(img_src)
                    else:
                        if verbose:
                            logger.info(f"Removing duplicate image: {img_src}")
                        img.decompose()
                else:
                    if verbose:
                        logger.info("Removing image without src attribute")
                    img.decompose()
        else:
            if verbose:
                logger.info("Removing all images as retain_images=False")
            for img in element.find_all("img"):
                img.decompose()

    def add_element_with_spacing(element_str):
        """Add element with appropriate spacing."""
        cleaned_html_parts.append(element_str)
        if any(f"<{tag}" in element_str.lower() for tag in ["div", "p", "article", "section", "h1", "h2", "h3", "h4", "h5", "h6"]):
            cleaned_html_parts.append("\n")

    # Process elements
    for element in body.find_all(recursive=False):
        if verbose:
            logger.info(f"Processing element: <{element.name}>")
            
        # Skip already removed elements
        if element.name in ["menu", "search", "nav", "aside", "footer", "script", "style"]:
            if verbose:
                logger.info(f"Skipping unwanted tag: <{element.name}>")
            continue

        # Handle images
        if element.name == "img":
            if retain_images and element.has_attr("src"):
                img_src = urljoin(base_url, element["src"])
                if img_src not in processed_images:
                    element["src"] = img_src
                    processed_images.add(img_src)
                    add_element_with_spacing(str(element))
            continue

        # Handle headers
        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            header_id = f"{element.name}:{element.get_text(strip=True)}"
            if header_id not in processed_headers:
                processed_headers.add(header_id)
                process_images(element)
                for a_tag in element.find_all("a"):
                    a_tag.unwrap()
                add_element_with_spacing(str(element))
                if verbose:
                    logger.info(f"Retaining header: <{header_id}>")
            continue

        # Handle container elements
        if element.name in ["div", "section", "article", "figure"]:
            if not is_unwanted_element(element):
                process_images(element)
                content_text = element.get_text(strip=True)
                if content_text and content_text not in processed_content:
                    processed_content.add(content_text)
                    add_element_with_spacing(str(element))
            continue

        # Handle retained tags
        if element.name in retain_tags:
            content_text = element.get_text(strip=True)
            if content_text and content_text not in processed_content:
                if any(keyword.lower() in content_text.lower() for keyword in retain_keywords) or (
                    element.contents and len(content_text.split()) >= min_word_length
                ):
                    process_images(element)
                    processed_content.add(content_text)
                    add_element_with_spacing(str(element))

    # Create final cleaned HTML
    final_html = "".join(cleaned_html_parts)
    final_soup = BeautifulSoup(final_html, "lxml")

    # Final cleanup of empty elements
    for element in final_soup.find_all():
        if element.name != "img" and (not element.contents or not element.get_text(strip=True)):
            element.decompose()

    if verbose:
        logger.info(f"Processed {len(processed_content)} content blocks")
        logger.info(f"Processed {len(processed_images)} images")
        logger.info(f"Processed {len(processed_headers)} headers")

    return str(final_soup)


def html_to_markdown(html_content: str, double_space: bool = True) -> str:
    """
    Convert HTML content to markdown format.

    Args:
        html_content (str): HTML content to convert
        double_space (bool): Whether to add extra spacing between elements

    Returns:
        str: Converted markdown content
    """
    print("📝 Converting to markdown...")
    html2text_converter = html2text.HTML2Text()
    html2text_converter.body_width = 0
    html2text_converter.single_line_break = (
        True  # Important: Keep original HTML line breaks
    )
    html2text_converter.wrap_links = False
    html2text_converter.inline_links = True  # Important: Keep inline links
    html2text_converter.ignore_emphasis = False
    html2text_converter.pad_tables = True
    markdown_content = html2text_converter.handle(html_content)

    # Improved Regex: Add newlines after links ONLY if they are followed by other links or block-level elements
    markdown_content = re.sub(
        r"]\(/.*?\)(?=\s*(\[|$|#))", r"](/.*?)\n", markdown_content
    )

    if double_space:
        lines = markdown_content.splitlines()
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if line.strip() != "":  # Don't add extra newlines to blank lines.
                new_lines.append("")  # Add empty string for extra newline
        markdown_content = "\n".join(new_lines)

    return markdown_content


def url_to_markdown(url: str, retain_images: bool = False) -> Optional[str]:
    """
    Convert webpage content directly to markdown.

    Args:
        url (str): URL to convert
        retain_images (bool): Whether to keep images in output

    Returns:
        Optional[str]: Converted markdown content or None if failed
    """
    cleaned_html = parse_html(url, retain_images)
    markdown_content = html_to_markdown(cleaned_html) if cleaned_html else None
    return markdown_content


class Chomp:
    """
    Main class for HTML to Markdown conversion.

    Attributes:
        url (Optional[str]): Source URL to process
        html (Optional[str]): Raw HTML content to process
        retain_images (bool): Whether to keep images in output
        cleaned_html (Optional[str]): Processed HTML content
        markdown (Optional[str]): Final markdown output
    """

    def __init__(
        self,
        url: Optional[str] = None,
        html: Optional[str] = None,
        retain_images: bool = False,
    ):
        """
        Initialize Chomp instance.

        Args:
            url (Optional[str]): Source URL to process
            html (Optional[str]): Raw HTML content to process
            retain_images (bool): Whether to keep images in output
        """
        self.url = url
        self.html = html
        self.retain_images = retain_images
        self.cleaned_html = None
        self.markdown = None

    def clean(self) -> str:
        """
        Clean HTML content using parse_html function.

        Returns:
            str: Cleaned HTML content

        Raises:
            ValueError: If neither URL nor HTML content is provided
        """
        if self.cleaned_html is None:
            if self.url:
                self.cleaned_html = parse_html(
                    self.url, retain_images=self.retain_images
                )
            elif self.html:
                self.cleaned_html = parse_html(
                    self.html, retain_images=self.retain_images
                )
            else:
                raise ValueError("Either URL or HTML content must be provided.")
        return self.cleaned_html

    def convert_to_markdown(self) -> str:
        """
        Convert cleaned HTML content to markdown.

        Returns:
            str: Converted markdown content
        """
        if self.markdown is None:
            self.clean()  # Will only clean if not already cleaned
            self.markdown = html_to_markdown(self.cleaned_html)
        return self.markdown

    def url_to_markdown(self) -> str:
        """
        Convert URL directly to markdown format.

        Returns:
            str: Converted markdown content

        Raises:
            ValueError: If URL is not provided
        """
        if not self.url:
            raise ValueError("URL must be provided for this method.")
        return self.convert_to_markdown()  # Uses existing methods


if __name__ == "__main__":
    # Example usage
    url = "https://github.com/nsasto/chomp"
    chomp = Chomp(url=url)
    markdown = chomp.url_to_markdown()
    print(markdown)

