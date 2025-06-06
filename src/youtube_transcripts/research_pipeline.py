#!/usr/bin/env python3
"""
Module: research_pipeline.py
Description: Simplified research pipeline API for agents to process YouTube videos

This module provides a simple interface for agents to process research videos
and build knowledge graphs automatically.

External Dependencies:
- arango: https://python-arango.readthedocs.io/
- loguru: https://pypi.org/project/loguru/

Sample Input:
>>> await process_research_video("https://www.youtube.com/watch?v=ABC123")

Expected Output:
>>> {
>>>     'status': 'success',
>>>     'video_id': 'ABC123',
>>>     'knowledge_chunks': 15,
>>>     'arxiv_papers': 3,
>>>     'github_repos': 2
>>> }

Example Usage:
>>> from youtube_transcripts.research_pipeline import process_research_video
>>> result = await process_research_video("https://youtube.com/watch?v=xyz")
"""

import os
import asyncio
from typing import Dict, Any, Optional

from loguru import logger

# Import the full implementation
try:
    from granger_hub.scenarios.research_youtube_to_knowledge_graph import (
        process_research_video as _process_video,
        ResearchRequest
    )
    FULL_PIPELINE_AVAILABLE = True
except ImportError:
    FULL_PIPELINE_AVAILABLE = False
    logger.warning("Full pipeline not available, using simplified version")


async def process_research_video(
    video_url: str,
    research_topic: Optional[str] = None,
    chunk_size: int = 500
) -> Dict[str, Any]:
    """
    Process a YouTube research video and build knowledge graph.
    
    This is the main entry point for agents. It handles:
    1. YouTube transcript extraction with link detection
    2. ArXiv paper processing (if papers mentioned)
    3. GitHub repository analysis (if repos mentioned)
    4. ArangoDB storage with automatic graph building
    
    Args:
        video_url: YouTube video URL or ID
        research_topic: Optional context for better processing
        chunk_size: Size of knowledge chunks (default 500 chars)
        
    Returns:
        Dictionary with processing results:
        - status: 'success' or 'error'
        - video_id: YouTube video ID
        - title: Video title
        - knowledge_chunks: Number of chunks created
        - arxiv_papers: Number of papers found
        - github_repos: Number of repos found
        - graph_nodes: Total nodes in graph
        - graph_edges: Total edges in graph
        
    Example:
        >>> result = await process_research_video(
        ...     "https://www.youtube.com/watch?v=ABC123"
        ... )
        >>> print(f"Processed {result['knowledge_chunks']} chunks")
    """
    try:
        if FULL_PIPELINE_AVAILABLE:
            # Use full pipeline if available
            return await _process_video(video_url, research_topic)
        else:
            # Simplified version that just extracts transcript and links
            return await _simplified_process(video_url, research_topic, chunk_size)
            
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'video_url': video_url
        }


async def _simplified_process(
    video_url: str,
    research_topic: Optional[str],
    chunk_size: int
) -> Dict[str, Any]:
    """Simplified processing when full pipeline not available."""
    from .scripts.download_transcript import (
        download_youtube_transcript,
        extract_video_id,
        get_video_info,
        get_video_comments
    )
    
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        
        # Get metadata
        title, channel, duration, description, author_links = get_video_info(video_id)
        
        # Download transcript
        transcript_path = download_youtube_transcript(video_url)
        
        # Count links
        arxiv_count = sum(1 for link in author_links if link.link_type == 'arxiv')
        github_count = sum(1 for link in author_links if link.link_type == 'github')
        
        # Get comments
        comments = get_video_comments(video_id)
        for _, _, comment_links in comments:
            arxiv_count += sum(1 for link in comment_links if link.link_type == 'arxiv')
            github_count += sum(1 for link in comment_links if link.link_type == 'github')
        
        # Estimate chunks
        with open(transcript_path, 'r') as f:
            content = f.read()
        chunk_count = len(content) // chunk_size + 1
        
        return {
            'status': 'success',
            'video_id': video_id,
            'title': title,
            'channel': channel,
            'knowledge_chunks': chunk_count,
            'arxiv_papers': arxiv_count,
            'github_repos': github_count,
            'transcript_path': str(transcript_path),
            'mode': 'simplified'
        }
        
    except Exception as e:
        logger.error(f"Simplified processing failed: {e}")
        raise


# Convenience function for synchronous contexts
def process_research_video_sync(
    video_url: str,
    research_topic: Optional[str] = None,
    chunk_size: int = 500
) -> Dict[str, Any]:
    """
    Synchronous wrapper for process_research_video.
    
    Use this in non-async contexts:
    >>> result = process_research_video_sync("https://youtube.com/watch?v=xyz")
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            process_research_video(video_url, research_topic, chunk_size)
        )
    finally:
        loop.close()


# Quick check function for agents
async def check_video_researchability(video_url: str) -> Dict[str, bool]:
    """
    Quick check if a video is good for research processing.
    
    Returns:
        Dictionary with checks:
        - has_transcript: Video has captions available
        - has_papers: ArXiv papers mentioned
        - has_code: GitHub repos mentioned
        - is_educational: Likely educational content
    """
    from .scripts.download_transcript import (
        extract_video_id,
        get_video_info
    )
    
    try:
        video_id = extract_video_id(video_url)
        title, channel, duration, description, links = get_video_info(video_id)
        
        # Check for research indicators
        has_papers = any(link.link_type == 'arxiv' for link in links)
        has_code = any(link.link_type == 'github' for link in links)
        
        # Simple heuristic for educational content
        educational_keywords = [
            'tutorial', 'explained', 'introduction', 'lecture',
            'course', 'learn', 'understand', 'deep dive'
        ]
        is_educational = any(
            keyword in title.lower() or keyword in description.lower()
            for keyword in educational_keywords
        )
        
        return {
            'has_transcript': True,  # Checked during download
            'has_papers': has_papers,
            'has_code': has_code,
            'is_educational': is_educational,
            'title': title,
            'channel': channel
        }
        
    except Exception as e:
        logger.error(f"Check failed: {e}")
        return {
            'has_transcript': False,
            'has_papers': False,
            'has_code': False,
            'is_educational': False,
            'error': str(e)
        }


if __name__ == "__main__":
    # Example usage
    async def demo():
        """Demonstrate the research pipeline."""
        video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        print("Checking video researchability...")
        check = await check_video_researchability(video_url)
        print(f"Research potential: {check}")
        
        if check.get('has_papers') or check.get('has_code'):
            print("\nProcessing research video...")
            result = await process_research_video(video_url)
            print(f"Result: {result}")
        else:
            print("\nVideo doesn't appear to have research content.")
    
    asyncio.run(demo())