#!/usr/bin/env python3
"""
Quick benchmark focusing on key differences between SQLite and ArangoDB
"""

import asyncio
import time
import os
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from youtube_transcripts.database_adapter import DatabaseAdapter
from youtube_transcripts.arango_integration import YouTubeTranscriptGraph


async def quick_benchmark():
    """Run a quick focused benchmark"""
    print("YouTube Transcripts - Quick Database Comparison")
    print("=" * 60)
    
    # Test data
    test_videos = [
        {
            'video_id': 'test_001',
            'title': 'Introduction to VERL Reinforcement Learning',
            'channel_name': 'AI Research Lab',
            'transcript': """
                Today we'll discuss VERL, a groundbreaking reinforcement learning framework.
                VERL can scale to thousands of GPUs efficiently. 
                Unlike traditional RL methods, VERL supports distributed training.
                The key innovation is in the actor-learner architecture.
                We've tested VERL on various benchmarks including Atari games.
                Results show 10x speedup compared to baseline methods.
                This work was published in arXiv:2024.12345.
            """,
            'upload_date': '2024-01-15',
            'speakers': [{'name': 'Dr. Jane Smith', 'affiliation': 'OpenAI'}]
        },
        {
            'video_id': 'test_002',
            'title': 'Scaling Laws in Deep Learning',
            'channel_name': 'ML Conference Talks',
            'transcript': """
                Scaling laws predict model performance based on compute and data.
                Recent work shows that VERL doesn't follow traditional scaling laws.
                We found that VERL can scale beyond 1000 GPUs with linear speedup.
                This contradicts earlier work that suggested diminishing returns.
                Our experiments used transformers with up to 70B parameters.
                See our paper at arXiv:2024.67890 for details.
            """,
            'upload_date': '2024-02-20',
            'speakers': [{'name': 'Prof. John Doe', 'affiliation': 'Stanford'}]
        }
    ]
    
    results = {}
    
    # Test SQLite
    print("\n1. SQLite Benchmark")
    print("-" * 40)
    
    # Initialize SQLite
    # Create temp file instead of :memory: to ensure proper initialization
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        sqlite_path = tmp.name
    
    adapter = DatabaseAdapter({'backend': 'sqlite', 'sqlite_path': sqlite_path})
    
    # Insert
    start = time.time()
    for video in test_videos:
        await adapter.store_transcript(video)
    sqlite_insert = time.time() - start
    print(f"Insert time: {sqlite_insert:.3f}s")
    
    # Search
    start = time.time()
    sqlite_results = await adapter.search("VERL reinforcement learning")
    sqlite_search = time.time() - start
    print(f"Search time: {sqlite_search*1000:.1f}ms, found {len(sqlite_results)} results")
    
    results['sqlite'] = {
        'insert_time': sqlite_insert,
        'search_time': sqlite_search,
        'search_results': len(sqlite_results)
    }
    
    # Test ArangoDB
    print("\n2. ArangoDB Benchmark")
    print("-" * 40)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize ArangoDB
        graph = YouTubeTranscriptGraph(
            db_name='youtube_benchmark_test',
            host=os.getenv('ARANGO_HOST', 'http://localhost:8529'),
            username=os.getenv('ARANGO_USER', 'root'),
            password=os.getenv('ARANGO_PASSWORD', 'openSesame')
        )
        
        # Clear existing data
        for collection in graph.collections.values():
            if graph.db.has_collection(collection):
                graph.db.collection(collection).truncate()
        
        # Insert with graph features
        start = time.time()
        for video in test_videos:
            await graph.store_transcript(video)
        arango_insert = time.time() - start
        print(f"Insert time (with embeddings): {arango_insert:.3f}s")
        
        # Hybrid search
        start = time.time()
        arango_results = await graph.hybrid_search("VERL reinforcement learning")
        arango_search = time.time() - start
        print(f"Hybrid search time: {arango_search*1000:.1f}ms, found {len(arango_results)} results")
        
        # Graph features
        start = time.time()
        network = await graph.get_citation_network('test_001')
        graph_time = time.time() - start
        print(f"Citation network retrieval: {graph_time*1000:.1f}ms")
        
        # Find contradictions (simulate)
        print("\nUnique ArangoDB Features:")
        print("- Semantic search with embeddings")
        print("- Citation network graphs")
        print("- Speaker relationship tracking")
        print("- Entity extraction and linking")
        
        results['arangodb'] = {
            'insert_time': arango_insert,
            'search_time': arango_search,
            'search_results': len(arango_results),
            'graph_time': graph_time
        }
        
    except Exception as e:
        print(f"ArangoDB test failed: {e}")
        results['arangodb'] = {'error': str(e)}
    
    # Comparison
    print("\n3. Comparison Summary")
    print("=" * 60)
    
    if 'error' not in results.get('arangodb', {}):
        print("\n| Metric | SQLite | ArangoDB | Winner |")
        print("|--------|--------|----------|--------|")
        
        # Insert speed
        sqlite_speed = 2 / results['sqlite']['insert_time']
        arango_speed = 2 / results['arangodb']['insert_time']
        winner = "SQLite" if sqlite_speed > arango_speed else "ArangoDB"
        print(f"| Insert Speed | {sqlite_speed:.0f} docs/s | {arango_speed:.0f} docs/s | {winner} |")
        
        # Search speed
        sqlite_ms = results['sqlite']['search_time'] * 1000
        arango_ms = results['arangodb']['search_time'] * 1000
        winner = "SQLite" if sqlite_ms < arango_ms else "ArangoDB"
        print(f"| Search Speed | {sqlite_ms:.1f}ms | {arango_ms:.1f}ms | {winner} |")
        
        print("\n**Key Differences:**")
        print("- SQLite: Faster for simple operations, minimal setup")
        print("- ArangoDB: Rich graph features, semantic search, better for research")
    
    # Generate report
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_path = Path(__file__).parent.parent / "docs" / "reports" / f"quick_benchmark_{timestamp}.md"
    
    report = f"""# Quick Database Benchmark Report

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Results

### SQLite
- Insert: {results['sqlite']['insert_time']:.3f}s for 2 documents
- Search: {results['sqlite']['search_time']*1000:.1f}ms
- Results found: {results['sqlite']['search_results']}

### ArangoDB
"""
    
    if 'error' not in results.get('arangodb', {}):
        report += f"""- Insert: {results['arangodb']['insert_time']:.3f}s for 2 documents (includes embeddings)
- Search: {results['arangodb']['search_time']*1000:.1f}ms
- Results found: {results['arangodb']['search_results']}
- Graph operations: {results['arangodb']['graph_time']*1000:.1f}ms

## Analysis

1. **Performance**: SQLite is {results['sqlite']['insert_time'] / results['arangodb']['insert_time']:.1f}x faster for inserts due to embedding generation overhead in ArangoDB

2. **Features**: ArangoDB provides:
   - Semantic search with embeddings
   - Graph relationships (citations, speakers)
   - Entity extraction and linking
   - Contradiction detection capabilities

3. **Use Cases**:
   - **SQLite**: Best for standalone tools, simple keyword search
   - **ArangoDB**: Best for research applications, semantic understanding
"""
    else:
        report += f"- Error: {results['arangodb']['error']}\n"
    
    report += """
## Recommendation

Both databases serve different needs:
- Use SQLite for simple, fast, standalone deployments
- Use ArangoDB when you need advanced research features and graph capabilities

The dual database support in YouTube Transcripts allows users to choose based on their needs.
"""
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    
    # Cleanup
    if 'sqlite_path' in locals():
        try:
            os.unlink(sqlite_path)
        except:
            pass


if __name__ == "__main__":
    asyncio.run(quick_benchmark())