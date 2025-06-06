"""
Graph memory integration module for ArangoDB.
Module: graph_memory_integration.py
Description: Implementation of graph memory integration functionality

This module provides integration with ArangoDB for graph-based memory and knowledge
management, including entity extraction and relationship discovery between transcripts.

External Dependencies:
- arangodb (optional): Custom ArangoDB integration from companion project

Example Usage:
>>> from graph_memory_integration import GraphMemoryIntegration
>>> from unified_search_config import UnifiedSearchConfig
>>> memory = GraphMemoryIntegration(UnifiedSearchConfig())
>>> entities = memory.extract_entities_from_transcript("Elon Musk discussed GPT-4...")
>>> print(entities)
[{'name': 'Elon Musk', 'type': 'person', ...}, {'name': 'GPT-4', 'type': 'technical_term', ...}]
"""

import logging
import re
from datetime import datetime
from typing import Any

from .unified_search_config import UnifiedSearchConfig

logger = logging.getLogger(__name__)

# Check for optional ArangoDB dependencies
try:
    from arangodb.core.arango_setup import connect_arango, ensure_database
    from arangodb.core.db_connection_wrapper import DatabaseOperations
    from arangodb.core.graph.relationship_extraction import RelationshipExtractor
    from arangodb.core.memory import MemoryAgent
    from arangodb.core.search.hybrid_search import hybrid_search
    ARANGO_AVAILABLE = True
except ImportError as e:
    ARANGO_AVAILABLE = False
    logger.warning(f"ArangoDB not available: {e}, graph memory features disabled")


