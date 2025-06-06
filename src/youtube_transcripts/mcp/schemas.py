"""
Module: schemas.py
Description: Implementation of schemas functionality

External Dependencies:
- pydantic: https://docs.pydantic.dev/

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/mcp/schemas.py

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request schema for searching transcripts"""
    query: str = Field(..., description="Search query for finding relevant transcripts")
    channels: list[str] | None = Field(None, description="Filter by specific channel URLs")
    limit: int = Field(10, description="Maximum number of results to return")

class SearchResult(BaseModel):
    """Individual search result"""
    video_id: str
    title: str
    channel_name: str
    publish_date: str
    transcript_snippet: str
    relevance_score: float

class SearchResponse(BaseModel):
    """Response schema for search results"""
    results: list[SearchResult]
    total_results: int
    query: str

class FetchRequest(BaseModel):
    """Request schema for fetching new transcripts"""
    channel_urls: list[str] = Field(..., description="YouTube channel URLs to fetch from")
    date_cutoff: str | None = Field(None, description="Date cutoff (e.g., '2025-01-01' or '6 months')")
    cleanup_months: int | None = Field(None, description="Remove transcripts older than this many months")

class FetchResponse(BaseModel):
    """Response schema for fetch operation"""
    processed_count: int
    deleted_count: int
    channels_processed: list[str]
    success: bool
    message: str

class QueryRequest(BaseModel):
    """Request schema for querying with Gemini"""
    question: str = Field(..., description="Question to answer using transcripts")
    channels: list[str] | None = Field(None, description="Filter by specific channel URLs")
    max_context_videos: int = Field(5, description="Maximum number of videos to use as context")

class QueryResponse(BaseModel):
    """Response schema for Gemini query"""
    answer: str
    sources: list[SearchResult]
    confidence: float
    model_used: str
