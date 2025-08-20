"""
Security tests for multi-tenant architecture.

Tests tenant data isolation, access control, encryption,
and row-level security policies.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from db.models.tenant import Tenant, TenantUser
from db.models.user import User
from db.models.message import Message
from db.models.thread import Thread
from db.models.participant import Participant
from db.models.audit import AuditLog
from db.tenant_session import get_tenant_session, get_system_session, session_manager
from services.tenant_service import TenantService
from services.security.tenant_security import TenantSecurityService
from services.security.types import KeyType


@pytest_asyncio.fixture
async def test_tenants():
    """Create test tenants for isolation testing."""
    async with get_system_session() as session:
        tenant_service = TenantService(session)

        # Create two test tenants
        tenant1 = await tenant_service.create_tenant(
            name="test-tenant-1",
            display_name="Test Tenant 1",
            admin_email="admin1@test.com",
            tier="standard"
        )

        tenant2 = await tenant_service.create_tenant(
            name="test-tenant-2",
            display_name="Test Tenant 2",
            admin_email="admin2@test.com",
            tier="premium"
        )

        yield tenant1, tenant2

        # Cleanup
        await tenant_service.delete_tenant(str(tenant1.id))
        await tenant_service.delete_tenant(str(tenant2.id))


@pytest_asyncio.fixture
async def test_users():
    """Create test users."""
    async with get_system_session() as session:
        user1 = User(
            email="user1@test.com",
            first_name="User",
            last_name="One",
            is_active=True
        )
        user2 = User(
            email="user2@test.com",
            first_name="User",
            last_name="Two",
            is_active=True
        )

        session.add(user1)
        session.add(user2)
        await session.commit()

        yield user1, user2

        # Cleanup
        await session.delete(user1)
        await session.delete(user2)
        await session.commit()


@pytest_asyncio.fixture
async def test_data(test_tenants, test_users):
    """Create test data for each tenant."""
    tenant1, tenant2 = test_tenants
    user1, user2 = test_users

    async with get_system_session() as session:
        # Create participants for each tenant
        participant1_t1 = Participant(
            tenant_id=tenant1.id,
            platform="gmail",
            platform_user_id="user1@gmail.com",
            display_name="User 1 Gmail",
            email="user1@gmail.com"
        )

        participant1_t2 = Participant(
            tenant_id=tenant2.id,
            platform="gmail",
            platform_user_id="user1@gmail.com",
            display_name="User 1 Gmail T2",
            email="user1@gmail.com"
        )

        session.add(participant1_t1)
        session.add(participant1_t2)
        await session.flush()

        # Create threads for each tenant
        thread1_t1 = Thread(
            tenant_id=tenant1.id,
            platform="gmail",
            platform_thread_id="thread1",
            title="Test Thread 1 - Tenant 1",
            participants=[participant1_t1.id]
        )

        thread1_t2 = Thread(
            tenant_id=tenant2.id,
            platform="gmail",
            platform_thread_id="thread1",
            title="Test Thread 1 - Tenant 2",
            participants=[participant1_t2.id]
        )

        session.add(thread1_t1)
        session.add(thread1_t2)
        await session.flush()

        # Create messages for each tenant
        message1_t1 = Message(
            tenant_id=tenant1.id,
            platform="gmail",
            platform_message_id="msg1",
            thread_id=thread1_t1.id,
            sender_id=participant1_t1.id,
            content_text="Secret message for tenant 1",
            timestamp=datetime.utcnow()
        )

        message1_t2 = Message(
            tenant_id=tenant2.id,
            platform="gmail",
            platform_message_id="msg1",
            thread_id=thread1_t2.id,
            sender_id=participant1_t2.id,
            content_text="Secret message for tenant 2",
            timestamp=datetime.utcnow()
        )

        session.add(message1_t1)
        session.add(message1_t2)
        await session.commit()

        yield {
            "tenant1": {
                "participant": participant1_t1,
                "thread": thread1_t1,
                "message": message1_t1
            },
            "tenant2": {
                "participant": participant1_t2,
                "thread": thread1_t2,
                "message": message1_t2
            }
        }


class TestTenantIsolation:
    """Test tenant data isolation using row-level security."""

    @pytest.mark.asyncio
    async def test_message_isolation(self, test_tenants, test_data):
        """Test that tenants can only access their own messages."""
        tenant1, tenant2 = test_tenants

        # Test tenant 1 can only see their messages
        async with get_tenant_session(str(tenant1.id)) as session:
            result = await session.execute(select(Message))
            messages = result.scalars().all()

            assert len(messages) == 1
            assert messages[0].content_text == "Secret message for tenant 1"
            assert messages[0].tenant_id == tenant1.id

        # Test tenant 2 can only see their messages
        async with get_tenant_session(str(tenant2.id)) as session:
            result = await session.execute(select(Message))
            messages = result.scalars().all()

            assert len(messages) == 1
            assert messages[0].content_text == "Secret message for tenant 2"
            assert messages[0].tenant_id == tenant2.id

    async def test_thread_isolation(self, test_tenants, test_data):
        """Test that tenants can only access their own threads."""
        tenant1, tenant2 = test_tenants

        # Test tenant 1 can only see their threads
        async with get_tenant_session(str(tenant1.id)) as session:
            result = await session.execute(select(Thread))
            threads = result.scalars().all()

            assert len(threads) == 1
            assert threads[0].title == "Test Thread 1 - Tenant 1"
            assert threads[0].tenant_id == tenant1.id

        # Test tenant 2 can only see their threads
        async with get_tenant_session(str(tenant2.id)) as session:
            result = await session.execute(select(Thread))
            threads = result.scalars().all()

            assert len(threads) == 1
            assert threads[0].title == "Test Thread 1 - Tenant 2"
            assert threads[0].tenant_id == tenant2.id

    async def test_participant_isolation(self, test_tenants, test_data):
        """Test that tenants can only access their own participants."""
        tenant1, tenant2 = test_tenants

        # Test tenant 1 can only see their participants
        async with get_tenant_session(str(tenant1.id)) as session:
            result = await session.execute(select(Participant))
            participants = result.scalars().all()

            assert len(participants) == 1
            assert participants[0].display_name == "User 1 Gmail"
            assert participants[0].tenant_id == tenant1.id

        # Test tenant 2 can only see their participants
        async with get_tenant_session(str(tenant2.id)) as session:
            result = await session.execute(select(Participant))
            participants = result.scalars().all()

            assert len(participants) == 1
            assert participants[0].display_name == "User 1 Gmail T2"
            assert participants[0].tenant_id == tenant2.id

    async def test_system_admin_access(self, test_tenants, test_data):
        """Test that system admin can access all tenant data."""
        tenant1, tenant2 = test_tenants

        # System admin should see all messages
        async with get_tenant_session(is_system_admin=True) as session:
            result = await session.execute(select(Message))
            messages = result.scalars().all()

            assert len(messages) == 2
            tenant_ids = {msg.tenant_id for msg in messages}
            assert tenant1.id in tenant_ids
            assert tenant2.id in tenant_ids

    async def test_cross_tenant_insert_blocked(self, test_tenants):
        """Test that tenants cannot insert data with wrong tenant_id."""
        tenant1, tenant2 = test_tenants

        # Try to insert message with wrong tenant_id
        async with get_tenant_session(str(tenant1.id)) as session:
            # Create a participant first
            participant = Participant(
                tenant_id=tenant1.id,
                platform="test",
                platform_user_id="test_user",
                display_name="Test User"
            )
            session.add(participant)
            await session.flush()

            thread = Thread(
                tenant_id=tenant1.id,
                platform="test",
                platform_thread_id="test_thread",
                title="Test Thread",
                participants=[participant.id]
            )
            session.add(thread)
            await session.flush()

            # Try to insert message with tenant2's ID (should fail)
            message = Message(
                tenant_id=tenant2.id,  # Wrong tenant ID
                platform="test",
                platform_message_id="test_msg",
                thread_id=thread.id,
                sender_id=participant.id,
                content_text="This should fail",
                timestamp=datetime.utcnow()
            )
            session.add(message)

            with pytest.raises(Exception):  # Should raise RLS violation
                await session.commit()


class TestTenantEncryption:
    """Test tenant-specific encryption and key management."""

    async def test_tenant_key_creation(self, test_tenants):
        """Test creation of tenant-specific encryption keys."""
        tenant1, tenant2 = test_tenants
        security_service = TenantSecurityService()

        # Create keys for tenant 1
        keys1 = await security_service.create_tenant_encryption_keys(
            str(tenant1.id),
            [KeyType.DATA_ENCRYPTION_KEY, KeyType.TOKEN_ENCRYPTION_KEY]
        )

        assert KeyType.DATA_ENCRYPTION_KEY.value in keys1
        assert KeyType.TOKEN_ENCRYPTION_KEY.value in keys1

        # Create keys for tenant 2
        keys2 = await security_service.create_tenant_encryption_keys(
            str(tenant2.id),
            [KeyType.DATA_ENCRYPTION_KEY, KeyType.TOKEN_ENCRYPTION_KEY]
        )

        # Keys should be different for different tenants
        assert keys1[KeyType.DATA_ENCRYPTION_KEY.value].key_id != keys2[KeyType.DATA_ENCRYPTION_KEY.value].key_id
        assert keys1[KeyType.TOKEN_ENCRYPTION_KEY.value].key_id != keys2[KeyType.TOKEN_ENCRYPTION_KEY.value].key_id

    async def test_tenant_data_encryption(self, test_tenants):
        """Test encryption and decryption of tenant-specific data."""
        tenant1, tenant2 = test_tenants
        security_service = TenantSecurityService()

        # Test data
        sensitive_data = "This is sensitive tenant data"
        field_name = "test_field"

        # Encrypt data for tenant 1
        encrypted1 = await security_service.encrypt_tenant_data(
            str(tenant1.id), sensitive_data, field_name
        )

        # Encrypt same data for tenant 2
        encrypted2 = await security_service.encrypt_tenant_data(
            str(tenant2.id), sensitive_data, field_name
        )

        # Encrypted values should be different (different keys)
        assert encrypted1["encrypted_value"] != encrypted2["encrypted_value"]
        assert encrypted1["key_id"] != encrypted2["key_id"]
        assert encrypted1["tenant_id"] == str(tenant1.id)
        assert encrypted2["tenant_id"] == str(tenant2.id)

        # Decrypt data for each tenant
        decrypted1 = await security_service.decrypt_tenant_data(
            str(tenant1.id), encrypted1, field_name
        )
        decrypted2 = await security_service.decrypt_tenant_data(
            str(tenant2.id), encrypted2, field_name
        )

        assert decrypted1 == sensitive_data
        assert decrypted2 == sensitive_data

    async def test_cross_tenant_decryption_blocked(self, test_tenants):
        """Test that tenants cannot decrypt each other's data."""
        tenant1, tenant2 = test_tenants
        security_service = TenantSecurityService()

        # Encrypt data for tenant 1
        sensitive_data = "Secret tenant 1 data"
        encrypted = await security_service.encrypt_tenant_data(
            str(tenant1.id), sensitive_data, "secret_field"
        )

        # Try to decrypt with tenant 2's context (should fail)
        with pytest.raises(Exception):
            await security_service.decrypt_tenant_data(
                str(tenant2.id), encrypted, "secret_field"
            )

    async def test_tenant_key_rotation(self, test_tenants):
        """Test rotation of tenant-specific encryption keys."""
        tenant1, _ = test_tenants
        security_service = TenantSecurityService()

        # Create initial keys
        initial_keys = await security_service.create_tenant_encryption_keys(
            str(tenant1.id), [KeyType.DATA_ENCRYPTION_KEY]
        )
        initial_key_id = initial_keys[KeyType.DATA_ENCRYPTION_KEY.value].key_id

        # Rotate keys
        rotation_results = await security_service.rotate_tenant_keys(
            str(tenant1.id), KeyType.DATA_ENCRYPTION_KEY
        )

        # New key should be different
        new_key_id = rotation_results[KeyType.DATA_ENCRYPTION_KEY.value]
        assert new_key_id != initial_key_id


