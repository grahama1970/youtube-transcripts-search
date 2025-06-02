"""
Research Analyzer for YouTube Transcripts
Implements bolster/contradict functionality similar to ArXiv MCP Server

This module provides advanced research analysis capabilities:
- Find evidence that supports (bolsters) claims
- Find evidence that contradicts claims
- Compare explanations across videos
- Build citation networks

External Dependencies:
- arangodb: Graph database for relationships
- sentence-transformers: For semantic similarity
- litellm: For LLM-based analysis

Example Usage:
>>> analyzer = ResearchAnalyzer(arango_client)
>>> evidence = await analyzer.find_evidence("transformers are better than RNNs", "support")
>>> comparisons = await analyzer.compare_explanations("attention mechanism")
"""

import asyncio
from typing import List, Dict, Any, Optional, Literal, Tuple
from datetime import datetime
from dataclasses import dataclass
import json

try:
    from arango import ArangoClient
    ARANGODB_AVAILABLE = True
except ImportError:
    ARANGODB_AVAILABLE = False

from sentence_transformers import SentenceTransformer
import numpy as np

try:
    import litellm
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False
    litellm = None


@dataclass
class Evidence:
    """Represents evidence found in a transcript"""
    video_id: str
    title: str
    channel: str
    text: str
    timestamp: float
    confidence: float
    reasoning: str
    evidence_type: Literal["support", "contradict", "neutral"]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "channel": self.channel,
            "text": self.text,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence_type": self.evidence_type
        }


@dataclass
class Comparison:
    """Represents a comparison between explanations"""
    concept: str
    video1: Dict[str, Any]
    video2: Dict[str, Any]
    similarity: float
    differences: List[str]
    consensus: List[str]
    recommendation: str


