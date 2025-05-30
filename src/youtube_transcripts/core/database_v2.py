"""
Enhanced database module with scientific metadata support.

This module extends the original database with JSON fields for storing
extracted metadata while maintaining backward compatibility.

External Documentation:
- SQLite JSON1: https://www.sqlite.org/json1.html
- FTS5: https://www.sqlite.org/fts5.html
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..config import DB_PATH


def initialize_database(db_path: Path = DB_PATH) -> None:
    """Initialize SQLite database with enhanced schema including metadata fields."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create main transcripts table with metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcripts_metadata (
            video_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            publish_date TEXT NOT NULL,
            duration INTEGER,
            transcript TEXT NOT NULL,
            summary TEXT,
            enhanced_transcript TEXT,
            metadata JSON,
            citations JSON,
            speakers JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create FTS5 virtual table for full-text search
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS transcripts_fts
        USING fts5(
            video_id, 
            title, 
            channel_name, 
            publish_date, 
            transcript, 
            summary, 
            enhanced_transcript,
            content=transcripts_metadata,
            tokenize=porter
        )
    ''')
    
    # Create triggers to keep FTS in sync with main table
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS transcripts_metadata_ai AFTER INSERT ON transcripts_metadata BEGIN
            INSERT INTO transcripts_fts(
                video_id, title, channel_name, publish_date, 
                transcript, summary, enhanced_transcript
            ) VALUES (
                new.video_id, new.title, new.channel_name, new.publish_date,
                new.transcript, new.summary, new.enhanced_transcript
            );
        END;
    ''')
    
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS transcripts_metadata_ad AFTER DELETE ON transcripts_metadata BEGIN
            DELETE FROM transcripts_fts WHERE video_id = old.video_id;
        END;
    ''')
    
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS transcripts_metadata_au AFTER UPDATE ON transcripts_metadata BEGIN
            UPDATE transcripts_fts SET
                title = new.title,
                channel_name = new.channel_name,
                publish_date = new.publish_date,
                transcript = new.transcript,
                summary = new.summary,
                enhanced_transcript = new.enhanced_transcript
            WHERE video_id = new.video_id;
        END;
    ''')
    
    # Create indexes for efficient queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transcripts_publish_date 
        ON transcripts_metadata(publish_date DESC)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transcripts_channel 
        ON transcripts_metadata(channel_name)
    ''')
    
    conn.commit()
    conn.close()


def migrate_from_v1(db_path: Path = DB_PATH) -> None:
    """Migrate from v1 database (FTS5 only) to v2 (separate tables with metadata)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if migration is needed
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='transcripts_metadata'
    """)
    if cursor.fetchone():
        print("Database already migrated to v2")
        return
    
    print("Migrating database to v2...")
    
    # Read all data from v1 FTS table
    cursor.execute('''
        SELECT video_id, title, channel_name, publish_date, 
               transcript, summary, enhanced_transcript
        FROM transcripts
    ''')
    old_data = cursor.fetchall()
    
    # Initialize v2 schema
    initialize_database(db_path)
    
    # Insert data into new schema
    for row in old_data:
        cursor.execute('''
            INSERT OR IGNORE INTO transcripts_metadata (
                video_id, title, channel_name, publish_date, 
                transcript, summary, enhanced_transcript
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', row)
    
    # Rename old table
    cursor.execute('ALTER TABLE transcripts RENAME TO transcripts_v1_backup')
    
    conn.commit()
    conn.close()
    
    print(f"Migrated {len(old_data)} transcripts to v2 schema")


def add_transcript(video_id: str, title: str, channel_name: str, publish_date: str, 
                  transcript: str, summary: str = '', enhanced_transcript: str = '',
                  duration: Optional[int] = None, metadata: Optional[Dict] = None,
                  citations: Optional[List[Dict]] = None, speakers: Optional[List[Dict]] = None,
                  db_path: Path = DB_PATH) -> None:
    """Add or update a transcript with metadata."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Convert metadata to JSON strings
    metadata_json = json.dumps(metadata) if metadata else None
    citations_json = json.dumps(citations) if citations else None
    speakers_json = json.dumps(speakers) if speakers else None
    
    cursor.execute('''
        INSERT OR REPLACE INTO transcripts_metadata (
            video_id, title, channel_name, publish_date, duration,
            transcript, summary, enhanced_transcript,
            metadata, citations, speakers, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (video_id, title, channel_name, publish_date, duration,
          transcript, summary, enhanced_transcript,
          metadata_json, citations_json, speakers_json))
    
    conn.commit()
    conn.close()


def update_metadata(video_id: str, metadata: Dict[str, Any], 
                   db_path: Path = DB_PATH) -> None:
    """Update only the metadata fields for a transcript."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Extract specific metadata fields
    citations = metadata.get('citations', [])
    speakers = metadata.get('speakers', [])
    
    # Remove citations and speakers from general metadata
    general_metadata = {k: v for k, v in metadata.items() 
                       if k not in ['citations', 'speakers']}
    
    cursor.execute('''
        UPDATE transcripts_metadata
        SET metadata = ?, citations = ?, speakers = ?, updated_at = CURRENT_TIMESTAMP
        WHERE video_id = ?
    ''', (json.dumps(general_metadata), json.dumps(citations), 
          json.dumps(speakers), video_id))
    
    conn.commit()
    conn.close()


def search_transcripts(query: str, channel_names: Optional[List[str]] = None,
                      limit: int = 10, filters: Optional[Dict] = None,
                      db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Search transcripts with optional metadata filters."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Base query joining FTS with metadata table
    if query and query.strip():
        # Use FTS for text search
        base_query = '''
            SELECT 
                m.video_id, m.title, m.channel_name, m.publish_date, 
                m.transcript, m.summary, m.enhanced_transcript, m.duration,
                m.metadata, m.citations, m.speakers,
                f.rank
            FROM transcripts_fts f
            JOIN transcripts_metadata m ON f.video_id = m.video_id
            WHERE f.transcripts_fts MATCH ?
        '''
        params = [query]
    else:
        # No text search, just browse
        base_query = '''
            SELECT 
                video_id, title, channel_name, publish_date, 
                transcript, summary, enhanced_transcript, duration,
                metadata, citations, speakers,
                0 as rank
            FROM transcripts_metadata
            WHERE 1=1
        '''
        params = []
    
    # Add channel filter
    if channel_names:
        placeholders = ','.join(['?' for _ in channel_names])
        base_query += f' AND m.channel_name IN ({placeholders})'
        params.extend(channel_names)
    
    # Add metadata filters
    if filters:
        if 'has_citations' in filters and filters['has_citations']:
            base_query += ' AND m.citations IS NOT NULL'
        
        if 'institution' in filters:
            base_query += """ AND json_extract(m.metadata, '$.institutions') 
                            LIKE '%' || ? || '%'"""
            params.append(filters['institution'])
        
        if 'content_type' in filters:
            base_query += """ AND json_extract(m.metadata, '$.content_type') = ?"""
            params.append(filters['content_type'])
    
    # Order and limit
    if query and query.strip():
        base_query += ' ORDER BY f.rank'
    else:
        base_query += ' ORDER BY m.publish_date DESC'
    
    base_query += ' LIMIT ?'
    params.append(limit)
    
    cursor.execute(base_query, params)
    results = cursor.fetchall()
    conn.close()
    
    # Parse results
    transcripts = []
    for r in results:
        transcript = {
            'video_id': r[0],
            'title': r[1],
            'channel_name': r[2],
            'publish_date': r[3],
            'transcript': r[4],
            'summary': r[5],
            'enhanced_transcript': r[6],
            'duration': r[7],
            'metadata': json.loads(r[8]) if r[8] else {},
            'citations': json.loads(r[9]) if r[9] else [],
            'speakers': json.loads(r[10]) if r[10] else [],
            'rank': r[11]
        }
        transcripts.append(transcript)
    
    return transcripts


def get_transcript_by_video_id(video_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Get a transcript with all metadata by video ID."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            video_id, title, channel_name, publish_date, 
            transcript, summary, enhanced_transcript, duration,
            metadata, citations, speakers
        FROM transcripts_metadata
        WHERE video_id = ?
    ''', [video_id])
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'video_id': result[0],
            'title': result[1],
            'channel_name': result[2],
            'published_at': result[3],
            'content': result[4],
            'summary': result[5],
            'enhanced_transcript': result[6],
            'duration': result[7],
            'metadata': json.loads(result[8]) if result[8] else {},
            'citations': json.loads(result[9]) if result[9] else [],
            'speakers': json.loads(result[10]) if result[10] else []
        }
    
    return None


def cleanup_old_transcripts(months: int, db_path: Path = DB_PATH) -> int:
    """Remove transcripts older than specified months."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=months * 30)).strftime('%Y-%m-%d')
    
    # Count records to delete
    cursor.execute(
        'SELECT COUNT(*) FROM transcripts_metadata WHERE publish_date < ?', 
        (cutoff_date,)
    )
    deleted_count = cursor.fetchone()[0]
    
    # Delete from main table (triggers will handle FTS)
    cursor.execute(
        'DELETE FROM transcripts_metadata WHERE publish_date < ?', 
        (cutoff_date,)
    )
    
    conn.commit()
    conn.close()
    
    return deleted_count


# Maintain backward compatibility
def search_transcripts_v1(*args, **kwargs):
    """Legacy search function for backward compatibility."""
    # Remove v2-specific parameters
    kwargs.pop('filters', None)
    results = search_transcripts(*args, **kwargs)
    
    # Remove v2-specific fields
    for r in results:
        r.pop('metadata', None)
        r.pop('citations', None)
        r.pop('speakers', None)
        r.pop('duration', None)
    
    return results


if __name__ == "__main__":
    # Test migration and new features
    from pathlib import Path
    
    test_db = Path("test_metadata.db")
    
    print("=== Database V2 Test ===\n")
    
    # Initialize database
    initialize_database(test_db)
    print("✓ Database initialized")
    
    # Add test transcript with metadata
    test_metadata = {
        'urls': ['https://arxiv.org/abs/2301.00234', 'https://github.com/test/repo'],
        'institutions': ['MIT', 'Stanford'],
        'keywords': ['machine learning', 'transformers'],
        'technical_terms': ['BERT', 'GPT-4']
    }
    
    test_citations = [
        {'type': 'arxiv', 'id': '2301.00234', 'text': 'arXiv:2301.00234'},
        {'type': 'author_year', 'text': 'Devlin et al., 2019'}
    ]
    
    test_speakers = [
        {'name': 'Dr. Jane Smith', 'title': 'Professor', 'affiliation': 'MIT'}
    ]
    
    add_transcript(
        video_id='test_001',
        title='Deep Learning Lecture',
        channel_name='MIT OpenCourseWare',
        publish_date='2024-01-15',
        transcript='This is a test transcript about transformers and BERT.',
        duration=3600,
        metadata=test_metadata,
        citations=test_citations,
        speakers=test_speakers,
        db_path=test_db
    )
    print("✓ Added test transcript with metadata")
    
    # Search and verify
    results = search_transcripts('transformers', db_path=test_db)
    if results:
        r = results[0]
        print(f"\n✓ Found transcript: {r['title']}")
        print(f"  Metadata: {len(r['metadata'].get('urls', []))} URLs, "
              f"{len(r['metadata'].get('institutions', []))} institutions")
        print(f"  Citations: {len(r['citations'])} citations")
        print(f"  Speakers: {len(r['speakers'])} speakers")
    
    # Clean up
    test_db.unlink()
    print("\n✓ Database v2 test complete!")