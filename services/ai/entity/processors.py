"""
Entity extraction processors using different NLP approaches.

This module contains specialized processors for entity extraction
using spaCy, Transformers, and LLM-based approaches.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
import json

# NLP libraries
try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available - entity extraction will be limited")

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning(
        "Transformers not available - advanced NER will be limited")

from .types import ExtractedEntity, EntityRelation, ExtractionResult
from ..base import BaseAIAgent, AIProvider
from ..providers import get_provider
from db.models.entity import EntityType
from config.config import settings

logger = logging.getLogger(__name__)


class SpacyProcessor:
    """spaCy-based entity extraction processor."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize spaCy processor."""
        self.model_name = model_name
        self.nlp = None
        self._load_model()

    def _load_model(self):
        """Load spaCy model."""
        if not SPACY_AVAILABLE:
            logger.warning("spaCy not available")
            return

        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Loaded spaCy model: {self.model_name}")
        except OSError:
            logger.warning(
                f"spaCy model {self.model_name} not found, trying en_core_web_sm")
            try:
                self.nlp = spacy.load("en_core_web_sm")
                self.model_name = "en_core_web_sm"
            except OSError:
                logger.error("No spaCy models available")
                self.nlp = None

    async def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy NER."""
        if not self.nlp:
            return []

        try:
            doc = self.nlp(text)
            entities = []

            for ent in doc.ents:
                # Map spaCy labels to our EntityType
                entity_type = self._map_spacy_label(ent.label_)
                if entity_type:
                    entity = ExtractedEntity(
                        type=entity_type,
                        value=ent.text,
                        confidence=0.7,  # Default confidence for spaCy
                        start_position=ent.start_char,
                        end_position=ent.end_char,
                        source_method="spacy",
                        context=text[max(0, ent.start_char-50)
                                         :ent.end_char+50],
                        metadata={
                            'spacy_label': ent.label_,
                            'spacy_confidence': getattr(ent, 'confidence', 0.7)
                        }
                    )
                    entities.append(entity)

            logger.debug(f"spaCy extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"spaCy entity extraction failed: {e}")
            return []

    def _map_spacy_label(self, spacy_label: str) -> Optional[EntityType]:
        """Map spaCy entity labels to our EntityType enum."""
        mapping = {
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'GPE': EntityType.LOCATION,  # Geopolitical entity
            'LOC': EntityType.LOCATION,
            'DATE': EntityType.DATE,
            'TIME': EntityType.DATE,
            'MONEY': EntityType.FINANCIAL,
            'CARDINAL': EntityType.NUMBER,
            'ORDINAL': EntityType.NUMBER,
            'PERCENT': EntityType.NUMBER,
            'QUANTITY': EntityType.NUMBER,
            'EMAIL': EntityType.EMAIL,
            'URL': EntityType.URL,
            'PHONE': EntityType.PHONE
        }
        return mapping.get(spacy_label)


class TransformerProcessor:
    """Transformer-based entity extraction processor."""

    def __init__(self, model_name: str = "dbmdz/bert-large-cased-finetuned-conll03-english"):
        """Initialize transformer processor."""
        self.model_name = model_name
        self.pipeline = None
        self._load_model()

    def _load_model(self):
        """Load transformer model."""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available")
            return

        try:
            self.pipeline = pipeline(
                "ner",
                model=self.model_name,
                tokenizer=self.model_name,
                aggregation_strategy="simple"
            )
            logger.info(f"Loaded transformer model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load transformer model: {e}")
            self.pipeline = None

    async def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using transformer NER."""
        if not self.pipeline:
            return []

        try:
            # Run NER pipeline
            results = self.pipeline(text)
            entities = []

            for result in results:
                # Map transformer labels to our EntityType
                entity_type = self._map_transformer_label(
                    result['entity_group'])
                if entity_type:
                    entity = ExtractedEntity(
                        type=entity_type,
                        value=result['word'],
                        confidence=result['score'],
                        start_position=result['start'],
                        end_position=result['end'],
                        source_method="transformers",
                        context=text[max(0, result['start']-50)
                                         :result['end']+50],
                        metadata={
                            'transformer_label': result['entity_group'],
                            'transformer_score': result['score']
                        }
                    )
                    entities.append(entity)

            logger.debug(f"Transformer extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"Transformer entity extraction failed: {e}")
            return []

    def _map_transformer_label(self, transformer_label: str) -> Optional[EntityType]:
        """Map transformer entity labels to our EntityType enum."""
        mapping = {
            'PER': EntityType.PERSON,
            'PERSON': EntityType.PERSON,
            'ORG': EntityType.ORGANIZATION,
            'LOC': EntityType.LOCATION,
            'MISC': EntityType.OTHER,
            'DATE': EntityType.DATE,
            'TIME': EntityType.DATE,
            'MONEY': EntityType.FINANCIAL,
            'PERCENT': EntityType.NUMBER,
            'EMAIL': EntityType.EMAIL,
            'URL': EntityType.URL,
            'PHONE': EntityType.PHONE
        }
        return mapping.get(transformer_label.upper())


class LLMProcessor(BaseAIAgent):
    """LLM-based entity extraction processor."""

    def __init__(self, provider: AIProvider = None, model: str = None):
        """Initialize LLM processor."""
        super().__init__(
            name="llm_entity_extractor",
            provider=provider,
            model=model
        )

    async def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using LLM."""
        try:
            prompt = self._build_extraction_prompt(text)

            # Get LLM provider
            llm_provider = get_provider(
                self.provider or settings.DEFAULT_LLM_PROVIDER)

            # Generate response
            response = await llm_provider.generate_completion(
                prompt=prompt,
                model=self.model or settings.DEFAULT_CHAT_MODEL,
                max_tokens=2000,
                temperature=0.1
            )

            # Parse LLM response
            entities = self._parse_llm_response(response, text)

            logger.debug(f"LLM extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []

    def _build_extraction_prompt(self, text: str) -> str:
        """Build prompt for LLM entity extraction."""
        return f"""
Extract entities from the following text and return them as JSON.

Entity types to extract:
- PERSON: Names of people
- ORGANIZATION: Companies, institutions, groups
- LOCATION: Places, addresses, cities, countries
- DATE: Dates, times, temporal expressions
- EMAIL: Email addresses
- PHONE: Phone numbers
- URL: Web addresses
- FINANCIAL: Money amounts, financial terms
- NUMBER: Quantities, measurements
- OTHER: Other important entities

Text to analyze:
{text}

Return a JSON array of entities with this format:
[
  {{
    "type": "PERSON",
    "value": "John Smith",
    "start": 10,
    "end": 20,
    "confidence": 0.9
  }}
]

JSON:"""

    def _parse_llm_response(self, response: str, original_text: str) -> List[ExtractedEntity]:
        """Parse LLM response into ExtractedEntity objects."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                return []

            entities_data = json.loads(json_match.group())
            entities = []

            for entity_data in entities_data:
                try:
                    entity_type = EntityType(entity_data['type'].upper())
                    entity = ExtractedEntity(
                        type=entity_type,
                        value=entity_data['value'],
                        confidence=entity_data.get('confidence', 0.8),
                        start_position=entity_data.get('start'),
                        end_position=entity_data.get('end'),
                        source_method="llm",
                        context=original_text[
                            max(0, entity_data.get('start', 0)-50):
                            entity_data.get('end', len(original_text))+50
                        ] if entity_data.get('start') is not None else None,
                        metadata={
                            'llm_confidence': entity_data.get('confidence', 0.8)
                        }
                    )
                    entities.append(entity)
                except (ValueError, KeyError) as e:
                    logger.warning(
                        f"Failed to parse entity: {entity_data}, error: {e}")
                    continue

            return entities

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []
