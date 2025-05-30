# youtube_transcripts/mcp/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class SearchRequest(BaseModel):
    """Request schema for searching transcripts"""
    query: str = Field(..., description="Search query for finding relevant transcripts")
    channels: Optional[List[str]] = Field(None, description="Filter by specific channel URLs")
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
    results: List[SearchResult]
    total_results: int
    query: str

class FetchRequest(BaseModel):
    """Request schema for fetching new transcripts"""
    channel_urls: List[str] = Field(..., description="YouTube channel URLs to fetch from")
    date_cutoff: Optional[str] = Field(None, description="Date cutoff (e.g., '2025-01-01' or '6 months')")
    cleanup_months: Optional[int] = Field(None, description="Remove transcripts older than this many months")

class FetchResponse(BaseModel):
    """Response schema for fetch operation"""
    processed_count: int
    deleted_count: int
    channels_processed: List[str]
    success: bool
    message: str

class QueryRequest(BaseModel):
    """Request schema for querying with Gemini"""
    question: str = Field(..., description="Question to answer using transcripts")
    channels: Optional[List[str]] = Field(None, description="Filter by specific channel URLs")
    max_context_videos: int = Field(5, description="Maximum number of videos to use as context")

class QueryResponse(BaseModel):
    """Response schema for Gemini query"""
    answer: str
    sources: List[SearchResult]
    confidence: float
    model_used: str
