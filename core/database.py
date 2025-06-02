# youtube_transcripts/core/database.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..config import DB_PATH

def initialize_database(db_path: Path = DB_PATH) -> None:
    """Initialize SQLite database with FTS5 table for BM25 search and answers table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS transcripts
        USING fts5(video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript, tokenize=porter)
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_metadata (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            channel_name TEXT,
            publish_date TEXT,
            url TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            query TEXT,
            answer TEXT,
            timestamp TEXT,
            video_ids TEXT
        )
    ''')
    conn.commit()
    conn.close()

def store_transcript(
    video_id: str,
    title: str,
    channel_name: str,
    publish_date: datetime,
    transcript: str,
    summary: str,
    enhanced_transcript: str,
    db_path: Path = DB_PATH
) -> None:
    """Store transcript, summary, and enhanced transcript in SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO video_metadata (video_id, title, channel_name, publish_date, url)
        VALUES (?, ?, ?, ?, ?)
    ''', (video_id, title, channel_name, publish_date.strftime('%Y-%m-%d'), f"https://www.youtube.com/watch?v={video_id}"))
    cursor.execute('''
        INSERT INTO transcripts (video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (video_id, title, channel_name, publish_date.strftime('%Y-%m-%d'), transcript, summary, enhanced_transcript))
    conn.commit()
    conn.close()

def cleanup_old_transcripts(max_age_months: int, db_path: Path = DB_PATH) -> int:
    """Remove transcripts older than max_age_months to manage database size."""
    cutoff_date = datetime.now() - timedelta(days=max_age_months * 30)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM video_metadata
        WHERE publish_date < ?
    ''', (cutoff_date.strftime('%Y-%m-%d'),))
    cursor.execute('''
        DELETE FROM transcripts
        WHERE publish_date < ?
    ''', (cutoff_date.strftime('%Y-%m-%d'),))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

def check_transcript_exists(video_id: str, db_path: Path = DB_PATH) -> bool:
    """Check if a transcript exists for the given video ID."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT video_id FROM video_metadata WHERE video_id = ?", (video_id,))
    exists = bool(cursor.fetchone())
    conn.close()
    return exists

def store_answer(query: str, answer: str, video_ids: List[str], db_path: Path = DB_PATH) -> None:
    """Store Gemini's answer in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO answers (query, answer, timestamp, video_ids)
        VALUES (?, ?, ?, ?)
    ''', (query, answer, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ','.join(video_ids)))
    conn.commit()
    conn.close()

def check_cached_answer(query: str, db_path: Path = DB_PATH) -> Optional[tuple[str, str]]:
    """Check if the query has a cached answer."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT answer, video_ids FROM answers WHERE query = ?", (query,))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Initialize database
    total_tests += 1
    try:
        initialize_database()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcripts'")
        if not cursor.fetchone():
            all_validation_failures.append("Transcripts table not created")
        conn.close()
    except Exception as e:
        all_validation_failures.append(f"Database initialization failed: {str(e)}")

    # Test 2: Store transcript
    total_tests += 1
    try:
        test_video_id = "test123"
        store_transcript(
            video_id=test_video_id,
            title="Test Video",
            channel_name="Test Channel",
            publish_date=datetime.now(),
            transcript="This is a test transcript.",
            summary="Test summary.",
            enhanced_transcript="Enhanced test transcript."
        )
        if not check_transcript_exists(test_video_id):
            all_validation_failures.append("Transcript not stored correctly")
    except Exception as e:
        all_validation_failures.append(f"Store transcript failed: {str(e)}")

    # Test 3: Cleanup old transcripts
    total_tests += 1
    try:
        deleted = cleanup_old_transcripts(max_age_months=0)  # Should delete all
        if deleted < 1:
            all_validation_failures.append("Cleanup did not delete test transcript")
    except Exception as e:
        all_validation_failures.append(f"Cleanup failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
