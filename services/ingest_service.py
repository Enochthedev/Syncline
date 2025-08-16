"""
Ingestion service for fetching messages from various platforms.

This service coordinates the fetching and initial processing of messages
from different platforms like Gmail, X (Twitter), Slack, etc.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from integrations.gmail_client.fetch import fetch_emails
from integrations.x_client.fetch import fetch_dms
from integrations.x_client.auth import get_user_api
from services.message import MessageNormalizer, get_message_normalizer
from services.events import EventBus, get_event_bus, Event, EventType

logger = logging.getLogger(__name__)

# Dummy placeholder for X tokens


def mock_user_auth_flow():
    # This would normally happen in a web server callback
    saved_token = {
        'oauth_token': '...',
        'oauth_token_secret': '...'
    }
    verifier = '...'
    return get_user_api(saved_token['oauth_token'], verifier, saved_token)


def ingest_all():
    print("📩 Fetching Gmail...")
    emails = fetch_emails()
    for email in emails:
        print(f"[GMAIL] {email['snippet'][:80]}...")

    print("🐦 Fetching Twitter DMs...")
    api = mock_user_auth_flow()  # Replace with actual session/token flow
    dms = fetch_dms(api)
    for dm in dms:
        print(f"[X] From {dm['sender']}: {dm['text']}")
