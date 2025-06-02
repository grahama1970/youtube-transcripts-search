# youtube_transcripts/mcp/wrapper.py
from fastmcp import FastMCP
from typing import Dict, Any, List
from ..core.database import initialize_database, check_transcript_exists, store_answer, check_cached_answer, cleanup_old_transcripts
from ..core.transcript import get_channel_videos, get_transcript, enhance_transcript, parse_date_cutoff
from ..core.query import summarize_transcript, prefilter_transcripts, query_gemini
from ..cli.validators import validate_channel_urls, validate_date_cutoff, validate_cleanup_months
from ..cli.schemas import QueryResult, Transcript
from ..mcp.schema import get_mcp_schemas

def create_mcp_server(name: str = "youtube-transcripts", host: str = "localhost", port: int = 5000) -> FastMCP:
    """Create and configure FastMCP server."""
    mcp = FastMCP(name)
    schemas = get_mcp_schemas()

    @mcp.tool(name="fetch")
    async def fetch_tool(channels: str, date_cutoff: str, cleanup_months: int) -> Dict[str, Any]:
        """MCP wrapper for fetch command."""
        try:
            channel_urls = validate_channel_urls(channels)
            date_cutoff_valid = validate_date_cutoff(date_cutoff)
            cleanup_months_valid = validate_cleanup_months(cleanup_months)
            
            initialize_database()
            date_cutoff_dt = parse_date_cutoff(date_cutoff_valid)
            
            deleted = cleanup_old_transcripts(cleanup_months_valid)
            results = []
            
            for channel_url in channel_urls:
                videos = get_channel_videos(channel_url, date_cutoff_dt)
                channel_name = Channel(channel_url).channel_name or "Unknown Channel"
                
                for video_id, title, publish_date in videos:
                    if check_transcript_exists(video_id):
                        results.append(f"Skipped existing video: {title}")
                        continue
                    
                    transcript = get_transcript(video_id)
                    if transcript:
                        summary = summarize_transcript(transcript)
                        enhanced_transcript = enhance_transcript(transcript)
                        store_transcript(video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript)
                        results.append(f"Stored transcript for: {title}")
                    else:
                        results.append(f"No transcript available for: {title}")
            
            return {"status": "success", "results": results, "deleted": deleted}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool(name="query")
    async def query_tool(question: str, channels: str) -> Dict[str, Any]:
        """MCP wrapper for query command."""
        try:
            channel_urls = validate_channel_urls(channels)
            
            cached = check_cached_answer(question)
            if cached:
                answer, video_ids = cached
                return {"status": "success", "answer": answer, "video_ids": video_ids, "cached": True}
            
            filtered_transcripts = prefilter_transcripts(question)
            if not filtered_transcripts:
                return {"status": "error", "error": "No relevant transcripts found"}
            
            answer, video_ids = query_gemini(question, filtered_transcripts)
            store_answer(question, answer, video_ids)
            
            result = QueryResult(
                answer=answer,
                videos=[
                    Transcript(
                        video_id=t["video_id"],
                        title=t["title"],
                        channel_name=t["channel_name"],
                        publish_date=t["publish_date"],
                        transcript=t["transcript"],
                        enhanced_transcript=t["enhanced_transcript"],
                        rank=t["rank"]
                    )
                    for t in filtered_transcripts
                ]
            )
            return {
                "status": "success",
                "answer": result.answer,
                "videos": [t.dict() for t in result.videos]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return mcp

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Create MCP server
    total_tests += 1
    try:
        mcp = create_mcp_server()
        if not isinstance(mcp, FastMCP):
            all_validation_failures.append("MCP server creation failed")
    except Exception as e:
        all_validation_failures.append(f"MCP server creation failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
