"""
Tests for content processing utilities.

Tests HTML cleaning, format conversion, and content standardization.
"""

import pytest
from services.message_normalizer import ContentProcessor
from services.message_schema import ContentType, MessageContent


class TestContentProcessor:
    """Test content processing utilities."""

    def test_html_cleaning(self):
        """Test HTML content cleaning."""
        dangerous_html = '''
        <script>alert('xss')</script>
        <p onclick="malicious()">Safe content</p>
        <style>body { display: none; }</style>
        <div>Good content</div>
        '''

        cleaned = ContentProcessor.clean_html(dangerous_html)

        assert '<script>' not in cleaned
        assert '<style>' not in cleaned
        assert 'onclick=' not in cleaned
        assert 'Good content' in cleaned

    def test_html_cleaning_edge_cases(self):
        """Test HTML cleaning edge cases."""
        # Test empty content
        assert ContentProcessor.clean_html("") == ""
        assert ContentProcessor.clean_html(None) == ""

        # Test content with only dangerous elements
        dangerous_only = '<script>alert("test")</script><style>body{}</style>'
        cleaned = ContentProcessor.clean_html(dangerous_only)
        assert cleaned.strip() == ""

        # Test nested dangerous elements
        nested_dangerous = '<div><script>alert("nested")</script>Safe text</div>'
        cleaned = ContentProcessor.clean_html(nested_dangerous)
        assert 'Safe text' in cleaned
        assert '<script>' not in cleaned

    def test_html_to_text_conversion(self):
        """Test HTML to text conversion."""
        html = '<p>Hello <strong>world</strong>!</p><br><div>New line</div>'
        text = ContentProcessor.html_to_text(html)

        # <br> doesn't add space, <div> creates new line
        assert text == 'Hello world!New line'

        # Test HTML entity decoding
        html_with_entities = '<p>Hello &amp; goodbye &lt;world&gt;</p>'
        text = ContentProcessor.html_to_text(html_with_entities)

        assert text == 'Hello & goodbye <world>'

    def test_html_entity_decoding(self):
        """Test comprehensive HTML entity decoding."""
        test_cases = [
            ('&amp;', '&'),
            ('&lt;', '<'),
            ('&gt;', '>'),
            ('&quot;', '"'),
            ('&#39;', "'"),
            ('&nbsp;', ' '),
        ]

        for entity, expected in test_cases:
            html = f'<p>Test {entity} entity</p>'
            text = ContentProcessor.html_to_text(html)
            assert expected in text

    def test_html_to_markdown_conversion(self):
        """Test HTML to Markdown conversion."""
        html = '''
        <h1>Title</h1>
        <p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <a href="https://example.com">Link</a>
        '''

        markdown = ContentProcessor.html_to_markdown(html)

        assert '# Title' in markdown
        assert '**bold**' in markdown
        assert '*italic*' in markdown
        assert '- Item 1' in markdown
        assert '[Link](https://example.com)' in markdown

    def test_markdown_conversion_edge_cases(self):
        """Test Markdown conversion edge cases."""
        # Test empty HTML
        assert ContentProcessor.html_to_markdown("") == ""

        # Test HTML with only whitespace
        whitespace_html = '   <p>   </p>   '
        result = ContentProcessor.html_to_markdown(whitespace_html)
        assert result.strip() == ""

        # Test complex nested structures
        complex_html = '''
        <div>
            <h2>Section</h2>
            <p>Text with <code>inline code</code> and <a href="http://test.com">a link</a>.</p>
            <br>
            <p>Another paragraph.</p>
        </div>
        '''
        markdown = ContentProcessor.html_to_markdown(complex_html)
        assert '## Section' in markdown
        assert '`inline code`' in markdown
        assert '[a link](http://test.com)' in markdown

    def test_content_standardization(self):
        """Test content standardization across formats."""
        # Test HTML input
        html_content = '<p>Hello <strong>world</strong></p>'
        result = ContentProcessor.standardize_content(
            html_content, ContentType.HTML)

        assert result.html is not None
        assert result.text == 'Hello world'
        assert result.primary_format == ContentType.HTML

        # Test text input
        text_content = 'Plain text message'
        result = ContentProcessor.standardize_content(
            text_content, ContentType.TEXT)

        assert result.text == 'Plain text message'
        assert result.html is None
        assert result.primary_format == ContentType.TEXT

        # Test markdown input
        markdown_content = '**Bold** text with *italic*'
        result = ContentProcessor.standardize_content(
            markdown_content, ContentType.MARKDOWN)

        assert result.markdown == '**Bold** text with *italic*'
        assert 'Bold text with italic' in result.text  # Markdown stripped

    def test_content_standardization_empty_input(self):
        """Test content standardization with empty input."""
        # Test empty string
        result = ContentProcessor.standardize_content("", ContentType.TEXT)
        assert not result.has_content()

        # Test None input
        result = ContentProcessor.standardize_content(None, ContentType.HTML)
        assert not result.has_content()

        # Test whitespace-only input
        result = ContentProcessor.standardize_content("   ", ContentType.TEXT)
        assert not result.has_content()

    def test_whitespace_normalization(self):
        """Test whitespace normalization in content processing."""
        # Test multiple spaces
        html_with_spaces = '<p>Multiple    spaces   here</p>'
        cleaned = ContentProcessor.clean_html(html_with_spaces)
        assert 'Multiple spaces here' in cleaned

        # Test newlines and tabs
        html_with_whitespace = '<p>Text\n\twith\r\nwhitespace</p>'
        text = ContentProcessor.html_to_text(html_with_whitespace)
        assert 'Text with whitespace' in text

    def test_malicious_content_removal(self):
        """Test removal of various malicious content patterns."""
        malicious_patterns = [
            '<script src="evil.js"></script>',
            '<img src="x" onerror="alert(1)">',
            '<div onload="malicious()">Content</div>',
            '<a href="javascript:alert(1)">Link</a>',
            '<iframe src="evil.html"></iframe>',
            '<object data="evil.swf"></object>',
            '<embed src="evil.swf">',
        ]

        for pattern in malicious_patterns:
            html = f'<div>Safe content {pattern} More safe content</div>'
            cleaned = ContentProcessor.clean_html(html)

            # Should remove the malicious parts but keep safe content
            assert 'Safe content' in cleaned
            assert 'More safe content' in cleaned

            # Should not contain dangerous elements or attributes
            assert 'script' not in cleaned.lower()
            assert 'onerror' not in cleaned.lower()
            assert 'onload' not in cleaned.lower()
            assert 'javascript:' not in cleaned.lower()

    def test_content_format_detection(self):
        """Test content format detection and handling."""
        # Test that HTML content is properly identified and processed
        html_content = '<div><p>HTML content</p></div>'
        result = ContentProcessor.standardize_content(
            html_content, ContentType.HTML)

        assert result.html is not None
        assert result.text == 'HTML content'
        assert result.primary_format == ContentType.HTML

        # Test that text content preserves formatting
        text_with_newlines = 'Line 1\nLine 2\nLine 3'
        result = ContentProcessor.standardize_content(
            text_with_newlines, ContentType.TEXT)

        assert result.text == text_with_newlines
        assert result.primary_format == ContentType.TEXT
