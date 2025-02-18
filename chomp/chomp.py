import requests
from bs4 import BeautifulSoup
import html2text


def get_raw_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        print(f"Error downloading URL: {e}")
        return ""

    soup = BeautifulSoup(html_content, "html.parser")
    return soup  # Return the *entire* soup, not just the body


def clean_html(
    url_or_html=None,
    retain_images=False,
    min_el_length=20,
    retain_tags=None,
    retain_keywords=None,
):
    """Downloads and cleans HTML content, with flexible content retention."""

    if retain_tags is None:
        retain_tags = [
            "p",
            "strong",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]  # Default retain tags
    if retain_keywords is None:
        retain_keywords = []  # Default retain keywords

    if url_or_html is None:  # Handle if no URL or HTML is passed
        return ""

    if url_or_html.startswith(("http", "https", "www")):
        print("🌐 Downloading HTML content...")
        soup = get_raw_html(url_or_html)  # Get the entire soup object
    else:
        print("📄 Parsing provided HTML content...")
        url_or_html = f"<div>{url_or_html}</div>"  # Wrap the HTML in a div tag
        soup = BeautifulSoup(url_or_html, "html.parser")

    body = soup.find("body")

    if not body:
        body = soup  # If no body tag is found, use the soup itself
    body_soup = BeautifulSoup(
        str(body), "html.parser"
    )  # Correctly create body_soup from provided HTML

    # Remove irrelevant tags and content from the body
    for tag in body_soup.find_all(["nav", "aside", "footer", "script", "style"]):
        tag.decompose()

    cleaned_html_parts = []
    elements_to_remove = []

    # Process container elements (div, section, article) from the BODY
    for element in body_soup.find_all(["div", "section", "article", "figure"]):
        remove_element = False

        if (
            "related" in element.text.lower()
            or any(
                keyword
                in (
                    (
                        element.get("class", [])
                        if isinstance(element.get("class"), list)
                        else [element.get("class", [])]
                    )
                    + (
                        element.get("id", [])
                        if isinstance(element.get("id"), list)
                        else [element.get("id", [])]
                    )
                )
                for keyword in ["social", "comment", "sidebar", "widget", "menu", "nav"]
            )
            or len(element.get_text(strip=True)) < min_el_length
        ):

            remove_element = True

        if retain_images and not remove_element:
            for img in element.find_all("img"):
                if img.has_attr("src"):
                    img["src"] = img["src"]
                else:
                    img.decompose()

        if remove_element:
            elements_to_remove.append(element)  # Add to removal list
        else:
            cleaned_html_parts.append(str(element))  # Keep if not removing

    # ***KEY CHANGE: Find Headers Outside the Body if not present inside***
    headers = body_soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not headers:  # Check if no headers are found in the body
        headers = soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6"]
        )  # Get headers from the entire soup

    for (
        header_tag
    ) in headers:  # Iterate over the headers found (either in or outside the body)
        # Handle anchor tags within headers
        for a_tag in header_tag.find_all("a"):
            a_tag.unwrap()  # Or a_tag.decompose() as needed
        cleaned_html_parts.append(
            str(header_tag)
        )  # Add header tag to list - NO CONDITIONAL REMOVAL

    # ***KEY CHANGE: Flexible Content Retention (for non-header tags)***
    for tag in body_soup.find_all(retain_tags):
        if tag.name not in [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]:  # Exclude headers from this check
            if any(keyword.lower() in tag.text.lower() for keyword in retain_keywords):
                cleaned_html_parts.append(str(tag))
            elif not tag.contents or (len(tag.get_text(strip=True)) < 10):
                tag.decompose()

    for img in body_soup.find_all("img"):
        cleaned_html_parts.append(str(img))

    for element in elements_to_remove:
        element.decompose()

    cleaned_soup = BeautifulSoup("".join(cleaned_html_parts), "html.parser")

    return str(cleaned_soup)


def html_to_markdown(html_content):
    print("📝 Converting to markdown...")
    html2text_converter = html2text.HTML2Text()
    html2text_converter.body_width = 0  # Prevents wrapping text improperly
    html2text_converter.single_line_break = True  # Avoids excessive line breaks
    markdown_content = html2text_converter.handle(html_content)
    return markdown_content


def url_to_markdown(url, retain_images=False):
    cleaned_html = clean_html(url, retain_images=False)
    markdown_content = html_to_markdown(cleaned_html) if clean_html else None

    return markdown_content


class Chomp:
    def __init__(self, url=None, html=None, retain_images=False):
        self.url = url
        self.html = html
        self.retain_images = retain_images
        self.cleaned_html = None
        self.markdown = None

    def clean(self):
        if self.url:
            self.cleaned_html = clean_html(self.url, retain_images=self.retain_images)
        elif self.html:
            self.cleaned_html = clean_html(self.html, retain_images=self.retain_images)
        else:
            raise ValueError("Either URL or HTML content must be provided.")
        return self.cleaned_html

    def convert_to_markdown(self):
        if not self.cleaned_html:
            self.clean()
        self.markdown = html_to_markdown(self.cleaned_html)
        return self.markdown

    def url_to_markdown(self):
        if not self.url:
            raise ValueError("URL must be provided for this method.")
        self.cleaned_html = clean_html(self.url, retain_images=self.retain_images)
        self.markdown = html_to_markdown(self.cleaned_html)
        return self.markdown


if __name__ == "__main__":
    url = "https://www.example.com"
    chomp = Chomp(url=url)
    markdown = chomp.url_to_markdown()
    print(markdown)
