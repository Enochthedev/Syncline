"""
Entity Extraction Agent for the MESH ingestion system.

This module is now organized into smaller, focused components.
For the main functionality, use:

from services.ai.entity import get_entity_extractor, ExtractedEntity, EntityConfidence

This file is kept for backward compatibility.
"""

# Import everything from the organized structure for backward compatibility
from .entity import *

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import json

# NLP libraries
import spacy
from spacy import displacy
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification

# Local imports
from .base import BaseAIAgent, AIProvider, AIProcessingError
from .providers import get_provider
from services.message_schema import NormalizedMessage, MessageContent
from db.models.entity import EntityType
from config.config import settings

logger = logging.getLogger(__name__)


class EntityConfidence(str, Enum):
    """Entity confidence levels."""
    HIGH = "high"      # 0.8+
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"        # 0.2-0.5
    VERY_LOW = "very_low"  # <0.2


@dataclass
class ExtractedEntity:
    """Represents an extracted entity with metadata."""
    type: EntityType
    value: str
    normalized_value: Optional[str] = None
    confidence: float = 0.0
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    context: Optional[str] = None
    source: str = "unknown"  # spacy, transformers, llm
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_confidence_level(self) -> EntityConfidence:
        """Get confidence level category."""
        if self.confidence >= 0.8:
            return EntityConfidence.HIGH
        elif self.confidence >= 0.5:
            return EntityConfidence.MEDIUM
        elif self.confidence >= 0.2:
            return EntityConfidence.LOW
        else:
            return EntityConfidence.VERY_LOW


