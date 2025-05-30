#!/usr/bin/env python3
"""
Migration script to upgrade database from v1 to v2 with metadata support.

This script migrates the existing FTS5-only database to the new schema
with separate tables for metadata and maintains backward compatibility.

Usage:
    python scripts/migrate_to_v2.py [--db-path /path/to/database.db]
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.youtube_transcripts.core.database_v2 import migrate_from_v1, initialize_database
from src.youtube_transcripts.config import DB_PATH


def main():
    """Run the migration."""
    parser = argparse.ArgumentParser(description="Migrate YouTube transcripts database to v2")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help="Path to the database file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if v2 tables already exist"
    )
    
    args = parser.parse_args()
    
    if not args.db_path.exists():
        print(f"Error: Database not found at {args.db_path}")
        sys.exit(1)
    
    print(f"Migrating database: {args.db_path}")
    
    try:
        # Run migration
        migrate_from_v1(args.db_path)
        print("\n✅ Migration completed successfully!")
        
        # Show some stats
        import sqlite3
        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM transcripts_metadata")
        count = cursor.fetchone()[0]
        print(f"Total transcripts migrated: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()