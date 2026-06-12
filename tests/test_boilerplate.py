"""Tests for the HTML boilerplate stripper."""

import pytest
from research_engine.sources.web_scraper import BoilerplateStripper

def test_boilerplate_stripping_tags():
    html = """
    <html>
      <head><title>Test</title></head>
      <body>
        <header>
          <h1>Site Name</h1>
          <nav><a href="/">Home</a></nav>
        </header>
        <aside>
          <h3>Sidebar widget</h3>
          <p>Some advertisements here.</p>
        </aside>
        <article>
          <h2>Actual Article Title</h2>
          <p>This is the actual article content that should be preserved.</p>
        </article>
        <footer>
          <p>Copyright 2026</p>
        </footer>
      </body>
    </html>
    """
    parser = BoilerplateStripper()
    parser.feed(html)
    cleaned = parser.get_cleaned_text()

    # The headers, navs, asides, and footers should be stripped
    assert "Site Name" not in cleaned
    assert "Home" not in cleaned
    assert "Sidebar widget" not in cleaned
    assert "Copyright 2026" not in cleaned

    # The article content must be preserved
    assert "Actual Article Title" in cleaned
    assert "This is the actual article content that should be preserved." in cleaned

def test_boilerplate_stripping_classes_and_ids():
    html = """
    <div>
      <div id="sidebar-menu">Sidebar items</div>
      <div class="cookie-banner-ads">Please accept cookies</div>
      <p>Valid text here</p>
      <div class="share-social-buttons">Share on Twitter</div>
    </div>
    """
    parser = BoilerplateStripper()
    parser.feed(html)
    cleaned = parser.get_cleaned_text()

    assert "Sidebar items" not in cleaned
    assert "Please accept cookies" not in cleaned
    assert "Share on Twitter" not in cleaned
    assert "Valid text here" in cleaned
