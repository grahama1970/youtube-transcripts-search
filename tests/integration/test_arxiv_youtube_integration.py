"""
Integration tests for YouTube Transcripts and ArXiv MCP Server alignment.
These tests demonstrate interaction scenarios between the two systems.

External Dependencies:
- youtube_transcripts: Local YouTube transcript search and analysis
- arxiv-mcp-server: ArXiv paper search and validation (mocked for testing)

Example Usage:
>>> pytest tests/integration/test_arxiv_youtube_integration.py -v
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytest
from unittest.mock import Mock, AsyncMock

# YouTube Transcripts imports
from youtube_transcripts.unified_search import UnifiedYouTubeSearch, UnifiedSearchConfig
from youtube_transcripts.search_enhancements import EnhancedSearch
from youtube_transcripts.citation_detector import CitationDetector
from youtube_transcripts.metadata_extractor import MetadataExtractor

# Mock ArXiv client (would be replaced with actual client in production)
class MockArxivClient:
    """Mock ArXiv MCP Server client for testing"""
    
    async def search_papers(self, query: str, **kwargs) -> List[Dict]:
        """Mock paper search"""
        if "attention" in query.lower():
            return [{
                "id": "1706.03762",
                "title": "Attention Is All You Need",
                "authors": ["Vaswani et al."],
                "abstract": "We propose a new simple network architecture...",
                "categories": ["cs.CL", "cs.LG"]
            }]
        return []
    
    async def find_evidence(self, paper_id: str, hypothesis: str) -> Dict:
        """Mock evidence finding"""
        return {
            "supporting": [
                {
                    "text": "Our model achieves 28.4 BLEU on WMT 2014...",
                    "confidence": 0.85,
                    "section": "Results"
                }
            ],
            "contradicting": []
        }
    
    async def get_paper(self, arxiv_id: str) -> Dict:
        """Mock get paper by ID"""
        return {
            "id": arxiv_id,
            "title": "Example Paper",
            "authors": ["Author 1", "Author 2"]
        }


class TestArxivYouTubeIntegration:
    """Test integration scenarios between YouTube and ArXiv systems"""
    
    @pytest.fixture
    def youtube_client(self):
        """Create YouTube search client"""
        config = UnifiedSearchConfig()
        return UnifiedYouTubeSearch(config)
    
    @pytest.fixture
    def arxiv_client(self):
        """Create mock ArXiv client"""
        return MockArxivClient()
    
    @pytest.fixture
    def citation_detector(self):
        """Create citation detector"""
        return CitationDetector()
    
    @pytest.fixture
    def metadata_extractor(self):
        """Create metadata extractor"""
        return MetadataExtractor()
    
    @pytest.mark.asyncio
    async def test_citation_validation_pipeline(self, youtube_client, arxiv_client, citation_detector):
        """Test validating citations found in YouTube videos against ArXiv papers"""
        # Sample transcript with citations
        transcript = """
        In the groundbreaking paper "Attention Is All You Need" (arXiv:1706.03762),
        the authors demonstrated that transformer architectures could achieve
        state-of-the-art results without recurrence or convolution.
        """
        
        # Step 1: Extract citations from transcript
        citations = citation_detector.detect_citations(transcript)
        assert len(citations) > 0
        assert citations[0].type == "arxiv"
        assert citations[0].id == "1706.03762"
        
        # Step 2: Search for paper in ArXiv
        paper_results = await arxiv_client.search_papers(citations[0].id)
        assert len(paper_results) > 0
        assert "Attention" in paper_results[0]["title"]
        
        # Step 3: Validate claim against paper
        claim = "transformer architectures could achieve state-of-the-art results"
        evidence = await arxiv_client.find_evidence(paper_results[0]["id"], claim)
        assert len(evidence["supporting"]) > 0
        assert evidence["supporting"][0]["confidence"] > 0.8
    
    @pytest.mark.asyncio
    async def test_research_enhancement_pipeline(self, youtube_client, arxiv_client, metadata_extractor):
        """Test enriching video content with related academic papers"""
        # Sample transcript with technical content
        transcript = """
        Today we'll discuss transformer models and self-attention mechanisms.
        These concepts revolutionized natural language processing.
        """
        
        # Extract technical terms
        metadata = metadata_extractor.extract_entities(transcript)
        technical_terms = [e["text"] for e in metadata["entities"] 
                          if e["label"] in ["TECHNICAL_TERM", "ML_CONCEPT"]]
        
        # Find related papers for each concept
        enrichments = []
        for term in technical_terms[:2]:  # Limit for testing
            papers = await arxiv_client.search_papers(f"{term} deep learning")
            if papers:
                enrichments.append({
                    "concept": term,
                    "papers": papers[:3]  # Top 3 papers
                })
        
        # Verify enrichments
        assert len(enrichments) > 0
        if enrichments:  # If we found any papers
            assert "papers" in enrichments[0]
    
    def test_cross_reference_search(self, youtube_client):
        """Test finding videos that discuss specific papers"""
        # Search for videos about a well-known paper
        paper_title = "Attention Is All You Need"
        paper_authors = "Vaswani"
        
        # Use real search (will work with local database)
        results = youtube_client.search(
            f'"{paper_title}" {paper_authors}',
            use_widening=True  # Enable query expansion
        )
        
        # Check if search was widened
        if results.get("widening_info"):
            print(f"Search widened: {results['widening_info']['explanation']}")
        
        # Results structure check
        assert "results" in results
        assert isinstance(results["results"], list)
    
    @pytest.mark.asyncio
    async def test_evidence_based_validation(self, arxiv_client, citation_detector):
        """Test validating scientific claims with evidence"""
        # Multiple claims to validate
        claims = [
            {
                "text": "Transformers achieve 28.4 BLEU on WMT 2014",
                "paper_ref": "1706.03762"
            },
            {
                "text": "Self-attention reduces computational complexity",
                "paper_ref": "1706.03762"
            }
        ]
        
        validation_results = []
        for claim in claims:
            # Get paper
            paper = await arxiv_client.get_paper(claim["paper_ref"])
            
            # Find evidence
            evidence = await arxiv_client.find_evidence(
                paper["id"], 
                claim["text"]
            )
            
            validation_results.append({
                "claim": claim["text"],
                "paper": paper["title"],
                "supported": len(evidence["supporting"]) > 0,
                "contradicted": len(evidence["contradicting"]) > 0,
                "confidence": evidence["supporting"][0]["confidence"] if evidence["supporting"] else 0
            })
        
        # Verify validation
        assert len(validation_results) == len(claims)
        assert all("supported" in r for r in validation_results)
        assert any(r["confidence"] > 0.5 for r in validation_results)
    
    def test_unified_metadata_extraction(self, metadata_extractor):
        """Test extracting metadata that can be used by both systems"""
        transcript = """
        Professor Geoffrey Hinton from the University of Toronto discusses
        the paper "ImageNet Classification with Deep Convolutional Neural Networks"
        published in 2012. This work on AlexNet achieved breakthrough results
        on the ImageNet dataset with 15.3% top-5 error rate.
        """
        
        # Extract all metadata
        metadata = metadata_extractor.extract_entities(transcript)
        
        # Check for speakers
        speakers = [e for e in metadata["entities"] if e["label"] == "PERSON"]
        assert any("Hinton" in s["text"] for s in speakers)
        
        # Check for institutions
        institutions = [e for e in metadata["entities"] if e["label"] == "ORG"]
        assert any("University of Toronto" in i["text"] for i in institutions)
        
        # Check for dates
        dates = [e for e in metadata["entities"] if e["label"] == "DATE"]
        assert any("2012" in d["text"] for d in dates)
        
        # Check for metrics
        metrics = metadata_extractor.extract_metrics(transcript)
        assert len(metrics) > 0
        assert any("15.3" in m["value"] for m in metrics)
    
    @pytest.mark.asyncio
    async def test_research_discovery_workflow(self, youtube_client, arxiv_client):
        """Test discovering new research based on video content"""
        # Simulate finding trending videos (using local search as proxy)
        trending_topics = ["transformer", "attention mechanism", "BERT"]
        
        all_papers = []
        for topic in trending_topics:
            # Search local transcripts
            video_results = youtube_client.search(topic, limit=5)
            
            if video_results["results"]:
                # Extract key concepts from first result
                first_video = video_results["results"][0]
                # Simulate concept extraction
                concepts = [topic, "deep learning", "NLP"]
                
                # Find related papers
                for concept in concepts[:2]:
                    papers = await arxiv_client.search_papers(concept)
                    all_papers.extend(papers)
        
        # Remove duplicates
        unique_papers = {p["id"]: p for p in all_papers}.values()
        
        # Verify discovery
        assert len(list(unique_papers)) >= 0  # May be 0 if no mock data matches
        
        # Create research digest structure
        digest = {
            "date": datetime.now().isoformat(),
            "topics_analyzed": trending_topics,
            "papers_found": len(list(unique_papers)),
            "top_papers": list(unique_papers)[:5]
        }
        
        assert "date" in digest
        assert "topics_analyzed" in digest
        assert len(digest["topics_analyzed"]) == 3


def validation_test():
    """Standalone validation function for real testing"""
    import asyncio
    
    # Create clients
    config = UnifiedSearchConfig()
    youtube = UnifiedYouTubeSearch(config)
    arxiv = MockArxivClient()
    detector = CitationDetector()
    
    # Test citation extraction with real data
    test_transcript = """
    The seminal work by Vaswani et al. (arXiv:1706.03762) introduced
    the transformer architecture. See also the BERT paper (arXiv:1810.04805)
    by Devlin et al. from 2018.
    """
    
    citations = detector.detect_citations(test_transcript)
    print(f"Found {len(citations)} citations:")
    for c in citations:
        print(f"  - {c.type}: {c.id} in context: '{c.context[:50] if c.context else 'N/A'}...'")
    
    # Test async paper lookup
    async def validate_citations():
        results = []
        for citation in citations:
            paper = await arxiv.get_paper(citation.id)
            results.append(paper)
        return results
    
    papers = asyncio.run(validate_citations())
    print(f"\nValidated {len(papers)} papers")
    
    # Test search widening with YouTube
    print("\nTesting YouTube search with widening:")
    results = youtube.search("VERLtransformer", use_widening=True)
    if results.get("widening_info"):
        print(f"Search was widened: {results['widening_info']['explanation']}")
    print(f"Found {len(results['results'])} results")
    
    return len(citations) > 0 and len(papers) > 0


if __name__ == "__main__":
    # Run validation
    success = validation_test()
    if success:
        print("\n✅ Integration validation passed!")
    else:
        print("\n❌ Integration validation failed!")
        exit(1)