# YOUTUBE TRANSCRIPTS CONTEXT — CLAUDE.md

> **Inherits standards from global and workspace CLAUDE.md files with overrides below.**

## Project Context
**Purpose:** YouTube video transcript extraction and analysis  
**Type:** Processing Spoke  
**Status:** Active

## Project-Specific Overrides

### Special Dependencies
```toml
# YouTube Transcripts requires video and search libraries
google-api-python-client = "^2.100.0"
youtube-transcript-api = "^0.6.0"
sqlite-fts5 = "^0.1.0"
yt-dlp = "^2023.9.24"
```

### Environment Variables
```bash
# .env additions for YouTube Transcripts
YOUTUBE_API_KEY=your_youtube_api_key
YOUTUBE_DATA_DIR=/home/graham/workspace/data/youtube
SQLITE_DB_PATH=youtube_transcripts.db
ENABLE_METADATA_EXTRACTION=true
MAX_TRANSCRIPT_LENGTH=50000
```

### Special Considerations
- **API Limits:** YouTube API v3 has daily quota restrictions
- **SQLite FTS5:** Full-text search requires SQLite with FTS5 extension
- **Progressive Search:** Implements widening search strategies
- **Async Processing:** Agent system for background transcript processing

---

## License

MIT License — see [LICENSE](LICENSE) for details.