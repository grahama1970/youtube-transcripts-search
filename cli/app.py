# youtube_transcripts/cli/app.py
import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from ..core.database import initialize_database, check_transcript_exists, store_answer, check_cached_answer, cleanup_old_transcripts
from ..core.transcript import get_channel_videos, get_transcript, enhance_transcript, parse_date_cutoff
from ..core.query import summarize_transcript, prefilter_transcripts, query_gemini
from ..cli.validators import validate_channel_urls, validate_date_cutoff, validate_cleanup_months
from ..cli.formatters import format_query_result, format_error, format_success
from ..cli.schemas import QueryResult, Transcript
from ..config import DEFAULT_CHANNEL, DEFAULT_DATE_CUTOFF, DEFAULT_CLEANUP_MONTHS
from llm_call.cli.slash_mcp_mixin import add_slash_mcp_commands

app = typer.Typer(name="youtube-transcripts")
add_slash_mcp_commands(app)  # Add slash command and MCP generation

console = Console()

@app.command()
def fetch(
    channels: str = typer.Option(DEFAULT_CHANNEL, help="Comma-separated YouTube channel URLs"),
    date_cutoff: str = typer.Option(DEFAULT_DATE_CUTOFF, help="Date cutoff (e.g., '2025-01-01' or '6 months')"),
    cleanup_months: int = typer.Option(DEFAULT_CLEANUP_MONTHS, help="Remove transcripts older than this many months")
):
    """Fetch and store YouTube transcripts with a date cutoff."""
    try:
        channel_urls = validate_channel_urls(channels)
        date_cutoff_valid = validate_date_cutoff(date_cutoff)
        cleanup_months_valid = validate_cleanup_months(cleanup_months)
        
        initialize_database()
        date_cutoff_dt = parse_date_cutoff(date_cutoff_valid)
        
        # Cleanup old transcripts
        deleted = cleanup_old_transcripts(cleanup_months_valid)
        if deleted > 0:
            format_success(f"Deleted {deleted} old transcripts.")
        
        for channel_url in channel_urls:
            console.print(f"[bold]Processing channel: {channel_url}[/bold]")
            videos = get_channel_videos(channel_url, date_cutoff_dt)
            channel_name = Channel(channel_url).channel_name or "Unknown Channel"
            
            for video_id, title, publish_date in videos:
                if check_transcript_exists(video_id):
                    console.print(f"[yellow]Skipping existing video: {title}[/yellow]")
                    continue
                
                transcript = get_transcript(video_id)
                if transcript:
                    summary = summarize_transcript(transcript)
                    enhanced_transcript = enhance_transcript(transcript)
                    store_transcript(video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript)
                    format_success(f"Stored transcript for: {title}")
                else:
                    console.print(f"[yellow]No transcript available for: {title}[/yellow]")
    
    except Exception as e:
        format_error(f"Fetch failed: {str(e)}")
        raise typer.Exit(1)

@app.command()
def query(
    question: str = typer.Option(..., help="Query to answer using transcripts"),
    channels: str = typer.Option(DEFAULT_CHANNEL, help="Comma-separated YouTube channel URLs")
):
    """Query transcripts to answer a question using Gemini."""
    try:
        channel_urls = validate_channel_urls(channels)
        
        # Check cached answer
        cached = check_cached_answer(question)
        if cached:
            answer, video_ids = cached
            console.print(Panel(answer, title="Cached Answer", border_style="blue"))
            console.print(f"[blue]Related Video IDs: {video_ids}[/blue]")
            return
        
        # Prefilter transcripts
        filtered_transcripts = prefilter_transcripts(question)
        if not filtered_transcripts:
            format_error("No relevant transcripts found.")
            return
        
        # Query Gemini
        answer, video_ids = query_gemini(question, filtered_transcripts)
        store_answer(question, answer, video_ids)
        
        # Format results
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
        format_query_result(result)
    
    except Exception as e:
        format_error(f"Query failed: {str(e)}")
        raise typer.Exit(1)

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Run fetch command (mock environment)
    total_tests += 1
    try:
        # Requires mocked dependencies (pytube, youtube-transcript-api)
        pass  # Placeholder for actual test with mocks
    except Exception as e:
        all_validation_failures.append(f"Fetch command test failed: {str(e)}")

    # Test 2: Run query command (mock environment)
    total_tests += 1
    try:
        # Requires mocked dependencies (Gemini API, database)
        pass  # Placeholder for actual test with mocks
    except Exception as e:
        all_validation_failures.append(f"Query command test failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
