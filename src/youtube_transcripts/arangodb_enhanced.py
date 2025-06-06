"""
Enhanced ArangoDB Integration for YouTube Transcripts
Implements advanced features using Granger's utilities
Module: arangodb_enhanced.py
Description: Implementation of arangodb enhanced functionality

This module provides:
- Contradiction detection
- Temporal queries
- Cross-encoder reranking
- Community detection
- Memory bank integration

External Dependencies:
- arangodb.core: Granger's utilities
- litellm: For LLM-based analysis

Example Usage:
>>> from youtube_transcripts.arangodb_enhanced import EnhancedYouTubeGraph
>>> graph = EnhancedYouTubeGraph()
>>> contradictions = await graph.find_contradictions("VERL scales infinitely")
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# Import Granger's utilities
try:
    from arangodb.core.graph.community_detection import detect_communities
    from arangodb.core.graph.contradiction_detector import ContradictionDetector
    from arangodb.core.graph.entity_resolution import EntityResolver
    from arangodb.core.graph.relationship_extraction import RelationshipExtractor
    from arangodb.core.memory.memory_agent import MemoryAgent
    from arangodb.core.models import (
        ContradictionAnalysis,
        EntityReference,
        RelationshipProposal,
        SearchConfig,
        SearchMethod,
        SearchResult,
        TemporalEntity,
    )
    from arangodb.core.search.cross_encoder_reranking import rerank_results
    from arangodb.core.search.hybrid_search import hybrid_search
    GRANGER_AVAILABLE = True
except ImportError:
    GRANGER_AVAILABLE = False
    print("Warning: Granger utilities not available for enhanced features")

from .arango_integration import YouTubeTranscriptGraph


@dataclass
class ContradictionResult:
    """Result of contradiction detection"""
    claim: str
    contradicting_video: dict[str, Any]
    contradiction_text: str
    confidence: float
    reasoning: str
    temporal_context: str | None = None


@dataclass
class CommunityCluster:
    """Represents a community of related videos/topics"""
    cluster_id: str
    name: str
    videos: list[str]
    topics: list[str]
    central_figures: list[str]
    size: int


class EnhancedYouTubeGraph(YouTubeTranscriptGraph):
    """
    Enhanced YouTube graph with advanced Granger features
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if GRANGER_AVAILABLE:
            self.entity_resolver = EntityResolver(self.db)
            self.relationship_extractor = RelationshipExtractor(self.db)
            self.contradiction_detector = ContradictionDetector(self.db)
            self.memory_agent = MemoryAgent(self.db)
        else:
            print("Enhanced features not available without Granger utilities")

    async def enhanced_search(self, query: str,
                            use_cross_encoder: bool = True,
                            search_methods: list[SearchMethod] | None = None,
                            weights: dict[str, float] | None = None,
                            limit: int = 10) -> list[SearchResult]:
        """
        Enhanced search using Granger's hybrid search with reranking
        
        Args:
            query: Search query
            use_cross_encoder: Whether to rerank results
            search_methods: Methods to use (BM25, SEMANTIC, etc.)
            weights: Weight for each method
            limit: Maximum results
            
        Returns:
            List of search results with enhanced scoring
        """
        if not GRANGER_AVAILABLE:
            # Fallback to basic search
            return await self.hybrid_search(query, limit)

        # Default search configuration
        if search_methods is None:
            search_methods = [SearchMethod.BM25, SearchMethod.SEMANTIC]

        if weights is None:
            weights = {"bm25": 0.3, "semantic": 0.7}

        # Create search config
        config = SearchConfig(
            methods=search_methods,
            weights=weights,
            min_score=0.1
        )

        # Perform hybrid search
        results = await hybrid_search(
            db=self.db,
            query_text=query,
            collections=[self.collections['transcripts']],
            search_config=config,
            limit=limit * 2 if use_cross_encoder else limit  # Get more for reranking
        )

        # Apply cross-encoder reranking if requested
        if use_cross_encoder and results.get('results'):
            reranked = await rerank_results(
                query=query,
                results=results['results'],
                top_k=limit,
                model_name='cross-encoder/ms-marco-MiniLM-L-6-v2'
            )
            results['results'] = reranked
            results['reranked'] = True

        return results

    async def find_contradictions(self, claim: str,
                                temporal_window: timedelta | None = None,
                                min_confidence: float = 0.7) -> list[ContradictionResult]:
        """
        Find videos that contradict a given claim
        
        Args:
            claim: The claim to check
            temporal_window: Only check videos within this time window
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of contradictions found
        """
        if not GRANGER_AVAILABLE:
            return []

        # Search for relevant videos
        search_results = await self.enhanced_search(claim, limit=20)

        contradictions = []

        for result in search_results.get('results', []):
            # Get full transcript
            transcript = result.get('transcript', '')

            # Use Granger's contradiction detector
            analysis = await self.contradiction_detector.analyze(
                claim=claim,
                context=transcript,
                metadata={
                    'video_id': result.get('video_id'),
                    'upload_date': result.get('upload_date')
                }
            )

            if analysis.is_contradiction and analysis.confidence >= min_confidence:
                # Check temporal constraint
                if temporal_window:
                    upload_date = datetime.fromisoformat(result.get('upload_date', ''))
                    if datetime.now() - upload_date > temporal_window:
                        continue

                contradictions.append(ContradictionResult(
                    claim=claim,
                    contradicting_video={
                        'video_id': result.get('video_id'),
                        'title': result.get('title'),
                        'channel': result.get('channel_name'),
                        'url': f"https://youtube.com/watch?v={result.get('video_id')}"
                    },
                    contradiction_text=analysis.contradiction_text,
                    confidence=analysis.confidence,
                    reasoning=analysis.reasoning,
                    temporal_context=f"Uploaded on {result.get('upload_date')}"
                ))

        return sorted(contradictions, key=lambda x: x.confidence, reverse=True)

    async def extract_and_link_entities(self, video_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract entities and create relationships using Granger utilities
        
        Args:
            video_data: Video information including transcript
            
        Returns:
            Enhanced video data with linked entities
        """
        if not GRANGER_AVAILABLE:
            return video_data

        transcript = video_data.get('transcript', '')

        # Extract entities
        entities = await self.entity_resolver.extract_entities(transcript)

        # Resolve entity references (link similar entities)
        resolved_entities = []
        for entity in entities:
            resolved = await self.entity_resolver.resolve(
                entity_text=entity.text,
                entity_type=entity.type,
                context=transcript
            )
            resolved_entities.append(resolved)

        # Extract relationships between entities
        relationships = await self.relationship_extractor.extract_relationships(
            text=transcript,
            entities=resolved_entities
        )

        # Store entities and relationships
        for entity in resolved_entities:
            await self._store_resolved_entity(entity, video_data['video_id'])

        for relationship in relationships:
            await self._store_relationship(relationship, video_data['video_id'])

        # Add to video data
        video_data['resolved_entities'] = resolved_entities
        video_data['relationships'] = relationships

        return video_data

    async def detect_topic_communities(self, min_community_size: int = 5) -> list[CommunityCluster]:
        """
        Detect communities of related videos using graph algorithms
        
        Args:
            min_community_size: Minimum videos for a valid community
            
        Returns:
            List of detected communities
        """
        if not GRANGER_AVAILABLE:
            return []

        # Detect communities using Louvain algorithm
        communities = await detect_communities(
            db=self.db,
            graph_name='youtube_knowledge_graph',
            algorithm='louvain',
            min_size=min_community_size
        )

        clusters = []

        for comm_id, community in enumerate(communities):
            # Get videos in community
            video_ids = [node for node in community if node.startswith('video_')]

            if len(video_ids) < min_community_size:
                continue

            # Analyze community to extract topics and figures
            topics = await self._extract_community_topics(video_ids)
            figures = await self._extract_central_figures(video_ids)

            # Generate community name based on topics
            name = self._generate_community_name(topics)

            clusters.append(CommunityCluster(
                cluster_id=f"cluster_{comm_id}",
                name=name,
                videos=video_ids,
                topics=topics[:10],  # Top 10 topics
                central_figures=figures[:5],  # Top 5 figures
                size=len(video_ids)
            ))

        return sorted(clusters, key=lambda x: x.size, reverse=True)

    async def track_search_interaction(self, user_id: str, query: str,
                                     selected_results: list[str],
                                     search_metadata: dict[str, Any] | None = None):
        """
        Track user search interactions for personalization
        
        Args:
            user_id: User identifier
            query: Search query
            selected_results: Video IDs that were clicked/selected
            search_metadata: Additional metadata about the search
        """
        if not GRANGER_AVAILABLE:
            return

        # Store search interaction in memory bank
        await self.memory_agent.store_memory(
            user_message=query,
            agent_response=f"Found {len(selected_results)} relevant videos",
            metadata={
                'user_id': user_id,
                'selected_videos': selected_results,
                'search_type': 'youtube_transcript_search',
                **(search_metadata or {})
            }
        )

        # Update user preferences based on selections
        await self._update_user_preferences(user_id, selected_results)

    async def get_temporal_evolution(self, topic: str,
                                   time_range: tuple[datetime, datetime],
                                   granularity: str = 'month') -> dict[str, Any]:
        """
        Track how a topic evolved over time
        
        Args:
            topic: Topic to track
            time_range: Start and end dates
            granularity: 'day', 'week', 'month', 'year'
            
        Returns:
            Temporal evolution data
        """
        aql = """
        FOR video IN youtube_transcripts
            FILTER video.upload_date >= @start_date
            FILTER video.upload_date <= @end_date
            FILTER CONTAINS(LOWER(video.transcript), LOWER(@topic))
            COLLECT period = DATE_FORMAT(video.upload_date, @format)
            WITH COUNT INTO video_count
            RETURN {
                period: period,
                count: video_count
            }
        """

        # Format string based on granularity
        format_map = {
            'day': '%Y-%m-%d',
            'week': '%Y-W%V',
            'month': '%Y-%m',
            'year': '%Y'
        }

        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                'start_date': time_range[0].isoformat(),
                'end_date': time_range[1].isoformat(),
                'topic': topic,
                'format': format_map.get(granularity, '%Y-%m')
            }
        )

        evolution_data = list(cursor)

        # Analyze changes in discussion
        changes = await self._analyze_topic_changes(topic, evolution_data)

        return {
            'topic': topic,
            'time_range': {
                'start': time_range[0].isoformat(),
                'end': time_range[1].isoformat()
            },
            'granularity': granularity,
            'data_points': evolution_data,
            'total_videos': sum(d['count'] for d in evolution_data),
            'peak_period': max(evolution_data, key=lambda x: x['count']) if evolution_data else None,
            'changes': changes
        }

    async def _store_resolved_entity(self, entity: EntityReference, video_id: str):
        """Store resolved entity with enhanced metadata"""
        entity_doc = {
            '_key': entity.id,
            'text': entity.text,
            'type': entity.type,
            'canonical_form': entity.canonical_form,
            'aliases': entity.aliases,
            'confidence': entity.confidence,
            'metadata': entity.metadata
        }

        entities_coll = self.db.collection(self.collections['entities'])
        entities_coll.insert(entity_doc, overwrite=True)

        # Create edge to video
        edge_doc = {
            '_from': f"{self.collections['transcripts']}/{video_id}",
            '_to': f"{self.collections['entities']}/{entity.id}",
            'positions': entity.positions,
            'confidence': entity.confidence
        }

        mentions_coll = self.db.collection(self.edge_collections['mentions'])
        mentions_coll.insert(edge_doc, overwrite=True)

    async def _store_relationship(self, relationship: RelationshipProposal, video_id: str):
        """Store entity relationship"""
        edge_doc = {
            '_from': f"{self.collections['entities']}/{relationship.entity1_id}",
            '_to': f"{self.collections['entities']}/{relationship.entity2_id}",
            'type': relationship.relationship_type,
            'confidence': relationship.confidence,
            'evidence': relationship.evidence,
            'video_id': video_id
        }

        related_coll = self.db.collection(self.edge_collections['related_to'])
        related_coll.insert(edge_doc, overwrite=True)

    async def _extract_community_topics(self, video_ids: list[str]) -> list[str]:
        """Extract common topics from a community of videos"""
        aql = """
        FOR video_id IN @video_ids
            FOR entity IN 1..1 OUTBOUND CONCAT(@transcripts_coll, '/', video_id) youtube_mentions
                FILTER entity.type IN ['TECHNICAL_TERM', 'ML_CONCEPT', 'TOPIC']
                COLLECT topic = entity.text WITH COUNT INTO frequency
                SORT frequency DESC
                RETURN topic
        """

        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                'video_ids': video_ids,
                'transcripts_coll': self.collections['transcripts']
            }
        )

        return list(cursor)

    async def _extract_central_figures(self, video_ids: list[str]) -> list[str]:
        """Extract central figures from a community"""
        aql = """
        FOR video_id IN @video_ids
            FOR speaker IN 1..1 OUTBOUND CONCAT(@transcripts_coll, '/', video_id) youtube_speaks_in
                COLLECT name = speaker.name, affiliation = speaker.affiliation 
                WITH COUNT INTO appearances
                SORT appearances DESC
                RETURN CONCAT(name, ' (', affiliation, ')')
        """

        cursor = self.db.aql.execute(
            aql,
            bind_vars={
                'video_ids': video_ids,
                'transcripts_coll': self.collections['transcripts']
            }
        )

        return list(cursor)

    def _generate_community_name(self, topics: list[str]) -> str:
        """Generate descriptive name for community"""
        if not topics:
            return "General Discussion"

        # Take top 3 topics
        main_topics = topics[:3]
        return f"{', '.join(main_topics)} Community"

    async def _update_user_preferences(self, user_id: str, video_ids: list[str]):
        """Update user preferences based on video selections"""
        # This would update a user preferences collection
        # tracking topics, channels, speakers they're interested in
        pass

    async def _analyze_topic_changes(self, topic: str, evolution_data: list[dict]) -> dict[str, Any]:
        """Analyze how discussion of a topic changed over time"""
        if not evolution_data:
            return {}

        # Calculate trend
        counts = [d['count'] for d in evolution_data]
        if len(counts) > 1:
            trend = 'increasing' if counts[-1] > counts[0] else 'decreasing'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'volatility': self._calculate_volatility(counts),
            'growth_rate': (counts[-1] - counts[0]) / counts[0] if counts[0] > 0 else 0
        }

    def _calculate_volatility(self, values: list[int]) -> float:
        """Calculate volatility of a time series"""
        if len(values) < 2:
            return 0.0

        import statistics
        return statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) > 0 else 0.0


# Example usage
async def example_enhanced_usage():
    """Example of using enhanced features"""

    graph = EnhancedYouTubeGraph()

    # 1. Enhanced search with cross-encoder reranking
    print("=== Enhanced Search ===")
    results = await graph.enhanced_search(
        "VERL reinforcement learning",
        use_cross_encoder=True,
        weights={"bm25": 0.2, "semantic": 0.8}
    )

    if results.get('reranked'):
        print("Results were reranked using cross-encoder")

    # 2. Find contradictions
    print("\n=== Contradiction Detection ===")
    contradictions = await graph.find_contradictions(
        "VERL can only scale to 100 GPUs",
        temporal_window=timedelta(days=365)
    )

    for c in contradictions[:3]:
        print(f"Contradiction found in: {c.contradicting_video['title']}")
        print(f"Confidence: {c.confidence:.2f}")
        print(f"Reasoning: {c.reasoning}")

    # 3. Detect communities
    print("\n=== Community Detection ===")
    communities = await graph.detect_topic_communities(min_community_size=3)

    for community in communities[:3]:
        print(f"\nCommunity: {community.name}")
        print(f"Size: {community.size} videos")
        print(f"Main topics: {', '.join(community.topics[:5])}")
        print(f"Key figures: {', '.join(community.central_figures[:3])}")

    # 4. Track temporal evolution
    print("\n=== Temporal Evolution ===")
    evolution = await graph.get_temporal_evolution(
        topic="transformer",
        time_range=(datetime(2023, 1, 1), datetime(2024, 12, 31)),
        granularity='month'
    )

    print(f"Topic '{evolution['topic']}' appeared in {evolution['total_videos']} videos")
    print(f"Peak period: {evolution['peak_period']['period']} with {evolution['peak_period']['count']} videos")
    print(f"Trend: {evolution['changes']['trend']}")


if __name__ == "__main__":
    asyncio.run(example_enhanced_usage())