class TestTenantQuotas:
    """Test tenant quota enforcement and management."""

    async def test_quota_checking(self, test_tenants):
        """Test quota checking functionality."""
        tenant1, _ = test_tenants

        async with get_system_session() as session:
            tenant_service = TenantService(session)

            # Check message quota
            quota_status = await tenant_service.check_quota(
                str(tenant1.id), "messages", 1000
            )

            assert quota_status["tenant_id"] == str(tenant1.id)
            assert quota_status["quota_type"] == "messages"
            assert quota_status["current_usage"] >= 0
            assert quota_status["limit"] > 0
            assert "allowed" in quota_status

    async def test_quota_enforcement(self, test_tenants):
        """Test that quotas are enforced."""
        tenant1, _ = test_tenants

        async with get_system_session() as session:
            tenant_service = TenantService(session)

            # Set very low quota
            await tenant_service.update_tenant(str(tenant1.id), {
                "max_messages_per_month": 1
            })

            # Update usage to exceed quota
            await tenant_service.update_quota_usage(
                str(tenant1.id), "messages", 2
            )

            # Check quota should show exceeded
            quota_status = await tenant_service.check_quota(
                str(tenant1.id), "messages", 1
            )

            assert not quota_status["allowed"]

    async def test_quota_usage_tracking(self, test_tenants):
        """Test quota usage tracking."""
        tenant1, _ = test_tenants

        async with get_system_session() as session:
            tenant_service = TenantService(session)

            # Get initial usage
            initial_stats = await tenant_service.get_tenant_statistics(str(tenant1.id))
            initial_messages = initial_stats["current_usage"]["messages_this_month"]

            # Update usage
            await tenant_service.update_quota_usage(
                str(tenant1.id), "messages", 10
            )

            # Check updated usage
            updated_stats = await tenant_service.get_tenant_statistics(str(tenant1.id))
            updated_messages = updated_stats["current_usage"]["messages_this_month"]

            assert updated_messages == initial_messages + 10


