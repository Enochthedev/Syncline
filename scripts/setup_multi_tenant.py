#!/usr/bin/env python3
"""
Setup script for multi-tenant architecture.

This script:
1. Runs database migrations
2. Sets up row-level security policies
3. Creates initial system admin user
4. Validates the setup
"""

from services.security.tenant_security import TenantSecurityService
from services.tenant_service import TenantService
from db.models.user import User
from db.tenant_session import execute_rls_setup, session_manager
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_multi_tenant():
    """Set up multi-tenant architecture."""
    try:
        logger.info("Starting multi-tenant setup...")

        # 1. Check database connectivity
        logger.info("Checking database connectivity...")
        health = await session_manager.health_check()
        if not health:
            logger.error("Database health check failed")
            return False

        # 2. Set up RLS policies
        logger.info("Setting up row-level security policies...")
        try:
            await execute_rls_setup()
            logger.info("RLS policies set up successfully")
        except Exception as e:
            logger.warning(f"RLS setup failed (may already exist): {e}")

        # 3. Create system admin user if not exists
        logger.info("Creating system admin user...")
        from db.tenant_session import get_system_session

        async with get_system_session() as session:
            # Check if system admin exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == "admin@system.local")
            )
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                admin_user = User(
                    email="admin@system.local",
                    first_name="System",
                    last_name="Admin",
                    is_active=True,
                    is_system_admin=True
                )
                session.add(admin_user)
                await session.commit()
                logger.info("System admin user created")
            else:
                logger.info("System admin user already exists")

        # 4. Test tenant creation
        logger.info("Testing tenant creation...")
        async with get_system_session() as session:
            tenant_service = TenantService(session)

            # Try to create a test tenant
            try:
                test_tenant = await tenant_service.create_tenant(
                    name="test-setup",
                    display_name="Test Setup Tenant",
                    admin_email="test@setup.local",
                    tier="standard"
                )
                logger.info(f"Test tenant created: {test_tenant.id}")

                # Test tenant security
                security_service = TenantSecurityService()
                keys = await security_service.create_tenant_encryption_keys(
                    str(test_tenant.id)
                )
                logger.info(
                    f"Tenant encryption keys created: {len(keys)} keys")

                # Clean up test tenant
                await tenant_service.delete_tenant(str(test_tenant.id))
                logger.info("Test tenant cleaned up")

            except Exception as e:
                logger.error(f"Tenant creation test failed: {e}")
                return False

        logger.info("Multi-tenant setup completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Multi-tenant setup failed: {e}")
        return False


async def validate_setup():
    """Validate multi-tenant setup."""
    try:
        logger.info("Validating multi-tenant setup...")

        # Check RLS functions
        from db.tenant_session import get_system_session
        from sqlalchemy import text

        async with get_system_session() as session:
            # Check if RLS functions exist
            result = await session.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'current_tenant_id')")
            )
            if not result.scalar():
                logger.error("RLS function current_tenant_id not found")
                return False

            result = await session.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'is_system_admin')")
            )
            if not result.scalar():
                logger.error("RLS function is_system_admin not found")
                return False

            # Check if RLS is enabled on tables
            result = await session.execute(
                text("SELECT relrowsecurity FROM pg_class WHERE relname = 'messages'")
            )
            if not result.scalar():
                logger.error("RLS not enabled on messages table")
                return False

            logger.info("RLS validation passed")

        # Test session manager
        health = await session_manager.health_check()
        if not health:
            logger.error("Session manager health check failed")
            return False

        logger.info("Multi-tenant setup validation passed!")
        return True

    except Exception as e:
        logger.error(f"Setup validation failed: {e}")
        return False


async def main():
    """Main setup function."""
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        success = await validate_setup()
    else:
        success = await setup_multi_tenant()

    if success:
        logger.info("Setup completed successfully")
        sys.exit(0)
    else:
        logger.error("Setup failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
