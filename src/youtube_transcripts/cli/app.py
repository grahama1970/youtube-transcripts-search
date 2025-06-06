"""
Module: app.py
Description: Functions for app operations

External Dependencies:
- typer: [Documentation URL]
- rich: [Documentation URL]
- youtube_transcripts: [Documentation URL]
- : [Documentation URL]
- google: [Documentation URL]
- sqlite3: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/cli/app.py
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from youtube_transcripts.config import DEFAULT_CHANNEL, DEFAULT_CLEANUP_MONTHS, DEFAULT_DATE_CUTOFF
from youtube_transcripts.core.database import initialize_database, search_transcripts
from youtube_transcripts.core.transcript import process_channels
from youtube_transcripts.core.validators import validate_date_cutoff, validate_youtube_url
from youtube_transcripts.mcp.formatters import format_transcript_for_llm

app = typer.Typer(name='youtube-transcripts')

# Add slash command and MCP generation
from .slash_mcp_mixin import add_slash_mcp_commands

# Import and register prompts
try:
    from ..mcp.youtube_prompts import register_all_prompts
    prompt_registry = register_all_prompts()
except ImportError:
    prompt_registry = None

console = Console()

@app.command()
def fetch(
    channel: str = typer.Option(None, "--channel", help='YouTube channel URL (can be comma-separated for multiple)'),
    channels: str = typer.Option(None, hidden=True, help='Deprecated: Use --channel instead'),
    days: int = typer.Option(None, "--days", help='Fetch videos from last N days'),
    date_cutoff: str = typer.Option(None, help='Date cutoff (e.g., 2025-01-01 or 6 months)'),
    cleanup_months: int = typer.Option(DEFAULT_CLEANUP_MONTHS, help='Remove transcripts older than this many months')
):
    """Fetch and store YouTube transcripts with a date cutoff"""
    initialize_database()

    # Handle backward compatibility and determine channel input
    channel_input = channel or channels or DEFAULT_CHANNEL

    # Handle days parameter
    if days:
        date_cutoff = f"{days} days"
    elif not date_cutoff:
        date_cutoff = DEFAULT_DATE_CUTOFF

    # Parse and validate channels
    channel_list = [url.strip() for url in channel_input.split(',')]
    invalid_channels = [url for url in channel_list if not validate_youtube_url(url)]

    if invalid_channels:
        console.print(f"[red]Invalid channel URLs: {', '.join(invalid_channels)}[/red]")
        raise typer.Exit(1)

    # Validate date cutoff
    if not validate_date_cutoff(date_cutoff):
        console.print(f"[red]Invalid date cutoff: {date_cutoff}[/red]")
        console.print("Use format: YYYY-MM-DD or 'N months' or 'N days'")
        raise typer.Exit(1)

    console.print(f"[cyan]Fetching transcripts from {len(channel_list)} channel(s)...[/cyan]")
    console.print(f"Date cutoff: {date_cutoff}")

    try:
        processed, deleted = process_channels(channel_list, date_cutoff, cleanup_months)

        console.print(f"[green]✓ Processed {processed} transcripts[/green]")
        if deleted > 0:
            console.print(f"[yellow]✓ Cleaned up {deleted} old transcripts[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        raise typer.Exit(1)

@app.command()
def search(
    query: str = typer.Argument(..., help='Search query'),
    channel: str = typer.Option('', "--channel", help='YouTube channel name to filter'),
    channels: str = typer.Option('', hidden=True, help='Deprecated: Use --channel instead'),
    limit: int = typer.Option(10, help='Maximum number of results'),
    youtube: bool = typer.Option(False, "--youtube", help="Search all of YouTube via API"),
    days: int = typer.Option(None, "--days", help="Filter YouTube results to last N days"),
    max_results: int = typer.Option(50, "--max-results", help="Maximum YouTube API results"),
    fetch_transcripts: bool = typer.Option(False, "--fetch-transcripts", help="Automatically fetch transcripts for YouTube results")
):
    """Search through stored transcripts or all of YouTube"""

    if youtube:
        # Use YouTube API search
        try:
            from datetime import datetime, timedelta

            from youtube_transcripts.unified_search import UnifiedSearchConfig, UnifiedYouTubeSearch

            config = UnifiedSearchConfig()
            search_system = UnifiedYouTubeSearch(config)

            # Prepare date filter
            published_after = None
            if days:
                published_after = datetime.now() - timedelta(days=days)

            console.print(f"[cyan]Searching YouTube for: {query}[/cyan]")

            results = search_system.search_youtube_api(
                query=query,
                max_results=max_results,
                published_after=published_after,
                fetch_transcripts=fetch_transcripts,
                store_transcripts=fetch_transcripts
            )

            if not results.get('items'):
                console.print("[yellow]No YouTube results found[/yellow]")
                return

            # Create results table
            table = Table(title=f"YouTube Search Results for: {query}")
            table.add_column("Title", style="cyan", no_wrap=False)
            table.add_column("Channel", style="green")
            table.add_column("Published", style="yellow")
            table.add_column("Video ID", style="magenta")

            for item in results['items']:
                title = item['snippet']['title']
                table.add_row(
                    title[:60] + '...' if len(title) > 60 else title,
                    item['snippet']['channelTitle'],
                    item['snippet']['publishedAt'][:10],
                    item['id']['videoId']
                )

            console.print(table)

            # Show quota status
            if hasattr(search_system, 'youtube_api'):
                quota = search_system.youtube_api.get_quota_status()
                console.print(f"\n[dim]Quota used: {quota['used']}/{quota['limit']} (Searches remaining: {quota['searches_remaining']})[/dim]")

            if fetch_transcripts:
                console.print(f"\n[green]✓ Fetched and stored transcripts for {len(results['items'])} videos[/green]")

        except Exception as e:
            console.print(f"[red]YouTube API Error: {e!s}[/red]")
            console.print("[yellow]Falling back to local search...[/yellow]")
            youtube = False  # Fall through to local search

    if not youtube:
        # Local database search
        initialize_database()

        # Handle backward compatibility
        channel_input = channel or channels

        # Parse channels if provided
        channel_list = None
        if channel_input:
            channel_list = [url.strip() for url in channel_input.split(',')]

        results = search_transcripts(query, channel_list, limit)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        # Create results table
        table = Table(title=f"Local Search Results for: {query}")
        table.add_column("Title", style="cyan", no_wrap=False)
        table.add_column("Channel", style="green")
        table.add_column("Date", style="yellow")
        table.add_column("Relevance", style="magenta")

        for result in results:
            table.add_row(
                result['title'][:60] + '...' if len(result['title']) > 60 else result['title'],
                result['channel_name'],
                result['publish_date'],
                str(abs(result['rank']))[:6]
            )

        console.print(table)

@app.command()
def query(
    question: str = typer.Option(..., help='Query to answer using transcripts'),
    channels: str = typer.Option(DEFAULT_CHANNEL, help='Comma-separated YouTube channel URLs')
):
    """Query transcripts to answer a question using Gemini"""
    initialize_database()

    try:
        import google.generativeai as genai

        from youtube_transcripts.config import GEMINI_API_KEY

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except Exception:
        console.print("[red]Error: Gemini API not configured[/red]")
        console.print("Please set GEMINI_API_KEY environment variable")
        raise typer.Exit(1)

    # Parse channels
    channel_list = None
    if channels:
        channel_list = [url.strip() for url in channels.split(',')]

    console.print("[cyan]Searching for relevant content...[/cyan]")

    # Search for relevant transcripts
    results = search_transcripts(question, channel_list, limit=5)

    if not results:
        console.print("[yellow]No relevant transcripts found[/yellow]")
        return

    console.print(f"[green]Found {len(results)} relevant videos[/green]")

    # Format context
    context = format_transcript_for_llm(results, max_videos=5)

    # Create prompt
    prompt = f"""Based on the following YouTube video transcripts, please answer this question: {question}

