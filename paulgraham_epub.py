# pip install ebooklib beautifulsoup4 requests
# python paulgraham_epub.py

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

BASE_URL = "https://paulgraham.com/"
INDEX_URL = BASE_URL + "articles.html"

# First three articles in order
PRIORITY_ARTICLES = [
    "https://paulgraham.com/greatwork.html",
    "https://paulgraham.com/selfindulgence.html",
    "https://paulgraham.com/kids.html"
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PaulGrahamScraper/1.0)"}

def safe_filename(name):
    """Convert a string to a safe filename."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return re.sub(r'\s+', '_', name).strip('_')

def get_article_links():
    """Scrape all article URLs from the index page."""
    r = requests.get(INDEX_URL, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a['href']
        if href.endswith(".html") and not href.startswith("index"):
            full_url = BASE_URL + href
            if full_url not in links:
                links.append(full_url)

    # Remove priority articles from the rest of the list to avoid duplication
    rest_links = [link for link in links if link not in PRIORITY_ARTICLES]
    return PRIORITY_ARTICLES + rest_links

def extract_article(url):
    """Extract the title and main content of the article."""
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Main content
    body_content = ""
    font_tag = soup.find("font")
    if font_tag:
        paragraphs = font_tag.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        if text:
            body_content += f"<p>{text}</p>"

    return title, body_content

def create_epub(chapters):
    """Create EPUB file with Roboto font."""
    book = epub.EpubBook()
    book.set_identifier("paul-graham-articles")
    book.set_title("Paul Graham Articles")
    book.set_language("en")
    book.add_author("Paul Graham")

    # Add Roboto font
    roboto_url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        fr = requests.get(roboto_url)
        with open(font_path, "wb") as f:
            f.write(fr.content)
    with open(font_path, "rb") as f:
        font_content = f.read()
    font_item = epub.EpubItem(uid="Roboto", file_name="fonts/Roboto-Regular.ttf", media_type="application/x-font-ttf", content=font_content)
    book.add_item(font_item)

    # Style
    style = """
    @font-face {
        font-family: 'Roboto';
        src: url('fonts/Roboto-Regular.ttf');
    }
    body { font-family: 'Roboto', sans-serif; }
    """
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/style.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    # Add chapters
    epub_chapters = []
    for title, content in chapters:
        filename = safe_filename(title) + ".xhtml"
        c = epub.EpubHtml(title=title, file_name=filename, lang="en")
        c.set_content(f"<html><head></head><body>{content}</body></html>")
        c.add_item(nav_css)
        book.add_item(c)
        epub_chapters.append(c)

    # Table of contents
    book.toc = tuple(epub_chapters)
    book.spine = ["nav"] + epub_chapters

    # Add default NCX and Nav
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub("PaulGrahamArticles.epub", book)

if __name__ == "__main__":
    all_links = get_article_links()
    chapters = []
    for url in all_links:
        print(f"Fetching {url}...")
        try:
            title, content = extract_article(url)
            chapters.append((title, content))
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
        time.sleep(2)  # Polite delay

    print("Creating EPUB...")
    create_epub(chapters)
    print("Done! Saved as PaulGrahamArticles.epub")
