"""
Content processing utilities for message normalization.

This module handles content cleaning, format conversion, and text processing
for messages from different platforms.
"""

import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import logging

from services.message_schema import MessageContent, ContentType
from utils.mime_utils import clean_mime_type, resolve_mime_type, is_safe_mime_type

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
        """Convert HTML content to plain text."""
        if not html_content:
            return ""

        # Clean HTML first
        clean_html = ContentProcessor.clean_html(html_content)

        # Convert common HTML entities
        clean_html = clean_html.replace('&nbsp;', ' ')
        clean_html = clean_html.replace('&amp;', '&')
        clean_html = clean_html.replace('&lt;', '<')
        clean_html = clean_html.replace('&gt;', '>')
        clean_html = clean_html.replace('&quot;', '"')
        clean_html = clean_html.replace('&#39;', "'")

        # Convert line breaks
        clean_html = re.sub(r'<br\s*/?>', '\n', clean_html,
                            flags=re.IGNORECASE)
        clean_html = re.sub(r'</p>', '\n\n', clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r'</div>', '\n', clean_html, flags=re.IGNORECASE)

        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', clean_html)

        # Normalize whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r'[ \t]+', ' ', text)      # Multiple spaces to single
        text = text.strip()

        return text

    @staticmethod
    def clean_text(text_content: str) -> str:
        """Clean plain text content."""
        if not text_content:
            return ""

        # Normalize line endings
        text_content = text_content.replace('\r\n', '\n').replace('\r', '\n')

        # Remove excessive whitespace
        text_content = re.sub(r'[ \t]+', ' ', text_content)
        text_content = re.sub(r'\n\s*\n\s*\n', '\n\n', text_content)

        return text_content.strip()

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text content."""
        if not text:
            return []

        # URL pattern that matches http/https URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
        urls = re.findall(url_pattern, text, re.IGNORECASE)

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
    def extract_mentions(text: str, platform: str) -> List[str]:
        """Extract mentions from text based on platform conventions."""
        if not text:
            return []

        mentions = []

        if platform.lower() == 'gmail':
            # Gmail doesn't have traditional mentions, but we can extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            mentions = re.findall(email_pattern, text)

        elif platform.lower() in ['slack', 'discord']:
            # Slack/Discord style mentions: @username or <@userid>
            mention_patterns = [
                r'@([a-zA-Z0-9._-]+)',  # @username
                r'<@([A-Z0-9]+)>',      # <@userid>
            ]
            for pattern in mention_patterns:
                mentions.extend(re.findall(pattern, text))

        elif platform.lower() == 'twitter':
            # Twitter style mentions: @username
            mentions = re.findall(r'@([a-zA-Z0-9_]+)', text)

        return list(set(mentions))  # Remove duplicates

    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Extract hashtags from text."""
        if not text:
            return []

        # Match hashtags (# followed by alphanumeric characters and underscores)
        hashtag_pattern = r'#([a-zA-Z0-9_]+)'
        hashtags = re.findall(hashtag_pattern, text)

        return list(set(hashtags))  # Remove duplicates

    @staticmethod
    def detect_language(text: str) -> Optional[str]:
        """Detect the language of text content."""
        if not text or len(text.strip()) < 10:
            return None

        try:
            # Simple language detection based on character patterns
            # This is a basic implementation - could be enhanced with proper language detection

            # Check for common English words
            english_words = ['the', 'and', 'or', 'but', 'in',
                             'on', 'at', 'to', 'for', 'of', 'with', 'by']
            text_lower = text.lower()
            english_count = sum(
                1 for word in english_words if f' {word} ' in f' {text_lower} ')

            if english_count >= 2:
                return 'en'

            # Check for other language patterns
            if re.search(r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', text_lower):
                return 'es'  # Spanish/French/other Romance languages

            if re.search(r'[äöüß]', text_lower):
                return 'de'  # German

            # Default to English if uncertain
            return 'en'

        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return 'en'

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """Calculate a hash for content deduplication."""
        if not content:
            return ""

        # Normalize content for hashing
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def truncate_content(content: str, max_length: int = 10000) -> str:
        """Truncate content to maximum length while preserving word boundaries."""
        if not content or len(content) <= max_length:
            return content

        # Find the last space before the limit
        truncated = content[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > max_length * 0.8:  # If we found a space reasonably close to the limit
            return content[:last_space] + '...'
        else:
            return content[:max_length] + '...'

    @staticmethod
    def normalize_content(
        raw_content: Dict[str, Any],
        platform: str,
        content_type: ContentType = ContentType.TEXT
    ) -> MessageContent:
        """Normalize content from platform-specific format to unified format."""
        try:
            text = ""
            html = ""
            markdown = ""

            # Extract content based on platform
            if platform.lower() == 'gmail':
                # Gmail provides both text and HTML
                text = raw_content.get('text', '')
                html = raw_content.get('html', '')

                # If we only have HTML, convert to text
                if html and not text:
                    text = ContentProcessor.html_to_text(html)

                # Clean HTML if present
                if html:
                    html = ContentProcessor.clean_html(html)

            elif platform.lower() in ['slack', 'discord']:
                # Slack/Discord often use markdown-like formatting
                text = raw_content.get('text', '')
                markdown = raw_content.get(
                    'markdown', text)  # Use text as fallback

            elif platform.lower() == 'twitter':
                # Twitter is primarily text
                text = raw_content.get('text', '')

            else:
                # Generic handling
                text = raw_content.get('text', '')
                html = raw_content.get('html', '')
                markdown = raw_content.get('markdown', '')

            # Clean and process text content
            if text:
                text = ContentProcessor.clean_text(text)

            # Extract metadata
            urls = ContentProcessor.extract_urls(text or html or markdown)
            mentions = ContentProcessor.extract_mentions(
                text or markdown, platform)
            hashtags = ContentProcessor.extract_hashtags(text or markdown)
            language = ContentProcessor.detect_language(text)

            # Calculate content hash for deduplication
            content_hash = ContentProcessor.calculate_content_hash(
                text or html or markdown)

            # Truncate if too long
            if text and len(text) > 10000:
                text = ContentProcessor.truncate_content(text, 10000)

            return MessageContent(
                text=text or None,
                html=html or None,
                markdown=markdown or None,
                content_type=content_type,
                language=language,
                urls=urls,
                mentions=mentions,
                hashtags=hashtags,
                content_hash=content_hash
            )

        except Exception as e:
            logger.error(
                f"Content normalization failed for platform {platform}: {e}")
            # Return minimal content on error
            fallback_text = str(raw_content.get('text', ''))
            return MessageContent(
                text=fallback_text if fallback_text else None,
                content_type=ContentType.TEXT,
                language='en',
                content_hash=ContentProcessor.calculate_content_hash(
                    fallback_text)
            )
