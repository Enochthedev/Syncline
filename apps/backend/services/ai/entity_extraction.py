"""
Entity Extraction Service

Extracts named entities from messages using spaCy NER:
- Person names (PERSON)
- Organizations (ORG)
- Dates and times (DATE)
- Locations (LOCATION, GPE)
- Topics and keywords (custom extraction)
- Confidence scoring
- Storage in database
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

import spacy
from spacy.language import Language
from spacy.tokens import Doc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import settings
from db.models.entity import Entity
from db.models.message import Message

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Types of entities that can be extracted."""

    PERSON = "PERSON"
    ORG = "ORG"
    DATE = "DATE"
    TIME = "TIME"
    LOCATION = "LOCATION"
    GPE = "GPE"  # Geopolitical entity (countries, cities, states)
    TOPIC = "TOPIC"  # Custom: extracted topics/keywords
    EMAIL = "EMAIL"  # Custom: email addresses
    PHONE = "PHONE"  # Custom: phone numbers
    URL = "URL"  # Custom: URLs
    MONEY = "MONEY"
    PRODUCT = "PRODUCT"
    EVENT = "EVENT"


class ExtractedEntity:
    """
    Represents an extracted entity with metadata.

    Attributes:
        text: Entity text
        type: Entity type
        start_pos: Start position in text
        end_pos: End position in text
        confidence: Confidence score (0.0 to 1.0)
        normalized_value: Normalized/canonical form
        context: Surrounding context
    """

    def __init__(
        self,
        text: str,
        entity_type: EntityType,
        start_pos: int,
        end_pos: int,
        confidence: float = 1.0,
        normalized_value: Optional[str] = None,
        context: Optional[str] = None,
    ):
        self.text = text
        self.type = entity_type
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.confidence = confidence
        self.normalized_value = normalized_value or text
        self.context = context

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "text": self.text,
            "type": self.type.value,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence,
            "normalized_value": self.normalized_value,
            "context": self.context,
        }


