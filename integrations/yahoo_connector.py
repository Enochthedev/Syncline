"""
Yahoo Mail connector for MESH ingestion system.

This connector integrates with Yahoo Mail using IMAP protocol
since Yahoo doesn't provide a comprehensive REST API like Gmail.
"""

import asyncio
import email
import imaplib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .base_connector import BaseConnector, ConnectorHealth, ConnectorStatus
from services.message_schema import RawMessage, MessageContent, Attachment, Participant
from services.event_bus import EventBus
from config.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class YahooCredentials:
    """Yahoo Mail credentials for IMAP access."""
    email: str
    app_password: str  # Yahoo requires app-specific passwords
    imap_server: str = "imap.mail.yahoo.com"
    imap_port: int = 993


class YahooConnector(BaseConnector):
    """
    Yahoo Mail connector using IMAP protocol.

    Note: Yahoo Mail doesn't provide push notifications like Gmail,
    so this connector uses polling with configurable intervals.
    """

    def __init__(self, credentials: YahooCredentials, event_bus: EventBus, settings: Settings):
        super().__init__("yahoo", event_bus, settings)
        self.credentials = credentials
        self.imap_client: Optional[imaplib.IMAP4_SSL] = None
        self.last_uid = 0
        self.polling_interval = 30  # seconds
        self._running = False

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with Yahoo Mail using IMAP."""
        try:
            # Update credentials if provided
            if credentials:
                self.credentials = YahooCredentials(**credentials)

            # Test IMAP connection
            await self._connect_imap()
            await self._disconnect_imap()

            self.status = ConnectorStatus.CONNECTED
            logger.info(
                f"Yahoo Mail authentication successful for {self.credentials.email}")
            return True

        except Exception as e:
            logger.error(f"Yahoo Mail authentication failed: {e}")
            self.status = ConnectorStatus.ERROR
            self.last_error = str(e)
            return False

    async def _connect_imap(self) -> None:
        """Establish IMAP connection to Yahoo Mail."""
        try:
            # Run IMAP operations in thread pool since imaplib is synchronous
            loop = asyncio.get_event_loop()

            def _connect():
                client = imaplib.IMAP4_SSL(
                    self.credentials.imap_server,
                    self.credentials.imap_port
                )
                client.login(self.credentials.email,
                             self.credentials.app_password)
                return client

            self.imap_client = await loop.run_in_executor(None, _connect)

        except Exception as e:
            logger.error(f"Failed to connect to Yahoo IMAP: {e}")
            raise

    async def _disconnect_imap(self) -> None:
        """Disconnect from IMAP server."""
        if self.imap_client:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.imap_client.logout)
            except Exception as e:
                logger.warning(f"Error during IMAP logout: {e}")
            finally:
                self.imap_client = None

    async def start_real_time_ingestion(self) -> None:
        """Start polling for new messages."""
        if self._running:
            logger.warning("Yahoo connector already running")
            return

        self._running = True
        self.status = ConnectorStatus.RUNNING

        logger.info(
            f"Starting Yahoo Mail polling every {self.polling_interval} seconds")

        while self._running:
            try:
                await self._poll_messages()
                await asyncio.sleep(self.polling_interval)

            except Exception as e:
                logger.error(f"Error during Yahoo Mail polling: {e}")
                self.last_error = str(e)
                self.status = ConnectorStatus.ERROR
                # Back off on error
                await asyncio.sleep(self.polling_interval * 2)

    async def stop_real_time_ingestion(self) -> None:
        """Stop polling for messages."""
        self._running = False
        await self._disconnect_imap()
        self.status = ConnectorStatus.CONNECTED
        logger.info("Yahoo Mail polling stopped")

    async def _poll_messages(self) -> None:
        """Poll for new messages since last check."""
        try:
            await self._connect_imap()

            # Select INBOX
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.imap_client.select, "INBOX")

            # Search for messages newer than last UID
            search_criteria = f"UID {self.last_uid + 1}:*" if self.last_uid > 0 else "ALL"

            def _search():
                typ, data = self.imap_client.search(None, search_criteria)
                return data[0].split() if data[0] else []

            message_ids = await loop.run_in_executor(None, _search)

            # Process new messages
            for msg_id in message_ids:
                try:
                    raw_message = await self._fetch_message(msg_id.decode())
                    if raw_message:
                        await self.event_bus.publish("MESSAGE_RECEIVED", {
                            "platform": self.platform,
                            "message": raw_message.to_dict()
                        })

                        # Update last UID
                        uid = int(msg_id.decode())
                        if uid > self.last_uid:
                            self.last_uid = uid

                except Exception as e:
                    logger.error(
                        f"Error processing Yahoo message {msg_id}: {e}")

        finally:
            await self._disconnect_imap()

    async def _fetch_message(self, message_id: str) -> Optional[RawMessage]:
        """Fetch and parse a single message."""
        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                typ, data = self.imap_client.fetch(message_id, "(RFC822)")
                return data[0][1] if data and data[0] else None

            raw_email = await loop.run_in_executor(None, _fetch)
            if not raw_email:
                return None

            # Parse email
            msg = email.message_from_bytes(raw_email)

            # Extract basic info
            sender_email = msg.get("From", "")
            sender_name = email.utils.parseaddr(
                sender_email)[0] or sender_email

            recipients = []
            for header in ["To", "Cc", "Bcc"]:
                if msg.get(header):
                    for addr in msg.get(header).split(","):
                        addr = addr.strip()
                        if addr:
                            name, email_addr = email.utils.parseaddr(addr)
                            recipients.append(Participant(
                                platform_user_id=email_addr,
                                display_name=name or email_addr,
                                email=email_addr
                            ))

            # Extract content
            content_text = ""
            content_html = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        content_text = part.get_payload(
                            decode=True).decode("utf-8", errors="ignore")
                    elif content_type == "text/html":
                        content_html = part.get_payload(
                            decode=True).decode("utf-8", errors="ignore")
                    elif part.get_filename():
                        # Handle attachment
                        filename = part.get_filename()
                        content = part.get_payload(decode=True)
                        attachments.append(Attachment(
                            filename=filename,
                            content_type=content_type,
                            size=len(content) if content else 0,
                            content=content
                        ))
            else:
                content_text = msg.get_payload(
                    decode=True).decode("utf-8", errors="ignore")

            # Parse timestamp
            date_str = msg.get("Date", "")
            timestamp = datetime.now(timezone.utc)
            if date_str:
                try:
                    timestamp = email.utils.parsedate_to_datetime(date_str)
                except Exception:
                    pass

            return RawMessage(
                platform="yahoo",
                platform_message_id=message_id,
                platform_thread_id=msg.get("Message-ID", message_id),
                sender=Participant(
                    platform_user_id=sender_email,
                    display_name=sender_name,
                    email=sender_email
                ),
                recipients=recipients,
                content=MessageContent(
                    text=content_text,
                    html=content_html
                ),
                attachments=attachments,
                timestamp=timestamp,
                metadata={
                    "subject": msg.get("Subject", ""),
                    "message_id": msg.get("Message-ID", ""),
                    "in_reply_to": msg.get("In-Reply-To", ""),
                    "references": msg.get("References", ""),
                    "headers": dict(msg.items())
                }
            )

        except Exception as e:
            logger.error(f"Error fetching Yahoo message {message_id}: {e}")
            return None

    async def fetch_historical_messages(self, cursor: Optional[str] = None, limit: int = 100) -> List[RawMessage]:
        """Fetch historical messages from Yahoo Mail."""
        messages = []

        try:
            await self._connect_imap()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.imap_client.select, "INBOX")

            # Search for messages
            def _search():
                typ, data = self.imap_client.search(None, "ALL")
                return data[0].split() if data[0] else []

            message_ids = await loop.run_in_executor(None, _search)

            # Apply cursor and limit
            start_idx = 0
            if cursor:
                try:
                    start_idx = int(cursor)
                except ValueError:
                    pass

            end_idx = min(start_idx + limit, len(message_ids))

            # Fetch messages
            for i in range(start_idx, end_idx):
                msg_id = message_ids[i].decode()
                raw_message = await self._fetch_message(msg_id)
                if raw_message:
                    messages.append(raw_message)

        except Exception as e:
            logger.error(f"Error fetching Yahoo historical messages: {e}")
            raise
        finally:
            await self._disconnect_imap()

        return messages

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Yahoo Mail doesn't support webhooks, so this is not implemented."""
        logger.warning("Yahoo Mail doesn't support webhooks")

    async def get_health_status(self) -> ConnectorHealth:
        """Get connector health status."""
        try:
            # Test connection
            await self._connect_imap()
            await self._disconnect_imap()

            return ConnectorHealth(
                status=self.status,
                last_check=datetime.now(timezone.utc),
                message="Yahoo Mail connector healthy",
                details={
                    "email": self.credentials.email,
                    "server": self.credentials.imap_server,
                    "last_uid": self.last_uid,
                    "polling_interval": self.polling_interval
                }
            )

        except Exception as e:
            return ConnectorHealth(
                status=ConnectorStatus.ERROR,
                last_check=datetime.now(timezone.utc),
                message=f"Yahoo Mail connector error: {e}",
                details={
                    "error": str(e),
                    "email": self.credentials.email
                }
            )
