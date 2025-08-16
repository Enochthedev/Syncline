#!/usr/bin/env python3
"""
Entity Extraction Agent Demo

This script demonstrates the capabilities of the EntityExtractionAgent
for extracting entities from messages with different NLP approaches.
"""

from db.models.entity import EntityType
from services.message_schema import NormalizedMessage, MessageContent, Participant, Platform
from services.ai.entity_extraction import EntityExtractionAgent, create_entity_extraction_agent
import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


async def demo_entity_extraction():
    """Demonstrate entity extraction capabilities."""
    print("🤖 Entity Extraction Agent Demo")
    print("=" * 50)

    # Create entity extraction agent (disable LLM validation for demo)
    agent = create_entity_extraction_agent(
        enable_llm_validation=False  # Disable to avoid needing API keys
    )

    # Sample messages to test
    sample_messages = [
        {
            "id": "demo-1",
            "content": "Hi John Doe, please review the quarterly_report.pdf by Friday. "
            "We need to schedule a meeting with Acme Corp next week. "
            "My phone is (555) 123-4567 and email is john@example.com. "
            "Don't forget to complete the task: submit budget proposal.",
            "description": "Business email with multiple entity types"
        },
        {
            "id": "demo-2",
            "content": "Meeting with Sarah Johnson from Microsoft at 2:00 PM tomorrow. "
            "Location: Conference Room A, Building 2. "
            "Budget approved: $50,000 for the Q4 initiative. "
            "Action item: Everyone needs to submit feedback by Dec 10th.",
            "description": "Meeting notification with dates, money, and tasks"
        },
        {
            "id": "demo-3",
            "content": "Can you send the presentation.pptx to mike.davis@company.com? "
            "Also, call me at +1 (800) 555-0199 after 3 PM. "
            "The project deadline is December 15th, 2024.",
            "description": "Simple request with files, contacts, and dates"
        }
    ]

    for i, msg_data in enumerate(sample_messages, 1):
        print(f"\n📧 Message {i}: {msg_data['description']}")
        print("-" * 60)
        print(f"Content: {msg_data['content']}")
        print()

        # Create normalized message
        message = NormalizedMessage(
            id=msg_data["id"],
            platform=Platform.GMAIL,
            content=MessageContent(text=msg_data["content"]),
            sender=Participant(
                display_name="Demo Sender",
                email="sender@example.com"
            ),
            timestamp=datetime.utcnow()
        )

        try:
            # Extract entities
            result = await agent.process(message)

            print(f"⚡ Processing time: {result.processing_time:.3f}s")
            print(
                f"📊 Found {len(result.entities)} entities and {len(result.relationships)} relationships")
            print()

            # Group entities by type
            entities_by_type = {}
            for entity in result.entities:
                if entity.type not in entities_by_type:
                    entities_by_type[entity.type] = []
                entities_by_type[entity.type].append(entity)

            # Display entities by type
            for entity_type, entities in entities_by_type.items():
                print(f"🏷️  {entity_type.value.upper()}:")
                for entity in entities:
                    confidence_emoji = "🟢" if entity.confidence >= 0.8 else "🟡" if entity.confidence >= 0.5 else "🔴"
                    print(
                        f"   {confidence_emoji} {entity.value} (confidence: {entity.confidence:.2f}, source: {entity.source})")
                    if entity.normalized_value and entity.normalized_value != entity.value:
                        print(f"      → normalized: {entity.normalized_value}")
                print()

            # Display relationships
            if result.relationships:
                print("🔗 RELATIONSHIPS:")
                for rel in result.relationships:
                    print(
                        f"   {rel.entity1_id} --[{rel.relationship_type}]--> {rel.entity2_id} (confidence: {rel.confidence:.2f})")
                print()

            # Display metadata
            print("📈 PROCESSING METADATA:")
            for key, value in result.metadata.items():
                print(f"   {key}: {value}")

        except Exception as e:
            print(f"❌ Error processing message: {e}")

        print("\n" + "=" * 80)

    # Display agent statistics
    print("\n📊 Agent Statistics:")
    stats = agent.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")


async def demo_confidence_levels():
    """Demonstrate confidence level categorization."""
    print("\n🎯 Confidence Level Demo")
    print("=" * 30)

    from services.ai.entity_extraction import ExtractedEntity, EntityConfidence

    # Create entities with different confidence levels
    test_entities = [
        ExtractedEntity(type=EntityType.person, value="John Doe",
                        confidence=0.95, source="test"),
        ExtractedEntity(type=EntityType.person, value="Jane Smith",
                        confidence=0.65, source="test"),
        ExtractedEntity(type=EntityType.organization,
                        value="Acme Corp", confidence=0.35, source="test"),
        ExtractedEntity(type=EntityType.email,
                        value="test@example.com", confidence=0.15, source="test"),
    ]

    for entity in test_entities:
        level = entity.get_confidence_level()
        emoji = {
            EntityConfidence.HIGH: "🟢",
            EntityConfidence.MEDIUM: "🟡",
            EntityConfidence.LOW: "🟠",
            EntityConfidence.VERY_LOW: "🔴"
        }[level]

        print(f"{emoji} {entity.value} ({entity.type.value}) - {level.value} confidence ({entity.confidence:.2f})")


async def demo_normalization():
    """Demonstrate entity normalization."""
    print("\n🔧 Entity Normalization Demo")
    print("=" * 35)

    agent = EntityExtractionAgent()

    test_cases = [
        (EntityType.person, "john doe", "Person name normalization"),
        (EntityType.organization, "Acme Corp Inc.", "Organization suffix removal"),
        (EntityType.email, "John@Example.COM", "Email case normalization"),
        (EntityType.phone, "555-123-4567", "Phone number formatting"),
        (EntityType.phone, "15551234567", "Phone with country code"),
        (EntityType.task, "TODO: submit report", "Task prefix removal"),
    ]

    for entity_type, raw_value, description in test_cases:
        normalized = agent._normalize_entity_value(raw_value, entity_type)
        print(f"📝 {description}:")
        print(f"   Input:  '{raw_value}'")
        print(f"   Output: '{normalized}'")
        print()


async def main():
    """Run all demos."""
    try:
        await demo_entity_extraction()
        await demo_confidence_levels()
        await demo_normalization()

        print("\n✅ Entity Extraction Agent Demo completed successfully!")
        print("\nThe EntityExtractionAgent provides:")
        print("• Multi-model entity extraction (spaCy + Transformers + patterns)")
        print("• Support for 10+ entity types (person, org, date, task, file, etc.)")
        print("• Confidence scoring and quality assessment")
        print("• Entity relationship detection")
        print("• Automatic deduplication and normalization")
        print("• LLM-based validation and enrichment (optional)")
        print("• Comprehensive error handling and fallbacks")

    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
