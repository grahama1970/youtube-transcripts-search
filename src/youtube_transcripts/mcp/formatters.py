"""
Module: formatters.py
Description: Functions for formatters operations

External Dependencies:
- None (uses only standard library)

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/mcp/formatters.py
from datetime import datetime
from typing import Any


def format_search_results(results: list[dict[str, Any]], query: str) -> dict[str, Any]:
    """Format search results for MCP response"""
    formatted_results = []

    for result in results:
        # Create snippet from transcript
        transcript = result.get('transcript', '')
        snippet_length = 200

        # Try to find query terms in transcript for better snippet
        query_lower = query.lower()
        transcript_lower = transcript.lower()

        start_idx = transcript_lower.find(query_lower)
        if start_idx != -1:
            # Center snippet around query match
            start = max(0, start_idx - snippet_length // 2)
            end = min(len(transcript), start_idx + len(query) + snippet_length // 2)
            snippet = '...' + transcript[start:end] + '...'
        else:
            # Just take beginning of transcript
            snippet = transcript[:snippet_length] + '...' if len(transcript) > snippet_length else transcript

        formatted_results.append({
            'video_id': result['video_id'],
            'title': result['title'],
            'channel_name': result['channel_name'],
            'publish_date': result['publish_date'],
            'transcript_snippet': snippet,
            'relevance_score': abs(result.get('rank', 0))  # Convert negative rank to positive score
        })

    return {
        'results': formatted_results,
        'total_results': len(formatted_results),
        'query': query
    }

def format_fetch_response(processed_count: int, deleted_count: int,
                         channel_urls: list[str], success: bool = True,
                         error_message: str = '') -> dict[str, Any]:
    """Format fetch operation response"""
    message = f"Successfully processed {processed_count} videos"
    if deleted_count > 0:
        message += f" and cleaned up {deleted_count} old transcripts"

    if error_message:
        message = error_message
        success = False

    return {
        'processed_count': processed_count,
        'deleted_count': deleted_count,
        'channels_processed': channel_urls,
        'success': success,
        'message': message
    }

def format_transcript_for_llm(results: list[dict[str, Any]], max_videos: int = 5) -> str:
    """Format transcripts for LLM context"""
    context_parts = []

    for i, result in enumerate(results[:max_videos]):
        context_parts.append(f"""
Video {i+1}: {result['title']}
Channel: {result['channel_name']}
Date: {result['publish_date']}
Transcript:
{result['transcript']}
---
""")

    return '\n'.join(context_parts)

def format_query_response(answer: str, sources: list[dict[str, Any]],
                         confidence: float = 1.0, model: str = 'gemini-pro') -> dict[str, Any]:
    """Format query response for MCP"""
    return {
        'answer': answer,
        'sources': [
            {
                'video_id': source['video_id'],
                'title': source['title'],
                'channel_name': source['channel_name'],
                'publish_date': source['publish_date'],
                'transcript_snippet': source.get('transcript', '')[:200] + '...',
                'relevance_score': abs(source.get('rank', 0))
            }
            for source in sources
        ],
        'confidence': confidence,
        'model_used': model
    }

def format_error_response(error: Exception, operation: str) -> dict[str, Any]:
    """Format error response"""
    return {
        'success': False,
        'error': str(error),
        'error_type': type(error).__name__,
        'operation': operation,
        'timestamp': datetime.now().isoformat()
    }
