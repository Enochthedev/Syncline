"""
Attachment handler for downloading and storing message attachments.

Handles downloading attachments from platform URLs and storing them
in the blob storage system with proper metadata tracking.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from uuid import UUID
import aiohttp

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models.attachment import Attachment
from db.models.message import Message
from services.storage.blob_storage import (
    get_default_storage_manager,
    BlobStorageError,
    BlobNotFoundError
)

logger = logging.getLogger(__name__)


class AttachmentHandler:
    """
    Handler for message attachment operations.
    
    Manages downloading attachments from platform URLs and storing
    them in the blob storage system with database metadata.
    """

    def __init__(self, storage_manager=None):
        """
        Initialize attachment handler.
        
        Args:
            storage_manager: Optional BlobStorageManager instance
        """
        self.storage_manager = storage_manager or get_default_storage_manager()
        logger.info("AttachmentHandler initialized")

    async def download_and_store_attachment(
        self,
        db: AsyncSession,
        message_id: UUID,
        platform_url: str,
        filename: str,
        mime_type: Optional[str] = None,
        timeout: int = 30
    ) -> Attachment:
        """
        Download attachment from URL and store it.
        
        Args:
            db: Database session
            message_id: ID of the message this attachment belongs to
            platform_url: URL to download the attachment from
            filename: Original filename
            mime_type: MIME type of the file
            timeout: Download timeout in seconds
            
        Returns:
            Created Attachment model instance
            
        Raises:
            BlobStorageError: If download or storage fails
        """
        try:
            # Generate storage path: attachments/{message_id}/{filename}
            storage_path = f"attachments/{message_id}/{filename}"

            # Download and store the file
            stored_path = await self.storage_manager.store_from_url(
                url=platform_url,
                storage_path=storage_path,
                timeout=timeout
            )

            # Get file metadata
            metadata = await self.storage_manager.get_metadata(stored_path)
            file_size = metadata.get('size', 0)

            # Create attachment record in database
            attachment = Attachment(
                message_id=message_id,
                filename=filename,
                mime_type=mime_type,
                size_bytes=file_size,
                storage_path=stored_path,
                platform_url=platform_url
            )

            db.add(attachment)
            await db.commit()
            await db.refresh(attachment)

            logger.info(
                f"Downloaded and stored attachment: {filename} "
                f"({file_size} bytes) for message {message_id}"
            )

            return attachment

        except Exception as e:
            await db.rollback()
            logger.error(
                f"Failed to download attachment {filename} "
                f"from {platform_url}: {e}"
            )
            raise

    async def store_attachment_content(
        self,
        db: AsyncSession,
        message_id: UUID,
        filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
        platform_url: Optional[str] = None
    ) -> Attachment:
        """
        Store attachment content directly (without downloading).
        
        Args:
            db: Database session
            message_id: ID of the message this attachment belongs to
            filename: Original filename
            content: File content as bytes
            mime_type: MIME type of the file
            platform_url: Optional original platform URL
            
        Returns:
            Created Attachment model instance
            
        Raises:
            BlobStorageError: If storage fails
        """
        try:
            # Generate storage path
            storage_path = f"attachments/{message_id}/{filename}"

            # Store the file
            stored_path = await self.storage_manager.store(
                path=storage_path,
                content=content,
                content_type=mime_type
            )

            # Create attachment record in database
            attachment = Attachment(
                message_id=message_id,
                filename=filename,
                mime_type=mime_type,
                size_bytes=len(content),
                storage_path=stored_path,
                platform_url=platform_url
            )

            db.add(attachment)
            await db.commit()
            await db.refresh(attachment)

            logger.info(
                f"Stored attachment: {filename} "
                f"({len(content)} bytes) for message {message_id}"
            )

            return attachment

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to store attachment {filename}: {e}")
            raise

    async def get_attachment_content(
        self,
        db: AsyncSession,
        attachment_id: UUID
    ) -> bytes:
        """
        Retrieve attachment content from storage.
        
        Args:
            db: Database session
            attachment_id: ID of the attachment
            
        Returns:
            File content as bytes
            
        Raises:
            ValueError: If attachment not found in database
            BlobNotFoundError: If file not found in storage
        """
        try:
            # Get attachment record from database
            result = await db.execute(
                select(Attachment).where(Attachment.id == attachment_id)
            )
            attachment = result.scalar_one_or_none()

            if not attachment:
                raise ValueError(f"Attachment not found: {attachment_id}")

            # Retrieve content from storage
            content = await self.storage_manager.retrieve(attachment.storage_path)

            logger.debug(
                f"Retrieved attachment content: {attachment.filename} "
                f"({len(content)} bytes)"
            )

            return content

        except Exception as e:
            logger.error(f"Failed to get attachment content {attachment_id}: {e}")
            raise

    async def delete_attachment(
        self,
        db: AsyncSession,
        attachment_id: UUID
    ) -> bool:
        """
        Delete attachment from storage and database.
        
        Args:
            db: Database session
            attachment_id: ID of the attachment to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            # Get attachment record
            result = await db.execute(
                select(Attachment).where(Attachment.id == attachment_id)
            )
            attachment = result.scalar_one_or_none()

            if not attachment:
                return False

            # Delete from storage
            try:
                await self.storage_manager.delete(attachment.storage_path)
            except BlobNotFoundError:
                logger.warning(
                    f"Attachment file not found in storage: {attachment.storage_path}"
                )

            # Delete from database
            await db.delete(attachment)
            await db.commit()

            logger.info(f"Deleted attachment: {attachment.filename}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete attachment {attachment_id}: {e}")
            raise

    async def get_message_attachments(
        self,
        db: AsyncSession,
        message_id: UUID
    ) -> List[Attachment]:
        """
        Get all attachments for a message.
        
        Args:
            db: Database session
            message_id: ID of the message
            
        Returns:
            List of Attachment instances
        """
        try:
            result = await db.execute(
                select(Attachment)
                .where(Attachment.message_id == message_id)
                .order_by(Attachment.created_at)
            )
            attachments = result.scalars().all()

            logger.debug(f"Found {len(attachments)} attachments for message {message_id}")
            return list(attachments)

        except Exception as e:
            logger.error(f"Failed to get attachments for message {message_id}: {e}")
            raise

    async def process_message_attachments(
        self,
        db: AsyncSession,
        message_id: UUID,
        attachment_data: List[Dict[str, Any]]
    ) -> List[Attachment]:
        """
        Process and store multiple attachments for a message.
        
        Args:
            db: Database session
            message_id: ID of the message
            attachment_data: List of attachment info dicts with keys:
                - url: Platform URL to download from
                - filename: Original filename
                - mime_type: Optional MIME type
                
        Returns:
            List of created Attachment instances
        """
        attachments = []

        for data in attachment_data:
            try:
                attachment = await self.download_and_store_attachment(
                    db=db,
                    message_id=message_id,
                    platform_url=data['url'],
                    filename=data['filename'],
                    mime_type=data.get('mime_type')
                )
                attachments.append(attachment)

            except Exception as e:
                logger.error(
                    f"Failed to process attachment {data.get('filename')}: {e}"
                )
                # Continue processing other attachments
                continue

        logger.info(
            f"Processed {len(attachments)}/{len(attachment_data)} "
            f"attachments for message {message_id}"
        )

        return attachments

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on attachment handler.
        
        Returns:
            Health status dictionary
        """
        try:
            storage_health = await self.storage_manager.health_check()

            return {
                'status': storage_health['status'],
                'storage': storage_health,
                'stats': self.storage_manager.get_stats()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global attachment handler instance
_default_attachment_handler: Optional[AttachmentHandler] = None


def get_default_attachment_handler() -> AttachmentHandler:
    """
    Get the default attachment handler instance.
    
    Returns:
        AttachmentHandler instance
    """
    global _default_attachment_handler

    if _default_attachment_handler is None:
        _default_attachment_handler = AttachmentHandler()

    return _default_attachment_handler
