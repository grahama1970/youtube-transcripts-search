#!/usr/bin/env python3
"""
Migration tool for YouTube Transcripts: SQLite to ArangoDB
Migrates existing SQLite data to ArangoDB with enrichment

Usage:
    python scripts/migrate_to_arangodb.py [--sqlite-path PATH] [--batch-size N]
"""

import asyncio
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from youtube_transcripts.arango_integration import YouTubeTranscriptGraph
from youtube_transcripts.arangodb_enhanced import EnhancedYouTubeGraph
from youtube_transcripts.citation_detector import CitationDetector
from youtube_transcripts.metadata_extractor import MetadataExtractor
from youtube_transcripts.speaker_extractor import SpeakerExtractor


class YouTubeTranscriptMigrator:
    """Migrates YouTube transcripts from SQLite to ArangoDB"""
    
    def __init__(self, sqlite_path: str, use_enhanced: bool = True):
        self.sqlite_path = sqlite_path
        self.graph = EnhancedYouTubeGraph() if use_enhanced else YouTubeTranscriptGraph()
        
        # Initialize extractors
        self.citation_detector = CitationDetector()
        self.metadata_extractor = MetadataExtractor()
        self.speaker_extractor = SpeakerExtractor()
        
        # Statistics
        self.stats = {
            'total_videos': 0,
            'migrated': 0,
            'enriched': 0,
            'failed': 0,
            'citations_found': 0,
            'entities_found': 0,
            'speakers_found': 0
        }
    
    async def migrate(self, batch_size: int = 100, enrich: bool = True):
        """
        Perform the migration
        
        Args:
            batch_size: Number of records to process at once
            enrich: Whether to enrich data during migration
        """
        print(f"Starting migration from {self.sqlite_path} to ArangoDB")
        print(f"Enrichment: {'Enabled' if enrich else 'Disabled'}")
        print(f"Batch size: {batch_size}")
        
        # Connect to SQLite
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Count total videos
        cursor.execute("SELECT COUNT(*) as count FROM transcripts")
        self.stats['total_videos'] = cursor.fetchone()['count']
        print(f"Total videos to migrate: {self.stats['total_videos']}")
        
        # Migrate in batches
        offset = 0
        
        while True:
            # Fetch batch
            cursor.execute("""
                SELECT * FROM transcripts 
                ORDER BY rowid 
                LIMIT ? OFFSET ?
            """, (batch_size, offset))
            
            rows = cursor.fetchall()
            if not rows:
                break
            
            # Process batch
            await self._process_batch(rows, enrich)
            
            offset += batch_size
            
            # Progress update
            progress = (self.stats['migrated'] / self.stats['total_videos']) * 100
            print(f"Progress: {self.stats['migrated']}/{self.stats['total_videos']} ({progress:.1f}%)")
        
        # Migrate related tables
        await self._migrate_citations(conn)
        await self._migrate_speakers(conn)
        await self._migrate_evidence(conn)
        
        conn.close()
        
        # Final report
        self._print_final_report()
    
    async def _process_batch(self, rows: List[sqlite3.Row], enrich: bool):
        """Process a batch of videos"""
        tasks = []
        
        for row in rows:
            video_data = self._row_to_dict(row)
            
            if enrich:
                video_data = await self._enrich_video_data(video_data)
            
            tasks.append(self._migrate_video(video_data))
        
        # Process all videos in batch concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        for result in results:
            if isinstance(result, Exception):
                self.stats['failed'] += 1
                print(f"Failed to migrate video: {result}")
            else:
                self.stats['migrated'] += 1
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary"""
        video_data = dict(row)
        
        # Parse metadata if stored as JSON
        if 'metadata' in video_data and video_data['metadata']:
            try:
                video_data['metadata'] = json.loads(video_data['metadata'])
            except:
                video_data['metadata'] = {}
        
        # Ensure required fields
        video_data['upload_date'] = video_data.get('publish_date', '')
        
        return video_data
    
    async def _enrich_video_data(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich video data with extracted information"""
        transcript = video_data.get('transcript', '')
        
        if not transcript:
            return video_data
        
        try:
            # Extract citations
            citations = self.citation_detector.detect_citations(transcript)
            video_data['citations'] = [
                {
                    'type': c.type,
                    'id': c.id,
                    'text': c.text,
                    'context': c.context,
                    'confidence': c.confidence
                }
                for c in citations
            ]
            self.stats['citations_found'] += len(citations)
            
            # Extract metadata/entities
            metadata = self.metadata_extractor.extract_entities(transcript)
            video_data['entities'] = metadata.get('entities', [])
            self.stats['entities_found'] += len(video_data['entities'])
            
            # Extract speakers
            speakers = self.speaker_extractor.extract_speakers(transcript)
            video_data['speakers'] = speakers
            self.stats['speakers_found'] += len(speakers)
            
            self.stats['enriched'] += 1
            
        except Exception as e:
            print(f"Failed to enrich video {video_data.get('video_id')}: {e}")
        
        return video_data
    
    async def _migrate_video(self, video_data: Dict[str, Any]):
        """Migrate a single video to ArangoDB"""
        try:
            # Store in ArangoDB
            if hasattr(self.graph, 'extract_and_link_entities'):
                # Use enhanced features if available
                video_data = await self.graph.extract_and_link_entities(video_data)
            
            await self.graph.store_transcript(video_data)
            
        except Exception as e:
            raise Exception(f"Failed to migrate {video_data.get('video_id')}: {e}")
    
    async def _migrate_citations(self, conn: sqlite3.Connection):
        """Migrate citations table if it exists"""
        cursor = conn.cursor()
        
        # Check if citations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='citations'
        """)
        
        if not cursor.fetchone():
            return
        
        print("\nMigrating citations...")
        
        cursor.execute("SELECT * FROM citations")
        citations = cursor.fetchall()
        
        # Group by video_id
        video_citations = {}
        for row in citations:
            video_id = row['video_id']
            if video_id not in video_citations:
                video_citations[video_id] = []
            
            video_citations[video_id].append({
                'type': row['citation_type'],
                'id': row['identifier'],
                'text': row['text'],
                'context': row.get('context', ''),
                'confidence': row.get('confidence', 1.0)
            })
        
        # Update videos with citations
        for video_id, citations in video_citations.items():
            try:
                video = await self.graph.get_transcript(video_id)
                if video:
                    video['citations'] = citations
                    await self.graph.store_transcript(video)
            except Exception as e:
                print(f"Failed to migrate citations for {video_id}: {e}")
    
    async def _migrate_speakers(self, conn: sqlite3.Connection):
        """Migrate speakers if table exists"""
        cursor = conn.cursor()
        
        # Check if speakers table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='speakers'
        """)
        
        if not cursor.fetchone():
            return
        
        print("\nMigrating speakers...")
        
        # Get all speakers with their video associations
        cursor.execute("""
            SELECT s.*, vs.video_id, vs.role
            FROM speakers s
            JOIN video_speakers vs ON s.id = vs.speaker_id
        """)
        
        # Group by video
        video_speakers = {}
        for row in cursor.fetchall():
            video_id = row['video_id']
            if video_id not in video_speakers:
                video_speakers[video_id] = []
            
            video_speakers[video_id].append({
                'name': row['name'],
                'title': row.get('title', ''),
                'affiliation': row.get('affiliation', ''),
                'role': row.get('role', 'speaker')
            })
        
        # Update videos with speakers
        for video_id, speakers in video_speakers.items():
            try:
                video = await self.graph.get_transcript(video_id)
                if video:
                    video['speakers'] = speakers
                    await self.graph.store_transcript(video)
            except Exception as e:
                print(f"Failed to migrate speakers for {video_id}: {e}")
    
    async def _migrate_evidence(self, conn: sqlite3.Connection):
        """Migrate evidence table if it exists"""
        cursor = conn.cursor()
        
        # Check if evidence table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='evidence'
        """)
        
        if not cursor.fetchone():
            return
        
        print("\nMigrating evidence...")
        
        # Evidence would be stored separately in ArangoDB
        # This is a placeholder for future implementation
    
    def _print_final_report(self):
        """Print migration summary"""
        print("\n" + "="*60)
        print("MIGRATION COMPLETE")
        print("="*60)
        
        print(f"\nTotal videos: {self.stats['total_videos']}")
        print(f"Successfully migrated: {self.stats['migrated']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Success rate: {(self.stats['migrated']/self.stats['total_videos']*100):.1f}%")
        
        if self.stats['enriched'] > 0:
            print(f"\nEnrichment Statistics:")
            print(f"Videos enriched: {self.stats['enriched']}")
            print(f"Citations found: {self.stats['citations_found']}")
            print(f"Entities found: {self.stats['entities_found']}")
            print(f"Speakers found: {self.stats['speakers_found']}")
        
        print(f"\nMigration completed at: {datetime.now().isoformat()}")


async def verify_migration(sqlite_path: str, sample_size: int = 10):
    """Verify migration by comparing SQLite and ArangoDB data"""
    print("\n" + "="*60)
    print("VERIFYING MIGRATION")
    print("="*60)
    
    # Connect to SQLite
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get sample videos from SQLite
    cursor.execute(f"SELECT video_id, title FROM transcripts LIMIT {sample_size}")
    sqlite_videos = cursor.fetchall()
    
    # Initialize ArangoDB
    graph = YouTubeTranscriptGraph()
    
    # Verify each video
    verified = 0
    for row in sqlite_videos:
        video_id = row['video_id']
        
        # Get from ArangoDB
        arango_video = await graph.get_transcript(video_id)
        
        if arango_video:
            print(f"✅ {video_id}: {row['title'][:50]}...")
            verified += 1
        else:
            print(f"❌ {video_id}: Not found in ArangoDB")
    
    print(f"\nVerification: {verified}/{len(sqlite_videos)} videos found in ArangoDB")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate YouTube transcripts from SQLite to ArangoDB"
    )
    parser.add_argument(
        "--sqlite-path",
        default="youtube_transcripts.db",
        help="Path to SQLite database (default: youtube_transcripts.db)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of videos to process in each batch (default: 100)"
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip enrichment during migration"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration after completion"
    )
    parser.add_argument(
        "--use-basic",
        action="store_true",
        help="Use basic graph instead of enhanced"
    )
    
    args = parser.parse_args()
    
    # Check if SQLite database exists
    if not Path(args.sqlite_path).exists():
        print(f"Error: SQLite database not found at {args.sqlite_path}")
        sys.exit(1)
    
    # Run migration
    async def run():
        migrator = YouTubeTranscriptMigrator(
            args.sqlite_path,
            use_enhanced=not args.use_basic
        )
        
        await migrator.migrate(
            batch_size=args.batch_size,
            enrich=not args.no_enrich
        )
        
        if args.verify:
            await verify_migration(args.sqlite_path)
    
    asyncio.run(run())


if __name__ == "__main__":
    main()