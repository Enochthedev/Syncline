"""
MIME type cleaning and content standardization utilities.

This module provides utilities for cleaning, normalizing, and categorizing
MIME types from various platforms and sources.
"""

import re
from typing import Dict, Set, Optional, Tuple
from enum import Enum


class MimeCategory(str, Enum):
    """High-level MIME type categories."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    APPLICATION = "application"
    MULTIPART = "multipart"
    MESSAGE = "message"
    UNKNOWN = "unknown"


class MimeTypeRegistry:
    """Registry of known MIME types and their properties."""

    # Common MIME type mappings and corrections
    MIME_TYPE_CORRECTIONS = {
        # Microsoft Office formats
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',

        # Legacy Office formats
        'application/msword': 'application/msword',
        'application/vnd.ms-excel': 'application/vnd.ms-excel',
        'application/vnd.ms-powerpoint': 'application/vnd.ms-powerpoint',

        # Common corrections
        'text/x-python': 'text/x-python-script',
        'application/x-javascript': 'application/javascript',
        'application/x-json': 'application/json',
        'image/jpg': 'image/jpeg',
        'audio/mp3': 'audio/mpeg',
        'video/x-msvideo': 'video/avi',

        # Platform-specific corrections
        # Keep as-is, but flag for further analysis
        'application/octet-stream': 'application/octet-stream',
    }

    # File extensions to MIME type mapping
    EXTENSION_TO_MIME = {
        # Text formats
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.xml': 'text/xml',
        '.json': 'application/json',
        '.md': 'text/markdown',
        '.rtf': 'application/rtf',

        # Image formats
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',

        # Video formats
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv',
        '.flv': 'video/x-flv',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.m4v': 'video/x-m4v',

        # Audio formats
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.flac': 'audio/flac',
        '.wma': 'audio/x-ms-wma',

        # Document formats
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',

        # Archive formats
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.bz2': 'application/x-bzip2',

        # Programming files
        '.py': 'text/x-python-script',
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.java': 'text/x-java-source',
        '.cpp': 'text/x-c++src',
        '.c': 'text/x-csrc',
        '.h': 'text/x-chdr',
        '.php': 'application/x-httpd-php',
        '.rb': 'text/x-ruby',
        '.go': 'text/x-go',
        '.rs': 'text/x-rust',
        '.swift': 'text/x-swift',
        '.kt': 'text/x-kotlin',
        '.ts': 'application/typescript',
        '.sql': 'application/sql',
        '.sh': 'application/x-sh',
        '.bat': 'application/x-bat',
        '.ps1': 'application/x-powershell',
    }

    # MIME types that are considered safe for processing
    SAFE_MIME_TYPES = {
        'text/plain', 'text/html', 'text/csv', 'text/markdown', 'text/xml',
        'application/json', 'application/pdf', 'application/rtf',
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
        'video/mp4', 'video/quicktime', 'video/webm',
        'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4',
        'application/msword', 'application/vnd.ms-excel', 'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
    }

    # MIME types that should be treated with caution
    POTENTIALLY_UNSAFE_MIME_TYPES = {
        'application/octet-stream',  # Generic binary
        'application/x-executable',
        'application/x-msdownload',
        'application/x-msdos-program',
        'text/x-shellscript',
        'application/x-sh',
        'application/x-bat',
        'application/javascript',  # Could contain malicious code
        'text/html',  # Could contain scripts (needs sanitization)
    }


class MimeTypeProcessor:
    """Processes and normalizes MIME types."""

    def __init__(self):
        self.registry = MimeTypeRegistry()

    def clean_mime_type(self, mime_type: str) -> str:
        """
        Clean and normalize a MIME type string.

        Args:
            mime_type: Raw MIME type string

        Returns:
            Cleaned and normalized MIME type
        """
        if not mime_type:
            return 'application/octet-stream'

        # Remove parameters and normalize
        cleaned = mime_type.split(';')[0].strip().lower()

        # Remove charset and other parameters
        cleaned = re.sub(r'\s*;.*$', '', cleaned)

        # Apply corrections
        cleaned = self.registry.MIME_TYPE_CORRECTIONS.get(cleaned, cleaned)

        # Validate format
        if not self._is_valid_mime_format(cleaned):
            return 'application/octet-stream'

        return cleaned

    def get_mime_category(self, mime_type: str) -> MimeCategory:
        """
        Get the high-level category for a MIME type.

        Args:
            mime_type: MIME type string

        Returns:
            MimeCategory enum value
        """
        cleaned = self.clean_mime_type(mime_type)

        if cleaned.startswith('text/'):
            return MimeCategory.TEXT
        elif cleaned.startswith('image/'):
            return MimeCategory.IMAGE
        elif cleaned.startswith('video/'):
            return MimeCategory.VIDEO
        elif cleaned.startswith('audio/'):
            return MimeCategory.AUDIO
        elif cleaned.startswith('application/'):
            return MimeCategory.APPLICATION
        elif cleaned.startswith('multipart/'):
            return MimeCategory.MULTIPART
        elif cleaned.startswith('message/'):
            return MimeCategory.MESSAGE
        else:
            return MimeCategory.UNKNOWN

    def guess_mime_from_filename(self, filename: str) -> Optional[str]:
        """
        Guess MIME type from filename extension.

        Args:
            filename: File name with extension

        Returns:
            Guessed MIME type or None if unknown
        """
        if not filename or '.' not in filename:
            return None

        extension = '.' + filename.split('.')[-1].lower()
        return self.registry.EXTENSION_TO_MIME.get(extension)

    def resolve_mime_type(self, declared_mime: Optional[str], filename: Optional[str]) -> str:
        """
        Resolve the best MIME type from declared type and filename.

        Args:
            declared_mime: MIME type declared by the source
            filename: Filename with extension

        Returns:
            Best guess MIME type
        """
        # Clean declared MIME type
        cleaned_declared = None
        if declared_mime:
            cleaned_declared = self.clean_mime_type(declared_mime)

        # Guess from filename
        guessed_from_filename = None
        if filename:
            guessed_from_filename = self.guess_mime_from_filename(filename)

        # Resolution logic
        if cleaned_declared and cleaned_declared != 'application/octet-stream':
            # Trust declared MIME type if it's specific
            return cleaned_declared
        elif guessed_from_filename:
            # Fall back to filename-based guess
            return guessed_from_filename
        elif cleaned_declared:
            # Use cleaned declared type as last resort
            return cleaned_declared
        else:
            # Default fallback
            return 'application/octet-stream'

    def is_safe_mime_type(self, mime_type: str) -> bool:
        """
        Check if a MIME type is considered safe for processing.

        Args:
            mime_type: MIME type to check

        Returns:
            True if safe, False otherwise
        """
        cleaned = self.clean_mime_type(mime_type)
        return cleaned in self.registry.SAFE_MIME_TYPES

    def is_potentially_unsafe(self, mime_type: str) -> bool:
        """
        Check if a MIME type is potentially unsafe.

        Args:
            mime_type: MIME type to check

        Returns:
            True if potentially unsafe, False otherwise
        """
        cleaned = self.clean_mime_type(mime_type)
        return cleaned in self.registry.POTENTIALLY_UNSAFE_MIME_TYPES

    def get_file_type_description(self, mime_type: str) -> str:
        """
        Get a human-readable description of the file type.

        Args:
            mime_type: MIME type

        Returns:
            Human-readable description
        """
        cleaned = self.clean_mime_type(mime_type)

        descriptions = {
            # Text formats
            'text/plain': 'Plain Text',
            'text/html': 'HTML Document',
            'text/csv': 'CSV Spreadsheet',
            'text/markdown': 'Markdown Document',
            'application/json': 'JSON Data',
            'application/xml': 'XML Document',
            'text/xml': 'XML Document',
            'application/rtf': 'Rich Text Document',

            # Images
            'image/jpeg': 'JPEG Image',
            'image/png': 'PNG Image',
            'image/gif': 'GIF Image',
            'image/bmp': 'Bitmap Image',
            'image/webp': 'WebP Image',
            'image/svg+xml': 'SVG Vector Image',

            # Videos
            'video/mp4': 'MP4 Video',
            'video/quicktime': 'QuickTime Video',
            'video/x-msvideo': 'AVI Video',
            'video/webm': 'WebM Video',

            # Audio
            'audio/mpeg': 'MP3 Audio',
            'audio/wav': 'WAV Audio',
            'audio/ogg': 'OGG Audio',
            'audio/mp4': 'M4A Audio',

            # Documents
            'application/pdf': 'PDF Document',
            'application/msword': 'Microsoft Word Document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Microsoft Word Document',
            'application/vnd.ms-excel': 'Microsoft Excel Spreadsheet',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Microsoft Excel Spreadsheet',
            'application/vnd.ms-powerpoint': 'Microsoft PowerPoint Presentation',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'Microsoft PowerPoint Presentation',

            # Archives
            'application/zip': 'ZIP Archive',
            'application/x-rar-compressed': 'RAR Archive',
            'application/x-7z-compressed': '7-Zip Archive',
            'application/gzip': 'Gzip Archive',
            'application/x-tar': 'TAR Archive',

            # Programming
            'text/x-python-script': 'Python Script',
            'application/javascript': 'JavaScript File',
            'text/css': 'CSS Stylesheet',
            'text/x-java-source': 'Java Source Code',
            'application/sql': 'SQL Script',
        }

        return descriptions.get(cleaned, f"Unknown File Type ({cleaned})")

    def _is_valid_mime_format(self, mime_type: str) -> bool:
        """Check if MIME type has valid format (type/subtype)."""
        if not mime_type:
            return False

        # Basic format check: type/subtype
        parts = mime_type.split('/')
        if len(parts) != 2:
            return False

        type_part, subtype_part = parts

        # Check for valid characters (RFC 2045)
        valid_chars = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9!#$&+\-\^_]*$')

        return (
            bool(type_part) and
            bool(subtype_part) and
            valid_chars.match(type_part) and
            valid_chars.match(subtype_part)
        )


# Global instance for easy access
mime_processor = MimeTypeProcessor()


def clean_mime_type(mime_type: str) -> str:
    """Convenience function to clean a MIME type."""
    return mime_processor.clean_mime_type(mime_type)


def get_mime_category(mime_type: str) -> MimeCategory:
    """Convenience function to get MIME category."""
    return mime_processor.get_mime_category(mime_type)


def resolve_mime_type(declared_mime: Optional[str], filename: Optional[str]) -> str:
    """Convenience function to resolve MIME type."""
    return mime_processor.resolve_mime_type(declared_mime, filename)


def is_safe_mime_type(mime_type: str) -> bool:
    """Convenience function to check if MIME type is safe."""
    return mime_processor.is_safe_mime_type(mime_type)


def get_file_type_description(mime_type: str) -> str:
    """Convenience function to get file type description."""
    return mime_processor.get_file_type_description(mime_type)