class EntityExtractionService:
    """
    Service for extracting named entities from text.

    Uses spaCy for NER with support for:
    - Standard entity types (PERSON, ORG, DATE, etc.)
    - Custom entity extraction (topics, emails, phones)
    - Confidence scoring
    - Batch processing
    - Database storage
    """

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        batch_size: int = 50,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize entity extraction service.

        Args:
            model_name: spaCy model name
            batch_size: Batch size for processing
            confidence_threshold: Minimum confidence for entities
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.confidence_threshold = confidence_threshold
        self._nlp: Optional[Language] = None

        logger.info(
            f"Initialized EntityExtractionService with model {model_name}, "
            f"batch_size={batch_size}, threshold={confidence_threshold}"
        )

    def _load_model(self) -> Language:
        """
        Load spaCy model lazily.

        Returns:
            spaCy Language model
        """
        if self._nlp is None:
            try:
                logger.info(f"Loading spaCy model: {self.model_name}")
                self._nlp = spacy.load(self.model_name)
                logger.info(f"Successfully loaded spaCy model: {self.model_name}")
            except OSError:
                logger.warning(
                    f"Model {self.model_name} not found. " f"Attempting to download..."
                )
                # Try to download the model
                import subprocess

                subprocess.run(
                    ["python", "-m", "spacy", "download", self.model_name], check=True
                )
                self._nlp = spacy.load(self.model_name)
                logger.info(f"Downloaded and loaded spaCy model: {self.model_name}")

        return self._nlp

    def extract_entities(
        self,
        text: str,
        include_context: bool = True,
        context_window: int = 50,
    ) -> list[ExtractedEntity]:
        """
        Extract entities from text.

        Args:
            text: Text to extract entities from
            include_context: Include surrounding context
            context_window: Characters before/after entity for context

        Returns:
            List of extracted entities
        """
        if not text or not text.strip():
            return []

        try:
            nlp = self._load_model()
            doc = nlp(text)

            entities = []

            # Extract standard spaCy entities
            for ent in doc.ents:
                # Map spaCy labels to our EntityType
                entity_type = self._map_spacy_label(ent.label_)

                if entity_type is None:
                    continue

                # Get context if requested
                context = None
                if include_context:
                    context = self._get_context(
                        text, ent.start_char, ent.end_char, context_window
                    )

                # Create extracted entity
                extracted = ExtractedEntity(
                    text=ent.text,
                    entity_type=entity_type,
                    start_pos=ent.start_char,
                    end_pos=ent.end_char,
                    confidence=1.0,  # spaCy doesn't provide confidence scores
                    normalized_value=ent.text.strip(),
                    context=context,
                )

                entities.append(extracted)

            # Extract custom entities (emails, phones, URLs)
            custom_entities = self._extract_custom_entities(text)
            entities.extend(custom_entities)

            # Filter by confidence threshold
            entities = [
                e for e in entities if e.confidence >= self.confidence_threshold
            ]

            logger.debug(f"Extracted {len(entities)} entities from text")
            return entities

        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            return []

    def extract_entities_batch(
        self,
        texts: list[str],
        include_context: bool = True,
        context_window: int = 50,
    ) -> list[list[ExtractedEntity]]:
        """
        Extract entities from multiple texts in batch.

        Args:
            texts: List of texts to process
            include_context: Include surrounding context
            context_window: Characters before/after entity for context

        Returns:
            List of entity lists (one per text)
        """
        if not texts:
            return []

        try:
            nlp = self._load_model()

            # Process texts in batch using spaCy's pipe
            results = []
            for doc in nlp.pipe(texts, batch_size=self.batch_size):
                entities = []

                # Extract standard entities
                for ent in doc.ents:
                    entity_type = self._map_spacy_label(ent.label_)

                    if entity_type is None:
                        continue

                    context = None
                    if include_context:
                        context = self._get_context(
                            doc.text, ent.start_char, ent.end_char, context_window
                        )

                    extracted = ExtractedEntity(
                        text=ent.text,
                        entity_type=entity_type,
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        confidence=1.0,
                        normalized_value=ent.text.strip(),
                        context=context,
                    )

                    entities.append(extracted)

                # Extract custom entities
                custom_entities = self._extract_custom_entities(doc.text)
                entities.extend(custom_entities)

                # Filter by confidence
                entities = [
                    e for e in entities if e.confidence >= self.confidence_threshold
                ]

                results.append(entities)

            logger.info(f"Extracted entities from {len(texts)} texts in batch")
            return results

        except Exception as e:
            logger.error(f"Failed to extract entities in batch: {e}")
            return [[] for _ in texts]

    async def extract_and_store_entities(
        self,
        message: Message,
        db: AsyncSession,
        force_regenerate: bool = False,
    ) -> list[Entity]:
        """
        Extract entities from a message and store in database.

        Args:
            message: Message to extract entities from
            db: Database session
            force_regenerate: Force regeneration if entities exist

        Returns:
            List of Entity objects
        """
        try:
            # Check if entities already exist
            if not force_regenerate:
                result = await db.execute(
                    select(Entity).where(Entity.message_id == message.id)
                )
                existing = result.scalars().all()
                if existing:
                    logger.debug(f"Entities already exist for message {message.id}")
                    return list(existing)

            # Extract text from message
            text = self._extract_text_from_message(message)

            if not text:
                logger.warning(f"No text content in message {message.id}")
                return []

            # Extract entities
            extracted_entities = self.extract_entities(text)

            if not extracted_entities:
                logger.debug(f"No entities found in message {message.id}")
                return []

            # Delete existing entities if regenerating
            if force_regenerate:
                await db.execute(select(Entity).where(Entity.message_id == message.id))
                existing = result.scalars().all()
                for entity in existing:
                    await db.delete(entity)

            # Create Entity objects
            entities = []
            for extracted in extracted_entities:
                entity = Entity(
                    message_id=message.id,
                    entity_type=extracted.type.value,
                    entity_text=extracted.text,
                    confidence=extracted.confidence,
                    entity_metadata={
                        "start_pos": extracted.start_pos,
                        "end_pos": extracted.end_pos,
                        "normalized_value": extracted.normalized_value,
                        "context": extracted.context,
                        "extractor": "spacy",
                    },
                )
                db.add(entity)
                entities.append(entity)

            await db.commit()

            # Refresh entities
            for entity in entities:
                await db.refresh(entity)

            logger.info(
                f"Extracted and stored {len(entities)} entities "
                f"for message {message.id}"
            )
            return entities

        except Exception as e:
            logger.error(f"Failed to extract and store entities: {e}")
            await db.rollback()
            return []

    async def extract_and_store_entities_batch(
        self,
        messages: list[Message],
        db: AsyncSession,
        force_regenerate: bool = False,
    ) -> list[list[Entity]]:
        """
        Extract entities from multiple messages in batch.

        Args:
            messages: List of messages to process
            db: Database session
            force_regenerate: Force regeneration if entities exist

        Returns:
            List of entity lists (one per message)
        """
        try:
            # Filter messages that need entity extraction
            messages_to_process = []

            if not force_regenerate:
                for message in messages:
                    result = await db.execute(
                        select(Entity).where(Entity.message_id == message.id)
                    )
                    existing = result.scalars().all()
                    if not existing:
                        messages_to_process.append(message)
            else:
                messages_to_process = messages

            if not messages_to_process:
                logger.debug("All messages already have entities")
                return []

            logger.info(f"Extracting entities from {len(messages_to_process)} messages")

            # Extract texts
            texts = [
                self._extract_text_from_message(msg) for msg in messages_to_process
            ]

            # Filter out empty texts
            valid_indices = [i for i, text in enumerate(texts) if text]
            valid_texts = [texts[i] for i in valid_indices]
            valid_messages = [messages_to_process[i] for i in valid_indices]

            if not valid_texts:
                logger.warning("No valid texts to extract entities from")
                return []

            # Extract entities in batch
            extracted_batch = self.extract_entities_batch(valid_texts)

            # Store entities
            all_entities = []
            for message, extracted_list in zip(valid_messages, extracted_batch):
                if not extracted_list:
                    all_entities.append([])
                    continue

                # Delete existing if regenerating
                if force_regenerate:
                    result = await db.execute(
                        select(Entity).where(Entity.message_id == message.id)
                    )
                    existing = result.scalars().all()
                    for entity in existing:
                        await db.delete(entity)

                # Create Entity objects
                entities = []
                for extracted in extracted_list:
                    entity = Entity(
                        message_id=message.id,
                        entity_type=extracted.type.value,
                        entity_text=extracted.text,
                        confidence=extracted.confidence,
                        entity_metadata={
                            "start_pos": extracted.start_pos,
                            "end_pos": extracted.end_pos,
                            "normalized_value": extracted.normalized_value,
                            "context": extracted.context,
                            "extractor": "spacy",
                        },
                    )
                    db.add(entity)
                    entities.append(entity)

                all_entities.append(entities)

            await db.commit()

            # Refresh all entities
            for entity_list in all_entities:
                for entity in entity_list:
                    await db.refresh(entity)

            total_entities = sum(len(e) for e in all_entities)
            logger.info(
                f"Extracted and stored {total_entities} entities "
                f"from {len(valid_messages)} messages"
            )
            return all_entities

        except Exception as e:
            logger.error(f"Failed to extract and store entities in batch: {e}")
            await db.rollback()
            return []

    async def get_entities_for_message(
        self,
        message_id: UUID,
        db: AsyncSession,
        entity_type: Optional[EntityType] = None,
    ) -> list[Entity]:
        """
        Get entities for a message.

        Args:
            message_id: Message ID
            db: Database session
            entity_type: Filter by entity type (optional)

        Returns:
            List of Entity objects
        """
        try:
            query = select(Entity).where(Entity.message_id == message_id)

            if entity_type:
                query = query.where(Entity.entity_type == entity_type.value)

            result = await db.execute(query)
            entities = result.scalars().all()

            return list(entities)

        except Exception as e:
            logger.error(f"Failed to get entities for message {message_id}: {e}")
            return []

    async def delete_entities_for_message(
        self,
        message_id: UUID,
        db: AsyncSession,
    ) -> bool:
        """
        Delete all entities for a message.

        Args:
            message_id: Message ID
            db: Database session

        Returns:
            True if successful
        """
        try:
            result = await db.execute(
                select(Entity).where(Entity.message_id == message_id)
            )
            entities = result.scalars().all()

            for entity in entities:
                await db.delete(entity)

            await db.commit()

            logger.info(f"Deleted {len(entities)} entities for message {message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete entities for message {message_id}: {e}")
            await db.rollback()
            return False

    async def process_unprocessed_messages(
        self,
        db: AsyncSession,
        limit: Optional[int] = None,
    ) -> int:
        """
        Process messages that don't have entities yet.

        Args:
            db: Database session
            limit: Maximum number of messages to process

        Returns:
            Number of messages processed
        """
        try:
            # Find messages without entities
            query = (
                select(Message)
                .outerjoin(Entity)
                .where(Entity.id.is_(None))
                .order_by(Message.created_at.desc())
            )

            if limit:
                query = query.limit(limit)

            result = await db.execute(query)
            messages = result.scalars().all()

            if not messages:
                logger.info("No unprocessed messages found")
                return 0

            logger.info(f"Found {len(messages)} messages without entities")

            # Process in batches
            processed = 0
            for i in range(0, len(messages), self.batch_size):
                batch = messages[i : i + self.batch_size]
                entity_lists = await self.extract_and_store_entities_batch(batch, db)
                processed += len([e for e in entity_lists if e])

            logger.info(f"Processed {processed} messages")
            return processed

        except Exception as e:
            logger.error(f"Failed to process unprocessed messages: {e}")
            return 0

    def _map_spacy_label(self, label: str) -> Optional[EntityType]:
        """
        Map spaCy entity label to our EntityType.

        Args:
            label: spaCy entity label

        Returns:
            EntityType or None if not mapped
        """
        mapping = {
            "PERSON": EntityType.PERSON,
            "ORG": EntityType.ORG,
            "DATE": EntityType.DATE,
            "TIME": EntityType.TIME,
            "GPE": EntityType.GPE,
            "LOC": EntityType.LOCATION,
            "MONEY": EntityType.MONEY,
            "PRODUCT": EntityType.PRODUCT,
            "EVENT": EntityType.EVENT,
        }

        return mapping.get(label)

    def _extract_custom_entities(self, text: str) -> list[ExtractedEntity]:
        """
        Extract custom entities (emails, phones, URLs).

        Args:
            text: Text to extract from

        Returns:
            List of extracted entities
        """
        import re

        entities = []

        # Email pattern
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_pattern, text):
            entities.append(
                ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.EMAIL,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,
                )
            )

        # Phone pattern (simple US format)
        phone_pattern = (
            r"\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b"
        )
        for match in re.finditer(phone_pattern, text):
            entities.append(
                ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.PHONE,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,
                )
            )

        # URL pattern
        url_pattern = r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)"
        for match in re.finditer(url_pattern, text):
            entities.append(
                ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.URL,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,
                )
            )

        return entities

    def _get_context(
        self,
        text: str,
        start_pos: int,
        end_pos: int,
        window: int = 50,
    ) -> str:
        """
        Get surrounding context for an entity.

        Args:
            text: Full text
            start_pos: Entity start position
            end_pos: Entity end position
            window: Characters before/after

        Returns:
            Context string
        """
        context_start = max(0, start_pos - window)
        context_end = min(len(text), end_pos + window)

        context = text[context_start:context_end]

        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."

        return context.strip()

    def _extract_text_from_message(self, message: Message) -> str:
        """
        Extract text content from message for entity extraction.

        Args:
            message: Message object

        Returns:
            Text content
        """
        try:
            content = message.content

            # Try to get text content
            if isinstance(content, dict):
                text = content.get("text", "")

                # If no plain text, try HTML (strip tags)
                if not text:
                    html = content.get("html", "")
                    if html:
                        # Simple HTML tag removal
                        import re

                        text = re.sub(r"<[^>]+>", "", html)

                return text.strip()

            # If content is a string, use it directly
            if isinstance(content, str):
                return content.strip()

            return ""

        except Exception as e:
            logger.error(f"Failed to extract text from message {message.id}: {e}")
            return ""

    def health_check(self) -> bool:
        """
        Check health of entity extraction service.

        Returns:
            True if healthy
        """
        try:
            # Try to load model
            nlp = self._load_model()

            # Test with simple text
            doc = nlp("Test entity extraction")

            logger.debug("Entity extraction service health check passed")
            return True

        except Exception as e:
            logger.error(f"Entity extraction service health check failed: {e}")
            return False


# Global service instance
_entity_extraction_service: Optional[EntityExtractionService] = None


def get_entity_extraction_service(
    model_name: Optional[str] = None,
    batch_size: Optional[int] = None,
    confidence_threshold: Optional[float] = None,
) -> EntityExtractionService:
    """
    Get the global entity extraction service instance.

    Args:
        model_name: spaCy model name
        batch_size: Batch size for processing
        confidence_threshold: Minimum confidence threshold

    Returns:
        Entity extraction service
    """
    global _entity_extraction_service

    if _entity_extraction_service is None:
        _entity_extraction_service = EntityExtractionService(
            model_name=model_name or "en_core_web_sm",
            batch_size=batch_size or settings.AI_BATCH_SIZE,
            confidence_threshold=confidence_threshold or 0.5,
        )

    return _entity_extraction_service


__all__ = [
    "EntityExtractionService",
    "EntityType",
    "ExtractedEntity",
    "get_entity_extraction_service",
]
