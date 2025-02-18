![Chomp](img/github-header-image.png)

# 🧭 Project Overview

Yet another web parser. Chomp is a collection of efficient and easy-to-use helpers designed to convert URLs and raw HTML into clean, structured Markdown—perfectly optimized for consumption by large language models (LLMs). Whether you're scraping web content, processing HTML documents, or extracting meaningful text from complex pages, Chomp ensures that the output remains readable, organized, and free from unnecessary clutter.

## 📦 Key Features:

- Smart Parsing: Extracts key content while filtering out ads, navigation elements, and unnecessary noise.
- Markdown Conversion: Transforms HTML structures into clear, hierarchical Markdown for easy readability.
- LLM Optimization: Produces structured outputs that enhance comprehension and usability for AI models.
- Lightweight & Fast: Designed for efficiency, making it ideal for automated pipelines and data processing tasks.

Whether you're building AI-powered applications, summarizing web pages, or simply tidying up raw HTML, Chomp helps you digest the web effortlessly! 🚀

## 🚀 Getting Started

Install the required dependencies:

```sh
pip install requests beautifulsoup4 html2text 
```

## 💡 Basic Usage

The simplest way to use Chomp is to convert a URL directly to Markdown:
```python
from chomp import Chomp

# Basic URL to Markdown conversion
chomp = Chomp(url="https://example.com")
markdown = chomp.url_to_markdown()
print(markdown)

# Retain images in the output
chomp_with_images = Chomp(url="https://example.com", retain_images=True)
markdown_with_images = chomp_with_images.url_to_markdown()
```

### 🔨 Working with Raw HTML

You can also process raw HTML content:
```python
html_content = """
<div>
    <h1>Hello World</h1>
    <p>This is a test paragraph with <strong>bold text</strong>.</p>
    <img src="example.jpg" alt="Test image">
</div>
"""

chomp = Chomp(html=html_content, retain_images=True)
markdown = chomp.convert_to_markdown()
```

### ⚙️ Advanced Features

The `parse_html` function offers additional customization:

```python
from chomp import parse_html, html_to_markdown

# Customize HTML parsing
cleaned_html = parse_html(
    url_or_html="https://example.com",
    retain_images=True,
    min_word_length=2,
    retain_tags=["p", "strong", "h1", "h2", "h3"],
    retain_keywords=["important", "featured"]
)

# Convert to markdown with custom spacing
markdown = html_to_markdown(cleaned_html, double_space=True)
```

### 🔍 Under the Hood

1. 🧠 Smart Content Extraction
* Automatically removes navigation menus, sidebars, and advertisements
* Preserves important content structure
* Handles duplicate content removal
* Image Processing

2. 🖼️ Optional image retention with proper URL handling
* Converts relative image paths to absolute URLs
* Removes duplicate images
* Markdown Optimization

3. 📝 Clean header hierarchy
* Proper spacing and formatting
* Link preservation
* Optional double-spacing for better readability

## 🤝 Contributions

This project is a work in progress and there's plenty room for improvement - contributions are always welcome! If you have any ideas or suggestions, feel free to open an issue or submit a pull request.

## 🛡️ Disclaimer

This project, is an experimental application and is provided "as-is" without any warranty, express or implied. Code is shared for educational purposes under the MIT license.
