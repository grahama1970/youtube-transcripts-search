"""
Scientific search CLI commands for YouTube transcripts.
Module: app_scientific.py
Description: Functions for app scientific operations

This module adds scientific search and export commands to the CLI,
including citation search, speaker search, and metadata filtering.
"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from src.youtube_transcripts.search_enhancements import EnhancedSearch, SearchExporter

app = typer.Typer(name='scientific')
console = Console()


@app.command()
def search_advanced(
    query: str = typer.Argument("", help="Search query (optional)"),
    channels: str | None = typer.Option(None, "--channels", help="Comma-separated channel names"),
    content_type: str | None = typer.Option(None, "--type", help="Content type: lecture, tutorial, conference, demo, discussion"),
    academic_level: str | None = typer.Option(None, "--level", help="Academic level: undergraduate, graduate, research, professional"),
    has_citations: bool = typer.Option(False, "--has-citations", help="Only show videos with citations"),
    institution: str | None = typer.Option(None, "--institution", help="Filter by institution (e.g., MIT, Stanford)"),
    speaker: str | None = typer.Option(None, "--speaker", help="Filter by speaker name"),
    min_quality: float | None = typer.Option(None, "--min-quality", help="Minimum quality score (0-1)"),
    limit: int = typer.Option(10, "--limit", help="Maximum results"),
    export_format: str | None = typer.Option(None, "--export", help="Export format: csv, markdown, json")
):
    """Advanced search with scientific metadata filters"""

    search = EnhancedSearch()

    # Parse channels
    channel_list = None
    if channels:
        channel_list = [ch.strip() for ch in channels.split(',')]

    # Perform search
    console.print("[cyan]Searching with advanced filters...[/cyan]")

    results = search.search(
        query=query,
        channels=channel_list,
        content_type=content_type,
        academic_level=academic_level,
        has_citations=has_citations,
        institution=institution,
        speaker=speaker,
        min_quality_score=min_quality,
        limit=limit
    )

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    # Display results
    _display_search_results(results)

    # Export if requested
    if export_format:
        _export_results(results, export_format)


@app.command()
def find_citations(
    citation: str = typer.Argument(..., help="Citation ID (arXiv ID, DOI, or author-year)"),
    export_bibtex: bool = typer.Option(False, "--bibtex", help="Export all citations as BibTeX")
):
    """Find all videos that cite a specific paper"""

    search = EnhancedSearch()

    console.print(f"[cyan]Searching for citations of: {citation}[/cyan]")

    results = search.search_by_citation(citation)

    if not results:
        console.print(f"[yellow]No videos found citing {citation}[/yellow]")
        return

    console.print(f"\n[green]Found {len(results)} videos citing this paper:[/green]\n")

    # Display results
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Title", style="white", width=50)
    table.add_column("Channel", style="yellow")
    table.add_column("Date", style="blue")
    table.add_column("Other Citations", style="green")

    video_ids = []
    for result in results:
        video_ids.append(result['video_id'])
        other_citations = len(result.get('citations', [])) - 1

        table.add_row(
            result['title'][:50] + "..." if len(result['title']) > 50 else result['title'],
            result['channel_name'],
            result['publish_date'],
            str(other_citations)
        )

    console.print(table)

    # Export citations if requested
    if export_bibtex:
        console.print("\n[cyan]Exporting citations...[/cyan]")
        bibtex = search.export_citations(video_ids, 'bibtex')

        output_path = Path(f"citations_{citation.replace(':', '_').replace('/', '_')}.bib")
        output_path.write_text(bibtex)
        console.print(f"[green]✓ Exported to {output_path}[/green]")


@app.command()
def find_speaker(
    name: str = typer.Argument(..., help="Speaker name to search for"),
    show_affiliations: bool = typer.Option(False, "--affiliations", help="Show speaker affiliations")
):
    """Find all videos featuring a specific speaker"""

    search = EnhancedSearch()

    console.print(f"[cyan]Searching for videos with speaker: {name}[/cyan]")

    results = search.get_speaker_videos(name)

    if not results:
        console.print(f"[yellow]No videos found with speaker {name}[/yellow]")
        return

    console.print(f"\n[green]Found {len(results)} videos:[/green]\n")

    # Display results
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Title", style="white", width=50)
    table.add_column("Channel", style="yellow")
    table.add_column("Date", style="blue")

    if show_affiliations:
        table.add_column("Speaker Info", style="green")

    for result in results:
        row = [
            result['title'][:50] + "..." if len(result['title']) > 50 else result['title'],
            result['channel_name'],
            result['publish_date']
        ]

        if show_affiliations:
            # Find speaker info
            speaker_info = []
            for speaker in result['speakers']:
                if name.lower() in speaker['name'].lower():
                    info = speaker['name']
                    if speaker.get('affiliation'):
                        info += f" ({speaker['affiliation']})"
                    speaker_info.append(info)
            row.append('\n'.join(speaker_info))

        table.add_row(*row)

    console.print(table)


@app.command()
def stats(
    show_institutions: bool = typer.Option(False, "--institutions", help="Show institution statistics"),
    show_topics: bool = typer.Option(False, "--topics", help="Show topic distribution"),
    limit: int = typer.Option(20, "--limit", help="Limit results")
):
    """Show statistics about the transcript database"""

    search = EnhancedSearch()

    if show_institutions:
        console.print("[cyan]Institution Statistics:[/cyan]\n")

        stats = search.get_institution_stats()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Institution", style="white")
        table.add_column("Count", style="yellow")

        for inst, count in list(stats.items())[:limit]:
            table.add_row(inst, str(count))

        console.print(table)

    # TODO: Add topic statistics when implemented
    if show_topics:
        console.print("\n[yellow]Topic statistics not yet implemented[/yellow]")


@app.command()
def export_citations(
    video_ids: str = typer.Argument(..., help="Comma-separated video IDs"),
    format: str = typer.Option("bibtex", "--format", help="Export format: bibtex, json, markdown"),
    output: str | None = typer.Option(None, "--output", help="Output file path")
):
    """Export citations from specific videos"""

    search = EnhancedSearch()

    # Parse video IDs
    ids = [vid.strip() for vid in video_ids.split(',')]

    console.print(f"[cyan]Exporting citations from {len(ids)} videos...[/cyan]")

    # Export citations
    exported = search.export_citations(ids, format)

    if output:
        output_path = Path(output)
        output_path.write_text(exported)
        console.print(f"[green]✓ Exported to {output_path}[/green]")
    else:
        console.print("\n[bold]Exported Citations:[/bold]\n")
        console.print(exported)


def _display_search_results(results: list[dict]) -> None:
    """Display search results in a formatted table."""

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Title", style="white", width=40)
    table.add_column("Channel", style="yellow")
    table.add_column("Type", style="blue")
    table.add_column("Level", style="green")
    table.add_column("Citations", style="cyan")
    table.add_column("Quality", style="magenta")

    for result in results:
        metadata = result.get('metadata', {})

        # Format quality score
        quality = metadata.get('quality_score', 0)
        quality_str = f"{quality:.0%}" if quality else "N/A"

        table.add_row(
            result['title'][:40] + "..." if len(result['title']) > 40 else result['title'],
            result['channel_name'][:20],
            metadata.get('content_type', 'unknown'),
            metadata.get('academic_level', 'unknown'),
            str(len(result.get('citations', []))),
            quality_str
        )

    console.print(table)
    console.print(f"\n[green]Found {len(results)} results[/green]")


def _export_results(results: list[dict], format: str) -> None:
    """Export search results to file."""

    timestamp = Path(".").resolve().name

    if format == 'csv':
        output_path = Path(f"search_results_{timestamp}.csv")
        SearchExporter.export_to_csv(results, output_path)

    elif format == 'markdown':
        output_path = Path(f"search_results_{timestamp}.md")
        markdown = SearchExporter.export_to_markdown(results)
        output_path.write_text(markdown)

    elif format == 'json':
        output_path = Path(f"search_results_{timestamp}.json")
        # Remove transcript text for smaller export
        export_data = []
        for r in results:
            export_item = {
                'video_id': r['video_id'],
                'title': r['title'],
                'channel_name': r['channel_name'],
                'publish_date': r['publish_date'],
                'metadata': r.get('metadata', {}),
                'citations': r.get('citations', []),
                'speakers': r.get('speakers', [])
            }
            export_data.append(export_item)

        output_path.write_text(json.dumps(export_data, indent=2))

    else:
        console.print(f"[red]Unknown export format: {format}[/red]")
        return

    console.print(f"[green]✓ Exported to {output_path}[/green]")


# Add scientific commands to main app
def add_scientific_commands(main_app: typer.Typer) -> None:
    """Add scientific search commands to the main CLI app."""
    main_app.add_typer(app, name="sci", help="Scientific search and analysis commands")


if __name__ == "__main__":
    # Test the CLI
    app()