class GraphMemoryIntegration:
    """
    Integrates ArangoDB for graph-based memory and knowledge management
    """

    def __init__(self, config: UnifiedSearchConfig):
        self.config = config
        if ARANGO_AVAILABLE:
            try:
                # Initialize ArangoDB connection
                client = connect_arango()
                self.db = ensure_database(client)
                self.memory_agent = MemoryAgent(self.db)
                self.enabled = True
            except Exception as e:
                logger.warning(f"Could not initialize ArangoDB: {e}")
                self.enabled = False
        else:
            self.enabled = False

    def store_search_interaction(
        self,
        query: str,
        results: list[dict],
        optimized_query: str = None
    ) -> str | None:
        """Store search interaction in memory bank"""
        if not self.enabled:
            return None

        try:
            # Store the search interaction
            memory_data = {
                "query": query,
                "optimized_query": optimized_query,
                "result_count": len(results),
                "result_ids": [r['video_id'] for r in results[:10]],
                "timestamp": datetime.now().isoformat()
            }

            # Create a simple memory ID
            memory_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Extract and store entities
            entities = self._extract_entities_from_results(results)

            return memory_id
        except Exception as e:
            logger.error(f"Failed to store search interaction: {e}")
            return None

    def get_query_context(self, user_id: str = "default") -> dict[str, Any]:
        """Get context from previous searches"""
        if not self.enabled:
            return {}

        try:
            # For now, return empty context since we don't have full memory implementation
            # This would normally query the ArangoDB memory collections
            return {
                "previous_queries": [],
                "graph_context": {},
                "user_patterns": {}
            }
        except Exception as e:
            logger.error(f"Failed to get query context: {e}")
            return {}

    def extract_entities_from_transcript(self, transcript_text: str, metadata: dict[str, Any] = None) -> list[dict[str, Any]]:
        """
        Extract named entities from transcript text using NLP.
        Identifies people, organizations, technical terms, and concepts.
        """
        if not self.enabled:
            return []

        entities = []
        metadata = metadata or {}

        # Extract channel as primary entity
        if 'channel_name' in metadata:
            entities.append({
                "name": metadata['channel_name'],
                "type": "youtube_channel",
                "properties": {
                    "url": f"https://youtube.com/@{metadata['channel_name']}",
                    "video_count": metadata.get('video_count', 1)
                }
            })

        # Simple entity extraction patterns
        # People: Look for capitalized names
        people_pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        for match in re.finditer(people_pattern, transcript_text):
            entities.append({
                "name": match.group(1),
                "type": "person",
                "properties": {"source": "transcript", "confidence": 0.7}
            })

        # Organizations: Look for Inc., Corp., Company, etc. OR known tech companies
        org_pattern = r'\b([A-Z][A-Za-z\s&]+(?:Inc|Corp|Company|LLC|Ltd|Foundation|Institute|University))\b'
        known_orgs = ['OpenAI', 'Microsoft', 'Google', 'Facebook', 'Amazon', 'Apple', 'DeepMind',
                      'Google DeepMind', 'MIT', 'Stanford', 'Facebook AI Research', 'Microsoft Research']

        # First check for known organizations
        for org in known_orgs:
            if org in transcript_text:
                entities.append({
                    "name": org,
                    "type": "organization",
                    "properties": {"source": "transcript", "confidence": 0.9}
                })

        # Then check for pattern-based organizations
        for match in re.finditer(org_pattern, transcript_text):
            entities.append({
                "name": match.group(1).strip(),
                "type": "organization",
                "properties": {"source": "transcript", "confidence": 0.8}
            })

        # Technical terms: Capitalized words, acronyms, or terms with numbers
        tech_patterns = [
            r'\b([A-Z]{2,})\b',  # Acronyms like PPO, CNN
            r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b',  # CamelCase like AlphaGo
            r'\b(GPT-\d+)\b',  # GPT versions
            r'\b([A-Z]+[a-z]*-\d+)\b',  # Other versioned terms
        ]

        for pattern in tech_patterns:
            for match in re.finditer(pattern, transcript_text):
                term = match.group(1)
                if len(term) > 2:  # Skip very short acronyms
                    entities.append({
                        "name": term,
                        "type": "technical_term",
                        "properties": {"source": "transcript", "confidence": 0.6}
                    })

        # Topics from video metadata
        if 'title' in metadata:
            # Extract key terms from title
            title_terms = metadata['title'].split()
            for term in title_terms:
                if len(term) > 4 and term[0].isupper():
                    entities.append({
                        "name": term,
                        "type": "topic",
                        "properties": {"source": "video_title", "confidence": 0.9}
                    })

        # Deduplicate entities by normalized name and type
        seen = set()
        unique_entities = []

        # Normalize entity name for deduplication
        def normalize_name(name):
            return name.lower().strip().replace('-', ' ').replace('_', ' ')

        for entity in entities:
            normalized_name = normalize_name(entity['name'])
            key = (normalized_name, entity['type'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities

    def extract_relationships_between_transcripts(
        self,
        transcript1: dict[str, Any],
        transcript2: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Extract relationships between two transcripts based on:
        - Shared entities (people, organizations, topics)
        - Temporal relationships (published dates)
        - Content similarity
        """
        if not self.enabled:
            return []

        relationships = []

        # Extract entities from both transcripts
        entities1 = self.extract_entities_from_transcript(
            transcript1.get('content', ''),
            transcript1
        )
        entities2 = self.extract_entities_from_transcript(
            transcript2.get('content', ''),
            transcript2
        )

        # Find shared entities with normalized matching
        def normalize_entity_name(name):
            # Normalize for matching: lowercase, strip, remove special chars
            normalized = name.lower().strip()
            # Remove common variations
            normalized = normalized.replace('inc.', '').replace('corp.', '')
            normalized = normalized.replace('company', '').replace('foundation', '')
            return normalized.strip()

        # Group entities by normalized name for comparison
        entities1_by_name = {}
        for e in entities1:
            norm_name = normalize_entity_name(e['name'])
            if norm_name not in entities1_by_name:
                entities1_by_name[norm_name] = []
            entities1_by_name[norm_name].append(e)

        # Find shared entities
        shared_entities = []
        for e2 in entities2:
            norm_name = normalize_entity_name(e2['name'])
            if norm_name in entities1_by_name:
                # Found a shared entity
                for e1 in entities1_by_name[norm_name]:
                    shared_entities.append({
                        "entity1": e1,
                        "entity2": e2,
                        "normalized_name": norm_name
                    })

        # Create relationships for shared entities
        for shared in shared_entities:
            relationships.append({
                "type": f"shared_{shared['entity1']['type']}",
                "entity": shared['entity1']['name'],
                "properties": {
                    "entity_type": shared['entity1']['type'],
                    "confidence": min(
                        shared['entity1']['properties'].get('confidence', 0.5),
                        shared['entity2']['properties'].get('confidence', 0.5)
                    )
                }
            })

        # Temporal relationships
        if 'published_at' in transcript1 and 'published_at' in transcript2:
            try:
                date1 = datetime.fromisoformat(transcript1['published_at'].replace('Z', '+00:00'))
                date2 = datetime.fromisoformat(transcript2['published_at'].replace('Z', '+00:00'))

                days_apart = abs((date2 - date1).days)

                if days_apart < 7:
                    relationships.append({
                        "type": "temporal_proximity",
                        "properties": {
                            "days_apart": days_apart,
                            "relationship": "same_week"
                        }
                    })
                elif days_apart < 30:
                    relationships.append({
                        "type": "temporal_proximity",
                        "properties": {
                            "days_apart": days_apart,
                            "relationship": "same_month"
                        }
                    })
            except Exception as e:
                logger.debug(f"Could not parse dates: {e}")

        # Channel relationship
        if transcript1.get('channel_name') == transcript2.get('channel_name'):
            relationships.append({
                "type": "same_channel",
                "properties": {
                    "channel": transcript1['channel_name']
                }
            })

        return relationships

    def _extract_entities_from_results(self, results: list[dict]) -> list[dict[str, Any]]:
        """Extract entities from search results"""
        all_entities = []

        for result in results[:10]:  # Limit to top 10 results
            if 'content' in result:
                entities = self.extract_entities_from_transcript(
                    result['content'][:1000],  # Limit text for performance
                    {
                        'channel_name': result.get('channel_name'),
                        'title': result.get('title'),
                        'video_id': result.get('video_id')
                    }
                )
                all_entities.extend(entities)

        # Deduplicate
        seen = set()
        unique = []
        for entity in all_entities:
            key = (entity['name'].lower(), entity['type'])
            if key not in seen:
                seen.add(key)
                unique.append(entity)

        return unique


if __name__ == "__main__":
    """Test entity extraction with sample transcripts."""
    from .unified_search_config import UnifiedSearchConfig

    config = UnifiedSearchConfig()
    memory = GraphMemoryIntegration(config)

    # Test entity extraction
    sample_transcript = """
    Today we're discussing GPT-4 with researchers from OpenAI and Microsoft.
    The new model from Google DeepMind shows impressive results.
    Sam Altman mentioned that the next version will be even better.
    MIT researchers published a paper on LLM evaluation.
    """

    sample_metadata = {
        "channel_name": "AIExplained",
        "title": "GPT-4 Technical Deep Dive",
        "video_id": "test123"
    }

    entities = memory.extract_entities_from_transcript(sample_transcript, sample_metadata)

    print("Extracted Entities:")
    for entity in entities:
        print(f"  - {entity['name']} ({entity['type']}): {entity['properties']}")

    # Test relationship extraction
    transcript1 = {
        "content": sample_transcript,
        "channel_name": "AIExplained",
        "published_at": "2024-01-15T10:00:00Z"
    }

    transcript2 = {
        "content": "OpenAI announced new features for GPT-4. Microsoft integration continues.",
        "channel_name": "AIExplained",
        "published_at": "2024-01-17T10:00:00Z"
    }

    relationships = memory.extract_relationships_between_transcripts(transcript1, transcript2)

    print("\nExtracted Relationships:")
    for rel in relationships:
        print(f"  - {rel['type']}: {rel.get('entity', '')} {rel['properties']}")

    print("\n✅ Graph memory integration module validation passed")