class TestTenantAccessControl:
    """Test tenant access control and user management."""

    async def test_user_tenant_association(self, test_tenants, test_users):
        """Test adding and removing users from tenants."""
        tenant1, _ = test_tenants
        user1, _ = test_users

        async with get_system_session() as session:
            tenant_service = TenantService(session)

            # Add user to tenant
            tenant_user = await tenant_service.add_user_to_tenant(
                str(tenant1.id), str(user1.id), "member"
            )

            assert tenant_user.tenant_id == tenant1.id
            assert tenant_user.user_id == user1.id
            assert tenant_user.role == "member"

            # Remove user from tenant
            success = await tenant_service.remove_user_from_tenant(
                str(tenant1.id), str(user1.id)
            )

            assert success

    async def test_duplicate_user_prevention(self, test_tenants, test_users):
        """Test that users cannot be added to the same tenant twice."""
        tenant1, _ = test_tenants
        user1, _ = test_users

        async with get_system_session() as session:
            tenant_service = TenantService(session)

            # Add user to tenant
            await tenant_service.add_user_to_tenant(
                str(tenant1.id), str(user1.id), "member"
            )

            # Try to add same user again (should fail)
            with pytest.raises(Exception):
                await tenant_service.add_user_to_tenant(
                    str(tenant1.id), str(user1.id), "admin"
                )