@dataclass
class EntityRelationship:
    """Represents a relationship between two entities."""
    entity1_id: str
    entity2_id: str
    relationship_type: str
    confidence: float
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityExtractionResult:
    """Result of entity extraction process."""
    message_id: str
    entities: List[ExtractedEntity]
    relationships: List[EntityRelationship]
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class EntityExtractionAgent(BaseAIAgent):
    """
    AI agent for extracting entities from messages with NER and LLM validation.

    Capabilities:
    - Named Entity Recognition using spaCy
    - Advanced entity detection with Transformers
    - LLM-based entity validation and enrichment
    - Entity relationship mapping
    - Confidence scoring and quality assessment
    """

    def __init__(
        self,
        provider: AIProvider = None,
        model: str = None,
        spacy_model: str = "en_core_web_sm",
        transformers_model: str = "dbmdz/bert-large-cased-finetuned-conll03-english",
        enable_llm_validation: bool = True,
        **kwargs
    ):
        """Initialize the entity extraction agent."""
        super().__init__(
            name="entity_extraction_agent",
            provider=provider,
            model=model,
            **kwargs
        )

        self.spacy_model_name = spacy_model
        self.transformers_model_name = transformers_model
        self.enable_llm_validation = enable_llm_validation

        # Initialize models
        self.spacy_nlp = None
        self.transformers_ner = None
        self._model_loading_lock = asyncio.Lock()

        # Entity type mappings
        self.spacy_to_entity_type = {
            "PERSON": EntityType.person,
            "ORG": EntityType.organization,
            "DATE": EntityType.date,
            "TIME": EntityType.date,
            "MONEY": EntityType.money,
            "GPE": EntityType.location,  # Geopolitical entity
            "LOC": EntityType.location,
            "PRODUCT": EntityType.topic,
            "EVENT": EntityType.topic,
            "WORK_OF_ART": EntityType.topic,
            "LAW": EntityType.topic,
            "LANGUAGE": EntityType.topic,
            "NORP": EntityType.topic,  # Nationalities, religious groups
        }

        # Task detection patterns
        self.task_patterns = [
            r'\b(?:todo|task|action item|follow up|need to|should|must|have to|remember to)\b.*',
            r'\b(?:deadline|due|by|before)\s+(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|\d{1,2}[\/\-]\d{1,2})',
            r'\b(?:meeting|call|appointment|schedule)\b.*',
            r'\b(?:complete|finish|deliver|submit|send|review)\b.*',
        ]

        # File detection patterns
        self.file_patterns = [
            r'\b[\w\-_]+\.(?:pdf|doc|docx|xls|xlsx|ppt|pptx|txt|csv|zip|rar|jpg|jpeg|png|gif|mp4|mp3|avi)\b',
            r'\b(?:document|file|attachment|report|spreadsheet|presentation|image|video|audio)\b',
            r'\b(?:shared|attached|uploaded|downloaded)\s+(?:file|document|image|video)\b',
        ]

    async def _ensure_models_loaded(self) -> None:
        """Ensure all NLP models are loaded."""
        async with self._model_loading_lock:
            if self.spacy_nlp is None:
                await self._load_spacy_model()

            if self.transformers_ner is None and self.transformers_model_name:
                await self._load_transformers_model()

    async def _load_spacy_model(self) -> None:
        """Load spaCy model in thread pool."""
        try:
            loop = asyncio.get_event_loop()
            self.spacy_nlp = await loop.run_in_executor(
                None, spacy.load, self.spacy_model_name
            )
            logger.info(f"Loaded spaCy model: {self.spacy_model_name}")
        except OSError as e:
            logger.error(
                f"Failed to load spaCy model {self.spacy_model_name}: {e}")
            logger.info("Falling back to blank English model")
            loop = asyncio.get_event_loop()
            self.spacy_nlp = await loop.run_in_executor(
                None, spacy.blank, "en"
            )

    async def _load_transformers_model(self) -> None:
        """Load Transformers NER model in thread pool."""
        try:
            loop = asyncio.get_event_loop()
            self.transformers_ner = await loop.run_in_executor(
                None,
                lambda: pipeline(
                    "ner",
                    model=self.transformers_model_name,
                    tokenizer=self.transformers_model_name,
                    aggregation_strategy="simple"
                )
            )
            logger.info(
                f"Loaded Transformers model: {self.transformers_model_name}")
        except Exception as e:
            logger.warning(
                f"Failed to load Transformers model {self.transformers_model_name}: {e}")
            self.transformers_ner = None

    async def process(self, message: NormalizedMessage, **kwargs) -> EntityExtractionResult:
        """
        Extract entities from a normalized message.

        Args:
            message: The normalized message to process
            **kwargs: Additional processing options

        Returns:
            EntityExtractionResult with extracted entities and relationships
        """
        start_time = datetime.utcnow()

        if not self._validate_input(message):
            raise AIProcessingError(
                "Invalid message input for entity extraction")

        # Ensure models are loaded
        await self._ensure_models_loaded()

        # Get message content
        content = message.content.get_primary_content()
        if not content:
            return EntityExtractionResult(
                message_id=message.id,
                entities=[],
                relationships=[],
                processing_time=0.0
            )

        # Extract entities using multiple methods
        entities = []

        # 1. spaCy NER
        spacy_entities = await self._extract_with_spacy(content)
        entities.extend(spacy_entities)

        # 2. Transformers NER (if available)
        if self.transformers_ner:
            transformers_entities = await self._extract_with_transformers(content)
            entities.extend(transformers_entities)

        # 3. Pattern-based extraction for tasks and files
        pattern_entities = await self._extract_with_patterns(content)
        entities.extend(pattern_entities)

        # 4. LLM-based validation and enrichment
        if self.enable_llm_validation and entities:
            entities = await self._validate_and_enrich_with_llm(content, entities)

        # 5. Deduplicate and merge similar entities
        entities = await self._deduplicate_entities(entities)

        # 6. Extract relationships between entities
        relationships = await self._extract_relationships(content, entities)

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        result = EntityExtractionResult(
            message_id=message.id,
            entities=entities,
            relationships=relationships,
            processing_time=processing_time,
            metadata={
                "content_length": len(content),
                "spacy_entities": len(spacy_entities),
                "transformers_entities": len(transformers_entities) if self.transformers_ner else 0,
                "pattern_entities": len(pattern_entities),
                "llm_validation": self.enable_llm_validation,
                "final_entity_count": len(entities),
                "relationship_count": len(relationships)
            }
        )

        logger.debug(
            f"Extracted {len(entities)} entities and {len(relationships)} relationships "
            f"from message {message.id} in {processing_time:.2f}s"
        )

        return result

    async def _extract_with_spacy(self, content: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER."""
        if not self.spacy_nlp:
            return []

        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, self.spacy_nlp, content)

            entities = []
            for ent in doc.ents:
                entity_type = self.spacy_to_entity_type.get(
                    ent.label_, EntityType.topic)

                # Get context (surrounding words)
                context_start = max(0, ent.start - 5)
                context_end = min(len(doc), ent.end + 5)
                context = doc[context_start:context_end].text

                entity = ExtractedEntity(
                    type=entity_type,
                    value=ent.text.strip(),
                    normalized_value=self._normalize_entity_value(
                        ent.text.strip(), entity_type),
                    confidence=0.7,  # Base confidence for spaCy
                    start_position=ent.start_char,
                    end_position=ent.end_char,
                    context=context,
                    source="spacy",
                    metadata={
                        "spacy_label": ent.label_,
                        "spacy_confidence": getattr(ent, 'confidence', 0.7)
                    }
                )
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"spaCy entity extraction failed: {e}")
            return []

    async def _extract_with_transformers(self, content: str) -> List[ExtractedEntity]:
        """Extract entities using Transformers NER."""
        if not self.transformers_ner:
            return []

        try:
            loop = asyncio.get_event_loop()
            ner_results = await loop.run_in_executor(None, self.transformers_ner, content)

            entities = []
            for result in ner_results:
                # Map Transformers labels to our entity types
                label = result['entity_group'].upper()
                entity_type = self._map_transformers_label(label)

                entity = ExtractedEntity(
                    type=entity_type,
                    value=result['word'].strip(),
                    normalized_value=self._normalize_entity_value(
                        result['word'].strip(), entity_type),
                    confidence=result['score'],
                    start_position=result.get('start'),
                    end_position=result.get('end'),
                    source="transformers",
                    metadata={
                        "transformers_label": label,
                        "transformers_score": result['score']
                    }
                )
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"Transformers entity extraction failed: {e}")
            return []

    def _map_transformers_label(self, label: str) -> EntityType:
        """Map Transformers NER labels to our entity types."""
        mapping = {
            "PER": EntityType.person,
            "PERSON": EntityType.person,
            "ORG": EntityType.organization,
            "LOC": EntityType.location,
            "MISC": EntityType.topic,
        }
        return mapping.get(label, EntityType.topic)

    async def _extract_with_patterns(self, content: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns."""
        entities = []

        # Extract tasks
        for pattern in self.task_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                entity = ExtractedEntity(
                    type=EntityType.task,
                    value=match.group().strip(),
                    normalized_value=self._normalize_task(
                        match.group().strip()),
                    confidence=0.6,
                    start_position=match.start(),
                    end_position=match.end(),
                    source="pattern",
                    metadata={"pattern_type": "task"}
                )
                entities.append(entity)

        # Extract files
        for pattern in self.file_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                entity = ExtractedEntity(
                    type=EntityType.file,
                    value=match.group().strip(),
                    normalized_value=self._normalize_filename(
                        match.group().strip()),
                    confidence=0.8,
                    start_position=match.start(),
                    end_position=match.end(),
                    source="pattern",
                    metadata={"pattern_type": "file"}
                )
                entities.append(entity)

        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.finditer(email_pattern, content)
        for match in matches:
            entity = ExtractedEntity(
                type=EntityType.email,
                value=match.group().strip(),
                normalized_value=match.group().strip().lower(),
                confidence=0.9,
                start_position=match.start(),
                end_position=match.end(),
                source="pattern",
                metadata={"pattern_type": "email"}
            )
            entities.append(entity)

        # Extract phone numbers
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        matches = re.finditer(phone_pattern, content)
        for match in matches:
            entity = ExtractedEntity(
                type=EntityType.phone,
                value=match.group().strip(),
                normalized_value=self._normalize_phone(match.group().strip()),
                confidence=0.8,
                start_position=match.start(),
                end_position=match.end(),
                source="pattern",
                metadata={"pattern_type": "phone"}
            )
            entities.append(entity)

        return entities

    async def _validate_and_enrich_with_llm(
        self,
        content: str,
        entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """Validate and enrich entities using LLM."""
        if not entities:
            return entities

        try:
            # Build prompt for LLM validation
            prompt = self._build_validation_prompt(content, entities)

            # Get LLM provider
            provider = get_provider(self.provider.value)

            # Generate validation response
            response = await provider.generate_completion(
                prompt=prompt,
                model=self.model,
                max_tokens=2000,
                temperature=0.1
            )

            # Parse LLM response and update entities
            validated_entities = await self._parse_llm_validation_response(response, entities)

            return validated_entities

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            return entities

    def _build_validation_prompt(self, content: str, entities: List[ExtractedEntity]) -> str:
        """Build prompt for LLM entity validation."""
        entities_json = []
        for i, entity in enumerate(entities):
            entities_json.append({
                "id": i,
                "type": entity.type.value,
                "value": entity.value,
                "confidence": entity.confidence,
                "source": entity.source
            })

        prompt = f"""
You are an expert entity extraction validator. Please review the following entities extracted from a message and provide validation feedback.

MESSAGE CONTENT:
{content}

EXTRACTED ENTITIES:
{json.dumps(entities_json, indent=2)}

Please validate each entity and respond with a JSON object containing:
1. "validated_entities": Array of entities with updated confidence scores (0.0-1.0)
2. "additional_entities": Array of any important entities that were missed
3. "corrections": Array of any corrections to entity types or values

For each entity, consider:
- Is the entity type correct?
- Is the entity value accurate and complete?
- What confidence level (0.0-1.0) should this entity have?
- Are there any normalization improvements?

Focus on entities related to: people, organizations, dates, tasks, files, topics, locations, money, phones, emails.

Respond only with valid JSON.
"""
        return prompt

    async def _parse_llm_validation_response(
        self,
        response: str,
        original_entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """Parse LLM validation response and update entities."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in LLM validation response")
                return original_entities

            validation_data = json.loads(json_match.group())

            # Update existing entities
            validated_entities = []
            for entity in original_entities:
                # Find corresponding validation data
                entity_id = original_entities.index(entity)
                validated_entity_data = None

                for val_entity in validation_data.get("validated_entities", []):
                    if val_entity.get("id") == entity_id:
                        validated_entity_data = val_entity
                        break

                if validated_entity_data:
                    # Update confidence and other fields
                    entity.confidence = min(
                        1.0, max(0.0, validated_entity_data.get("confidence", entity.confidence)))

                    # Update type if corrected
                    new_type = validated_entity_data.get("type")
                    if new_type and new_type in [t.value for t in EntityType]:
                        entity.type = EntityType(new_type)

                    # Update value if corrected
                    new_value = validated_entity_data.get("value")
                    if new_value:
                        entity.value = new_value
                        entity.normalized_value = self._normalize_entity_value(
                            new_value, entity.type)

                    # Mark as LLM validated
                    entity.metadata["llm_validated"] = True
                    entity.metadata["llm_confidence"] = entity.confidence

                validated_entities.append(entity)

            # Add any additional entities found by LLM
            for add_entity_data in validation_data.get("additional_entities", []):
                entity_type_str = add_entity_data.get("type")
                if entity_type_str and entity_type_str in [t.value for t in EntityType]:
                    additional_entity = ExtractedEntity(
                        type=EntityType(entity_type_str),
                        value=add_entity_data.get("value", ""),
                        normalized_value=self._normalize_entity_value(
                            add_entity_data.get("value", ""),
                            EntityType(entity_type_str)
                        ),
                        confidence=add_entity_data.get("confidence", 0.7),
                        source="llm",
                        metadata={"llm_discovered": True}
                    )
                    validated_entities.append(additional_entity)

            return validated_entities

        except Exception as e:
            logger.error(f"Failed to parse LLM validation response: {e}")
            return original_entities

    async def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate entities and merge similar ones."""
        if not entities:
            return entities

        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            if entity.type not in entities_by_type:
                entities_by_type[entity.type] = []
            entities_by_type[entity.type].append(entity)

        deduplicated = []

        for entity_type, type_entities in entities_by_type.items():
            # Sort by confidence (highest first)
            type_entities.sort(key=lambda x: x.confidence, reverse=True)

            # Deduplicate within type
            seen_values = set()
            for entity in type_entities:
                normalized = entity.normalized_value or entity.value.lower().strip()

                if normalized not in seen_values:
                    seen_values.add(normalized)
                    deduplicated.append(entity)
                else:
                    # Merge with existing entity (keep higher confidence)
                    existing = next(e for e in deduplicated if (
                        e.normalized_value or e.value.lower().strip()) == normalized)

                    # Always merge sources
                    if entity.source not in existing.source:
                        existing.source = f"{existing.source},{entity.source}"

                    # Update confidence if new entity has higher confidence
                    if entity.confidence > existing.confidence:
                        existing.confidence = entity.confidence

        return deduplicated

    async def _extract_relationships(
        self,
        content: str,
        entities: List[ExtractedEntity]
    ) -> List[EntityRelationship]:
        """Extract relationships between entities."""
        relationships = []

        if len(entities) < 2:
            return relationships

        # Simple relationship extraction based on proximity and patterns
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities[i+1:], i+1):
                relationship = await self._detect_relationship(content, entity1, entity2)
                if relationship:
                    relationships.append(relationship)

        return relationships

    async def _detect_relationship(
        self,
        content: str,
        entity1: ExtractedEntity,
        entity2: ExtractedEntity
    ) -> Optional[EntityRelationship]:
        """Detect relationship between two entities."""
        # Calculate proximity
        if entity1.start_position is not None and entity2.start_position is not None:
            distance = abs(entity1.start_position - entity2.start_position)

            # Only consider entities that are close to each other
            if distance > 200:  # More than 200 characters apart
                return None

            # Determine relationship type based on entity types and context
            relationship_type = self._determine_relationship_type(
                entity1, entity2, content)

            if relationship_type:
                # Closer = higher confidence
                confidence = max(0.3, 1.0 - (distance / 200.0))

                return EntityRelationship(
                    entity1_id=f"{entity1.type.value}:{entity1.value}",
                    entity2_id=f"{entity2.type.value}:{entity2.value}",
                    relationship_type=relationship_type,
                    confidence=confidence,
                    context=self._get_relationship_context(
                        content, entity1, entity2),
                    metadata={
                        "distance": distance,
                        "entity1_type": entity1.type.value,
                        "entity2_type": entity2.type.value
                    }
                )

        return None

    def _determine_relationship_type(
        self,
        entity1: ExtractedEntity,
        entity2: ExtractedEntity,
        content: str
    ) -> Optional[str]:
        """Determine the type of relationship between two entities."""
        type1, type2 = entity1.type, entity2.type

        # Person-Organization relationships
        if type1 == EntityType.person and type2 == EntityType.organization:
            return "works_at"
        elif type1 == EntityType.organization and type2 == EntityType.person:
            return "employs"

        # Person-Task relationships
        elif type1 == EntityType.person and type2 == EntityType.task:
            return "assigned_to"
        elif type1 == EntityType.task and type2 == EntityType.person:
            return "assigned_by"

        # Task-Date relationships
        elif type1 == EntityType.task and type2 == EntityType.date:
            return "due_date"
        elif type1 == EntityType.date and type2 == EntityType.task:
            return "deadline_for"

        # File-Person relationships
        elif type1 == EntityType.file and type2 == EntityType.person:
            return "shared_with"
        elif type1 == EntityType.person and type2 == EntityType.file:
            return "shared_by"

        # Topic relationships
        elif type1 == EntityType.topic or type2 == EntityType.topic:
            return "related_to"

        # Location relationships
        elif type1 == EntityType.location or type2 == EntityType.location:
            return "located_at"

        return None

    def _get_relationship_context(
        self,
        content: str,
        entity1: ExtractedEntity,
        entity2: ExtractedEntity
    ) -> str:
        """Get context around the relationship between two entities."""
        if entity1.start_position is None or entity2.start_position is None:
            return ""

        start = min(entity1.start_position, entity2.start_position)
        end = max(entity1.end_position or entity1.start_position + len(entity1.value),
                  entity2.end_position or entity2.start_position + len(entity2.value))

        # Expand context
        context_start = max(0, start - 50)
        context_end = min(len(content), end + 50)

        return content[context_start:context_end].strip()

    def _normalize_entity_value(self, value: str, entity_type: EntityType) -> str:
        """Normalize entity value based on type."""
        if entity_type == EntityType.person:
            return self._normalize_person_name(value)
        elif entity_type == EntityType.organization:
            return self._normalize_organization_name(value)
        elif entity_type == EntityType.email:
            return value.lower().strip()
        elif entity_type == EntityType.phone:
            return self._normalize_phone(value)
        elif entity_type == EntityType.file:
            return self._normalize_filename(value)
        elif entity_type == EntityType.task:
            return self._normalize_task(value)
        else:
            return value.strip()

    def _normalize_person_name(self, name: str) -> str:
        """Normalize person name."""
        # Remove extra whitespace and title case
        normalized = ' '.join(name.strip().split())
        return normalized.title()

    def _normalize_organization_name(self, org: str) -> str:
        """Normalize organization name."""
        # Remove common suffixes and normalize
        normalized = org.strip()
        suffixes = ['Inc.', 'Inc', 'LLC', 'Ltd.',
                    'Ltd', 'Corp.', 'Corp', 'Co.', 'Co']

        # Only remove the last suffix to avoid over-trimming
        for suffix in suffixes:
            if normalized.endswith(f' {suffix}'):
                normalized = normalized[:-len(suffix)-1].strip()
                break  # Only remove one suffix
        return normalized

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number."""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)

        # Format as (XXX) XXX-XXXX if US number
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone.strip()

    def _normalize_filename(self, filename: str) -> str:
        """Normalize filename."""
        return filename.strip().lower()

    def _normalize_task(self, task: str) -> str:
        """Normalize task description."""
        # Remove common task prefixes and clean up
        task = task.strip()
        prefixes = ['todo:', 'task:', 'action item:', 'need to',
                    'should', 'must', 'have to', 'remember to']

        for prefix in prefixes:
            if task.lower().startswith(prefix):
                task = task[len(prefix):].strip()
                break

        return task.capitalize()

    def _build_prompt(self, input_data: Any, **kwargs) -> str:
        """Build prompt for LLM processing (required by base class)."""
        if isinstance(input_data, NormalizedMessage):
            content = input_data.content.get_primary_content()
            return f"Extract entities from this message: {content}"
        return str(input_data)

    def _validate_input(self, input_data: Any) -> bool:
        """Validate input data."""
        return isinstance(input_data, NormalizedMessage)

    def _post_process_response(self, response: str, input_data: Any) -> Any:
        """Post-process response (required by base class)."""
        return response


# Factory function for creating entity extraction agent
def create_entity_extraction_agent(**kwargs) -> EntityExtractionAgent:
    """Create and configure an entity extraction agent."""
    return EntityExtractionAgent(**kwargs)


# Global instance
_entity_extraction_agent = None


async def get_entity_extraction_agent() -> EntityExtractionAgent:
    """Get the global entity extraction agent instance."""
    global _entity_extraction_agent
    if _entity_extraction_agent is None:
        _entity_extraction_agent = create_entity_extraction_agent()
    return _entity_extraction_agent
