#!/usr/bin/env python3
"""
Proactive Memory Agent Demo

This example demonstrates how to use the ProactiveMemoryAgent for:
- Commitment tracking and follow-up detection
- Contact dossier generation with relationship insights
- File tracking system for shared resources
- Nudge generation with contextual reminders
"""

from services.message_schema import (
    NormalizedMessage,
    MessageContent,
    Participant,
    Platform
)
from services.ai.memory.types import (
    Commitment,
    CommitmentType,
    CommitmentStatus,
    MemoryContext
)
from services.ai.memory.agent import ProactiveMemoryAgent
from uuid import uuid4
from datetime import datetime, timedelta
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def demo_commitment_tracking():
    """Demonstrate commitment tracking functionality."""
    print("=== Commitment Tracking Demo ===")

    # Initialize the agent
    agent = ProactiveMemoryAgent()

    # Create a sample message with commitments
    sender = Participant(
        id=str(uuid4()),
        display_name="John Doe",
        email="john@example.com"
    )

    recipient = Participant(
        id=str(uuid4()),
        display_name="Jane Smith",
        email="jane@example.com"
    )

    content = MessageContent(
        text="I'll send you the quarterly report by Friday. Also, let me schedule a meeting for next week to discuss the project timeline."
    )

    message = NormalizedMessage(
        id=str(uuid4()),
        platform=Platform.GMAIL,
        thread_id=str(uuid4()),
        sender=sender,
        recipients=[recipient],
        content=content,
        timestamp=datetime.utcnow()
    )

    # Track commitments from the message
    try:
        commitments = await agent.track_commitment(message)
        print(f"✅ Extracted {len(commitments)} commitments from message")

        for commitment in commitments:
            print(f"   - {commitment.type.value}: {commitment.description}")
            print(f"     Confidence: {commitment.confidence_score:.2f}")
            if commitment.due_date:
                print(f"     Due: {commitment.due_date}")
    except Exception as e:
        print(f"❌ Error tracking commitments: {e}")

    print()


async def demo_file_tracking():
    """Demonstrate file reference tracking."""
    print("=== File Tracking Demo ===")

    agent = ProactiveMemoryAgent()

    # Create message with file references
    sender = Participant(
        id=str(uuid4()),
        display_name="Alice Johnson"
    )

    content = MessageContent(
        text="Here's the project proposal document we discussed. I've also attached the budget spreadsheet."
    )

    message = NormalizedMessage(
        id=str(uuid4()),
        platform=Platform.SLACK,
        thread_id=str(uuid4()),
        sender=sender,
        recipients=[],
        content=content,
        timestamp=datetime.utcnow()
    )

    # Track file references
    try:
        files = await agent.track_file_reference(message)
        print(f"✅ Tracked {len(files)} file references")

        for file_ref in files:
            print(f"   - {file_ref.filename}")
            print(f"     Type: {file_ref.file_type}")
            print(f"     Shared by: {file_ref.shared_by}")
    except Exception as e:
        print(f"❌ Error tracking files: {e}")

    print()


async def demo_nudge_generation():
    """Demonstrate proactive nudge generation."""
    print("=== Nudge Generation Demo ===")

    agent = ProactiveMemoryAgent()
    user_id = str(uuid4())

    # Add some test commitments
    overdue_commitment = Commitment(
        type=CommitmentType.TASK,
        description="Submit quarterly report",
        committed_by=user_id,
        due_date=datetime.utcnow() - timedelta(days=2),
        status=CommitmentStatus.PENDING
    )

    upcoming_commitment = Commitment(
        type=CommitmentType.MEETING,
        description="Team standup meeting",
        committed_by=user_id,
        due_date=datetime.utcnow() + timedelta(hours=2),
        status=CommitmentStatus.PENDING
    )

    # Store commitments in agent
    agent._commitments[overdue_commitment.id] = overdue_commitment
    agent._commitments[upcoming_commitment.id] = upcoming_commitment

    # Generate nudges
    try:
        nudges = await agent.generate_nudges(user_id)
        print(f"✅ Generated {len(nudges)} nudges")

        for nudge in nudges:
            priority_emoji = {
                "low": "🔵",
                "medium": "🟡",
                "high": "🟠",
                "urgent": "🔴"
            }

            emoji = priority_emoji.get(nudge.priority.value, "⚪")
            print(f"   {emoji} {nudge.title}")
            print(f"     {nudge.message}")
            print(f"     Priority: {nudge.priority.value}")
            print(f"     Type: {nudge.type.value}")
    except Exception as e:
        print(f"❌ Error generating nudges: {e}")

    print()


async def demo_contact_dossier():
    """Demonstrate contact dossier generation."""
    print("=== Contact Dossier Demo ===")

    agent = ProactiveMemoryAgent()
    contact_id = str(uuid4())
    user_id = str(uuid4())

    try:
        # This would normally query the database, but for demo we'll mock it
        print("📋 Contact dossier generation requires database integration")
        print("   In a real scenario, this would:")
        print("   - Analyze communication patterns")
        print("   - Generate relationship insights")
        print("   - Create AI-powered summaries")
        print("   - Track shared files and commitments")

        # Show what a dossier would contain
        print("\n📊 Sample dossier structure:")
        print("   - Contact information and platforms")
        print("   - Communication frequency and patterns")
        print("   - Relationship strength score")
        print("   - Common topics and shared interests")
        print("   - Shared files and resources")
        print("   - Active commitments and follow-ups")
        print("   - AI-generated personality insights")

    except Exception as e:
        print(f"❌ Error generating dossier: {e}")

    print()


async def demo_memory_analysis():
    """Demonstrate comprehensive memory analysis."""
    print("=== Memory Analysis Demo ===")

    agent = ProactiveMemoryAgent()

    # Create analysis context
    context = MemoryContext(
        user_id=str(uuid4()),
        contact_id=str(uuid4()),
        time_window_start=datetime.utcnow() - timedelta(days=7),
        time_window_end=datetime.utcnow(),
        include_commitments=True,
        include_files=True,
        include_insights=True
    )

    try:
        # Perform memory analysis
        result = await agent.process(context)

        print(f"✅ Memory analysis completed in {result.processing_time:.2f}s")
        print(f"   - Commitments found: {len(result.commitments)}")
        print(f"   - Files tracked: {len(result.files)}")
        print(f"   - Nudges generated: {len(result.nudges)}")
        print(f"   - Insights discovered: {len(result.insights)}")

    except Exception as e:
        print(f"❌ Error in memory analysis: {e}")

    print()


async def main():
    """Run all demos."""
    print("🧠 Proactive Memory Agent Demo")
    print("=" * 50)
    print()

    await demo_commitment_tracking()
    await demo_file_tracking()
    await demo_nudge_generation()
    await demo_contact_dossier()
    await demo_memory_analysis()

    print("✨ Demo completed!")
    print("\nThe Proactive Memory Agent provides:")
    print("• Intelligent commitment tracking with AI-powered extraction")
    print("• Comprehensive file and resource tracking across platforms")
    print("• Proactive nudges for follow-ups and deadlines")
    print("• Rich contact dossiers with relationship insights")
    print("• Context-aware memory analysis and suggestions")


if __name__ == "__main__":
    asyncio.run(main())
