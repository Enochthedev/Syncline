"""
WhatsApp Authentication Routes

Handles WhatsApp login, logout, and session management.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from api.dependencies.auth import get_current_active_user
from db.models.user import User
from db.models.platform_connection import PlatformConnection
from services.whatsapp_session_manager import get_whatsapp_session_manager

from .models import WhatsAppLoginResponse, WhatsAppSessionResponse
from .utils import get_user_whatsapp_connection

router = APIRouter()


@router.post("/{connection_id}/session/create", summary="Create WhatsApp Session")
async def create_whatsapp_session(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Create a new WhatsApp session."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)
    
    session_manager = get_whatsapp_session_manager()
    session = await session_manager.create_session(db, connection_id, current_user.id)
    
    return {
        "connection_id": connection_id,
        "is_logged_in": session.is_logged_in,
        "phone_number": session.phone_number,
        "session_age_seconds": None
    }


@router.get("/{connection_id}/session/status", summary="Get Session Status")
async def get_session_status(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Get current WhatsApp session status with auto-sync on login transition."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)

    session_manager = get_whatsapp_session_manager()

    # Use check_login_completion which has smart transition detection and auto-sync
    status_result = await session_manager.check_login_completion(db, connection_id)

    if not status_result["success"]:
        raise HTTPException(status_code=500, detail=status_result.get("error", "Status check failed"))

    return {
        "connection_id": connection_id,
        "is_logged_in": status_result.get("login_completed", False),
        "phone_number": status_result.get("phone"),
        "session_age_seconds": status_result.get("session_age"),
        "auto_sync": status_result.get("auto_sync"),
        "message": status_result.get("message")
    }


@router.get("/{connection_id}/login", response_model=WhatsAppLoginResponse, summary="Get QR Code")
async def get_whatsapp_qr_code(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
) -> WhatsAppLoginResponse:
    """Get QR code for WhatsApp login with auto-sync."""
    from sqlalchemy import update
    from db.models.platform_connection import ConnectionStatus
    
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)
    
    # Check if this connection has valid credentials (was previously logged in)
    has_credentials = bool(
        connection.credentials and 
        connection.credentials.get("matrix_access_token") and
        connection.credentials.get("matrix_user_id")
    )
    
    session_manager = get_whatsapp_session_manager()
    status_result = await session_manager.check_login_status(db, connection_id)
    
    if not status_result["success"]:
        raise HTTPException(status_code=500, detail=status_result.get("error", "Status check failed"))
    
    # Only return already_logged_in if:
    # 1. The bridge is logged in, AND
    # 2. This connection has existing credentials (was previously connected)
    if status_result.get("logged_in") and has_credentials:
        # Update connection status to ACTIVE
        await db.execute(
            update(PlatformConnection)
            .where(PlatformConnection.id == connection_id)
            .values(status=ConnectionStatus.ACTIVE)
        )
        await db.commit()
        
        auto_sync_result = await session_manager.auto_sync_chats(db, connection_id)
        return WhatsAppLoginResponse(
            connection_id=connection_id,
            qr_code=None,
            already_logged_in=True,
            message="Already logged in to WhatsApp",
            auto_sync=auto_sync_result
        )
    
    # Need to login - get QR code
    qr_result = await session_manager.get_qr_code(db, connection_id)
    
    if not qr_result["success"]:
        raise HTTPException(status_code=500, detail=qr_result.get("error", "Failed to get QR code"))
    
    return WhatsAppLoginResponse(
        connection_id=connection_id,
        qr_code=qr_result.get("qr_code"),
        pairing_code=qr_result.get("pairing_code"),
        already_logged_in=False,
        message="Scan QR code with WhatsApp mobile app"
    )


class PhoneLoginRequest(BaseModel):
    """Request for phone number login."""
    phone: str


@router.post("/{connection_id}/login/phone", summary="Login with Phone Number")
async def login_with_phone(
    connection_id: UUID,
    request: PhoneLoginRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """
    Login to WhatsApp using phone number and pairing code.
    
    This is the preferred method for mobile apps:
    1. User enters their phone number
    2. Backend sends command to bridge to get pairing code
    3. User enters pairing code in WhatsApp on their phone
    4. Connection is established
    """
    import logging
    from integrations.whatsapp_connector import WhatsAppConnector
    from config.config import settings
    
    logger = logging.getLogger(__name__)
    
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)
    
    # Normalize phone number
    phone = request.phone.strip()
    if not phone.startswith('+'):
        phone = '+' + phone
    
    logger.info(f"Phone login requested for {phone}")
    
    # Create connector directly with settings
    credentials = dict(connection.credentials) if connection.credentials else {}
    if not credentials.get("matrix_homeserver_url"):
        credentials["matrix_homeserver_url"] = settings.MATRIX_HOMESERVER_URL
    if not credentials.get("matrix_access_token"):
        credentials["matrix_access_token"] = settings.MATRIX_ACCESS_TOKEN
    if not credentials.get("matrix_user_id"):
        credentials["matrix_user_id"] = settings.MATRIX_USER_ID
    if not credentials.get("bridge_bot_id"):
        credentials["bridge_bot_id"] = settings.WHATSAPP_BRIDGE_BOT_ID
    
    connector = WhatsAppConnector(
        connection_id=connection_id,
        credentials=credentials,
    )
    
    try:
        await connector.connect()
        logger.info("Connected to Matrix, requesting pairing code...")
        
        pairing_code = await connector.login_with_phone(phone)
        
        logger.info(f"Got pairing code: {pairing_code}")
        
        # Handle the case where the bridge sends code directly to WhatsApp
        if pairing_code == "CHECK_PHONE":
            return {
                "connection_id": str(connection_id),
                "pairing_code": None,
                "phone_number": phone,
                "check_phone": True,
                "message": "Check your WhatsApp for a pairing code notification!",
                "instructions": [
                    "1. A notification was sent to your WhatsApp",
                    "2. Open WhatsApp on your phone",
                    "3. Go to Settings > Linked Devices", 
                    "4. Follow the prompts to complete linking"
                ]
            }
        
        return {
            "connection_id": str(connection_id),
            "pairing_code": pairing_code,
            "phone_number": phone,
            "check_phone": False,
            "message": f"Enter this code in WhatsApp: {pairing_code}",
            "instructions": [
                "1. Open WhatsApp on your phone",
                "2. Go to Settings > Linked Devices",
                "3. Tap 'Link a Device'",
                "4. Select 'Link with phone number instead'",
                "5. Enter the 8-character code shown above"
            ]
        }
        
    except Exception as e:
        logger.error(f"Phone login failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pairing code: {str(e)}"
        )
    finally:
        await connector.disconnect()


@router.post("/{connection_id}/logout", summary="Logout from WhatsApp")
async def logout_whatsapp(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Logout from WhatsApp."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)
    
    session_manager = get_whatsapp_session_manager()
    result = await session_manager.logout(db, connection_id)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "success": True,
        "message": "Successfully logged out from WhatsApp"
    }


@router.delete("/{connection_id}/session", summary="Clean Up Session")
async def cleanup_whatsapp_session(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """Clean up WhatsApp session and logout."""
    connection = await get_user_whatsapp_connection(connection_id, current_user, db)
    
    session_manager = get_whatsapp_session_manager()
    
    # First logout
    logout_result = await session_manager.logout(db, connection_id)
    
    # Then cleanup session
    cleanup_result = await session_manager.cleanup_session(db, connection_id)
    
    return {
        "success": cleanup_result.get("success", False),
        "logout_success": logout_result.get("success", False),
        "message": "Session cleaned up and logged out"
    }