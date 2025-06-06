"""
Module: app_enhanced.py
Description: Functions for app enhanced operations

External Dependencies:
- typer: [Documentation URL]
- rich: [Documentation URL]
- youtube_transcripts: [Documentation URL]
- ollama: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# youtube_transcripts/src/youtube_transcripts/cli/app_enhanced.py
"""
Enhanced CLI commands for unified search with DeepRetrieval integration
Add these commands to your existing app.py or use as a separate module
"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import track
from rich.table import Table

from youtube_transcripts.cli.slash_mcp_mixin import add_slash_mcp_commands

# After creating the search_app
search_app = typer.Typer(help="Advanced search commands with DeepRetrieval")
add_slash_mcp_commands(search_app)  # This adds MCP generation capabilities

from youtube_transcripts.core.database import get_transcript_by_video_id, initialize_database, search_transcripts
from youtube_transcripts.core.transcript import TranscriptFetcher
from youtube_transcripts.unified_search import UnifiedSearchConfig, UnifiedYouTubeSearch

console = Console()

# Add these commands to your existing app or create a new command group
search_app = typer.Typer(help="Advanced search commands with DeepRetrieval")


@search_app.command("unified")
def search_unified(
    query: str = typer.Argument(..., help="Search query"),
    channels: list[str] | None = typer.Option(None, "--channel", "-c", help="Specific channels to search"),
    optimize: bool = typer.Option(True, "--optimize/--no-optimize", help="Use DeepRetrieval query optimization"),
    use_memory: bool = typer.Option(True, "--memory/--no-memory", help="Use ArangoDB graph memory"),
    user: str = typer.Option("default", "--user", "-u", help="User ID for personalized context"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results to display"),
    export: str | None = typer.Option(None, "--export", "-e", help="Export results to JSON file"),
):
    """
    Unified search with DeepRetrieval optimization and graph memory
    
    Examples:
        youtube-transcripts search unified "VERL reinforcement learning"
        youtube-transcripts search unified "Monte Carlo tree search" -c TrelisResearch
        youtube-transcripts search unified "LLM training" --no-optimize --export results.json
    """
    # Configure search system
    config = UnifiedSearchConfig(
        ollama_model="qwen2.5:3b",
        use_lora=Path("/home/graham/workspace/experiments/unsloth_wip/lora_model").exists()
    )

    # Initialize search
    with console.status("[bold green]Initializing search system..."):
        search_system = UnifiedYouTubeSearch(config)

    # Execute search
    with console.status(f"[bold blue]Searching for: {query}"):
        results = search_system.search(
            query=query,
            channels=channels,
            user_id=user,
            use_optimization=optimize,
            use_memory=use_memory
        )

    # Display results
    console.print(f"\n[bold]Query:[/bold] {query}")

    if optimize and results['optimized_query'] != query:
        console.print(f"[bold]Optimized:[/bold] [green]{results['optimized_query']}[/green]")
        if results['reasoning']:
            console.print(f"[dim]Reasoning: {results['reasoning']}[/dim]")

    console.print(f"\n[bold]Found {results['total_found']} results across {len(results['channels_searched'])} channels[/bold]\n")

    # Create results table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Channel", style="green")
    table.add_column("Date", style="yellow")
    table.add_column("Relevance", justify="right")

    for i, result in enumerate(results['results'][:limit], 1):
        table.add_row(
            str(i),
            result['title'][:50] + "..." if len(result['title']) > 50 else result['title'],
            result['channel_name'],
            result['publish_date'],
            f"{result.get('rank', 0):.2f}"
        )

    console.print(table)

    # Show context usage
    if results.get('context_used'):
        console.print("\n[dim]✓ Used previous search context[/dim]")

    # Export if requested
    if export:
        with open(export, 'w') as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]✓ Results exported to {export}[/green]")

    # Show memory ID if stored
    if results.get('memory_id'):
        console.print(f"\n[dim]Memory ID: {results['memory_id']}[/dim]")


