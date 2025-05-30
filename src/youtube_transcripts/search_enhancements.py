"""
Enhanced search functionality with scientific metadata support.

This module extends the existing search capabilities with filters for
citations, speakers, institutions, and content types.

External Documentation:
- SQLite JSON1: https://www.sqlite.org/json1.html
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from src.youtube_transcripts.core.database_v2 import search_transcripts as search_v2
from src.youtube_transcripts.citation_detector import CitationDetector
from src.youtube_transcripts.config import DB_PATH


class EnhancedSearch:
    """Enhanced search with scientific metadata filters."""
    
    def __init__(self, db_path: Path = DB_PATH):
        """Initialize enhanced search.
        
        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self.citation_detector = CitationDetector(use_ollama=False)
    
    def search(self, 
               query: str = "",
               channels: Optional[List[str]] = None,
               content_type: Optional[str] = None,
               academic_level: Optional[str] = None,
               has_citations: bool = False,
               institution: Optional[str] = None,
               speaker: Optional[str] = None,
               min_quality_score: Optional[float] = None,
               limit: int = 10) -> List[Dict[str, Any]]:
        """Search with enhanced filters.
        
        Args:
            query: Text search query
            channels: Filter by channel names
            content_type: Filter by content type (lecture, tutorial, etc.)
            academic_level: Filter by academic level
            has_citations: Only show transcripts with citations
            institution: Filter by mentioned institution
            speaker: Filter by speaker name
            min_quality_score: Minimum quality score
            limit: Maximum results
            
        Returns:
            List of matching transcripts with metadata
        """
        # Build filters dictionary
        filters = {}
        if content_type:
            filters['content_type'] = content_type
        if has_citations:
            filters['has_citations'] = True
        if institution:
            filters['institution'] = institution
        
        # Use enhanced search
        results = search_v2(
            query=query,
            channel_names=channels,
            limit=limit * 2,  # Get more results for post-filtering
            filters=filters,
            db_path=self.db_path
        )
        
        # Post-filter results
        filtered_results = []
        for result in results:
            # Filter by academic level
            if academic_level:
                metadata = result.get('metadata', {})
                if metadata.get('academic_level') != academic_level:
                    continue
            
            # Filter by speaker
            if speaker:
                speakers = result.get('speakers', [])
                speaker_names = [s.get('name', '').lower() for s in speakers]
                if not any(speaker.lower() in name for name in speaker_names):
                    continue
            
            # Filter by quality score
            if min_quality_score:
                metadata = result.get('metadata', {})
                quality = metadata.get('quality_score', 0)
                if quality < min_quality_score:
                    continue
            
            filtered_results.append(result)
            
            if len(filtered_results) >= limit:
                break
        
        return filtered_results
    
    def search_by_citation(self, citation_id: str) -> List[Dict[str, Any]]:
        """Find all transcripts that cite a specific paper.
        
        Args:
            citation_id: arXiv ID, DOI, or author-year citation
            
        Returns:
            List of transcripts containing the citation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Search in citations JSON field
        query = """
            SELECT 
                video_id, title, channel_name, publish_date, 
                transcript, summary, enhanced_transcript, duration,
                metadata, citations, speakers
            FROM transcripts_metadata
            WHERE citations LIKE ?
            ORDER BY publish_date DESC
        """
        
        cursor.execute(query, [f'%{citation_id}%'])
        results = cursor.fetchall()
        conn.close()
        
        # Parse results
        transcripts = []
        for r in results:
            # Verify citation is actually present
            citations = json.loads(r[9]) if r[9] else []
            if any(citation_id in str(cite) for cite in citations):
                transcript = {
                    'video_id': r[0],
                    'title': r[1],
                    'channel_name': r[2],
                    'publish_date': r[3],
                    'transcript': r[4],
                    'summary': r[5],
                    'enhanced_transcript': r[6],
                    'duration': r[7],
                    'metadata': json.loads(r[8]) if r[8] else {},
                    'citations': citations,
                    'speakers': json.loads(r[10]) if r[10] else []
                }
                transcripts.append(transcript)
        
        return transcripts
    
    def get_citation_network(self, video_id: str) -> Dict[str, Any]:
        """Get citation network for a video.
        
        Args:
            video_id: Video ID to analyze
            
        Returns:
            Citation network with related videos
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get citations for the given video
        cursor.execute("""
            SELECT citations FROM transcripts_metadata
            WHERE video_id = ?
        """, [video_id])
        
        result = cursor.fetchone()
        if not result or not result[0]:
            return {'video_id': video_id, 'citations': [], 'cited_by': []}
        
        citations = json.loads(result[0])
        
        # Find other videos citing the same papers
        related_videos = set()
        for citation in citations:
            cite_id = citation.get('id') or citation.get('text')
            if cite_id:
                cursor.execute("""
                    SELECT video_id, title FROM transcripts_metadata
                    WHERE citations LIKE ? AND video_id != ?
                """, [f'%{cite_id}%', video_id])
                
                for row in cursor.fetchall():
                    related_videos.add((row[0], row[1]))
        
        conn.close()
        
        return {
            'video_id': video_id,
            'citations': citations,
            'related_videos': [
                {'video_id': vid, 'title': title} 
                for vid, title in related_videos
            ]
        }
    
    def get_speaker_videos(self, speaker_name: str) -> List[Dict[str, Any]]:
        """Find all videos featuring a specific speaker.
        
        Args:
            speaker_name: Name of the speaker
            
        Returns:
            List of videos with the speaker
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                video_id, title, channel_name, publish_date, speakers
            FROM transcripts_metadata
            WHERE speakers LIKE ?
            ORDER BY publish_date DESC
        """
        
        cursor.execute(query, [f'%{speaker_name}%'])
        results = cursor.fetchall()
        conn.close()
        
        videos = []
        for r in results:
            speakers = json.loads(r[4]) if r[4] else []
            # Verify speaker is present
            if any(speaker_name.lower() in s.get('name', '').lower() 
                   for s in speakers):
                videos.append({
                    'video_id': r[0],
                    'title': r[1],
                    'channel_name': r[2],
                    'publish_date': r[3],
                    'speakers': speakers
                })
        
        return videos
    
    def get_institution_stats(self) -> Dict[str, int]:
        """Get statistics about mentioned institutions.
        
        Returns:
            Dictionary of institution counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT metadata FROM transcripts_metadata
            WHERE metadata IS NOT NULL
        """)
        
        institution_counts = {}
        for row in cursor.fetchall():
            metadata = json.loads(row[0])
            institutions = metadata.get('institutions', [])
            for inst in institutions:
                institution_counts[inst] = institution_counts.get(inst, 0) + 1
        
        conn.close()
        
        # Sort by count
        return dict(sorted(institution_counts.items(), 
                          key=lambda x: x[1], reverse=True))
    
    def export_citations(self, video_ids: List[str], 
                        format: str = 'bibtex') -> str:
        """Export citations from multiple videos.
        
        Args:
            video_ids: List of video IDs
            format: Export format (bibtex, json, markdown)
            
        Returns:
            Formatted citations
        """
        all_citations = []
        seen_citations = set()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for video_id in video_ids:
            cursor.execute("""
                SELECT citations, title FROM transcripts_metadata
                WHERE video_id = ?
            """, [video_id])
            
            result = cursor.fetchone()
            if result and result[0]:
                citations = json.loads(result[0])
                video_title = result[1]
                
                for cite in citations:
                    # Create unique key to avoid duplicates
                    key = f"{cite.get('type')}:{cite.get('id', cite.get('text'))}"
                    if key not in seen_citations:
                        seen_citations.add(key)
                        # Add video context
                        cite['source_video'] = video_title
                        all_citations.append(cite)
        
        conn.close()
        
        # Convert to Citation objects for formatting
        from src.youtube_transcripts.citation_detector import Citation
        citation_objects = []
        for cite in all_citations:
            citation_objects.append(Citation(
                type=cite.get('type', 'unknown'),
                text=cite.get('text', ''),
                id=cite.get('id'),
                authors=cite.get('authors'),
                year=cite.get('year'),
                title=cite.get('title')
            ))
        
        # Use citation detector's formatting
        return self.citation_detector.format_for_export(citation_objects, format)


