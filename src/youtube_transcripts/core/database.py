# youtube_transcripts/core/database.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..config import DB_PATH

def initialize_database(db_path: Path = DB_PATH) -> None:
    """Initialize SQLite database with FTS5 table for BM25 search"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS transcripts
        USING fts5(video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript, tokenize=porter)
    ''')
    conn.commit()
    conn.close()

def add_transcript(video_id: str, title: str, channel_name: str, publish_date: str, 
                  transcript: str, summary: str = '', enhanced_transcript: str = '', 
                  db_path: Path = DB_PATH) -> None:
    """Add a transcript to the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO transcripts 
        (video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript))
    conn.commit()
    conn.close()

def search_transcripts(query: str, channel_names: Optional[List[str]] = None, 
                      limit: int = 10, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Search transcripts using FTS5 (BM25 ranking)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Handle empty query
    if not query or not query.strip():
        # Return all transcripts when query is empty
        base_query = '''
            SELECT video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript,
                   0 as rank
            FROM transcripts
            ORDER BY publish_date DESC
            LIMIT ?
        '''
        cursor.execute(base_query, [limit])
        results = cursor.fetchall()
        
        # If channels specified, filter in Python
        if channel_names:
            results = [r for r in results if r[2] in channel_names]
        
        conn.close()
        
        return [
            {
                'video_id': r[0],
                'title': r[1],
                'channel_name': r[2],
                'publish_date': r[3],
                'transcript': r[4],
                'summary': r[5],
                'enhanced_transcript': r[6],
                'rank': r[7]
            }
            for r in results
        ]
    
    # Clean query for FTS5 - remove special characters that cause syntax errors
    clean_query = query.replace('?', '').replace('!', '').replace(':', '').replace('"', '')
    
    # FTS5 doesn't support OR in MATCH queries like standard SQL
    # Instead, we'll use the implicit OR behavior of FTS5 where 
    # multiple words are treated as "word1 OR word2 OR word3"
    # Simply use the cleaned query as-is
    match_query = clean_query
    
    base_query = '''
        SELECT video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript,
               rank
        FROM transcripts
        WHERE transcripts MATCH ?
        ORDER BY rank
        LIMIT ?
    '''
    
    cursor.execute(base_query, [match_query, limit])
    results = cursor.fetchall()
    
    # If channels specified, filter in Python
    if channel_names:
        results = [r for r in results if r[2] in channel_names]
    
    conn.close()
    
    return [
        {
            'video_id': r[0],
            'title': r[1],
            'channel_name': r[2],
            'publish_date': r[3],
            'transcript': r[4],
            'summary': r[5],
            'enhanced_transcript': r[6],
            'rank': r[7]
        }
        for r in results
    ]

def cleanup_old_transcripts(months: int, db_path: Path = DB_PATH) -> int:
    """Remove transcripts older than specified months"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=months * 30)).strftime('%Y-%m-%d')
    
    # First, get the count of records to delete
    cursor.execute('SELECT COUNT(*) FROM transcripts WHERE publish_date < ?', (cutoff_date,))
    deleted_count = cursor.fetchone()[0]
    
    # For FTS5 tables, we need to delete by rowid
    cursor.execute('SELECT rowid FROM transcripts WHERE publish_date < ?', (cutoff_date,))
    rowids_to_delete = [row[0] for row in cursor.fetchall()]
    
    # Delete each row by rowid
    for rowid in rowids_to_delete:
        cursor.execute('DELETE FROM transcripts WHERE rowid = ?', (rowid,))
    
    conn.commit()
    conn.close()
    
    return deleted_count


def get_transcript_by_video_id(video_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Get a transcript by video ID"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query the transcript
    cursor.execute('''
        SELECT video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript
        FROM transcripts
        WHERE video_id = ?
    ''', [video_id])
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'video_id': result[0],
            'title': result[1],
            'channel_name': result[2],
            'published_at': result[3],  # Using published_at for consistency
            'content': result[4],  # Using content instead of transcript for consistency
            'summary': result[5],
            'enhanced_transcript': result[6]
        }
    
    return None
