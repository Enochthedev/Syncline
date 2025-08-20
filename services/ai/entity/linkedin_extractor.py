"""
LinkedIn-specific entity extraction for professional relationships and business context.

This module provides specialized entity extraction capabilities for LinkedIn messages,
focusing on professional entities like job titles, companies, industries, and business relationships.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import re

from .types import ExtractedEntity, EntityRelation, ExtractionResult
from .extractor import EntityExtractor
from db.models.entity import EntityType
from ..base import AIProvider

logger = logging.getLogger(__name__)


class LinkedInEntityExtractor:
    """
    Specialized entity extractor for LinkedIn messages with professional context awareness.

    Extends the base EntityExtractor with LinkedIn-specific entity types and
    professional relationship detection capabilities.
    """

    def __init__(self, provider: AIProvider = None, model: str = None):
        """Initialize LinkedIn entity extractor."""
        self.provider = provider
        self.model = model

        # LinkedIn-specific entity patterns
        self.job_title_patterns = [
            r'\b(?:CEO|CTO|CFO|COO|VP|Director|Manager|Lead|Senior|Junior|Associate|Analyst|Specialist|Coordinator|Assistant)\b',
            r'\b(?:Software Engineer|Data Scientist|Product Manager|Sales Representative|Marketing Manager|HR Manager)\b',
            r'\b(?:Consultant|Advisor|Founder|Co-founder|Partner|Principal|Executive|Officer)\b'
        ]

        self.company_indicators = [
            r'\bat\s+([A-Z][a-zA-Z\s&]+(?:Inc|LLC|Corp|Ltd|Co)\.?)',
            r'\bworks?\s+(?:at|for)\s+([A-Z][a-zA-Z\s&]+)',
            r'\bemployed\s+(?:at|by)\s+([A-Z][a-zA-Z\s&]+)',
            r'\b([A-Z][a-zA-Z\s&]+(?:Inc|LLC|Corp|Ltd|Co)\.?)\s+(?:employee|team|department)'
        ]

        self.industry_keywords = [
            'technology', 'healthcare', 'finance', 'education', 'retail', 'manufacturing',
            'consulting', 'marketing', 'sales', 'human resources', 'operations', 'legal',
            'real estate', 'construction', 'automotive', 'aerospace', 'telecommunications',
            'media', 'entertainment', 'hospitality', 'transportation', 'logistics'
        ]

        self.business_opportunity_keywords = [
            'opportunity', 'partnership', 'collaboration', 'investment', 'funding',
            'acquisition', 'merger', 'joint venture', 'strategic alliance', 'deal',
            'contract', 'proposal', 'pitch', 'presentation', 'meeting', 'conference'
        ]

    async def extract_linkedin_entities(
        self,
        text: str,
        sender_context: Optional[Dict[str, Any]] = None,
        recipient_context: Optional[List[Dict[str, Any]]] = None
    ) -> ExtractionResult:
        """
        Extract entities from LinkedIn message with professional context.

        Args:
            text: Message text to analyze
            sender_context: Professional context of the sender
            recipient_context: Professional context of recipients

        Returns:
            ExtractionResult with LinkedIn-specific entities and relationships
        """
        start_time = datetime.utcnow()

        # Initialize base result (since we don't inherit from EntityExtractor)
        base_result = ExtractionResult(
            entities=[],
            relations=[],
            processing_time=0.0,
            methods_used=[],
            confidence_stats={},
            metadata={}
        )

        # Then add LinkedIn-specific entities
        linkedin_entities = []

        # Extract job titles
        job_titles = self._extract_job_titles(text)
        linkedin_entities.extend(job_titles)

        # Extract companies
        companies = self._extract_companies(text)
        linkedin_entities.extend(companies)

        # Extract industries
        industries = self._extract_industries(text)
        linkedin_entities.extend(industries)

        # Extract business opportunities
        opportunities = self._extract_business_opportunities(text)
        linkedin_entities.extend(opportunities)

        # Extract professional skills
        skills = self._extract_professional_skills(text)
        linkedin_entities.extend(skills)

        # Combine with base entities
        all_entities = base_result.entities + linkedin_entities

        # Extract professional relationships
        professional_relations = self._extract_professional_relationships(
            all_entities, text, sender_context, recipient_context
        )

        # Combine with base relations
        all_relations = base_result.relations + professional_relations

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Create enhanced result
        result = ExtractionResult(
            entities=all_entities,
            relations=all_relations,
            processing_time=processing_time,
            methods_used=base_result.methods_used + ['linkedin_professional'],
            confidence_stats=self._calculate_confidence_stats(all_entities),
            metadata={
                **base_result.metadata,
                'linkedin_specific_entities': len(linkedin_entities),
                'professional_relationships': len(professional_relations),
                'business_context_detected': len(opportunities) > 0,
                'sender_context_used': sender_context is not None,
                'recipient_context_used': recipient_context is not None
            }
        )

        logger.debug(
            f"LinkedIn entity extraction completed: {len(linkedin_entities)} professional entities, "
            f"{len(professional_relations)} professional relationships"
        )

        return result

    def _extract_job_titles(self, text: str) -> List[ExtractedEntity]:
        """Extract job titles from text."""
        entities = []

        for pattern in self.job_title_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = ExtractedEntity(
                    type=EntityType.job_title,
                    value=match.group(0),
                    normalized_value=match.group(0).title(),
                    confidence=0.8,
                    start_position=match.start(),
                    end_position=match.end(),
                    source_method='linkedin_job_title_pattern',
                    context=self._get_context(
                        text, match.start(), match.end()),
                    metadata={
                        'entity_category': 'professional',
                        'extraction_method': 'pattern_matching'
                    }
                )
                entities.append(entity)

        return entities

    def _extract_companies(self, text: str) -> List[ExtractedEntity]:
        """Extract company names from text."""
        entities = []

        for pattern in self.company_indicators:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                company_name = match.group(
                    1) if match.groups() else match.group(0)
                entity = ExtractedEntity(
                    type=EntityType.organization,
                    value=company_name,
                    normalized_value=company_name.strip(),
                    confidence=0.75,
                    start_position=match.start(),
                    end_position=match.end(),
                    source_method='linkedin_company_pattern',
                    context=self._get_context(
                        text, match.start(), match.end()),
                    metadata={
                        'entity_category': 'professional',
                        'organization_type': 'company',
                        'extraction_method': 'pattern_matching'
                    }
                )
                entities.append(entity)

        return entities

    def _extract_industries(self, text: str) -> List[ExtractedEntity]:
        """Extract industry mentions from text."""
        entities = []
        text_lower = text.lower()

        for industry in self.industry_keywords:
            if industry in text_lower:
                # Find the position of the industry mention
                start_pos = text_lower.find(industry)
                end_pos = start_pos + len(industry)

                entity = ExtractedEntity(
                    type=EntityType.industry,
                    value=industry,
                    normalized_value=industry.title(),
                    confidence=0.7,
                    start_position=start_pos,
                    end_position=end_pos,
                    source_method='linkedin_industry_keyword',
                    context=self._get_context(text, start_pos, end_pos),
                    metadata={
                        'entity_category': 'professional',
                        'extraction_method': 'keyword_matching'
                    }
                )
                entities.append(entity)

        return entities

    def _extract_business_opportunities(self, text: str) -> List[ExtractedEntity]:
        """Extract business opportunity mentions from text."""
        entities = []
        text_lower = text.lower()

        for opportunity in self.business_opportunity_keywords:
            if opportunity in text_lower:
                start_pos = text_lower.find(opportunity)
                end_pos = start_pos + len(opportunity)

                entity = ExtractedEntity(
                    type=EntityType.business_opportunity,
                    value=opportunity,
                    normalized_value=opportunity.title(),
                    confidence=0.6,
                    start_position=start_pos,
                    end_position=end_pos,
                    source_method='linkedin_opportunity_keyword',
                    context=self._get_context(text, start_pos, end_pos),
                    metadata={
                        'entity_category': 'business',
                        'opportunity_type': self._classify_opportunity_type(opportunity),
                        'extraction_method': 'keyword_matching'
                    }
                )
                entities.append(entity)

        return entities

    def _extract_professional_skills(self, text: str) -> List[ExtractedEntity]:
        """Extract professional skills from text."""
        entities = []

        # Common professional skills patterns
        skill_patterns = [
            r'\b(?:Python|Java|JavaScript|React|Angular|Node\.js|SQL|AWS|Azure|Docker|Kubernetes)\b',
            r'\b(?:project management|data analysis|machine learning|artificial intelligence|blockchain)\b',
            r'\b(?:leadership|communication|problem solving|team management|strategic planning)\b'
        ]

        for pattern in skill_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = ExtractedEntity(
                    type=EntityType.skill,
                    value=match.group(0),
                    normalized_value=match.group(0).title(),
                    confidence=0.65,
                    start_position=match.start(),
                    end_position=match.end(),
                    source_method='linkedin_skill_pattern',
                    context=self._get_context(
                        text, match.start(), match.end()),
                    metadata={
                        'entity_category': 'professional',
                        'skill_type': self._classify_skill_type(match.group(0)),
                        'extraction_method': 'pattern_matching'
                    }
                )
                entities.append(entity)

        return entities

    def _extract_professional_relationships(
        self,
        entities: List[ExtractedEntity],
        text: str,
        sender_context: Optional[Dict[str, Any]] = None,
        recipient_context: Optional[List[Dict[str, Any]]] = None
    ) -> List[EntityRelation]:
        """Extract professional relationships between entities."""
        relations = []

        # Extract relationships between people and organizations
        people = [e for e in entities if e.type == EntityType.person]
        organizations = [e for e in entities if e.type ==
                         EntityType.organization]
        job_titles = [e for e in entities if e.type == EntityType.job_title]

        # Person-Organization relationships
        for person in people:
            for org in organizations:
                if self._are_entities_related(person, org, text):
                    relation = EntityRelation(
                        source_entity=person,
                        target_entity=org,
                        relation_type="works_at",
                        confidence=0.7,
                        context=self._get_relationship_context(
                            person, org, text),
                        metadata={
                            'relationship_category': 'professional',
                            'inferred_from': 'proximity_and_context'
                        }
                    )
                    relations.append(relation)

        # Person-Job Title relationships
        for person in people:
            for job_title in job_titles:
                if self._are_entities_related(person, job_title, text):
                    relation = EntityRelation(
                        source_entity=person,
                        target_entity=job_title,
                        relation_type="has_job_title",
                        confidence=0.75,
                        context=self._get_relationship_context(
                            person, job_title, text),
                        metadata={
                            'relationship_category': 'professional',
                            'inferred_from': 'proximity_and_context'
                        }
                    )
                    relations.append(relation)

        # Add context-based relationships if available
        if sender_context:
            relations.extend(self._extract_context_relationships(
                entities, sender_context, 'sender'))

        if recipient_context:
            for i, context in enumerate(recipient_context):
                relations.extend(self._extract_context_relationships(
                    entities, context, f'recipient_{i}'))

        return relations

    def _are_entities_related(self, entity1: ExtractedEntity, entity2: ExtractedEntity, text: str) -> bool:
        """Check if two entities are related based on proximity and context."""
        if (entity1.start_position is not None and entity2.start_position is not None):
            distance = abs(entity1.start_position - entity2.start_position)
            return distance < 50  # Within 50 characters
        return False

    def _get_relationship_context(self, entity1: ExtractedEntity, entity2: ExtractedEntity, text: str) -> str:
        """Get context text for a relationship between two entities."""
        if (entity1.start_position is not None and entity2.start_position is not None):
            start = min(entity1.start_position, entity2.start_position)
            end = max(entity1.end_position or 0, entity2.end_position or 0)
            return text[max(0, start - 20):min(len(text), end + 20)]
        return ""

    def _extract_context_relationships(
        self,
        entities: List[ExtractedEntity],
        context: Dict[str, Any],
        context_type: str
    ) -> List[EntityRelation]:
        """Extract relationships based on participant context."""
        relations = []

        # Find person entities that match the context
        people = [e for e in entities if e.type == EntityType.person]

        for person in people:
            # Create relationships based on context information
            if context.get('company'):
                # Create a company entity if not already present
                company_entity = ExtractedEntity(
                    type=EntityType.organization,
                    value=context['company'],
                    normalized_value=context['company'],
                    confidence=0.9,
                    source_method='linkedin_context',
                    metadata={
                        'entity_category': 'professional',
                        'from_context': context_type
                    }
                )

                relation = EntityRelation(
                    source_entity=person,
                    target_entity=company_entity,
                    relation_type="works_at",
                    confidence=0.9,
                    context=f"From {context_type} context",
                    metadata={
                        'relationship_category': 'professional',
                        'inferred_from': 'participant_context'
                    }
                )
                relations.append(relation)

            if context.get('job_title'):
                # Create a job title entity
                job_title_entity = ExtractedEntity(
                    type=EntityType.job_title,
                    value=context['job_title'],
                    normalized_value=context['job_title'],
                    confidence=0.9,
                    source_method='linkedin_context',
                    metadata={
                        'entity_category': 'professional',
                        'from_context': context_type
                    }
                )

                relation = EntityRelation(
                    source_entity=person,
                    target_entity=job_title_entity,
                    relation_type="has_job_title",
                    confidence=0.9,
                    context=f"From {context_type} context",
                    metadata={
                        'relationship_category': 'professional',
                        'inferred_from': 'participant_context'
                    }
                )
                relations.append(relation)

        return relations

    def _classify_opportunity_type(self, opportunity: str) -> str:
        """Classify the type of business opportunity."""
        opportunity_lower = opportunity.lower()

        if opportunity_lower in ['investment', 'funding', 'acquisition', 'merger']:
            return 'financial'
        elif opportunity_lower in ['partnership', 'collaboration', 'joint venture', 'strategic alliance']:
            return 'partnership'
        elif opportunity_lower in ['contract', 'deal', 'proposal']:
            return 'commercial'
        elif opportunity_lower in ['meeting', 'conference', 'presentation', 'pitch']:
            return 'networking'
        else:
            return 'general'

    def _classify_skill_type(self, skill: str) -> str:
        """Classify the type of professional skill."""
        skill_lower = skill.lower()

        technical_skills = ['python', 'java', 'javascript', 'react',
                            'angular', 'node.js', 'sql', 'aws', 'azure', 'docker', 'kubernetes']
        if skill_lower in technical_skills:
            return 'technical'

        analytical_skills = ['data analysis',
                             'machine learning', 'artificial intelligence']
        if skill_lower in analytical_skills:
            return 'analytical'

        management_skills = ['project management',
                             'leadership', 'team management', 'strategic planning']
        if skill_lower in management_skills:
            return 'management'

        return 'soft_skill'

    def _get_context(self, text: str, start: int, end: int, window: int = 30) -> str:
        """Get context around an entity mention."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]

    def _calculate_confidence_stats(self, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """Calculate confidence statistics for extracted entities."""
        if not entities:
            return {}

        confidences = [e.confidence for e in entities]

        return {
            'total_entities': len(entities),
            'avg_confidence': sum(confidences) / len(confidences),
            'min_confidence': min(confidences),
            'max_confidence': max(confidences),
            'high_confidence_count': len([c for c in confidences if c >= 0.8]),
            'medium_confidence_count': len([c for c in confidences if 0.5 <= c < 0.8]),
            'low_confidence_count': len([c for c in confidences if c < 0.5])
        }


# Global LinkedIn entity extractor instance
_linkedin_entity_extractor = None


async def get_linkedin_entity_extractor() -> LinkedInEntityExtractor:
    """Get the global LinkedIn entity extractor instance."""
    global _linkedin_entity_extractor
    if _linkedin_entity_extractor is None:
        _linkedin_entity_extractor = LinkedInEntityExtractor()
    return _linkedin_entity_extractor
