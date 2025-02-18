import requests
from bs4 import BeautifulSoup
import html2text
import re
from urllib.parse import urljoin


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

    if url_or_html.startswith(("http", "https", "www")):
        print("🌐 Downloading HTML content...")
        soup = get_raw_html(url_or_html)
    else:
        print("📄 Parsing provided HTML content...")
        soup = BeautifulSoup(f"<div>{url_or_html}</div>", "lxml")

    body = soup.find("body")
    if not body:
        body = soup

    body_soup = BeautifulSoup(str(body), "lxml")

    for tag in body_soup.find_all(["nav", "aside", "footer", "script", "style"]):
        tag.decompose()

    cleaned_html_parts = []
    elements_to_remove = []

    keywords_regex = re.compile(
        r"(social|comment(s)?|sidebar|widget|menu|nav)", re.IGNORECASE
    )

    # 1. Process main content containers (div, section, article, figure):
    for element in body_soup.find_all(["div", "section", "article", "figure"]):
        remove_element = False

        classes = element.get("class", [])
        ids = element.get("id", [])

        if (
            "related" in element.text.lower()
            or any(
                keywords_regex.search(item)
                for item in (classes if isinstance(classes, list) else [classes])
                + (ids if isinstance(ids, list) else [ids])
                if isinstance(item, str)
            )
            or len(element.get_text(strip=True).split()) < min_word_length
        ):
            remove_element = True

        if retain_images and not remove_element:
            for img in element.find_all("img"):
                if img.has_attr("src"):
                    img["src"] = urljoin(url_or_html, img["src"])
                else:
                    img.decompose()

        if not remove_element:  # Only add if not marked for removal
            cleaned_html_parts.append(element)

        if remove_element:
            elements_to_remove.append(element)

    # 2. Process headers (h1-h6):
    headers = body_soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    for header_tag in headers:
        for a_tag in header_tag.find_all("a"):
            a_tag.unwrap()
        cleaned_html_parts.append(header_tag)

    # 3. Process retained tags (p, strong, etc. - excluding headers):
    for tag in body_soup.find_all(retain_tags):
        if tag.name not in ["h1", "h2", "h3", "h4", "h5", "h6"]:  # Exclude headers
            if any(keyword.lower() in tag.text.lower() for keyword in retain_keywords):
                cleaned_html_parts.append(tag)
            elif not tag.contents or (
                len(tag.get_text(strip=True).split()) < min_word_length
            ):
                tag.decompose()

    # 4. Process images *outside* of other elements (important!):
    for img in body_soup.find_all(
        "img"
    ):  # These might be outside the div/section/etc loop
        # Check if already added (if they were inside retained div/section/etc)
        if img not in cleaned_html_parts:
            cleaned_html_parts.append(img)

    for element in elements_to_remove:
        element.decompose()

    cleaned_soup = BeautifulSoup("", "lxml")
    for element in cleaned_html_parts:
        cleaned_soup.append(element)

    for element in cleaned_soup.find_all():
        if not element.contents or (
            len(element.get_text(strip=True)) == 0 and element.name not in ["img"]
        ):
            element.decompose()

    return str(cleaned_soup)


def html_to_markdown(html_content):
    print("📝 Converting to markdown...")
    html2text_converter = html2text.HTML2Text()
    html2text_converter.body_width = 0
    html2text_converter.single_line_break = True
    markdown_content = html2text_converter.handle(html_content)
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
    url = "https://www.example.com"  # Or any URL you want to test
    chomp = Chomp(url=url)
    markdown = chomp.url_to_markdown()
    print(markdown)
