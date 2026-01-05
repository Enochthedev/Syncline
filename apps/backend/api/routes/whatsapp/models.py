"""
WhatsApp API Models

Shared Pydantic models for WhatsApp endpoints.
"""

from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from integrations.whatsapp_connector import BridgeStatus


class WhatsAppLoginResponse(BaseModel):
    """Response with QR code for WhatsApp login."""
    connection_id: UUID = Field(description="Connection ID")
    qr_code: Optional[str] = Field(None, description="QR code data for scanning")
    pairing_code: Optional[str] = Field(None, description="Pairing code for phone login")
    already_logged_in: bool = Field(default=False, description="Whether already logged in")
    message: str = Field(description="Status message")
    auto_sync: Optional[Dict] = Field(None, description="Auto-sync results")


class WhatsAppStatusResponse(BaseModel):
    """WhatsApp connection status."""
    connection_id: UUID = Field(description="Connection ID")
    bridge_status: BridgeStatus = Field(description="Bridge connection status")
    is_healthy: bool = Field(description="Overall health status")


class WhatsAppSessionResponse(BaseModel):
    """WhatsApp session status."""
    connection_id: UUID = Field(description="Connection ID")
    is_logged_in: bool = Field(description="Whether logged in")
    phone_number: Optional[str] = Field(None, description="Phone number if logged in")
    session_age_seconds: Optional[int] = Field(None, description="Session age in seconds")