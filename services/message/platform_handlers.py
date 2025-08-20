"""
Platform-specific message handlers for normalization.

This module provides specialized handlers for different messaging platforms
to convert their specific message formats to the unified schema.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod

from services.message_schema import (
    RawMessage, NormalizedMessage, MessageContent, Attachment, Participant, Thread,
    Platform, ContentType, AttachmentType
)
from .content_processor import ContentProcessor

logger = logging.getLogger(__name__)


class BasePlatformHandler(ABC):
    """Abstract base class for platform-specific message handlers."""

    @abstractmethod
    def normalize_message(self, raw_message: RawMessage) -> NormalizedMessage:
        """Normalize a raw message to the unified format."""
        pass

    @abstractmethod
    def normalize_participant(self, raw_participant: Dict[str, Any]) -> Participant:
        """Normalize participant information."""
        pass

    @abstractmethod
    def normalize_attachments(self, raw_attachments: List[Dict[str, Any]]) -> List[Attachment]:
        """Normalize attachment information."""
        pass


class GmailHandler(BasePlatformHandler):
    """Handler for Gmail messages."""

    def normalize_message(self, raw_message: RawMessage) -> NormalizedMessage:
        """Normalize Gmail message to unified format."""
        try:
            # Extract Gmail-specific data
            gmail_data = raw_message.platform_data

            # Normalize participants
            sender = self.normalize_participant(gmail_data.get('sender', {}))
            recipients = [
                self.normalize_participant(recipient)
                for recipient in gmail_data.get('recipients', [])
            ]

            # Normalize content
            content = ContentProcessor.normalize_content(
                gmail_data.get('content', {}),
                'gmail',
                ContentType.EMAIL
            )

            # Normalize attachments
            attachments = self.normalize_attachments(
                gmail_data.get('attachments', []))

            # Create thread information
            thread = Thread(
                id=gmail_data.get('thread_id', raw_message.id),
                subject=gmail_data.get('subject', ''),
                participant_count=len(recipients) + 1  # +1 for sender
            )

            return NormalizedMessage(
                id=raw_message.id,
                platform=Platform.GMAIL,
                thread_id=thread.id,
                sender=sender,
                recipients=recipients,
                content=content,
                attachments=attachments,
                thread=thread,
                timestamp=raw_message.timestamp,
                platform_message_id=gmail_data.get('message_id'),
                platform_thread_id=gmail_data.get('thread_id'),
                metadata={
                    'subject': gmail_data.get('subject', ''),
                    'labels': gmail_data.get('labels', []),
                    'importance': gmail_data.get('importance', 'normal')
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to normalize Gmail message {raw_message.id}: {e}")
            raise

    def normalize_participant(self, raw_participant: Dict[str, Any]) -> Participant:
        """Normalize Gmail participant."""
        return Participant(
            id=raw_participant.get('email', ''),
            display_name=raw_participant.get('name', ''),
            email=raw_participant.get('email'),
            platform_user_id=raw_participant.get('email'),
            is_bot=False  # Gmail doesn't typically have bots
        )

    def normalize_attachments(self, raw_attachments: List[Dict[str, Any]]) -> List[Attachment]:
        """Normalize Gmail attachments."""
        attachments = []

        for raw_attachment in raw_attachments:
            try:
                attachment = Attachment(
                    id=raw_attachment.get('attachment_id', ''),
                    filename=raw_attachment.get('filename', 'unknown'),
                    mime_type=raw_attachment.get(
                        'mime_type', 'application/octet-stream'),
                    size_bytes=raw_attachment.get('size', 0),
                    attachment_type=self._determine_attachment_type(
                        raw_attachment.get('mime_type', '')),
                    url=raw_attachment.get('url'),
                    local_path=raw_attachment.get('local_path'),
                    metadata={
                        'content_id': raw_attachment.get('content_id'),
                        'inline': raw_attachment.get('inline', False)
                    }
                )
                attachments.append(attachment)

            except Exception as e:
                logger.warning(f"Failed to normalize attachment: {e}")
                continue

        return attachments

    def _determine_attachment_type(self, mime_type: str) -> AttachmentType:
        """Determine attachment type from MIME type."""
        if not mime_type:
            return AttachmentType.OTHER

        mime_lower = mime_type.lower()

        if mime_lower.startswith('image/'):
            return AttachmentType.IMAGE
        elif mime_lower.startswith('video/'):
            return AttachmentType.VIDEO
        elif mime_lower.startswith('audio/'):
            return AttachmentType.AUDIO
        elif mime_lower in ['application/pdf', 'text/plain', 'application/msword',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return AttachmentType.DOCUMENT
        else:
            return AttachmentType.OTHER


class SlackHandler(BasePlatformHandler):
    """Handler for Slack messages."""

    def normalize_message(self, raw_message: RawMessage) -> NormalizedMessage:
        """Normalize Slack message to unified format."""
        try:
            slack_data = raw_message.platform_data

            # Normalize participants
            sender = self.normalize_participant(slack_data.get('sender', {}))

            # Slack messages are typically in channels, so recipients are implicit
            recipients = []

            # Normalize content
            content = ContentProcessor.normalize_content(
                slack_data.get('content', {}),
                'slack',
                ContentType.CHAT
            )

            # Normalize attachments
            attachments = self.normalize_attachments(
                slack_data.get('attachments', []))

            # Create thread information
            thread = Thread(
                id=slack_data.get('channel_id', raw_message.id),
                subject=slack_data.get('channel_name', ''),
                participant_count=slack_data.get('channel_member_count', 1)
            )

            return NormalizedMessage(
                id=raw_message.id,
                platform=Platform.SLACK,
                thread_id=thread.id,
                sender=sender,
                recipients=recipients,
                content=content,
                attachments=attachments,
                thread=thread,
                timestamp=raw_message.timestamp,
                platform_message_id=slack_data.get('ts'),
                platform_thread_id=slack_data.get('channel_id'),
                metadata={
                    'channel_name': slack_data.get('channel_name', ''),
                    'channel_type': slack_data.get('channel_type', 'public'),
                    'thread_ts': slack_data.get('thread_ts'),
                    'reactions': slack_data.get('reactions', [])
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to normalize Slack message {raw_message.id}: {e}")
            raise

    def normalize_participant(self, raw_participant: Dict[str, Any]) -> Participant:
        """Normalize Slack participant."""
        return Participant(
            id=raw_participant.get('user_id', ''),
            display_name=raw_participant.get(
                'display_name', raw_participant.get('real_name', '')),
            email=raw_participant.get('email'),
            platform_user_id=raw_participant.get('user_id'),
            is_bot=raw_participant.get('is_bot', False)
        )

    def normalize_attachments(self, raw_attachments: List[Dict[str, Any]]) -> List[Attachment]:
        """Normalize Slack attachments."""
        attachments = []

        for raw_attachment in raw_attachments:
            try:
                attachment = Attachment(
                    id=raw_attachment.get('id', ''),
                    filename=raw_attachment.get('name', 'unknown'),
                    mime_type=raw_attachment.get(
                        'mimetype', 'application/octet-stream'),
                    size_bytes=raw_attachment.get('size', 0),
                    attachment_type=self._determine_attachment_type(
                        raw_attachment.get('mimetype', '')),
                    url=raw_attachment.get('url_private'),
                    metadata={
                        'title': raw_attachment.get('title'),
                        'permalink': raw_attachment.get('permalink')
                    }
                )
                attachments.append(attachment)

            except Exception as e:
                logger.warning(f"Failed to normalize Slack attachment: {e}")
                continue

        return attachments

    def _determine_attachment_type(self, mime_type: str) -> AttachmentType:
        """Determine attachment type from MIME type."""
        # Same logic as Gmail handler
        return GmailHandler()._determine_attachment_type(mime_type)


class TwitterHandler(BasePlatformHandler):
    """Handler for Twitter/X messages."""

    def normalize_message(self, raw_message: RawMessage) -> NormalizedMessage:
        """Normalize Twitter message to unified format."""
        try:
            twitter_data = raw_message.platform_data

            # Normalize participants
            sender = self.normalize_participant(twitter_data.get('sender', {}))

            # Twitter mentions become recipients
            recipients = [
                self.normalize_participant(mention)
                for mention in twitter_data.get('mentions', [])
            ]

            # Normalize content
            content = ContentProcessor.normalize_content(
                twitter_data.get('content', {}),
                'twitter',
                ContentType.SOCIAL
            )

            # Normalize attachments (media)
            attachments = self.normalize_attachments(
                twitter_data.get('media', []))

            # Create thread information (for reply chains)
            thread = Thread(
                id=twitter_data.get('conversation_id', raw_message.id),
                subject='',  # Twitter doesn't have subjects
                participant_count=len(recipients) + 1
            )

            return NormalizedMessage(
                id=raw_message.id,
                platform=Platform.TWITTER,
                thread_id=thread.id,
                sender=sender,
                recipients=recipients,
                content=content,
                attachments=attachments,
                thread=thread,
                timestamp=raw_message.timestamp,
                platform_message_id=twitter_data.get('tweet_id'),
                platform_thread_id=twitter_data.get('conversation_id'),
                metadata={
                    'retweet_count': twitter_data.get('retweet_count', 0),
                    'like_count': twitter_data.get('like_count', 0),
                    'reply_count': twitter_data.get('reply_count', 0),
                    'is_retweet': twitter_data.get('is_retweet', False),
                    'hashtags': twitter_data.get('hashtags', [])
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to normalize Twitter message {raw_message.id}: {e}")
            raise

    def normalize_participant(self, raw_participant: Dict[str, Any]) -> Participant:
        """Normalize Twitter participant."""
        return Participant(
            id=raw_participant.get('username', ''),
            display_name=raw_participant.get('display_name', ''),
            email=None,  # Twitter doesn't expose emails
            platform_user_id=raw_participant.get('user_id'),
            is_bot=raw_participant.get('is_bot', False)
        )

    def normalize_attachments(self, raw_attachments: List[Dict[str, Any]]) -> List[Attachment]:
        """Normalize Twitter media attachments."""
        attachments = []

        for raw_media in raw_attachments:
            try:
                attachment = Attachment(
                    id=raw_media.get('media_key', ''),
                    filename=f"twitter_media_{raw_media.get('media_key', 'unknown')}",
                    mime_type=raw_media.get(
                        'type', 'image/jpeg'),  # Twitter default
                    size_bytes=raw_media.get('size', 0),
                    attachment_type=self._determine_twitter_media_type(
                        raw_media.get('type', '')),
                    url=raw_media.get('url'),
                    metadata={
                        'width': raw_media.get('width'),
                        'height': raw_media.get('height'),
                        'alt_text': raw_media.get('alt_text')
                    }
                )
                attachments.append(attachment)

            except Exception as e:
                logger.warning(f"Failed to normalize Twitter media: {e}")
                continue

        return attachments

    def _determine_twitter_media_type(self, media_type: str) -> AttachmentType:
        """Determine attachment type from Twitter media type."""
        if not media_type:
            return AttachmentType.IMAGE  # Default for Twitter

        media_lower = media_type.lower()

        if media_lower in ['photo', 'image']:
            return AttachmentType.IMAGE
        elif media_lower in ['video', 'animated_gif']:
            return AttachmentType.VIDEO
        else:
            return AttachmentType.OTHER


class LinkedInHandler(BasePlatformHandler):
    """Handler for LinkedIn messages with professional context awareness."""

    def normalize_message(self, raw_message: RawMessage) -> NormalizedMessage:
        """Normalize LinkedIn message to unified format with professional context."""
        try:
            linkedin_data = raw_message.raw_data

            # Normalize participants with professional context
            sender = self.normalize_participant(
                linkedin_data.get('sender', {}))
            recipients = [
                self.normalize_participant(recipient)
                for recipient in linkedin_data.get('recipients', [])
            ]

            # Normalize content with business context preservation
            content_data = linkedin_data.get('content', {})
            content = MessageContent(
                text=content_data.get('text', ''),
                html=content_data.get('html'),
                markdown=content_data.get('markdown'),
                primary_format=ContentType.TEXT
            )

            # Enhance content with professional context
            content = self._enhance_professional_content(
                content, linkedin_data)

            # Normalize attachments
            attachments = self.normalize_attachments(
                linkedin_data.get('attachments', []))

            # Create thread information
            thread = Thread(
                id=linkedin_data.get(
                    'conversation_id', raw_message.platform_message_id),
                title=linkedin_data.get('subject', ''),
                platform=Platform.LINKEDIN,
                platform_thread_id=linkedin_data.get('conversation_id', ''),
                participants=[sender.id] + [r.id for r in recipients]
            )

            return NormalizedMessage(
                id=raw_message.platform_message_id,
                platform=Platform.LINKEDIN,
                thread_id=thread.id,
                sender=sender,
                recipients=recipients,
                content=content,
                attachments=attachments,
                timestamp=raw_message.received_at,
                platform_message_id=linkedin_data.get(
                    'message_id', raw_message.platform_message_id),
                metadata={
                    'conversation_type': linkedin_data.get('conversation_type', 'direct'),
                    'professional_context': self._extract_professional_context(linkedin_data),
                    'business_relationship': self._analyze_business_relationship(sender, recipients),
                    'industry_context': linkedin_data.get('industry_context', {}),
                    'company_context': linkedin_data.get('company_context', {}),
                    'connection_degree': linkedin_data.get('connection_degree', 'unknown'),
                    'platform_thread_id': linkedin_data.get('conversation_id', '')
                },
                raw_data=linkedin_data
            )

        except Exception as e:
            logger.error(
                f"Failed to normalize LinkedIn message {raw_message.platform_message_id}: {e}")
            raise

    def normalize_participant(self, raw_participant: Dict[str, Any]) -> Participant:
        """Normalize LinkedIn participant with professional information."""
        participant = Participant(
            id=raw_participant.get('linkedin_id', ''),
            display_name=raw_participant.get('display_name', ''),
            email=raw_participant.get('email'),
            platform_user_id=raw_participant.get('linkedin_id'),
            platform=Platform.LINKEDIN
        )

        # Add professional metadata
        participant.metadata.update({
            'job_title': raw_participant.get('job_title'),
            'company': raw_participant.get('company'),
            'industry': raw_participant.get('industry'),
            'location': raw_participant.get('location'),
            'connection_degree': raw_participant.get('connection_degree'),
            'profile_url': raw_participant.get('profile_url'),
            'headline': raw_participant.get('headline'),
            'professional_summary': raw_participant.get('summary'),
            'skills': raw_participant.get('skills', []),
            'experience': raw_participant.get('experience', []),
            'education': raw_participant.get('education', [])
        })

        return participant

    def normalize_attachments(self, raw_attachments: List[Dict[str, Any]]) -> List[Attachment]:
        """Normalize LinkedIn attachments with business context."""
        attachments = []

        for raw_attachment in raw_attachments:
            try:
                attachment = Attachment(
                    id=raw_attachment.get('attachment_id', ''),
                    filename=raw_attachment.get('filename', 'unknown'),
                    mime_type=raw_attachment.get(
                        'mime_type', 'application/octet-stream'),
                    size_bytes=raw_attachment.get('size', 0),
                    attachment_type=self._determine_attachment_type(
                        raw_attachment.get('mime_type', '')),
                    url=raw_attachment.get('url'),
                    local_path=raw_attachment.get('local_path'),
                    metadata={
                        'business_context': raw_attachment.get('business_context'),
                        'document_type': raw_attachment.get('document_type'),
                        'shared_by_company': raw_attachment.get('shared_by_company'),
                        'is_professional_document': raw_attachment.get('is_professional_document', False)
                    }
                )
                attachments.append(attachment)

            except Exception as e:
                logger.warning(f"Failed to normalize LinkedIn attachment: {e}")
                continue

        return attachments

    def _enhance_professional_content(self, content: MessageContent, linkedin_data: Dict[str, Any]) -> MessageContent:
        """Enhance content with professional context markers."""
        if not content.text:
            return content

        # Add professional context markers to the content
        professional_markers = []

        # Check for business-related keywords
        business_keywords = ['meeting', 'project', 'proposal', 'contract', 'opportunity',
                             'collaboration', 'partnership', 'investment', 'client', 'customer']

        for keyword in business_keywords:
            if keyword.lower() in content.text.lower():
                professional_markers.append(keyword)

        # Add professional context to metadata
        if professional_markers:
            if not hasattr(content, 'metadata'):
                content.metadata = {}
            content.metadata['professional_keywords'] = professional_markers
            content.metadata['business_context_detected'] = True

        return content

    def _extract_professional_context(self, linkedin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract professional context from LinkedIn message data."""
        return {
            'sender_company': linkedin_data.get('sender', {}).get('company'),
            'sender_job_title': linkedin_data.get('sender', {}).get('job_title'),
            'sender_industry': linkedin_data.get('sender', {}).get('industry'),
            'conversation_context': linkedin_data.get('conversation_context', 'professional'),
            'is_business_inquiry': linkedin_data.get('is_business_inquiry', False),
            'is_recruitment_related': linkedin_data.get('is_recruitment_related', False),
            'is_sales_outreach': linkedin_data.get('is_sales_outreach', False),
            'professional_relationship_type': linkedin_data.get('professional_relationship_type', 'unknown')
        }

    def _analyze_business_relationship(self, sender: Participant, recipients: List[Participant]) -> Dict[str, Any]:
        """Analyze business relationship between participants."""
        relationship_analysis = {
            'relationship_type': 'professional',
            'same_company': False,
            'same_industry': False,
            'connection_strength': 'unknown'
        }

        if not recipients:
            return relationship_analysis

        sender_company = sender.metadata.get('company')
        sender_industry = sender.metadata.get('industry')

        for recipient in recipients:
            recipient_company = recipient.metadata.get('company')
            recipient_industry = recipient.metadata.get('industry')

            if sender_company and recipient_company:
                if sender_company.lower() == recipient_company.lower():
                    relationship_analysis['same_company'] = True
                    relationship_analysis['relationship_type'] = 'colleague'

            if sender_industry and recipient_industry:
                if sender_industry.lower() == recipient_industry.lower():
                    relationship_analysis['same_industry'] = True

            # Analyze connection degree
            connection_degree = recipient.metadata.get(
                'connection_degree', 'unknown')
            if connection_degree == '1st':
                relationship_analysis['connection_strength'] = 'direct'
            elif connection_degree == '2nd':
                relationship_analysis['connection_strength'] = 'second_degree'
            elif connection_degree == '3rd':
                relationship_analysis['connection_strength'] = 'third_degree'

        return relationship_analysis

    def _determine_attachment_type(self, mime_type: str) -> AttachmentType:
        """Determine attachment type from MIME type with LinkedIn-specific handling."""
        if not mime_type:
            return AttachmentType.OTHER

        mime_lower = mime_type.lower()

        # LinkedIn-specific document types
        if mime_lower in ['application/pdf', 'application/msword',
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return AttachmentType.DOCUMENT
        elif mime_lower.startswith('image/'):
            return AttachmentType.IMAGE
        elif mime_lower.startswith('video/'):
            return AttachmentType.VIDEO
        elif mime_lower.startswith('audio/'):
            return AttachmentType.AUDIO
        else:
            return AttachmentType.OTHER


class PlatformHandlerRegistry:
    """Registry for platform-specific message handlers."""

    def __init__(self):
        """Initialize the handler registry."""
        self._handlers: Dict[Platform, BasePlatformHandler] = {
            Platform.GMAIL: GmailHandler(),
            Platform.SLACK: SlackHandler(),
            Platform.TWITTER: TwitterHandler(),
            Platform.LINKEDIN: LinkedInHandler(),
        }

    def register_handler(self, platform: Platform, handler: BasePlatformHandler) -> None:
        """Register a handler for a specific platform."""
        self._handlers[platform] = handler
        logger.info(f"Registered handler for platform: {platform}")

    def get_handler(self, platform: Platform) -> Optional[BasePlatformHandler]:
        """Get the handler for a specific platform."""
        return self._handlers.get(platform)

    def get_supported_platforms(self) -> List[Platform]:
        """Get list of supported platforms."""
        return list(self._handlers.keys())

    def normalize_message(self, raw_message: RawMessage) -> NormalizedMessage:
        """Normalize a message using the appropriate platform handler."""
        handler = self.get_handler(raw_message.platform)

        if not handler:
            raise ValueError(
                f"No handler registered for platform: {raw_message.platform}")

        return handler.normalize_message(raw_message)


# Global registry instance
_platform_registry = PlatformHandlerRegistry()


def get_platform_registry() -> PlatformHandlerRegistry:
    """Get the global platform handler registry."""
    return _platform_registry
