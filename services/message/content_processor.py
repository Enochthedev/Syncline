"""
Content processing utilities for message normalization.

This module handles content cleaning, format conversion, and standardization
for messages from different platforms.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import logging

from .schema import MessageContent, ContentType

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Handles content cleaning and format conversion."""

    @staticmethod
    def clean_html(html_content: str) -> str:
        """Clean HTML content by removing dangerous tags and normalizing."""
        if not html_content:
            return ""

        # Remove script and style tags completely
        html_content = re.sub(
            r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(
            r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

        # Remove dangerous attributes
        html_content = re.sub(
            r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'\s*javascript\s*:', '',
                              html_content, flags=re.IGNORECASE)

        # Normalize whitespace
        html_content = re.sub(r'\s+', ' ', html_content).strip()

        return html_content

    @staticmethod
    def html_to_text(html_content: str) -> str:
        """Convert HTML to plain text."""
        if not html_content:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)

        # Decode HTML entities
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
        }

        for entity, char in html_entities.items():
            text = text.replace(entity, char)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @staticmethod
    def html_to_markdown(html_content: str) -> str:
        """Convert HTML to Markdown (basic conversion)."""
        if not html_content:
            return ""

        markdown = html_content

        # Convert common HTML tags to Markdown
        conversions = [
            (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
            (r'<b[^>]*>(.*?)</b>', r'**\1**'),
            (r'<em[^>]*>(.*?)</em>', r'*\1*'),
            (r'<i[^>]*>(.*?)</i>', r'*\1*'),
            (r'<code[^>]*>(.*?)</code>', r'`\1`'),
            (r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)'),
            (r'<br[^>]*/?>', '\n'),
            (r'<p[^>]*>(.*?)</p>', r'\1\n\n'),
            (r'<h1[^>]*>(.*?)</h1>', r'# \1\n'),
            (r'<h2[^>]*>(.*?)</h2>', r'## \1\n'),
            (r'<h3[^>]*>(.*?)</h3>', r'### \1\n'),
            (r'<li[^>]*>(.*?)</li>', r'- \1\n'),
        ]

        for pattern, replacement in conversions:
            markdown = re.sub(pattern, replacement, markdown,
                              flags=re.DOTALL | re.IGNORECASE)

        # Remove remaining HTML tags
        markdown = re.sub(r'<[^>]+>', '', markdown)

        # Clean up whitespace
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        markdown = markdown.strip()

        return markdown

    @staticmethod
    def standardize_content(content: str, content_type: ContentType) -> MessageContent:
        """Standardize content and generate multiple formats."""
        if not content:
            return MessageContent()

        # Normalize whitespace and remove null characters
        content = re.sub(r'\x00', '', content)  # Remove null bytes
        content = re.sub(r'\r\n', '\n', content)  # Normalize CRLF to LF
        content = re.sub(r'\r', '\n', content)    # Normalize CR to LF
        content = content.strip()

        if not content:
            return MessageContent()

        message_content = MessageContent(primary_format=content_type)

        if content_type == ContentType.HTML:
            message_content.html = ContentProcessor.clean_html(content)
            message_content.text = ContentProcessor.html_to_text(
                message_content.html)
            message_content.markdown = ContentProcessor.html_to_markdown(
                message_content.html)
        elif content_type == ContentType.MARKDOWN:
            message_content.markdown = content.strip()
            # Better markdown to text conversion
            text_content = content
            # Remove markdown formatting but preserve structure
            text_content = re.sub(r'\*\*(.*?)\*\*', r'\1',
                                  text_content)  # Bold
            text_content = re.sub(r'\*(.*?)\*', r'\1',
                                  text_content)      # Italic
            text_content = re.sub(
                r'`(.*?)`', r'\1', text_content)        # Code
            text_content = re.sub(
                r'#{1,6}\s+', '', text_content)         # Headers
            text_content = re.sub(
                r'\[([^\]]+)\]\([^)]+\)', r'\1', text_content)  # Links
            message_content.text = text_content.strip()
        else:  # Plain text
            message_content.text = content.strip()

        return message_content

    @staticmethod
    def extract_urls(content: str) -> List[str]:
        """Extract URLs from content."""
        if not content:
            return []

        # URL pattern that matches http/https URLs
        url_pattern = r'https?://[^\s<>"\'`]+[^\s<>"\'`.,;:!?)]'
        urls = re.findall(url_pattern, content, re.IGNORECASE)

        # Validate and clean URLs
        valid_urls = []
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.netloc and parsed.scheme in ['http', 'https']:
                    valid_urls.append(url)
            except Exception:
                continue

        return valid_urls

    @staticmethod
    def extract_mentions(content: str, platform_type: str = None) -> List[str]:
        """Extract mentions from content based on platform conventions."""
        if not content:
            return []

        mentions = []

        # Twitter/X style mentions (@username)
        if platform_type in ['twitter', 'x', None]:
            twitter_mentions = re.findall(r'@([a-zA-Z0-9_]+)', content)
            mentions.extend([f"@{mention}" for mention in twitter_mentions])

        # Email style mentions (email addresses)
        if platform_type in ['email', 'gmail', None]:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_mentions = re.findall(email_pattern, content)
            mentions.extend(email_mentions)

        # Slack/Discord style mentions (<@userid>)
        if platform_type in ['slack', 'discord', None]:
            slack_mentions = re.findall(r'<@([A-Z0-9]+)>', content)
            mentions.extend([f"<@{mention}>" for mention in slack_mentions])

        return list(set(mentions))  # Remove duplicates

    @staticmethod
    def extract_hashtags(content: str) -> List[str]:
        """Extract hashtags from content."""
        if not content:
            return []

        # Match hashtags (# followed by alphanumeric characters and underscores)
        hashtag_pattern = r'#([a-zA-Z0-9_]+)'
        hashtags = re.findall(hashtag_pattern, content)

        return [f"#{tag}" for tag in hashtags]

    @staticmethod
    def clean_text_for_processing(text: str) -> str:
        """Clean text for AI processing by removing noise and normalizing."""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common email artifacts
        text = re.sub(r'On .* wrote:', '', text)  # Email reply headers
        text = re.sub(r'From:.*?Subject:.*?\n', '', text, flags=re.DOTALL)

        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)

        # Normalize quotes
        text = re.sub(r'[""]', '"', text)
        text = re.sub(r'['']', "'", text)

        return text.strip()

    @staticmethod
    def truncate_content(content: str, max_length: int = 1000, preserve_words: bool = True) -> str:
        """Truncate content to a maximum length while preserving readability."""
        if not content or len(content) <= max_length:
            return content

        if preserve_words:
            # Find the last space before the max length
            truncated = content[:max_length]
            last_space = truncated.rfind(' ')
            if last_space > max_length * 0.8:  # Only if we don't lose too much
                truncated = truncated[:last_space]
            return truncated + "..."
        else:
            return content[:max_length] + "..."

    @staticmethod
    def detect_language(content: str) -> Optional[str]:
        """Detect the language of content (basic implementation)."""
        if not content:
            return None

        # Simple language detection based on common words
        # This is a basic implementation - in production, use a proper language detection library

        english_indicators = ['the', 'and', 'is', 'in',
                              'to', 'of', 'a', 'that', 'it', 'with']
        spanish_indicators = ['el', 'la', 'de',
                              'que', 'y', 'en', 'un', 'es', 'se', 'no']
        french_indicators = ['le', 'de', 'et', 'à',
                             'un', 'il', 'être', 'et', 'en', 'avoir']

        content_lower = content.lower()

        english_count = sum(
            1 for word in english_indicators if word in content_lower)
        spanish_count = sum(
            1 for word in spanish_indicators if word in content_lower)
        french_count = sum(
            1 for word in french_indicators if word in content_lower)

        if english_count >= spanish_count and english_count >= french_count:
            return 'en'
        elif spanish_count >= french_count:
            return 'es'
        elif french_count > 0:
            return 'fr'

        return 'en'  # Default to English
