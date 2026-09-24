"""
Content processing utilities for message normalization.

This module handles content cleaning, format conversion, HTML to text conversion,
markdown parsing, and content sanitization for messages from different platforms.
"""

import hashlib
import logging
import re
from html import unescape
from typing import List, Optional

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Handles content cleaning, format conversion, and sanitization."""

    @staticmethod
    def clean_html(html_content: str) -> str:
        """
        Clean HTML content by removing dangerous tags and normalizing.

        Args:
            html_content: Raw HTML content

        Returns:
            Cleaned HTML content
        """
        if not html_content:
            return ""

        # Remove script and style tags completely
        html_content = re.sub(
            r"<script[^>]*>.*?</script>",
            "",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html_content = re.sub(
            r"<style[^>]*>.*?</style>",
            "",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove dangerous attributes (onclick, onerror, etc.)
        html_content = re.sub(
            r'\s*on\w+\s*=\s*["\'][^"\']*["\']', "", html_content, flags=re.IGNORECASE
        )

        # Remove javascript: protocol
        html_content = re.sub(
            r"\s*javascript\s*:", "", html_content, flags=re.IGNORECASE
        )

        # Normalize whitespace
        html_content = re.sub(r"\s+", " ", html_content).strip()

        return html_content

    @staticmethod
    def html_to_text(html_content: str) -> str:
        """
        Convert HTML content to plain text.

        Args:
            html_content: HTML formatted content

        Returns:
            Plain text content
        """
        if not html_content:
            return ""

        # Clean HTML first
        clean_html = ContentProcessor.clean_html(html_content)

        # Convert common HTML entities
        clean_html = unescape(clean_html)

        # Convert line breaks
        clean_html = re.sub(r"<br\s*/?>", "\n", clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r"</p>", "\n\n", clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r"</div>", "\n", clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r"</h[1-6]>", "\n\n", clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r"</li>", "\n", clean_html, flags=re.IGNORECASE)

        # Remove all remaining HTML tags
        text = re.sub(r"<[^>]+>", "", clean_html)

        # Normalize whitespace
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)  # Multiple newlines to double
        text = re.sub(r"[ \t]+", " ", text)  # Multiple spaces to single
        text = text.strip()

        return text

    @staticmethod
    def clean_text(text_content: str) -> str:
        """
        Clean plain text content.

        Args:
            text_content: Raw text content

        Returns:
            Cleaned text content
        """
        if not text_content:
            return ""

        # Normalize line endings
        text_content = text_content.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive whitespace
        text_content = re.sub(r"[ \t]+", " ", text_content)
        text_content = re.sub(r"\n\s*\n\s*\n", "\n\n", text_content)

        return text_content.strip()

    @staticmethod
    def sanitize_content(content: str, max_length: int = 100000) -> str:
        """
        Sanitize content by removing potentially harmful patterns.

        Args:
            content: Content to sanitize
            max_length: Maximum allowed content length

        Returns:
            Sanitized content
        """
        if not content:
            return ""

        # Truncate if too long
        if len(content) > max_length:
            content = content[:max_length]

        # Remove null bytes
        content = content.replace("\x00", "")

        # Remove other control characters except newlines and tabs
        content = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]", "", content)

        return content

    @staticmethod
    def parse_markdown(markdown_content: str) -> str:
        """
        Parse markdown content to plain text (basic implementation).

        Args:
            markdown_content: Markdown formatted content

        Returns:
            Plain text content
        """
        if not markdown_content:
            return ""

        text = markdown_content

        # Remove markdown links but keep text: [text](url) -> text
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

        # Remove markdown images: ![alt](url) -> alt
        text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)

        # Remove bold/italic markers
        text = re.sub(r"\*\*([^\*]+)\*\*", r"\1", text)  # **bold**
        text = re.sub(r"__([^_]+)__", r"\1", text)  # __bold__
        text = re.sub(r"\*([^\*]+)\*", r"\1", text)  # *italic*
        text = re.sub(r"_([^_]+)_", r"\1", text)  # _italic_

        # Remove code blocks
        text = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"\1", text)  # Inline code

        # Remove headers
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        # Remove list markers
        text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

        # Clean up whitespace
        text = ContentProcessor.clean_text(text)

        return text

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """
        Extract URLs from text content.

        Args:
            text: Text content

        Returns:
            List of extracted URLs
        """
        if not text:
            return []

        # URL pattern that matches http/https URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
        urls = re.findall(url_pattern, text, re.IGNORECASE)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    @staticmethod
    def extract_mentions(text: str, platform: str) -> List[str]:
        """
        Extract mentions from text based on platform conventions.

        Args:
            text: Text content
            platform: Platform name

        Returns:
            List of extracted mentions
        """
        if not text:
            return []

        mentions = []
        platform_lower = platform.lower()

        if platform_lower == "gmail":
            # Gmail: extract email addresses
            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            mentions = re.findall(email_pattern, text)

        elif platform_lower in ["slack", "discord"]:
            # Slack/Discord: @username or <@userid>
            mention_patterns = [
                r"@([a-zA-Z0-9._-]+)",  # @username
                r"<@([A-Z0-9]+)>",  # <@userid>
            ]
            for pattern in mention_patterns:
                mentions.extend(re.findall(pattern, text))

        elif platform_lower in ["twitter", "telegram"]:
            # Twitter/Telegram: @username
            mentions = re.findall(r"@([a-zA-Z0-9_]+)", text)

        # Remove duplicates
        return list(set(mentions))

    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """
        Extract hashtags from text.

        Args:
            text: Text content

        Returns:
            List of extracted hashtags
        """
        if not text:
            return []

        # Match hashtags (# followed by alphanumeric characters and underscores)
        hashtag_pattern = r"#([a-zA-Z0-9_]+)"
        hashtags = re.findall(hashtag_pattern, text)

        # Remove duplicates
        return list(set(hashtags))

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """
        Calculate a hash for content deduplication.

        Args:
            content: Content to hash

        Returns:
            SHA256 hash of normalized content
        """
        if not content:
            return ""

        # Normalize content for hashing
        normalized = re.sub(r"\s+", " ", content.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def truncate_content(content: str, max_length: int = 10000) -> str:
        """
        Truncate content to maximum length while preserving word boundaries.

        Args:
            content: Content to truncate
            max_length: Maximum allowed length

        Returns:
            Truncated content
        """
        if not content or len(content) <= max_length:
            return content

        # Find the last space before the limit
        truncated = content[:max_length]
        last_space = truncated.rfind(" ")

        # If we found a space reasonably close to the limit
        if last_space > max_length * 0.8:
            return content[:last_space] + "..."
        else:
            return content[:max_length] + "..."

    @staticmethod
    def detect_language(text: str) -> Optional[str]:
        """
        Detect the language of text content (basic implementation).

        Args:
            text: Text content

        Returns:
            ISO 639-1 language code or None
        """
        if not text or len(text.strip()) < 10:
            return None

        try:
            # Simple language detection based on character patterns
            text_lower = text.lower()

            # Check for common English words
            english_words = [
                "the",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "is",
                "are",
            ]
            english_count = sum(
                1 for word in english_words if f" {word} " in f" {text_lower} "
            )

            if english_count >= 2:
                return "en"

            # Check for other language patterns
            if re.search(r"[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]", text_lower):
                return "es"  # Spanish/French/other Romance languages

            if re.search(r"[äöüß]", text_lower):
                return "de"  # German

            # Default to English if uncertain
            return "en"

        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return "en"