@search_app.command("multi-channel")
def fetch_multi_channel(
    channels: list[str] = typer.Argument(None, help="Channel names to fetch (use --all for all configured)"),
    all_channels: bool = typer.Option(False, "--all", help="Fetch all configured channels"),
    date_cutoff: str = typer.Option("6 months", "--since", help="Date cutoff (e.g., '3 months', '1 year')"),
    max_videos: int = typer.Option(50, "--max", help="Maximum videos per channel"),
    parallel: bool = typer.Option(False, "--parallel", help="Fetch channels in parallel"),
):
    """
    Fetch transcripts from multiple YouTube channels
    
    Examples:
        youtube-transcripts search multi-channel --all --since "3 months"
        youtube-transcripts search multi-channel TrelisResearch DiscoverAI --max 100
    """
    from youtube_transcripts.config import YOUTUBE_CHANNELS

    # Default channel configuration
    YOUTUBE_CHANNELS = {
        "TrelisResearch": "https://www.youtube.com/@TrelisResearch",
        "DiscoverAI": "https://www.youtube.com/@code4AI",
        "TwoMinutePapers": "https://www.youtube.com/@TwoMinutePapers",
        "YannicKilcher": "https://www.youtube.com/@YannicKilcher",
        "AndrejKarpathy": "https://www.youtube.com/@AndrejKarpathy",
        "AlexanderAmini": "https://www.youtube.com/@AlexanderAmini",
    }

    if all_channels:
        channels = list(YOUTUBE_CHANNELS.keys())
    elif not channels:
        console.print("[red]Error: Specify channel names or use --all[/red]")
        raise typer.Exit(1)

    # Initialize database
    initialize_database()

    # Track overall progress
    total_fetched = 0

    for channel in track(channels, description="Fetching channels..."):
        if channel not in YOUTUBE_CHANNELS:
            console.print(f"[yellow]Warning: Unknown channel '{channel}', skipping[/yellow]")
            continue

        url = YOUTUBE_CHANNELS[channel]
        console.print(f"\n[bold]Fetching from {channel}...[/bold]")

        try:
            fetcher = TranscriptFetcher()
            videos_fetched = fetcher.fetch_channel_transcripts(
                channel_url=url,
                date_cutoff=date_cutoff,
                max_videos=max_videos
            )

            total_fetched += videos_fetched
            console.print(f"[green]✓ Fetched {videos_fetched} videos from {channel}[/green]")

        except Exception as e:
            console.print(f"[red]✗ Error fetching {channel}: {e!s}[/red]")

    console.print(f"\n[bold green]Total videos fetched: {total_fetched}[/bold green]")