class TestTenantAuditLogging:
    """Test tenant-specific audit logging."""

    async def test_tenant_audit_isolation(self, test_tenants):
        """Test that audit logs are isolated by tenant."""
        tenant1, tenant2 = test_tenants

        async with get_system_session() as session:
            # Create audit logs for each tenant
            audit1 = AuditLog(
                tenant_id=tenant1.id,
                event_id=str(uuid.uuid4()),
                event_type="test_event",
                action="test_action_1",
                timestamp=datetime.utcnow(),
                integrity_hash="hash1"
            )

            audit2 = AuditLog(
                tenant_id=tenant2.id,
                event_id=str(uuid.uuid4()),
                event_type="test_event",
                action="test_action_2",
                timestamp=datetime.utcnow(),
                integrity_hash="hash2"
            )

            session.add(audit1)
            session.add(audit2)
            await session.commit()

        # Test tenant 1 can only see their audit logs
        async with get_tenant_session(str(tenant1.id)) as session:
            result = await session.execute(select(AuditLog))
            logs = result.scalars().all()

            assert len(logs) == 1
            assert logs[0].action == "test_action_1"
            assert logs[0].tenant_id == tenant1.id

        # Test tenant 2 can only see their audit logs
        async with get_tenant_session(str(tenant2.id)) as session:
            result = await session.execute(select(AuditLog))
            logs = result.scalars().all()

            assert len(logs) == 1
            assert logs[0].action == "test_action_2"
            assert logs[0].tenant_id == tenant2.id


