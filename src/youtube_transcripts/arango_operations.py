"""
ArangoDB Operations for YouTube Transcripts
Module: arango_operations.py
Description: Implementation of arango operations functionality

This module contains the main operations for storing, searching, and analyzing
YouTube transcripts using ArangoDB's graph capabilities.

External Dependencies:
- python-arango: ArangoDB Python driver
- arangodb.core: Granger's ArangoDB utilities (optional)
"""

import hashlib
from datetime import datetime
from typing import Any

from arango.database import StandardDatabase

# Import Granger's search utilities if available
try:
    from arangodb.core.search import hybrid_search as granger_hybrid_search
    from arangodb.core.search import semantic_search as granger_semantic_search
    from arangodb.core.utils.embedding_utils import get_embedding
    GRANGER_ARANGO = True
except ImportError:
    GRANGER_ARANGO = False

    # Fallback implementations
    async def get_embedding(text: str) -> list[float]:
        """Fallback embedding function"""
        # Simple hash-based pseudo-embedding for testing
        hash_val = hashlib.sha256(text.encode()).hexdigest()
        return [float(int(hash_val[i:i+2], 16)) / 255 for i in range(0, 64, 2)]


class YouTubeTranscriptOperations:
    """Operations for YouTube transcript data in ArangoDB"""

    def __init__(self, db: StandardDatabase, collections: dict[str, str],
                 edge_collections: dict[str, str]):
        """Initialize with database and collection names"""
        self.db = db
        self.collections = collections
        self.edge_collections = edge_collections

    async def store_transcript(self, video_data: dict[str, Any]) -> str:
        """
        Store a transcript and its relationships in the graph
        
        Args:
            video_data: Dictionary containing transcript data
            
        Returns:
            Document ID of the stored transcript
        """
        # Extract base transcript data
        transcript_doc = {
            '_key': video_data['video_id'],
            'video_id': video_data['video_id'],
            'title': video_data.get('title', ''),
            'channel_id': video_data.get('channel_id', ''),
            'channel_name': video_data.get('channel_name', ''),
            'content': video_data.get('content', ''),
            'duration_seconds': video_data.get('duration_seconds', 0),
            'fetched_at': video_data.get('fetched_at', datetime.utcnow().isoformat()),
            'view_count': video_data.get('view_count', 0),
            'like_count': video_data.get('like_count', 0),
            'comment_count': video_data.get('comment_count', 0),
            'upload_date': video_data.get('upload_date', ''),
            'description': video_data.get('description', ''),
            'tags': video_data.get('tags', []),
            'embedding': await get_embedding(
                f"{video_data.get('title', '')} {video_data.get('content', '')[:500]}"
            )
        }

        # Store transcript
        transcripts = self.db.collection(self.collections['transcripts'])
        transcript = transcripts.insert(transcript_doc, overwrite=True)
        transcript_id = transcript['_id']

        # Store channel if not exists
        await self._store_channel(video_data)

        # Extract and store citations
        if 'citations' in video_data:
            await self._store_citations(transcript_id, video_data['citations'])

        # Extract and store speakers
        if 'speakers' in video_data:
            await self._store_speakers(transcript_id, video_data['speakers'])

        # Extract and store entities
        if 'entities' in video_data:
            await self._store_entities(transcript_id, video_data['entities'])

        # Extract and store claims
        if 'claims' in video_data:
            await self._store_claims(transcript_id, video_data['claims'])

        return transcript_id

    async def _store_channel(self, video_data: dict[str, Any]):
        """Store channel information"""
        if not video_data.get('channel_id'):
            return

        channel_doc = {
            '_key': video_data['channel_id'],
            'channel_id': video_data['channel_id'],
            'name': video_data.get('channel_name', ''),
            'handle': video_data.get('channel_handle', ''),
            'description': video_data.get('channel_description', ''),
            'subscriber_count': video_data.get('channel_subscribers', 0)
        }

        channels = self.db.collection(self.collections['channels'])
        channels.insert(channel_doc, overwrite=True)

    async def _store_citations(self, transcript_id: str, citations: list[dict[str, Any]]):
        """Store citations and relationships"""
        citations_coll = self.db.collection(self.collections['citations'])
        cites_edge = self.db.collection(self.edge_collections['cites'])

        for citation in citations:
            # Create unique key for citation
            citation_key = hashlib.md5(
                f"{citation.get('paper_title', '')}_{citation.get('authors', [])}".encode()
            ).hexdigest()[:12]

            citation_doc = {
                '_key': citation_key,
                'paper_title': citation.get('paper_title', ''),
                'authors': citation.get('authors', []),
                'year': citation.get('year'),
                'arxiv_id': citation.get('arxiv_id'),
                'doi': citation.get('doi'),
                'venue': citation.get('venue'),
                'timestamp': citation.get('timestamp', 0),
                'context': citation.get('context', '')
            }

            # Insert citation
            citation_result = citations_coll.insert(citation_doc, overwrite=True)

            # Create edge from transcript to citation
            edge_doc = {
                '_from': transcript_id,
                '_to': citation_result['_id'],
                'timestamp': citation.get('timestamp', 0),
                'context': citation.get('context', '')
            }
            cites_edge.insert(edge_doc, overwrite=True)

    async def _store_speakers(self, transcript_id: str, speakers: list[dict[str, Any]]):
        """Store speakers and relationships"""
        speakers_coll = self.db.collection(self.collections['speakers'])
        speaks_edge = self.db.collection(self.edge_collections['speaks_in'])

        for speaker in speakers:
            speaker_key = hashlib.md5(
                f"{speaker.get('name', 'Unknown')}_{speaker.get('channel_id', '')}".encode()
            ).hexdigest()[:12]

            speaker_doc = {
                '_key': speaker_key,
                'name': speaker.get('name', 'Unknown'),
                'role': speaker.get('role', 'speaker'),
                'channel_id': speaker.get('channel_id'),
                'affiliation': speaker.get('affiliation')
            }

            speaker_result = speakers_coll.insert(speaker_doc, overwrite=True)

            # Create edge from speaker to transcript
            edge_doc = {
                '_from': speaker_result['_id'],
                '_to': transcript_id,
                'segments': speaker.get('segments', [])
            }
            speaks_edge.insert(edge_doc, overwrite=True)

    async def _store_entities(self, transcript_id: str, entities: list[dict[str, Any]]):
        """Store named entities and relationships"""
        entities_coll = self.db.collection(self.collections['entities'])
        mentions_edge = self.db.collection(self.edge_collections['mentions'])

        for entity in entities:
            entity_key = hashlib.md5(
                f"{entity.get('name', '')}_{entity.get('type', '')}".encode()
            ).hexdigest()[:12]

            entity_doc = {
                '_key': entity_key,
                'name': entity.get('name', ''),
                'type': entity.get('type', ''),
                'description': entity.get('description', ''),
                'wikipedia_url': entity.get('wikipedia_url'),
                'aliases': entity.get('aliases', [])
            }

            entity_result = entities_coll.insert(entity_doc, overwrite=True)

            # Create edge from transcript to entity
            edge_doc = {
                '_from': transcript_id,
                '_to': entity_result['_id'],
                'mentions': entity.get('mentions', []),
                'sentiment': entity.get('sentiment')
            }
            mentions_edge.insert(edge_doc, overwrite=True)

    async def _store_claims(self, transcript_id: str, claims: list[dict[str, Any]]):
        """Store claims and relationships"""
        claims_coll = self.db.collection(self.collections['claims'])
        supports_edge = self.db.collection(self.edge_collections['supports'])
        contradicts_edge = self.db.collection(self.edge_collections['contradicts'])

        for claim in claims:
            claim_key = hashlib.md5(claim.get('text', '').encode()).hexdigest()[:12]

            claim_doc = {
                '_key': claim_key,
                'text': claim.get('text', ''),
                'confidence': claim.get('confidence', 0.5),
                'evidence': claim.get('evidence', []),
                'timestamp': claim.get('timestamp', 0)
            }

            claim_result = claims_coll.insert(claim_doc, overwrite=True)

            # Create relationship based on stance
            if claim.get('stance') == 'supports':
                edge_doc = {
                    '_from': transcript_id,
                    '_to': claim_result['_id'],
                    'confidence': claim.get('confidence', 0.5)
                }
                supports_edge.insert(edge_doc, overwrite=True)
            elif claim.get('stance') == 'contradicts':
                edge_doc = {
                    '_from': transcript_id,
                    '_to': claim_result['_id'],
                    'confidence': claim.get('confidence', 0.5)
                }
                contradicts_edge.insert(edge_doc, overwrite=True)

    async def hybrid_search(self, query: str, limit: int = 10,
                          filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Perform hybrid search combining full-text and semantic search
        
        Args:
            query: Search query
            limit: Maximum results
            filters: Optional filters (channel, date_range, etc.)
            
        Returns:
            List of matching transcripts with scores
        """
        if GRANGER_ARANGO:
            # Use Granger's hybrid search
            return await granger_hybrid_search(
                self.db,
                self.collections['transcripts'],
                query,
                limit=limit,
                filters=filters
            )

        # Fallback implementation
        collection = self.db.collection(self.collections['transcripts'])

        # Build AQL query
        aql = """
        FOR doc IN @@collection
        """

        bind_vars = {'@collection': self.collections['transcripts']}

        # Add filters
        filter_conditions = []
        if filters:
            if 'channel' in filters:
                filter_conditions.append("doc.channel_name == @channel")
                bind_vars['channel'] = filters['channel']
            if 'after_date' in filters:
                filter_conditions.append("doc.fetched_at >= @after_date")
                bind_vars['after_date'] = filters['after_date']

        # Add search condition
        filter_conditions.append(
            "(CONTAINS(LOWER(doc.title), LOWER(@query)) OR "
            "CONTAINS(LOWER(doc.content), LOWER(@query)))"
        )
        bind_vars['query'] = query

        if filter_conditions:
            aql += " FILTER " + " AND ".join(filter_conditions)

        aql += """
        LIMIT @limit
        RETURN {
            video_id: doc.video_id,
            title: doc.title,
            channel_name: doc.channel_name,
            content: SUBSTRING(doc.content, 0, 500),
            fetched_at: doc.fetched_at,
            score: 1.0
        }
        """
        bind_vars['limit'] = limit

        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
        return list(cursor)

    async def get_citation_network(self, video_id: str, depth: int = 2) -> dict[str, Any]:
        """
        Get citation network for a video
        
        Args:
            video_id: Video ID
            depth: Traversal depth
            
        Returns:
            Citation network graph
        """
        aql = """
        FOR v, e, p IN 0..@depth ANY @start_vertex 
        GRAPH 'youtube_knowledge_graph'
        OPTIONS {uniqueVertices: 'global', uniqueEdges: 'global'}
        FILTER IS_SAME_COLLECTION('youtube_citations', v) OR 
               IS_SAME_COLLECTION('youtube_transcripts', v)
        RETURN {vertex: v, edge: e, path: p}
        """

        bind_vars = {
            'start_vertex': f"{self.collections['transcripts']}/{video_id}",
            'depth': depth
        }

        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
        results = list(cursor)

        # Build network structure
        nodes = {}
        edges = []

        for result in results:
            vertex = result['vertex']
            if vertex:
                nodes[vertex['_id']] = {
                    'id': vertex['_id'],
                    'type': 'citation' if 'paper_title' in vertex else 'transcript',
                    'label': vertex.get('paper_title', vertex.get('title', '')),
                    'data': vertex
                }

            edge = result['edge']
            if edge:
                edges.append({
                    'from': edge['_from'],
                    'to': edge['_to'],
                    'type': edge.get('_id', '').split('/')[0]
                })

        return {
            'nodes': list(nodes.values()),
            'edges': edges
        }

    async def find_related_videos(self, video_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Find videos related by citations, speakers, or entities"""
        aql = """
        LET target_video = DOCUMENT(@transcript_id)
        
        // Find videos with shared citations
        LET shared_citations = (
            FOR v1, e1, v2, e2 IN 2 ANY target_video
            GRAPH 'youtube_knowledge_graph'
            FILTER IS_SAME_COLLECTION('youtube_transcripts', v2)
            FILTER v2._key != target_video._key
            FILTER IS_SAME_COLLECTION('youtube_cites', e1)
            RETURN DISTINCT v2
        )
        
        // Find videos with shared speakers
        LET shared_speakers = (
            FOR v1, e1, v2, e2 IN 2 ANY target_video
            GRAPH 'youtube_knowledge_graph'
            FILTER IS_SAME_COLLECTION('youtube_transcripts', v2)
            FILTER v2._key != target_video._key
            FILTER IS_SAME_COLLECTION('youtube_speaks_in', e1)
            RETURN DISTINCT v2
        )
        
        // Combine and score
        FOR video IN UNION_DISTINCT(shared_citations, shared_speakers)
        COLLECT v = video WITH COUNT INTO score
        SORT score DESC
        LIMIT @limit
        RETURN {
            video_id: v.video_id,
            title: v.title,
            channel_name: v.channel_name,
            similarity_score: score,
            fetched_at: v.fetched_at
        }
        """

        bind_vars = {
            'transcript_id': f"{self.collections['transcripts']}/{video_id}",
            'limit': limit
        }

        cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
        return list(cursor)