Context from videos:
{context}

Please provide a comprehensive answer based on the information in these transcripts."""

    console.print("[cyan]Generating answer...[/cyan]")

    try:
        response = model.generate_content(prompt)

        console.print("\n[bold]Answer:[/bold]")
        console.print(response.text)

        console.print("\n[bold]Sources:[/bold]")
        for i, result in enumerate(results, 1):
            console.print(f"{i}. {result['title']} - {result['channel_name']} ({result['publish_date']})")

    except Exception as e:
        console.print(f"[red]Error generating response: {e!s}[/red]")
        raise typer.Exit(1)

@app.command()
def stats():
    """Show database statistics"""
    initialize_database()

    import sqlite3

    from youtube_transcripts.config import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM transcripts")
    total = cursor.fetchone()[0]

    # Get channel counts
    cursor.execute("""
        SELECT channel_name, COUNT(*) as count 
        FROM transcripts 
        GROUP BY channel_name 
        ORDER BY count DESC
    """)
    channels = cursor.fetchall()

    conn.close()

    console.print(f"[bold]Total transcripts:[/bold] {total}")

    if channels:
        table = Table(title="Transcripts by Channel")
        table.add_column("Channel", style="cyan")
        table.add_column("Count", style="green")

        for channel, count in channels:
            table.add_row(channel, str(count))

        console.print(table)

if __name__ == '__main__':
    app()

# Investigate why this is at the bottom of the file
from youtube_transcripts.cli.app_enhanced import register_commands

register_commands(app)
# Add slash command and MCP generation capabilities
add_slash_mcp_commands(app, command_prefix="generate", prompt_registry=prompt_registry)

if __name__ == "__main__":
    app()
