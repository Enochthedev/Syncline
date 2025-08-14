"""
Tests for MIME type processing utilities.

Tests MIME type cleaning, categorization, safety checks, and file type detection.
"""

import pytest
from utils.mime_utils import (
    MimeTypeProcessor, MimeCategory, clean_mime_type, get_mime_category,
    resolve_mime_type, is_safe_mime_type, get_file_type_description
)


class TestMimeTypeProcessor:
    """Test MIME type processing utilities."""

    def test_mime_type_cleaning(self):
        """Test MIME type cleaning and normalization."""
        processor = MimeTypeProcessor()

        # Test parameter removal
        assert processor.clean_mime_type(
            'text/html; charset=utf-8') == 'text/html'

        # Test case normalization
        assert processor.clean_mime_type('IMAGE/JPEG') == 'image/jpeg'

        # Test corrections
        assert processor.clean_mime_type('image/jpg') == 'image/jpeg'
        assert processor.clean_mime_type('audio/mp3') == 'audio/mpeg'

        # Test invalid formats
        assert processor.clean_mime_type(
            'invalid') == 'application/octet-stream'
        assert processor.clean_mime_type('') == 'application/octet-stream'

    def test_mime_type_cleaning_edge_cases(self):
        """Test MIME type cleaning edge cases."""
        processor = MimeTypeProcessor()

        # Test None input
        assert processor.clean_mime_type(None) == 'application/octet-stream'

        # Test whitespace handling
        assert processor.clean_mime_type('  text/plain  ') == 'text/plain'

        # Test multiple parameters
        assert processor.clean_mime_type(
            'text/html; charset=utf-8; boundary=something') == 'text/html'

        # Test malformed MIME types
        assert processor.clean_mime_type('text/') == 'application/octet-stream'
        assert processor.clean_mime_type(
            '/plain') == 'application/octet-stream'
        assert processor.clean_mime_type('text') == 'application/octet-stream'

    def test_mime_category_detection(self):
        """Test MIME category detection."""
        processor = MimeTypeProcessor()

        assert processor.get_mime_category('text/plain') == MimeCategory.TEXT
        assert processor.get_mime_category('image/jpeg') == MimeCategory.IMAGE
        assert processor.get_mime_category('video/mp4') == MimeCategory.VIDEO
        assert processor.get_mime_category('audio/mpeg') == MimeCategory.AUDIO
        assert processor.get_mime_category(
            'application/pdf') == MimeCategory.APPLICATION
        assert processor.get_mime_category(
            'multipart/mixed') == MimeCategory.MULTIPART
        assert processor.get_mime_category(
            'message/rfc822') == MimeCategory.MESSAGE
        assert processor.get_mime_category(
            'unknown/type') == MimeCategory.UNKNOWN

    def test_mime_guessing_from_filename(self):
        """Test MIME type guessing from filename."""
        processor = MimeTypeProcessor()

        assert processor.guess_mime_from_filename(
            'document.pdf') == 'application/pdf'
        assert processor.guess_mime_from_filename('image.JPG') == 'image/jpeg'
        assert processor.guess_mime_from_filename(
            'script.py') == 'text/x-python-script'
        assert processor.guess_mime_from_filename('noextension') is None
        assert processor.guess_mime_from_filename('unknown.xyz') is None

    def test_filename_extension_mapping(self):
        """Test comprehensive filename extension mapping."""
        processor = MimeTypeProcessor()

        test_cases = [
            # Images
            ('photo.png', 'image/png'),
            ('icon.gif', 'image/gif'),
            ('picture.bmp', 'image/bmp'),
            ('vector.svg', 'image/svg+xml'),

            # Documents
            ('report.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            ('spreadsheet.xlsx',
             'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('presentation.pptx',
             'application/vnd.openxmlformats-officedocument.presentationml.presentation'),

            # Archives
            ('archive.zip', 'application/zip'),
            ('backup.tar', 'application/x-tar'),
            ('compressed.gz', 'application/gzip'),

            # Programming files
            ('script.js', 'application/javascript'),
            ('style.css', 'text/css'),
            ('data.json', 'application/json'),
            ('config.xml', 'text/xml'),
        ]

        for filename, expected_mime in test_cases:
            result = processor.guess_mime_from_filename(filename)
            assert result == expected_mime, f"Failed for {filename}: expected {expected_mime}, got {result}"

    def test_mime_type_resolution(self):
        """Test MIME type resolution logic."""
        processor = MimeTypeProcessor()

        # Declared type takes precedence
        result = processor.resolve_mime_type('text/plain', 'document.pdf')
        assert result == 'text/plain'

        # Filename fallback when declared is generic
        result = processor.resolve_mime_type(
            'application/octet-stream', 'image.jpg')
        assert result == 'image/jpeg'

        # Filename only
        result = processor.resolve_mime_type(None, 'video.mp4')
        assert result == 'video/mp4'

        # Default fallback
        result = processor.resolve_mime_type(None, None)
        assert result == 'application/octet-stream'

    def test_mime_resolution_priority(self):
        """Test MIME type resolution priority logic."""
        processor = MimeTypeProcessor()

        # Specific declared type beats filename guess
        result = processor.resolve_mime_type('application/json', 'file.txt')
        assert result == 'application/json'

        # Generic declared type loses to filename guess
        result = processor.resolve_mime_type(
            'application/octet-stream', 'document.pdf')
        assert result == 'application/pdf'

        # Empty string treated as None
        result = processor.resolve_mime_type('', 'image.png')
        assert result == 'image/png'

    def test_safety_checks(self):
        """Test MIME type safety checks."""
        processor = MimeTypeProcessor()

        # Safe types
        assert processor.is_safe_mime_type('text/plain') is True
        assert processor.is_safe_mime_type('image/jpeg') is True
        assert processor.is_safe_mime_type('application/pdf') is True

        # Potentially unsafe types
        assert processor.is_potentially_unsafe(
            'application/octet-stream') is True
        assert processor.is_potentially_unsafe(
            'application/javascript') is True
        assert processor.is_potentially_unsafe('text/html') is True

    def test_safety_classification(self):
        """Test comprehensive safety classification."""
        processor = MimeTypeProcessor()

        safe_types = [
            'text/plain', 'text/csv', 'image/png', 'image/jpeg',
            'video/mp4', 'audio/mpeg', 'application/pdf'
        ]

        unsafe_types = [
            'application/octet-stream', 'application/x-executable',
            'application/javascript', 'text/x-shellscript'
        ]

        for mime_type in safe_types:
            assert processor.is_safe_mime_type(
                mime_type), f"{mime_type} should be safe"
            assert not processor.is_potentially_unsafe(
                mime_type), f"{mime_type} should not be unsafe"

        for mime_type in unsafe_types:
            assert processor.is_potentially_unsafe(
                mime_type), f"{mime_type} should be potentially unsafe"

    def test_file_type_descriptions(self):
        """Test human-readable file type descriptions."""
        processor = MimeTypeProcessor()

        assert 'PDF' in processor.get_file_type_description('application/pdf')
        assert 'JPEG' in processor.get_file_type_description('image/jpeg')
        assert 'Word' in processor.get_file_type_description(
            'application/msword')
        assert 'Unknown' in processor.get_file_type_description('unknown/type')

    def test_description_accuracy(self):
        """Test accuracy of file type descriptions."""
        processor = MimeTypeProcessor()

        test_cases = [
            ('text/plain', 'Plain Text'),
            ('image/png', 'PNG Image'),
            ('video/mp4', 'MP4 Video'),
            ('audio/mpeg', 'MP3 Audio'),
            ('application/zip', 'ZIP Archive'),
            ('application/msword', 'Microsoft Word Document'),
        ]

        for mime_type, expected_desc in test_cases:
            result = processor.get_file_type_description(mime_type)
            assert expected_desc in result, f"Description for {mime_type} should contain '{expected_desc}'"

    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        assert clean_mime_type('TEXT/PLAIN; charset=utf-8') == 'text/plain'
        assert get_mime_category('image/png') == MimeCategory.IMAGE
        assert resolve_mime_type('text/plain', 'file.txt') == 'text/plain'
        assert is_safe_mime_type('application/pdf') is True

    def test_mime_format_validation(self):
        """Test MIME type format validation."""
        processor = MimeTypeProcessor()

        # Valid formats
        valid_types = [
            'text/plain',
            'image/svg+xml',
            'application/x-7z-compressed'
        ]

        for mime_type in valid_types:
            assert processor._is_valid_mime_format(
                mime_type), f"{mime_type} should be valid"

        # Invalid formats
        invalid_types = [
            'text',
            'text/',
            '/plain',
            'text/plain/extra',
            'text plain',
            '',
            None
        ]

        for mime_type in invalid_types:
            assert not processor._is_valid_mime_format(
                mime_type), f"{mime_type} should be invalid"

    def test_mime_corrections(self):
        """Test MIME type corrections and normalizations."""
        processor = MimeTypeProcessor()

        corrections = [
            ('image/jpg', 'image/jpeg'),
            ('audio/mp3', 'audio/mpeg'),
            ('application/x-javascript', 'application/javascript'),
            ('application/x-json', 'application/json'),
            ('video/x-msvideo', 'video/avi'),
        ]

        for input_mime, expected_mime in corrections:
            result = processor.clean_mime_type(input_mime)
            assert result == expected_mime, f"Expected {input_mime} -> {expected_mime}, got {result}"
