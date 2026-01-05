
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
import uuid
import json

# Add parent directory to path to allow importing from apps/backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from db.session import get_session, init_db
from db.models import (
    User, 
    PlatformConnection, 
    PlatformType, 
    ConnectionStatus,
    Participant,
    RawMessage,
    Message,
    Contact
)
from services.auth.jwt_service import get_jwt_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    """Seed the database with initial test data."""
    logger.info("Starting database seeding...")
    
    # Initialize DB connection
    await init_db()
    
    async with get_session() as session:
        # Check if test user exists
        stmt = select(User).where(User.username == "testuser")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        # Get JWT service for hashing
        jwt_service = get_jwt_service()
        hashed_password = jwt_service.hash_password("password123")
        
        if not user:
            logger.info("Creating test user...")
            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password=hashed_password,
                full_name="Test User",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            logger.info("Test user already exists. Updating password...")
            user.hashed_password = hashed_password
            session.add(user)
            await session.commit()
            
        # Create Connections
        platforms = [
            (PlatformType.GMAIL, "active"),
            (PlatformType.SLACK, "active"),
            (PlatformType.DISCORD, "inactive"),
            (PlatformType.WHATSAPP, "active")
        ]
        
        connections = {}
        
        for platform_type, status_str in platforms:
            stmt = select(PlatformConnection).where(
                PlatformConnection.user_id == user.id,
                PlatformConnection.platform == platform_type
            )
            result = await session.execute(stmt)
            connection = result.scalar_one_or_none()
            
            if not connection:
                logger.info(f"Creating {platform_type.value} connection...")
                status = ConnectionStatus.ACTIVE if status_str == "active" else ConnectionStatus.INACTIVE
                connection = PlatformConnection(
                    user_id=user.id,
                    platform=platform_type,
                    credentials={"access_token": "dummy_token"},
                    status=status,
                    last_sync_at=datetime.utcnow()
                )
                session.add(connection)
                await session.commit()
                await session.refresh(connection)
            
            connections[platform_type] = connection

        # Create Contacts & Participants (Senders)
        senders_data = [
            {"platform": PlatformType.SLACK, "name": "Alice", "id": "U12345", "role": "Engineer"},
            {"platform": PlatformType.GMAIL, "name": "Bob", "id": "bob@example.com", "role": "PM"},
            {"platform": PlatformType.DISCORD, "name": "Charlie", "id": "D98765", "role": "Gamer"},
             {"platform": PlatformType.WHATSAPP, "name": "David", "id": "PRO123", "role": "Friend"}
        ]
        
        participants = {}
        
        for p_data in senders_data:
            # Check/Create Contact
            stmt = select(Contact).where(Contact.canonical_name == p_data["name"])
            result = await session.execute(stmt)
            contact = result.scalar_one_or_none()
            
            if not contact:
                 logger.info(f"Creating contact {p_data['name']}...")
                 contact = Contact(
                     canonical_name=p_data["name"],
                     contact_metadata={"role": p_data["role"]},
                     platform_identities={p_data["platform"].value: p_data["id"]}
                 )
                 session.add(contact)
                 await session.commit()
                 await session.refresh(contact)

            # Check/Create Participant
            stmt = select(Participant).where(
                Participant.platform == p_data["platform"].value,
                Participant.platform_user_id == p_data["id"]
            )
            result = await session.execute(stmt)
            participant = result.scalar_one_or_none()
            
            if not participant:
                logger.info(f"Creating participant {p_data['name']}...")
                participant = Participant(
                    platform=p_data["platform"].value,
                    platform_user_id=p_data["id"],
                    name=p_data["name"],
                    participant_metadata={"display_name": p_data["name"]},
                    contact_id=contact.id
                )
                session.add(participant)
                await session.commit()
                await session.refresh(participant)
            else:
                 if not participant.contact_id:
                     logger.info(f"Linking participant {p_data['name']} to contact...")
                     participant.contact_id = contact.id
                     session.add(participant)
                     await session.commit()
            
            participants[(p_data["platform"], p_data["name"])] = participant

        # Create Messages
        messages_data = [
            {
                "platform": PlatformType.SLACK,
                "sender": "Alice",
                "content": "Hey team, checking in on the Q4 roadmap.",
                "minutes_ago": 10
            },
            {
                "platform": PlatformType.GMAIL,
                "sender": "Bob",
                "content": "Attached is the invoice for last month.",
                "minutes_ago": 60
            },
            {
                "platform": PlatformType.DISCORD,
                "sender": "Charlie",
                "content": "Server is down! Can someone check?",
                "minutes_ago": 120
            },
             {
                "platform": PlatformType.WHATSAPP,
                "sender": "David",
                "content": "Are we still on for lunch?",
                "minutes_ago": 15
            }
        ]
        
        for msg_data in messages_data:
            platform = msg_data["platform"]
            connection = connections.get(platform)
            
            if connection:
                # Unique ID for message
                msg_id = f"msg_{uuid.uuid4()}"
                
                # Check if raw message exists (by platform_message_id and connection)
                stmt = select(RawMessage).where(
                    RawMessage.connection_id == connection.id,
                    RawMessage.platform_message_id == msg_id
                )
                result = await session.execute(stmt)
                existing_raw = result.scalar_one_or_none()
                
                if not existing_raw:
                    logger.info(f"Creating message from {msg_data['sender']} on {platform.value}...")
                    
                    # Create RawMessage
                    raw_msg = RawMessage(
                        connection_id=connection.id,
                        platform=platform.value,
                        platform_message_id=msg_id,
                        raw_data={"text": msg_data["content"]},
                        processed=True
                    )
                    session.add(raw_msg)
                    await session.commit()
                    await session.refresh(raw_msg)
                    
                    # Create Normalized Message
                    sender = participants.get((platform, msg_data["sender"]))
                    timestamp = datetime.utcnow() - timedelta(minutes=msg_data["minutes_ago"])
                    
                    message = Message(
                        connection_id=connection.id,
                        raw_message_id=raw_msg.id,
                        platform=platform.value,
                        platform_message_id=msg_id,
                        sender_id=sender.id if sender else None,
                        content={"text": msg_data["content"], "format": "text"},
                        timestamp=timestamp,
                        collected_at=datetime.utcnow(),
                        cleaned_at=datetime.utcnow()
                    )
                    session.add(message)
                    await session.commit()

    logger.info("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
