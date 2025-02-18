import requests
from bs4 import BeautifulSoup
import html2text
import re
from urllib.parse import urljoin


def is_valid_image_url(url):
    return url and (
        url.startswith(("http://", "https://", "/"))
        and any(
            url.lower().endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        )
    )


def get_raw_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Error downloading URL: {e}")
        return ""
    return BeautifulSoup(html_content, "lxml")


def clean_html(
    url_or_html=None,
    retain_images=False,
    min_word_length=2,
    retain_tags=None,
    retain_keywords=None,
):
    if retain_tags is None:
        retain_tags = ["p", "strong", "h1", "h2", "h3", "h4", "h5", "h6"]
    if retain_keywords is None:
        retain_keywords = []

    if url_or_html is None:
        return ""

    # Initial parsing
    if url_or_html.startswith(("http", "https", "www")):
        print("🌐 Downloading HTML content...")
        initial_soup = get_raw_html(url_or_html)
    else:
        print("📄 Parsing provided HTML content...")
        initial_soup = BeautifulSoup(f"<div>{url_or_html}</div>", "lxml")

    # Get body or main content area
    body = initial_soup.find("body") or initial_soup.find("main") or initial_soup

    # Create new soup for cleaned content
    cleaned_html_parts = []
    processed_headers = set()
    processed_images = set()
    processed_content = set()

    # Remove unwanted elements
    for tag in body.find_all(["nav", "aside", "footer", "script", "style"]):
        tag.decompose()

    # Compile regex for unwanted content
    keywords_regex = re.compile(
        r"(social|comment(s)?|sidebar|widget|menu|nav)", re.IGNORECASE
    )

    def is_unwanted_element(element):
        """Check if an element should be removed based on classes, ids, and content."""
        classes = element.get("class", [])
        ids = element.get("id", [])

        return (
            "related" in element.text.lower()
            or any(
                keywords_regex.search(str(item))
                for item in (classes if isinstance(classes, list) else [classes])
                + (ids if isinstance(ids, list) else [ids])
                if isinstance(item, str)
            )
            or len(element.get_text(strip=True).split()) < min_word_length
        )

    def process_images_in_element(element):
        """Process images within an element, handling duplicates."""
        if retain_images:
            for img in element.find_all("img"):
                if img.has_attr("src"):
                    img_src = urljoin(url_or_html, img["src"])
                    if img_src not in processed_images:
                        img["src"] = img_src
                        processed_images.add(img_src)
                    else:
                        img.decompose()
                else:
                    img.decompose()

    def add_element_with_spacing(element_str):
        """Add element with appropriate spacing."""
        cleaned_html_parts.append(element_str)
        # Add a line break after block elements
        if any(
            f"<{tag}" in element_str.lower()
            for tag in [
                "div",
                "p",
                "article",
                "section",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            ]
        ):
            cleaned_html_parts.append("\n")

    # Process all elements in document order
    for element in body.find_all():
        # Skip already processed or unwanted elements
        if element.parent is None:  # Already extracted
            continue

        if element.name in ["nav", "aside", "footer", "script", "style"]:
            element.decompose()
            continue

        # Process by element type while maintaining order
        if element.name == "img" and retain_images:
            if element.has_attr("src"):
                img_src = urljoin(url_or_html, element["src"])
                if img_src not in processed_images:
                    element["src"] = img_src
                    processed_images.add(img_src)
                    element.extract()
                    add_element_with_spacing(str(element))
                else:
                    element.decompose()
            else:
                element.decompose()

        elif element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            header_id = f"{element.name}:{element.get_text(strip=True)}"
            if header_id not in processed_headers:
                processed_headers.add(header_id)
                for a_tag in element.find_all("a"):
                    a_tag.unwrap()
                element.extract()
                add_element_with_spacing(str(element))

        elif element.name in ["div", "section", "article", "figure"]:
            if not is_unwanted_element(element):
                content_text = element.get_text(strip=True)
                if content_text and content_text not in processed_content:
                    processed_content.add(content_text)
                    element.extract()
                    add_element_with_spacing(str(element))

        elif element.name in retain_tags:
            content_text = element.get_text(strip=True)
            if content_text and content_text not in processed_content:
                if any(
                    keyword.lower() in content_text.lower()
                    for keyword in retain_keywords
                ) or (
                    element.contents and len(content_text.split()) >= min_word_length
                ):
                    processed_content.add(content_text)
                    element.extract()
                    add_element_with_spacing(str(element))

    # Create final cleaned HTML
    final_html = "".join(cleaned_html_parts)
    final_soup = BeautifulSoup(final_html, "lxml")

    # Remove any remaining empty elements except images
    for element in final_soup.find_all():
        if not element.contents and element.name != "img":
            element.decompose()
        elif element.name != "img" and len(element.get_text(strip=True)) == 0:
            element.decompose()

    return str(final_soup)


def html_to_markdown(html_content, double_space=False):
    print("📝 Converting to markdown...")
    html2text_converter = html2text.HTML2Text()
    html2text_converter.body_width = 0
    html2text_converter.single_line_break = True
    html2text_converter.wrap_links = False
    html2text_converter.inline_links = True
    # Ensure proper spacing around block elements
    html2text_converter.ignore_emphasis = False
    html2text_converter.pad_tables = True
    markdown_content = html2text_converter.handle(html_content)
    # Add extra line break after headers and paragraphs if needed
    markdown_content = re.sub(r"(\#{1,6}.*)\n([^\n])", r"\1\n\n\2", markdown_content)
    if double_space:
        markdown_content = re.sub(r"([^\n])\n([^\n])", r"\1\n\n\2", markdown_content)
    return markdown_content


def url_to_markdown(url, retain_images=False):
    cleaned_html = clean_html(url, retain_images)
    markdown_content = html_to_markdown(cleaned_html) if cleaned_html else None
    return markdown_content


class Chomp:
    def __init__(self, url=None, html=None, retain_images=False):
        self.url = url
        self.html = html
        self.retain_images = retain_images
        self.cleaned_html = None
        self.markdown = None

    def clean(self):
        """Clean HTML content if not already cleaned"""
        if self.cleaned_html is None:
            if self.url:
                self.cleaned_html = clean_html(
                    self.url, retain_images=self.retain_images
                )
            elif self.html:
                self.cleaned_html = clean_html(
                    self.html, retain_images=self.retain_images
                )
            else:
                raise ValueError("Either URL or HTML content must be provided.")
        return self.cleaned_html

    def convert_to_markdown(self):
        """Convert cleaned HTML to markdown"""
        if self.markdown is None:
            self.clean()  # Will only clean if not already cleaned
            self.markdown = html_to_markdown(self.cleaned_html)
        return self.markdown

    def url_to_markdown(self):
        """Convert URL directly to markdown"""
        if not self.url:
            raise ValueError("URL must be provided for this method.")
        return self.convert_to_markdown()  # Uses existing methods


if __name__ == "__main__":
    url = "https://www.example.com"  # Or any URL you want to test
    chomp = Chomp(url=url)
    markdown = chomp.url_to_markdown()
    print(markdown)