class TestDatabaseHealthAndSetup:
    """Test database health and RLS setup."""

    async def test_rls_functions_exist(self):
        """Test that RLS functions are properly set up."""
        async with get_system_session() as session:
            # Check if current_tenant_id function exists
            result = await session.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'current_tenant_id')")
            )
            assert result.scalar() is True

            # Check if is_system_admin function exists
            result = await session.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc WHERE proname = 'is_system_admin')")
            )
            assert result.scalar() is True

    async def test_rls_policies_exist(self):
        """Test that RLS policies are properly set up."""
        async with get_system_session() as session:
            # Check if RLS is enabled on messages table
            result = await session.execute(
                text("""
                    SELECT relrowsecurity 
                    FROM pg_class 
                    WHERE relname = 'messages'
                """)
            )
            assert result.scalar() is True

            # Check if policies exist
            result = await session.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM pg_policies 
                    WHERE tablename = 'messages'
                """)
            )
            assert result.scalar() > 0

    async def test_session_manager_health_check(self):
        """Test session manager health check."""
        health = await session_manager.health_check()
        assert health is True


# Integration test
class TestTenantIntegration:
    """Integration tests for complete tenant workflow."""

    async def test_complete_tenant_workflow(self):
        """Test complete tenant provisioning and usage workflow."""
        # Create tenant
        async with get_system_session() as session:
            tenant_service = TenantService(session)

            tenant = await tenant_service.create_tenant(
                name="integration-test",
                display_name="Integration Test Tenant",
                admin_email="admin@integration.test",
                tier="premium"
            )

            # Create user
            user = User(
                email="user@integration.test",
                first_name="Integration",
                last_name="User"
            )
            session.add(user)
            await session.flush()

            # Add user to tenant
            await tenant_service.add_user_to_tenant(
                str(tenant.id), str(user.id), "admin"
            )

            # Test tenant-specific operations
            async with get_tenant_session(str(tenant.id)) as tenant_session:
                # Create participant
                participant = Participant(
                    tenant_id=tenant.id,
                    platform="integration",
                    platform_user_id="test_user",
                    display_name="Test User"
                )
                tenant_session.add(participant)
                await tenant_session.flush()

                # Create thread
                thread = Thread(
                    tenant_id=tenant.id,
                    platform="integration",
                    platform_thread_id="test_thread",
                    title="Integration Test Thread",
                    participants=[participant.id]
                )
                tenant_session.add(thread)
                await tenant_session.flush()

                # Create message
                message = Message(
                    tenant_id=tenant.id,
                    platform="integration",
                    platform_message_id="test_message",
                    thread_id=thread.id,
                    sender_id=participant.id,
                    content_text="Integration test message",
                    timestamp=datetime.utcnow()
                )
                tenant_session.add(message)
                await tenant_session.commit()

                # Verify data exists
                result = await tenant_session.execute(select(Message))
                messages = result.scalars().all()
                assert len(messages) == 1
                assert messages[0].content_text == "Integration test message"

            # Test encryption
            security_service = TenantSecurityService()
            encrypted = await security_service.encrypt_tenant_data(
                str(tenant.id), "sensitive data", "test_field"
            )
            decrypted = await security_service.decrypt_tenant_data(
                str(tenant.id), encrypted, "test_field"
            )
            assert decrypted == "sensitive data"

            # Test quotas
            quota_status = await tenant_service.check_quota(
                str(tenant.id), "messages", 1
            )
            assert quota_status["allowed"] is True

            # Cleanup
            await tenant_service.delete_tenant(str(tenant.id))
            await session.delete(user)
            await session.commit()
