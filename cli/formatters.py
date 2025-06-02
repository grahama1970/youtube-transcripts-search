# youtube_transcripts/cli/formatters.py
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import List, Dict, Any
from .schemas import QueryResult, Transcript

console = Console()

def format_query_result(result: QueryResult) -> None:
    """Format query result with rich formatting."""
    console.print(Panel(result.answer, title="Answer", border_style="green"))
    
    if not result.videos:
        console.print("[yellow]No relevant videos found.[/yellow]")
        return
    
    table = Table(title="Relevant Videos", show_header=True, header_style="bold magenta")
    table.add_column("Title", style="cyan")
    table.add_column("Channel", style="cyan")
    table.add_column("Published", style="cyan")
    table.add_column("URL", style="cyan")
    table.add_column("BM25 Rank", style="cyan")
    
    for video in result.videos:
        table.add_row(
            video.title,
            video.channel_name,
            video.publish_date,
            f"https://www.youtube.com/watch?v={video.video_id}",
            f"{video.rank:.3f}"
        )
    
    console.print(table)

def format_error(message: str) -> None:
    """Format error message."""
    console.print(Panel(message, title="Error", border_style="red"))

def format_success(message: str) -> None:
    """Format success message."""
    console.print(f"[green]✅ {message}[/green]")

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Format query result
    total_tests += 1
    try:
        from .schemas import Transcript, QueryResult
        transcript = Transcript(
            video_id="test123",
            title="Test Video",
            channel_name="Test Channel",
            publish_date="2025-01-01",
            transcript="Test transcript",
            enhanced_transcript="Enhanced transcript",
            rank=-10.234
        )
        result = QueryResult(answer="Test answer", videos=[transcript])
        format_query_result(result)
    except Exception as e:
        all_validation_failures.append(f"Format query result failed: {str(e)}")

    # Test 2: Format error
    total_tests += 1
    try:
        format_error("Test error")
    except Exception as e:
        all_validation_failures.append(f"Format error failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