class SearchExporter:
    """Export search results in various formats."""
    
    @staticmethod
    def export_to_csv(results: List[Dict[str, Any]], 
                     output_path: Path) -> None:
        """Export search results to CSV.
        
        Args:
            results: Search results
            output_path: Output file path
        """
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if not results:
                return
            
            # Define fields to export
            fields = [
                'video_id', 'title', 'channel_name', 'publish_date',
                'content_type', 'academic_level', 'primary_topic',
                'num_citations', 'num_speakers', 'institutions'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            
            for result in results:
                metadata = result.get('metadata', {})
                row = {
                    'video_id': result.get('video_id'),
                    'title': result.get('title'),
                    'channel_name': result.get('channel_name'),
                    'publish_date': result.get('publish_date'),
                    'content_type': metadata.get('content_type', ''),
                    'academic_level': metadata.get('academic_level', ''),
                    'primary_topic': metadata.get('primary_topic', ''),
                    'num_citations': len(result.get('citations', [])),
                    'num_speakers': len(result.get('speakers', [])),
                    'institutions': ', '.join(metadata.get('institutions', []))
                }
                writer.writerow(row)
    
    @staticmethod
    def export_to_markdown(results: List[Dict[str, Any]]) -> str:
        """Export search results as markdown.
        
        Args:
            results: Search results
            
        Returns:
            Markdown formatted string
        """
        lines = ["# Search Results\n"]
        
        for result in results:
            metadata = result.get('metadata', {})
            
            lines.append(f"## {result['title']}\n")
            lines.append(f"**Channel:** {result['channel_name']}  ")
            lines.append(f"**Date:** {result['publish_date']}  ")
            lines.append(f"**Video ID:** {result['video_id']}\n")
            
            if metadata:
                lines.append("### Metadata")
                if metadata.get('content_type'):
                    lines.append(f"- **Type:** {metadata['content_type']}")
                if metadata.get('academic_level'):
                    lines.append(f"- **Level:** {metadata['academic_level']}")
                if metadata.get('keywords'):
                    lines.append(f"- **Keywords:** {', '.join(metadata['keywords'][:5])}")
                lines.append("")
            
            if result.get('citations'):
                lines.append("### Citations")
                for cite in result['citations'][:5]:
                    if cite.get('type') == 'arxiv':
                        lines.append(f"- [arXiv:{cite['id']}](https://arxiv.org/abs/{cite['id']})")
                    elif cite.get('type') == 'doi':
                        lines.append(f"- [DOI:{cite['id']}](https://doi.org/{cite['id']})")
                    else:
                        lines.append(f"- {cite.get('text', 'Unknown citation')}")
                lines.append("")
            
            if result.get('speakers'):
                lines.append("### Speakers")
                for speaker in result['speakers']:
                    speaker_info = speaker['name']
                    if speaker.get('affiliation'):
                        speaker_info += f" ({speaker['affiliation']})"
                    lines.append(f"- {speaker_info}")
                lines.append("")
            
            lines.append("---\n")
        
        return '\n'.join(lines)


if __name__ == "__main__":
    # Test enhanced search
    from pathlib import Path
    
    # Use test database
    test_db = Path("test_enhanced_search.db")
    
    # Initialize database with test data
    from src.youtube_transcripts.core.database_v2 import initialize_database, add_transcript
    initialize_database(test_db)
    
    # Add test transcript with metadata
    test_metadata = {
        'content_type': 'lecture',
        'academic_level': 'graduate',
        'keywords': ['machine learning', 'neural networks'],
        'institutions': ['MIT', 'Stanford'],
        'quality_score': 0.85
    }
    
    test_citations = [
        {'type': 'arxiv', 'id': '2301.00234', 'text': 'arXiv:2301.00234'},
        {'type': 'author_year', 'text': 'Vaswani et al., 2017'}
    ]
    
    test_speakers = [
        {'name': 'Dr. Jane Smith', 'affiliation': 'MIT'},
        {'name': 'Prof. John Doe', 'affiliation': 'Stanford'}
    ]
    
    add_transcript(
        video_id='enhanced_test_001',
        title='Advanced Machine Learning - Lecture 10',
        channel_name='MIT OpenCourseWare',
        publish_date='2024-01-20',
        transcript='Discussion of transformer architectures by Vaswani et al., 2017...',
        metadata=test_metadata,
        citations=test_citations,
        speakers=test_speakers,
        db_path=test_db
    )
    
    print("=== Enhanced Search Test ===\n")
    
    # Test search
    search = EnhancedSearch(test_db)
    
    # Test 1: Search with content type filter
    print("Test 1: Search for lectures")
    results = search.search(query="machine learning", content_type="lecture")
    print(f"Found {len(results)} results")
    if results:
        print(f"First result: {results[0]['title']}")
    
    # Test 2: Search by citation
    print("\nTest 2: Search by citation")
    results = search.search_by_citation("2301.00234")
    print(f"Found {len(results)} videos citing arXiv:2301.00234")
    
    # Test 3: Get speaker videos
    print("\nTest 3: Search by speaker")
    results = search.get_speaker_videos("Jane Smith")
    print(f"Found {len(results)} videos with Dr. Jane Smith")
    
    # Test 4: Export results
    print("\nTest 4: Export to markdown")
    results = search.search(query="machine")
    if results:
        markdown = SearchExporter.export_to_markdown(results)
        print("Markdown preview:")
        print(markdown[:500] + "...")
    
    # Clean up
    test_db.unlink()
    
    print("\n✓ Enhanced search test complete!")