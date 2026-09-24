"""
Enhanced WhatsApp Authentication Routes

Improved authentication with:
- Better error handling
- Enhanced timeouts
- Detailed logging
- Fallback mechanisms
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_database_session
from api.dependencies.auth import get_current_active_user
from config.config import settings
from db.models.platform_connection import PlatformConnection
from db.models.user import User
from integrations.whatsapp_connector_enhanced import EnhancedWhatsAppConnector

from .utils import get_user_whatsapp_connection

logger = logging.getLogger(__name__)

router = APIRouter()


class PhoneLoginRequest(BaseModel):
    """Request for phone number login"""

    phone: str = Field(
        ..., description="Phone number in international format (e.g., +1234567890)"
    )


class PhoneLoginResponse(BaseModel):
    """Response for phone login"""

    success: bool
    connection_id: str
    pairing_code: str | None = None
    phone_number: str
    check_phone: bool = False
    message: str
    instructions: list[str] = []
    debug_info: dict = {}


@router.post("/{connection_id}/login/phone-enhanced", response_model=PhoneLoginResponse)
async def login_with_phone_enhanced(
    connection_id: UUID,
    request: PhoneLoginRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """
    Enhanced phone number login with better error handling.

    This endpoint:
    - Uses enhanced connector with longer timeouts (30s instead of 5s)
    - Provides detailed error messages
    - Includes debug information
    - Has fallback mechanisms

    Process:
    1. User enters phone number
    2. Backend requests pairing code from bridge (with retries)
    3. User enters code in WhatsApp app
    4. Connection is established
    """

    logger.info(f"[PHONE_LOGIN] Starting phone login for connection {connection_id}")

    try:
        # Get connection
        connection = await get_user_whatsapp_connection(connection_id, current_user, db)

        # Normalize phone number
        phone = request.phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = "+" + phone

        logger.info(f"[PHONE_LOGIN] Normalized phone: {phone}")

        # Prepare credentials
        credentials = dict(connection.credentials) if connection.credentials else {}

        # Fill in defaults from settings
        if not credentials.get("matrix_homeserver_url"):
            credentials["matrix_homeserver_url"] = settings.MATRIX_HOMESERVER_URL
        if not credentials.get("matrix_access_token"):
            credentials["matrix_access_token"] = settings.MATRIX_ACCESS_TOKEN
        if not credentials.get("matrix_user_id"):
            credentials["matrix_user_id"] = settings.MATRIX_USER_ID
        if not credentials.get("bridge_bot_id"):
            credentials["bridge_bot_id"] = settings.WHATSAPP_BRIDGE_BOT_ID

        # Validate credentials
        missing_creds = []
        if not credentials.get("matrix_homeserver_url"):
            missing_creds.append("MATRIX_HOMESERVER_URL")
        if not credentials.get("matrix_access_token"):
            missing_creds.append("MATRIX_ACCESS_TOKEN")
        if not credentials.get("matrix_user_id"):
            missing_creds.append("MATRIX_USER_ID")
        if not credentials.get("bridge_bot_id"):
            missing_creds.append("WHATSAPP_BRIDGE_BOT_ID")

        if missing_creds:
            logger.error(f"[PHONE_LOGIN] Missing credentials: {missing_creds}")
            raise HTTPException(
                status_code=500,
                detail=f"Missing configuration: {', '.join(missing_creds)}. Check your .env file.",
            )

        logger.info(
            f"[PHONE_LOGIN] Using homeserver: {credentials['matrix_homeserver_url']}"
        )
        logger.info(f"[PHONE_LOGIN] Using user: {credentials['matrix_user_id']}")
        logger.info(f"[PHONE_LOGIN] Using bridge bot: {credentials['bridge_bot_id']}")

        # Create enhanced connector
        connector = EnhancedWhatsAppConnector(
            connection_id=connection_id,
            credentials=credentials,
        )

        try:
            # Connect to Matrix
            logger.info(f"[PHONE_LOGIN] Connecting to Matrix...")
            await connector.connect()
            logger.info(f"[PHONE_LOGIN] Connected successfully")

            # Check if already logged in
            logger.info(f"[PHONE_LOGIN] Checking login status...")
            status = await connector.get_bridge_status()

            if status.logged_in:
                logger.warning(f"[PHONE_LOGIN] Already logged in as {status.phone}")
                return PhoneLoginResponse(
                    success=True,
                    connection_id=str(connection_id),
                    pairing_code=None,
                    phone_number=status.phone or phone,
                    check_phone=False,
                    message=f"Already logged in as {status.phone}",
                    instructions=["You are already connected to WhatsApp"],
                    debug_info={"already_logged_in": True, "phone": status.phone},
                )

            # Request pairing code
            logger.info(f"[PHONE_LOGIN] Requesting pairing code for {phone}...")
            pairing_code = await connector.login_with_phone(phone)

            logger.info(f"[PHONE_LOGIN] Got response: {pairing_code}")

            # Handle different response types
            if pairing_code == "CHECK_PHONE":
                return PhoneLoginResponse(
                    success=True,
                    connection_id=str(connection_id),
                    pairing_code=None,
                    phone_number=phone,
                    check_phone=True,
                    message="Check your WhatsApp for a pairing notification!",
                    instructions=[
                        "1. A notification was sent to your WhatsApp",
                        "2. Open WhatsApp on your phone",
                        "3. Go to Settings > Linked Devices",
                        "4. Follow the prompts to complete linking",
                    ],
                    debug_info={"method": "notification", "bridge_sent_to_phone": True},
                )

            if pairing_code and len(pairing_code) >= 8:
                # Got pairing code
                return PhoneLoginResponse(
                    success=True,
                    connection_id=str(connection_id),
                    pairing_code=pairing_code,
                    phone_number=phone,
                    check_phone=False,
                    message=f"Enter this code in WhatsApp: {pairing_code}",
                    instructions=[
                        "1. Open WhatsApp on your phone",
                        "2. Go to Settings > Linked Devices",
                        "3. Tap 'Link a Device'",
                        "4. Select 'Link with phone number instead'",
                        f"5. Enter this code: {pairing_code}",
                    ],
                    debug_info={
                        "method": "pairing_code",
                        "code_length": len(pairing_code),
                    },
                )
            else:
                # Unexpected response
                logger.error(
                    f"[PHONE_LOGIN] Unexpected response from bridge: {pairing_code}"
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Failed to get pairing code from bridge",
                        "bridge_response": pairing_code,
                        "suggestions": [
                            "Check if WhatsApp bridge is running: docker ps | grep whatsapp",
                            "Check bridge logs: docker logs syncline-whatsapp-bridge",
                            "Try restarting bridge: docker-compose restart whatsapp-bridge",
                        ],
                    },
                )

        finally:
            try:
                await connector.disconnect()
                logger.info(f"[PHONE_LOGIN] Disconnected from Matrix")
            except Exception as e:
                logger.warning(f"[PHONE_LOGIN] Error disconnecting: {e}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PHONE_LOGIN] Phone login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "type": type(e).__name__,
                "suggestions": [
                    "Check if Matrix homeserver is accessible",
                    "Verify WhatsApp bridge is running",
                    "Check configuration in .env file",
                    "Review backend logs for details",
                ],
            },
        )


@router.get("/{connection_id}/login/diagnostics")
async def get_login_diagnostics(
    connection_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database_session),
):
    """
    Get diagnostic information for WhatsApp login.

    Use this endpoint to troubleshoot connection issues.
    """

    logger.info(f"[DIAGNOSTICS] Running login diagnostics for {connection_id}")

    diagnostics = {
        "connection_id": str(connection_id),
        "timestamp": datetime.utcnow().isoformat(),
        "tests": [],
    }

    try:
        # Get connection
        connection = await get_user_whatsapp_connection(connection_id, current_user, db)

        diagnostics["tests"].append(
            {
                "test": "connection_exists",
                "success": True,
                "details": {
                    "platform": connection.platform.value,
                    "status": connection.status.value,
                },
            }
        )

        # Check credentials
        credentials = dict(connection.credentials) if connection.credentials else {}

        if not credentials.get("matrix_homeserver_url"):
            credentials["matrix_homeserver_url"] = settings.MATRIX_HOMESERVER_URL
        if not credentials.get("matrix_access_token"):
            credentials["matrix_access_token"] = settings.MATRIX_ACCESS_TOKEN
        if not credentials.get("matrix_user_id"):
            credentials["matrix_user_id"] = settings.MATRIX_USER_ID
        if not credentials.get("bridge_bot_id"):
            credentials["bridge_bot_id"] = settings.WHATSAPP_BRIDGE_BOT_ID

        creds_ok = all(
            [
                credentials.get("matrix_homeserver_url"),
                credentials.get("matrix_access_token"),
                credentials.get("matrix_user_id"),
                credentials.get("bridge_bot_id"),
            ]
        )

        diagnostics["tests"].append(
            {
                "test": "credentials_configured",
                "success": creds_ok,
                "details": {
                    "homeserver": credentials.get("matrix_homeserver_url", "MISSING"),
                    "user_id": credentials.get("matrix_user_id", "MISSING"),
                    "bridge_bot": credentials.get("bridge_bot_id", "MISSING"),
                    "has_access_token": bool(credentials.get("matrix_access_token")),
                },
            }
        )

        if not creds_ok:
            return diagnostics

        # Test Matrix connection
        connector = EnhancedWhatsAppConnector(
            connection_id=connection_id,
            credentials=credentials,
        )

        try:
            await connector.connect()

            diagnostics["tests"].append(
                {
                    "test": "matrix_connection",
                    "success": True,
                    "details": "Successfully connected to Matrix homeserver",
                }
            )

            # Check bridge status
            status = await connector.get_bridge_status()

            diagnostics["tests"].append(
                {
                    "test": "bridge_status",
                    "success": True,
                    "details": {
                        "connected": status.connected,
                        "logged_in": status.logged_in,
                        "phone": status.phone,
                    },
                }
            )

        except Exception as e:
            diagnostics["tests"].append(
                {"test": "matrix_connection", "success": False, "error": str(e)}
            )
        finally:
            try:
                await connector.disconnect()
            except Exception as e:
                logger.debug(f"Failed to disconnect connector during cleanup: {e}")

        # Summary
        total_tests = len(diagnostics["tests"])
        passed = sum(1 for t in diagnostics["tests"] if t["success"])

        diagnostics["summary"] = {
            "total_tests": total_tests,
            "passed": passed,
            "failed": total_tests - passed,
            "all_passed": passed == total_tests,
        }

        # Recommendations
        recommendations = []

        for test in diagnostics["tests"]:
            if not test["success"]:
                if test["test"] == "credentials_configured":
                    recommendations.append(
                        "Configure missing environment variables in .env file"
                    )
                elif test["test"] == "matrix_connection":
                    recommendations.append(
                        "Check if Matrix homeserver is running and accessible"
                    )
                    recommendations.append("Verify MATRIX_ACCESS_TOKEN is valid")

        diagnostics["recommendations"] = recommendations

        return diagnostics

    except Exception as e:
        logger.error(f"[DIAGNOSTICS] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")


from datetime import datetime