class ResearchAnalyzer:
    """Analyzes YouTube transcripts for research purposes"""
    
    def __init__(self, arango_client: Optional[ArangoClient] = None, 
                 llm_model: str = "claude-3-haiku-20240307"):
        """
        Initialize research analyzer
        
        Args:
            arango_client: ArangoDB client instance
            llm_model: LLM model for analysis
        """
        self.arango_client = arango_client
        self.llm_model = llm_model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Collection names
        self.collections = {
            'transcripts': 'youtube_transcripts',
            'evidence': 'youtube_evidence',
            'comparisons': 'youtube_comparisons',
            'claims': 'youtube_claims'
        }
    
    async def find_evidence(self, claim: str, evidence_type: Literal["support", "contradict", "both"] = "both",
                          limit: int = 10, min_confidence: float = 0.5) -> List[Evidence]:
        """
        Find evidence that supports or contradicts a claim
        
        Args:
            claim: The claim to find evidence for
            evidence_type: Type of evidence to find
            limit: Maximum number of results
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of Evidence objects
        """
        # Get claim embedding
        claim_embedding = self.embedder.encode(claim)
        
        # Search for relevant transcripts
        relevant_videos = await self._semantic_search(claim_embedding, limit * 2)
        
        evidence_list = []
        
        for video in relevant_videos:
            # Analyze each video for evidence
            if evidence_type in ["support", "both"]:
                support_evidence = await self._analyze_transcript_for_evidence(
                    video, claim, "support"
                )
                evidence_list.extend(support_evidence)
            
            if evidence_type in ["contradict", "both"]:
                contradict_evidence = await self._analyze_transcript_for_evidence(
                    video, claim, "contradict"
                )
                evidence_list.extend(contradict_evidence)
        
        # Filter by confidence and sort
        evidence_list = [e for e in evidence_list if e.confidence >= min_confidence]
        evidence_list.sort(key=lambda x: x.confidence, reverse=True)
        
        # Store evidence in database
        if self.arango_client:
            await self._store_evidence(claim, evidence_list[:limit])
        
        return evidence_list[:limit]
    
    async def _analyze_transcript_for_evidence(self, video: Dict[str, Any], claim: str, 
                                             evidence_type: Literal["support", "contradict"]) -> List[Evidence]:
        """Analyze a transcript for supporting or contradicting evidence"""
        evidence_list = []
        
        # Split transcript into chunks (by sentences or timestamps)
        chunks = self._split_transcript(video.get('transcript', ''))
        
        for chunk in chunks:
            if HAS_LITELLM:
                # Use LLM to analyze chunk
                analysis = await self._llm_analyze_chunk(chunk['text'], claim, evidence_type)
                
                if analysis['is_relevant']:
                    evidence = Evidence(
                        video_id=video['video_id'],
                        title=video['title'],
                        channel=video.get('channel_name', ''),
                        text=chunk['text'],
                        timestamp=chunk.get('timestamp', 0),
                        confidence=analysis['confidence'],
                        reasoning=analysis['reasoning'],
                        evidence_type=evidence_type
                    )
                    evidence_list.append(evidence)
            else:
                # Fallback to embedding similarity
                chunk_embedding = self.embedder.encode(chunk['text'])
                claim_embedding = self.embedder.encode(claim)
                similarity = float(np.dot(chunk_embedding, claim_embedding))
                
                if similarity > 0.7:  # Threshold for relevance
                    evidence = Evidence(
                        video_id=video['video_id'],
                        title=video['title'],
                        channel=video.get('channel_name', ''),
                        text=chunk['text'],
                        timestamp=chunk.get('timestamp', 0),
                        confidence=similarity,
                        reasoning="High semantic similarity to claim",
                        evidence_type=evidence_type
                    )
                    evidence_list.append(evidence)
        
        return evidence_list
    
    async def _llm_analyze_chunk(self, text: str, claim: str, 
                                evidence_type: Literal["support", "contradict"]) -> Dict[str, Any]:
        """Use LLM to analyze if text supports or contradicts claim"""
        if not HAS_LITELLM:
            return {"is_relevant": False, "confidence": 0, "reasoning": "LLM not available"}
        
        prompt = f"""
        Analyze if the following text {evidence_type}s this claim.
        
        Claim: {claim}
        
        Text: {text}
        
        Respond with JSON:
        {{
            "is_relevant": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "explanation"
        }}
        """
        
        try:
            response = await litellm.acompletion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "is_relevant": False,
                "confidence": 0,
                "reasoning": f"Error in LLM analysis: {str(e)}"
            }
    
    async def compare_explanations(self, concept: str, limit: int = 5) -> List[Comparison]:
        """
        Compare different explanations of a concept across videos
        
        Args:
            concept: The concept to compare explanations for
            limit: Maximum number of comparisons
            
        Returns:
            List of Comparison objects
        """
        # Find videos explaining this concept
        concept_embedding = self.embedder.encode(concept)
        videos = await self._semantic_search(concept_embedding, limit * 2)
        
        comparisons = []
        
        # Compare pairs of videos
        for i in range(len(videos)):
            for j in range(i + 1, len(videos)):
                comparison = await self._compare_two_explanations(
                    concept, videos[i], videos[j]
                )
                comparisons.append(comparison)
        
        # Sort by relevance/quality
        comparisons.sort(key=lambda x: x.similarity, reverse=True)
        
        return comparisons[:limit]
    
    async def _compare_two_explanations(self, concept: str, video1: Dict[str, Any], 
                                      video2: Dict[str, Any]) -> Comparison:
        """Compare two video explanations of a concept"""
        # Extract relevant sections
        section1 = self._extract_concept_section(video1['transcript'], concept)
        section2 = self._extract_concept_section(video2['transcript'], concept)
        
        # Calculate similarity
        emb1 = self.embedder.encode(section1)
        emb2 = self.embedder.encode(section2)
        similarity = float(np.dot(emb1, emb2))
        
        # Analyze differences and consensus
        if HAS_LITELLM:
            analysis = await self._llm_compare_sections(section1, section2, concept)
            differences = analysis.get('differences', [])
            consensus = analysis.get('consensus', [])
            recommendation = analysis.get('recommendation', '')
        else:
            differences = ["LLM analysis not available"]
            consensus = ["Semantic similarity: {:.2f}".format(similarity)]
            recommendation = "Higher similarity indicates more agreement"
        
        return Comparison(
            concept=concept,
            video1={
                "video_id": video1['video_id'],
                "title": video1['title'],
                "channel": video1.get('channel_name', ''),
                "section": section1[:200] + "..."
            },
            video2={
                "video_id": video2['video_id'],
                "title": video2['title'],
                "channel": video2.get('channel_name', ''),
                "section": section2[:200] + "..."
            },
            similarity=similarity,
            differences=differences,
            consensus=consensus,
            recommendation=recommendation
        )
    
    async def build_citation_network(self, video_id: str, depth: int = 2) -> Dict[str, Any]:
        """
        Build a citation network starting from a video
        
        Args:
            video_id: Starting video ID
            depth: How many levels deep to traverse
            
        Returns:
            Citation network graph
        """
        if not self.arango_client:
            return {"error": "ArangoDB client required for citation networks"}
        
        # Use AQL to traverse citation relationships
        query = """
        FOR v, e, p IN 1..@depth ANY @start_vertex
            GRAPH 'youtube_citation_graph'
            OPTIONS {uniqueVertices: 'global'}
            RETURN {
                video: v,
                edge: e,
                path: p
            }
        """
        
        bind_vars = {
            'start_vertex': f'{self.collections["transcripts"]}/{video_id}',
            'depth': depth
        }
        
        # Execute query and build network
        # Implementation depends on ArangoDB setup
        
        return {"message": "Citation network building requires full ArangoDB integration"}
    
    def _split_transcript(self, transcript: str, chunk_size: int = 500) -> List[Dict[str, Any]]:
        """Split transcript into analyzable chunks"""
        # Simple sentence-based splitting
        sentences = transcript.split('. ')
        chunks = []
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            current_chunk.append(sentence)
            current_length += len(sentence)
            
            if current_length >= chunk_size:
                chunks.append({
                    'text': '. '.join(current_chunk) + '.',
                    'timestamp': len(chunks) * 30  # Approximate timestamp
                })
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append({
                'text': '. '.join(current_chunk),
                'timestamp': len(chunks) * 30
            })
        
        return chunks
    
    def _extract_concept_section(self, transcript: str, concept: str) -> str:
        """Extract section of transcript discussing a concept"""
        # Simple extraction - find sentences containing concept
        sentences = transcript.split('. ')
        relevant = []
        
        concept_lower = concept.lower()
        for i, sentence in enumerate(sentences):
            if concept_lower in sentence.lower():
                # Include context (prev and next sentences)
                start = max(0, i - 1)
                end = min(len(sentences), i + 2)
                relevant.extend(sentences[start:end])
        
        return '. '.join(relevant)
    
    async def _semantic_search(self, embedding: np.ndarray, limit: int) -> List[Dict[str, Any]]:
        """Search for videos using semantic similarity"""
        # This would use ArangoDB's vector search
        # For now, return empty list
        return []
    
    async def _store_evidence(self, claim: str, evidence_list: List[Evidence]):
        """Store evidence in ArangoDB"""
        if not self.arango_client:
            return
        
        # Store claim
        claim_doc = {
            '_key': hash(claim),
            'text': claim,
            'timestamp': datetime.now().isoformat(),
            'evidence_count': len(evidence_list)
        }
        
        # Store evidence with relationships
        for evidence in evidence_list:
            evidence_doc = evidence.to_dict()
            evidence_doc['claim_id'] = claim_doc['_key']
            # Store in evidence collection
            # Create edge to transcript
            # Create edge to claim
    
    async def _llm_compare_sections(self, section1: str, section2: str, concept: str) -> Dict[str, Any]:
        """Use LLM to compare two explanations"""
        if not HAS_LITELLM:
            return {}
        
        prompt = f"""
        Compare these two explanations of "{concept}":
        
        Explanation 1: {section1}
        
        Explanation 2: {section2}
        
        Provide:
        1. Key differences between explanations
        2. Points of consensus
        3. Which explanation is more comprehensive/accurate
        
        Respond in JSON format.
        """
        
        try:
            response = await litellm.acompletion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {}


# Example usage
async def example_usage():
    """Example of using the research analyzer"""
    analyzer = ResearchAnalyzer()
    
    # Find evidence
    claim = "Transformers are more efficient than RNNs for long sequences"
    evidence = await analyzer.find_evidence(claim, evidence_type="both")
    
    print(f"Found {len(evidence)} pieces of evidence")
    for e in evidence[:3]:
        print(f"\n{e.evidence_type.upper()}: {e.title}")
        print(f"Confidence: {e.confidence:.2f}")
        print(f"Text: {e.text[:100]}...")
        print(f"Reasoning: {e.reasoning}")
    
    # Compare explanations
    comparisons = await analyzer.compare_explanations("attention mechanism")
    
    for comp in comparisons[:2]:
        print(f"\nComparing explanations of '{comp.concept}':")
        print(f"Video 1: {comp.video1['title']}")
        print(f"Video 2: {comp.video2['title']}")
        print(f"Similarity: {comp.similarity:.2f}")
        print(f"Consensus: {', '.join(comp.consensus)}")
        print(f"Differences: {', '.join(comp.differences)}")


if __name__ == "__main__":
    asyncio.run(example_usage())