@search_app.command("train")
def train_search_model(
    epochs: int = typer.Option(5, "--epochs", "-e", help="Number of training epochs"),
    episodes: int = typer.Option(50, "--episodes", help="Episodes per epoch"),
    model: str = typer.Option("qwen2.5:3b", "--model", "-m", help="Ollama model to use"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
    checkpoint: str | None = typer.Option(None, "--checkpoint", help="Resume from checkpoint"),
):
    """
    Train the DeepRetrieval search optimization model
    
    Examples:
        youtube-transcripts search train --epochs 10 --episodes 100
        youtube-transcripts search train --model phi-2 --config custom_config.json
    """
    console.print("[bold]Starting DeepRetrieval Training[/bold]\n")

    # Check if Ollama is available
    try:
        import ollama
        client = ollama.Client()
        models = client.list()

        if not any(model in str(models) for model in [model, "qwen2.5:3b"]):
            console.print(f"[yellow]Warning: Model '{model}' not found in Ollama[/yellow]")
            console.print("Available models:", models)

    except Exception as e:
        console.print(f"[red]Error: Ollama not available - {e}[/red]")
        console.print("Install Ollama and pull the model:")
        console.print("  curl -fsSL https://ollama.ai/install.sh | sh")
        console.print(f"  ollama pull {model}")
        raise typer.Exit(1)

    # Run training
    from youtube_transcripts.scripts.train_deepretrieval import DeepRetrievalYouTubeTrainer

    trainer = DeepRetrievalYouTubeTrainer(config)
    trainer.config['training']['num_epochs'] = epochs
    trainer.config['training']['episodes_per_epoch'] = episodes
    trainer.config['model'] = model

    if checkpoint:
        # Load checkpoint
        with open(checkpoint) as f:
            checkpoint_data = json.load(f)
            trainer.training_buffer = checkpoint_data['training_buffer']
            console.print(f"[green]Resumed from checkpoint with {len(trainer.training_buffer)} episodes[/green]")

    # Train
    trainer.train()


@search_app.command("analyze")
def analyze_search_performance(
    input_file: str = typer.Option("training_data.json", "--input", "-i", help="Training data file"),
    output_file: str = typer.Option("analysis_report.md", "--output", "-o", help="Output report file"),
    top_k: int = typer.Option(10, "--top", help="Number of top examples to show"),
):
    """
    Analyze search training performance and generate report
    
    Examples:
        youtube-transcripts search analyze
        youtube-transcripts search analyze --input custom_data.json --top 20
    """
    if not Path(input_file).exists():
        console.print(f"[red]Error: Input file '{input_file}' not found[/red]")
        raise typer.Exit(1)

    with open(input_file) as f:
        data = json.load(f)

    # Compute statistics
    gains = [ep['gain'] for ep in data]
    positive_gains = sum(1 for g in gains if g > 0)

    # Generate report
    report = f"""# DeepRetrieval Training Analysis Report

## Summary Statistics

- **Total Episodes**: {len(data)}
- **Average Gain**: {np.mean(gains):.3f}
- **Success Rate**: {positive_gains / len(data):.2%}
- **Best Gain**: {max(gains):.3f}
- **Worst Gain**: {min(gains):.3f}

## Performance Distribution

| Reward Level | Count | Percentage |
|--------------|-------|------------|
| Excellent (5.0) | {sum(1 for ep in data if ep['optimized_reward'] == 5.0)} | {sum(1 for ep in data if ep['optimized_reward'] == 5.0) / len(data):.1%} |
| Good (4.0) | {sum(1 for ep in data if ep['optimized_reward'] == 4.0)} | {sum(1 for ep in data if ep['optimized_reward'] == 4.0) / len(data):.1%} |
| Acceptable (3.0) | {sum(1 for ep in data if ep['optimized_reward'] == 3.0)} | {sum(1 for ep in data if ep['optimized_reward'] == 3.0) / len(data):.1%} |
| Poor (≤1.0) | {sum(1 for ep in data if ep['optimized_reward'] <= 1.0)} | {sum(1 for ep in data if ep['optimized_reward'] <= 1.0) / len(data):.1%} |

## Top {top_k} Best Optimizations

"""

    # Add best examples
    best_episodes = sorted(data, key=lambda x: x['gain'], reverse=True)[:top_k]

    for i, ep in enumerate(best_episodes, 1):
        report += f"""
### {i}. Gain: {ep['gain']:.2f}
- **Original**: "{ep['original_query']}"
- **Optimized**: "{ep['optimized_query']}"
- **Results**: {ep['baseline_count']} → {ep['optimized_count']}
- **Reasoning**: {ep['reasoning'][:200]}...
"""

    # Add worst examples
    report += f"\n## Bottom {min(5, top_k)} Worst Optimizations\n"

    worst_episodes = sorted(data, key=lambda x: x['gain'])[:min(5, top_k)]

    for i, ep in enumerate(worst_episodes, 1):
        report += f"""
### {i}. Gain: {ep['gain']:.2f}
- **Original**: "{ep['original_query']}"
- **Optimized**: "{ep['optimized_query']}"
- **Results**: {ep['baseline_count']} → {ep['optimized_count']}
"""

    # Save report
    with open(output_file, 'w') as f:
        f.write(report)

    console.print(f"[green]✓ Analysis report saved to {output_file}[/green]")

    # Display summary
    console.print("\n[bold]Performance Summary:[/bold]")
    console.print(f"  Average Gain: {np.mean(gains):.3f}")
    console.print(f"  Success Rate: {positive_gains / len(data):.2%}")
    console.print(f"  Total Episodes: {len(data)}")


@search_app.command("compare")
def compare_search_methods(
    query: str = typer.Argument(..., help="Search query to test"),
    channels: list[str] | None = typer.Option(None, "--channel", "-c", help="Specific channels"),
):
    """
    Compare different search methods side-by-side
    
    Examples:
        youtube-transcripts search compare "VERL reinforcement learning"
        youtube-transcripts search compare "Monte Carlo" -c TrelisResearch
    """
    console.print(f"[bold]Comparing search methods for: '{query}'[/bold]\n")

    # Method 1: Basic search
    with console.status("[yellow]Running basic search..."):
        basic_results = search_transcripts(query, channel_names=channels, limit=10)

    # Method 2: Unified search with optimization
    config = UnifiedSearchConfig()
    search_system = UnifiedYouTubeSearch(config)

    with console.status("[green]Running optimized search..."):
        optimized_results = search_system.search(
            query=query,
            channels=channels,
            use_optimization=True,
            use_memory=False
        )

    # Method 3: Unified search with memory
    with console.status("[blue]Running search with memory context..."):
        memory_results = search_system.search(
            query=query,
            channels=channels,
            use_optimization=True,
            use_memory=True
        )

    # Compare results
    table = Table(title="Search Method Comparison", show_header=True)
    table.add_column("Method", style="bold")
    table.add_column("Results Found", justify="center")
    table.add_column("Optimized Query", max_width=40)
    table.add_column("Top Result", max_width=40)

    # Basic search
    table.add_row(
        "Basic Search",
        str(len(basic_results)),
        query,
        basic_results[0]['title'][:40] + "..." if basic_results else "No results"
    )

    # Optimized search
    table.add_row(
        "DeepRetrieval",
        str(optimized_results['total_found']),
        optimized_results['optimized_query'][:40] + "..." if len(optimized_results['optimized_query']) > 40 else optimized_results['optimized_query'],
        optimized_results['results'][0]['title'][:40] + "..." if optimized_results['results'] else "No results"
    )

    # Memory search
    table.add_row(
        "With Memory",
        str(memory_results['total_found']),
        memory_results['optimized_query'][:40] + "..." if len(memory_results['optimized_query']) > 40 else memory_results['optimized_query'],
        memory_results['results'][0]['title'][:40] + "..." if memory_results['results'] else "No results"
    )

    console.print(table)

    # Show optimization reasoning if available
    if optimized_results.get('reasoning'):
        console.print("\n[bold]Optimization Reasoning:[/bold]")
        console.print(f"[dim]{optimized_results['reasoning']}[/dim]")


@search_app.command("extract-entities")
def extract_entities(
    video_id: str = typer.Argument(..., help="YouTube video ID or URL"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file for entities"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, table"),
):
    """
    Extract named entities from a YouTube video transcript
    
    Examples:
        youtube-transcripts search extract-entities dQw4w9WgXcQ
        youtube-transcripts search extract-entities "https://youtube.com/watch?v=dQw4w9WgXcQ" -o entities.json
    """

    # Initialize systems
    initialize_database()
    config = UnifiedSearchConfig()
    search_system = UnifiedYouTubeSearch(config)

    # Extract video ID from URL if needed
    if "youtube.com" in video_id or "youtu.be" in video_id:
        import re
        match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', video_id)
        if match:
            video_id = match.group(1)

    # Get transcript
    transcript = get_transcript_by_video_id(video_id)
    if not transcript:
        console.print(f"[red]Error: No transcript found for video ID: {video_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Extracting entities from:[/bold] {transcript['title']}\n")

    # Extract entities
    with console.status("[bold green]Analyzing transcript..."):
        entities = search_system.graph_memory.extract_entities_from_transcript(
            transcript_text=transcript['content'],
            metadata={
                'video_id': video_id,
                'title': transcript['title'],
                'channel_name': transcript['channel_name']
            }
        )

    # Display results
    if format == "table":
        table = Table(title="Extracted Entities")
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Properties", style="yellow")

        for entity in entities:
            props = json.dumps(entity.get('properties', {}), indent=2)
            table.add_row(entity['type'], entity['name'], props)

        console.print(table)
    else:
        console.print(json.dumps(entities, indent=2))

    # Save if output specified
    if output:
        with open(output, 'w') as f:
            json.dump({
                'video_id': video_id,
                'title': transcript['title'],
                'entities': entities
            }, f, indent=2)
        console.print(f"\n[green]✓ Entities saved to {output}[/green]")

    console.print(f"\n[bold]Total entities found: {len(entities)}[/bold]")


@search_app.command("find-relationships")
def find_relationships(
    video_id1: str = typer.Argument(..., help="First video ID"),
    video_id2: str = typer.Argument(..., help="Second video ID"),
    visualize: bool = typer.Option(False, "--visualize", "-v", help="Generate visualization"),
):
    """
    Find relationships between two YouTube videos based on their content
    
    Examples:
        youtube-transcripts search find-relationships VIDEO_ID1 VIDEO_ID2
        youtube-transcripts search find-relationships VIDEO_ID1 VIDEO_ID2 --visualize
    """

    # Initialize systems
    initialize_database()
    config = UnifiedSearchConfig()
    search_system = UnifiedYouTubeSearch(config)

    # Get transcripts
    transcript1 = get_transcript_by_video_id(video_id1)
    transcript2 = get_transcript_by_video_id(video_id2)

    if not transcript1 or not transcript2:
        console.print("[red]Error: Could not find both transcripts[/red]")
        raise typer.Exit(1)

    console.print("[bold]Analyzing relationships between:[/bold]")
    console.print(f"1. {transcript1['title']}")
    console.print(f"2. {transcript2['title']}\n")

    # Extract relationships
    with console.status("[bold green]Finding relationships..."):
        relationships = search_system.graph_memory.extract_relationships_between_transcripts(
            transcript1, transcript2
        )

    # Display relationships
    table = Table(title="Discovered Relationships")
    table.add_column("Type", style="cyan")
    table.add_column("Direction", style="green")
    table.add_column("Properties", style="yellow")

    for rel in relationships:
        direction = f"{video_id1[:8]}... → {video_id2[:8]}..."
        if rel['from_id'] == video_id2:
            direction = f"{video_id2[:8]}... → {video_id1[:8]}..."

        props = json.dumps(rel.get('properties', {}), indent=2)
        table.add_row(rel['type'], direction, props)

    console.print(table)
    console.print(f"\n[bold]Total relationships found: {len(relationships)}[/bold]")

    if visualize:
        console.print("\n[yellow]Visualization feature not yet implemented[/yellow]")


@search_app.command("graph-search")
def graph_search(
    query: str = typer.Argument(..., help="Search query"),
    depth: int = typer.Option(2, "--depth", "-d", help="Graph traversal depth"),
    use_hybrid: bool = typer.Option(True, "--hybrid/--no-hybrid", help="Use hybrid search"),
):
    """
    Search using ArangoDB graph-based knowledge
    
    Examples:
        youtube-transcripts search graph-search "VERL training"
        youtube-transcripts search graph-search "Monte Carlo" --depth 3
    """
    # Initialize systems
    config = UnifiedSearchConfig()
    search_system = UnifiedYouTubeSearch(config)

    if not search_system.graph_memory.enabled:
        console.print("[red]Error: ArangoDB is not available[/red]")
        console.print("Please ensure ArangoDB is running and configured")
        raise typer.Exit(1)

    console.print(f"[bold]Graph Search:[/bold] {query}")
    console.print(f"[dim]Depth: {depth}, Hybrid: {use_hybrid}[/dim]\n")

    # Execute graph search
    with console.status("[bold green]Searching knowledge graph..."):
        results = search_system.graph_memory.search_with_arango_hybrid(
            query=query,
            limit=20
        )

    if not results:
        console.print("[yellow]No results found in knowledge graph[/yellow]")
        return

    # Display results
    table = Table(title="Graph Search Results")
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Type", style="green")
    table.add_column("Score", justify="right")

    for result in results[:10]:
        table.add_row(
            result['title'][:50] + "..." if len(result['title']) > 50 else result['title'],
            result.get('source', 'unknown'),
            f"{result.get('score', 0):.3f}"
        )

    console.print(table)
    console.print(f"\n[bold]Total results: {len(results)}[/bold]")


# If using as a separate module, export the app
def register_commands(app: typer.Typer):
    """Register search commands with the main app"""
    app.add_typer(search_app, name="search", help="Advanced search commands")


# Standalone usage
if __name__ == "__main__":
    search_app()
