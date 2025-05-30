#!/bin/zsh

# setup_youtube_transcripts.zsh
# Creates youtube_transcripts project structure in /home/graham/workspace/experiments
# Run with: ./setup_youtube_transcripts.zsh

set -e  # Exit on error

# Define base directory
BASE_DIR="/home/graham/workspace/experiments/youtube_transcripts"
CRON_SCRIPT="fetch_transcripts_cron.py"
LOG_FILE="${BASE_DIR}/setup.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Function to create a file with content
create_file() {
    local file_path="$1"
    local content="$2"
    local dir_path
    dir_path=$(dirname "${file_path}")
    
    log_message "Creating directory: ${dir_path}"
    mkdir -p "${dir_path}" || { log_message "ERROR: Failed to create ${dir_path}"; exit 1; }
    
    log_message "Writing to: ${file_path}"
    printf '%s\n' "${content}" > "${file_path}" || { log_message "ERROR: Failed to write ${file_path}"; exit 1; }
    
    log_message "Setting permissions for: ${file_path}"
    chmod 644 "${file_path}" || { log_message "ERROR: Failed to set permissions for ${file_path}"; exit 1; }
    
    log_message "Created: ${file_path}"
}

# Function to verify file creation
verify_files() {
    local missing_files=0
    for file in "$@"; do
        if [[ ! -f "${file}" ]]; then
            log_message "ERROR: Missing file: ${file}"
            ((missing_files++))
        fi
    done
    return ${missing_files}
}

# Create log file directory
log_message "Creating log file directory"
mkdir -p "$(dirname "${LOG_FILE}")" || { echo "ERROR: Failed to create log directory"; exit 1; }
touch "${LOG_FILE}" || { echo "ERROR: Failed to create ${LOG_FILE}"; exit 1; }

log_message "Starting setup in ${BASE_DIR}..."

# Create directory structure
log_message "Creating base directory structure"
mkdir -p "${BASE_DIR}"/{core,cli,mcp} || { log_message "ERROR: Failed to create directories"; exit 1; }

# Content for config.py
read -r -d '' CONFIG_PY << 'EOF' || true
# youtube_transcripts/config.py
import os
from pathlib import Path

# Environment variables or defaults
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY')
DB_PATH = Path('youtube_transcripts.db')
DEFAULT_CHANNEL = 'https://www.youtube.com/@TrelisResearch'
DEFAULT_DATE_CUTOFF = '6 months'
DEFAULT_CLEANUP_MONTHS = 12
ADVANCED_INFERENCE_PATH = Path('./ADVANCED-inference')
EOF

# Content for core/database.py
read -r -d '' DATABASE_PY << 'EOF' || true
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
    
    base_query = '''
        SELECT video_id, title, channel_name, publish_date, transcript, summary, enhanced_transcript,
               rank
        FROM transcripts
        WHERE transcripts MATCH ?
    '''
    
    if channel_names:
        placeholders = ','.join(['?' for _ in channel_names])
        base_query += f' AND channel_name IN ({placeholders})'
        params = [query] + channel_names
    else:
        params = [query]
    
    base_query += ' ORDER BY rank LIMIT ?'
    params.append(limit)
    
    cursor.execute(base_query, params)
    results = cursor.fetchall()
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
    cursor.execute('DELETE FROM transcripts WHERE publish_date < ?', (cutoff_date,))
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    return deleted_count
EOF

# Content for core/transcript.py
read -r -d '' TRANSCRIPT_PY << 'EOF' || true
# youtube_transcripts/core/transcript.py
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import Channel, YouTube
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re

from .database import add_transcript, cleanup_old_transcripts

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*&v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_channel_videos(channel_url: str, date_cutoff: Optional[datetime] = None) -> List[Dict[str, str]]:
    """Get all videos from a channel with optional date filtering"""
    try:
        channel = Channel(channel_url)
        videos = []
        
        for video_url in channel.video_urls:
            try:
                yt = YouTube(video_url)
                
                # Skip if video is older than cutoff
                if date_cutoff and yt.publish_date and yt.publish_date < date_cutoff:
                    continue
                
                videos.append({
                    'url': video_url,
                    'video_id': extract_video_id(video_url),
                    'title': yt.title,
                    'publish_date': yt.publish_date.strftime('%Y-%m-%d') if yt.publish_date else '',
                    'channel_name': yt.author
                })
            except Exception as e:
                print(f"Error processing video {video_url}: {e}")
                continue
                
        return videos
    except Exception as e:
        print(f"Error accessing channel {channel_url}: {e}")
        return []

def fetch_transcript(video_id: str) -> Optional[str]:
    """Fetch transcript for a video"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = ' '.join([entry['text'] for entry in transcript_list])
        return transcript
    except Exception as e:
        print(f"Error fetching transcript for {video_id}: {e}")
        return None

def process_channels(channel_urls: List[str], date_cutoff: Optional[str] = None, 
                    cleanup_months: Optional[int] = None) -> Tuple[int, int]:
    """Process multiple channels and store transcripts"""
    # Parse date cutoff
    cutoff_date = None
    if date_cutoff:
        if date_cutoff.endswith('months'):
            months = int(date_cutoff.split()[0])
            cutoff_date = datetime.now() - timedelta(days=months * 30)
        else:
            cutoff_date = datetime.strptime(date_cutoff, '%Y-%m-%d')
    
    # Cleanup old transcripts
    deleted_count = 0
    if cleanup_months:
        deleted_count = cleanup_old_transcripts(cleanup_months)
    
    # Process channels
    processed_count = 0
    for channel_url in channel_urls:
        videos = get_channel_videos(channel_url, cutoff_date)
        
        for video in videos:
            video_id = video['video_id']
            if not video_id:
                continue
                
            transcript = fetch_transcript(video_id)
            if transcript:
                add_transcript(
                    video_id=video_id,
                    title=video['title'],
                    channel_name=video['channel_name'],
                    publish_date=video['publish_date'],
                    transcript=transcript
                )
                processed_count += 1
    
    return processed_count, deleted_count
EOF

# Content for core/validators.py
read -r -d '' VALIDATORS_PY << 'EOF' || true
# youtube_transcripts/core/validators.py
import re
from datetime import datetime
from typing import Optional

def validate_youtube_url(url: str) -> bool:
    """Validate YouTube channel or video URL"""
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/@[\w-]+/?$',  # New channel format
        r'^https?://(?:www\.)?youtube\.com/c/[\w-]+/?$',  # /c/ format
        r'^https?://(?:www\.)?youtube\.com/channel/[\w-]+/?$',  # /channel/ format
        r'^https?://(?:www\.)?youtube\.com/user/[\w-]+/?$',  # /user/ format
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]{11}',  # Video URL
        r'^https?://youtu\.be/[\w-]{11}'  # Short video URL
    ]
    
    return any(re.match(pattern, url) for pattern in patterns)

def validate_date_cutoff(date_str: str) -> Optional[str]:
    """Validate date cutoff string"""
    # Check for relative date (e.g., "6 months")
    relative_pattern = r'^(\d+)\s*months?$'
    match = re.match(relative_pattern, date_str.lower())
    if match:
        return date_str
    
    # Check for absolute date (YYYY-MM-DD)
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        return None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename.strip()
EOF

# Content for mcp/schemas.py
read -r -d '' SCHEMAS_PY << 'EOF' || true
# youtube_transcripts/mcp/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class SearchRequest(BaseModel):
    """Request schema for searching transcripts"""
    query: str = Field(..., description="Search query for finding relevant transcripts")
    channels: Optional[List[str]] = Field(None, description="Filter by specific channel URLs")
    limit: int = Field(10, description="Maximum number of results to return")

class SearchResult(BaseModel):
    """Individual search result"""
    video_id: str
    title: str
    channel_name: str
    publish_date: str
    transcript_snippet: str
    relevance_score: float

class SearchResponse(BaseModel):
    """Response schema for search results"""
    results: List[SearchResult]
    total_results: int
    query: str

class FetchRequest(BaseModel):
    """Request schema for fetching new transcripts"""
    channel_urls: List[str] = Field(..., description="YouTube channel URLs to fetch from")
    date_cutoff: Optional[str] = Field(None, description="Date cutoff (e.g., '2025-01-01' or '6 months')")
    cleanup_months: Optional[int] = Field(None, description="Remove transcripts older than this many months")

class FetchResponse(BaseModel):
    """Response schema for fetch operation"""
    processed_count: int
    deleted_count: int
    channels_processed: List[str]
    success: bool
    message: str

class QueryRequest(BaseModel):
    """Request schema for querying with Gemini"""
    question: str = Field(..., description="Question to answer using transcripts")
    channels: Optional[List[str]] = Field(None, description="Filter by specific channel URLs")
    max_context_videos: int = Field(5, description="Maximum number of videos to use as context")

class QueryResponse(BaseModel):
    """Response schema for Gemini query"""
    answer: str
    sources: List[SearchResult]
    confidence: float
    model_used: str
EOF

# Content for mcp/formatters.py
read -r -d '' FORMATTERS_PY << 'EOF' || true
# youtube_transcripts/mcp/formatters.py
from typing import List, Dict, Any
import json
from datetime import datetime

def format_search_results(results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Format search results for MCP response"""
    formatted_results = []
    
    for result in results:
        # Create snippet from transcript
        transcript = result.get('transcript', '')
        snippet_length = 200
        
        # Try to find query terms in transcript for better snippet
        query_lower = query.lower()
        transcript_lower = transcript.lower()
        
        start_idx = transcript_lower.find(query_lower)
        if start_idx != -1:
            # Center snippet around query match
            start = max(0, start_idx - snippet_length // 2)
            end = min(len(transcript), start_idx + len(query) + snippet_length // 2)
            snippet = '...' + transcript[start:end] + '...'
        else:
            # Just take beginning of transcript
            snippet = transcript[:snippet_length] + '...' if len(transcript) > snippet_length else transcript
        
        formatted_results.append({
            'video_id': result['video_id'],
            'title': result['title'],
            'channel_name': result['channel_name'],
            'publish_date': result['publish_date'],
            'transcript_snippet': snippet,
            'relevance_score': abs(result.get('rank', 0))  # Convert negative rank to positive score
        })
    
    return {
        'results': formatted_results,
        'total_results': len(formatted_results),
        'query': query
    }

def format_fetch_response(processed_count: int, deleted_count: int, 
                         channel_urls: List[str], success: bool = True, 
                         error_message: str = '') -> Dict[str, Any]:
    """Format fetch operation response"""
    message = f"Successfully processed {processed_count} videos"
    if deleted_count > 0:
        message += f" and cleaned up {deleted_count} old transcripts"
    
    if error_message:
        message = error_message
        success = False
    
    return {
        'processed_count': processed_count,
        'deleted_count': deleted_count,
        'channels_processed': channel_urls,
        'success': success,
        'message': message
    }

def format_transcript_for_llm(results: List[Dict[str, Any]], max_videos: int = 5) -> str:
    """Format transcripts for LLM context"""
    context_parts = []
    
    for i, result in enumerate(results[:max_videos]):
        context_parts.append(f"""
Video {i+1}: {result['title']}
Channel: {result['channel_name']}
Date: {result['publish_date']}
Transcript:
{result['transcript']}
---
""")
    
    return '\n'.join(context_parts)

def format_query_response(answer: str, sources: List[Dict[str, Any]], 
                         confidence: float = 1.0, model: str = 'gemini-pro') -> Dict[str, Any]:
    """Format query response for MCP"""
    return {
        'answer': answer,
        'sources': [
            {
                'video_id': source['video_id'],
                'title': source['title'],
                'channel_name': source['channel_name'],
                'publish_date': source['publish_date'],
                'transcript_snippet': source.get('transcript', '')[:200] + '...',
                'relevance_score': abs(source.get('rank', 0))
            }
            for source in sources
        ],
        'confidence': confidence,
        'model_used': model
    }

def format_error_response(error: Exception, operation: str) -> Dict[str, Any]:
    """Format error response"""
    return {
        'success': False,
        'error': str(error),
        'error_type': type(error).__name__,
        'operation': operation,
        'timestamp': datetime.now().isoformat()
    }
EOF

# Content for mcp/schema.py
read -r -d '' SCHEMA_PY << 'EOF' || true
# youtube_transcripts/mcp/schema.py
schema = {
    "name": "youtube-transcripts",
    "version": "1.0.0",
    "description": "Search and query YouTube transcripts using Gemini",
    "tools": [
        {
            "name": "search_transcripts",
            "description": "Search through YouTube transcripts using semantic search",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Filter by channel URLs"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch_transcripts",
            "description": "Fetch and store new transcripts from YouTube channels",
            "input_schema": {
                "type": "object",
                "properties": {
                    "channel_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "YouTube channel URLs"
                    },
                    "date_cutoff": {
                        "type": "string",
                        "description": "Date cutoff (e.g., '2025-01-01' or '6 months')"
                    },
                    "cleanup_months": {
                        "type": "integer",
                        "description": "Remove transcripts older than this many months"
                    }
                },
                "required": ["channel_urls"]
            }
        },
        {
            "name": "query_transcripts",
            "description": "Query transcripts using Gemini to answer questions",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to answer"
                    },
                    "channels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Filter by channel URLs"
                    },
                    "max_context_videos": {
                        "type": "integer",
                        "description": "Max videos to use as context",
                        "default": 5
                    }
                },
                "required": ["question"]
            }
        }
    ]
}
EOF

# Content for mcp/wrapper.py
read -r -d '' WRAPPER_PY << 'EOF' || true
# youtube_transcripts/mcp/wrapper.py
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from youtube_transcripts.core.database import search_transcripts, initialize_database
from youtube_transcripts.core.transcript import process_channels
from youtube_transcripts.mcp.formatters import (
    format_search_results, format_fetch_response, 
    format_transcript_for_llm, format_query_response, format_error_response
)
from youtube_transcripts.mcp.schema import schema

# Import Gemini if available
try:
    import google.generativeai as genai
    from youtube_transcripts.config import GEMINI_API_KEY
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro')
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

def handle_search_transcripts(params):
    """Handle search_transcripts tool call"""
    try:
        query = params['query']
        channels = params.get('channels', None)
        limit = params.get('limit', 10)
        
        results = search_transcripts(query, channels, limit)
        return format_search_results(results, query)
    except Exception as e:
        return format_error_response(e, 'search_transcripts')

def handle_fetch_transcripts(params):
    """Handle fetch_transcripts tool call"""
    try:
        channel_urls = params['channel_urls']
        date_cutoff = params.get('date_cutoff', None)
        cleanup_months = params.get('cleanup_months', None)
        
        processed, deleted = process_channels(channel_urls, date_cutoff, cleanup_months)
        return format_fetch_response(processed, deleted, channel_urls)
    except Exception as e:
        return format_error_response(e, 'fetch_transcripts')

def handle_query_transcripts(params):
    """Handle query_transcripts tool call"""
    try:
        if not GEMINI_AVAILABLE:
            return {
                'success': False,
                'error': 'Gemini API not configured',
                'message': 'Please set GEMINI_API_KEY environment variable'
            }
        
        question = params['question']
        channels = params.get('channels', None)
        max_videos = params.get('max_context_videos', 5)
        
        # Search for relevant transcripts
        results = search_transcripts(question, channels, max_videos)
        
        if not results:
            return format_query_response(
                "No relevant transcripts found for your question.",
                [], 0.0
            )
        
        # Format context for LLM
        context = format_transcript_for_llm(results, max_videos)
        
        # Create prompt
        prompt = f"""Based on the following YouTube video transcripts, please answer this question: {question}

Context from videos:
{context}

Please provide a comprehensive answer based on the information in these transcripts. If the transcripts don't contain enough information to fully answer the question, please indicate what information is missing."""

        # Generate response
        response = gemini_model.generate_content(prompt)
        
        return format_query_response(
            response.text,
            results,
            confidence=0.9
        )
    except Exception as e:
        return format_error_response(e, 'query_transcripts')

def main():
    """Main MCP wrapper entry point"""
    # Initialize database
    initialize_database()
    
    # Read from stdin
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line)
            
            # Handle schema request
            if request.get('type') == 'schema':
                print(json.dumps(schema))
                sys.stdout.flush()
                continue
            
            # Handle tool calls
            tool_name = request.get('tool')
            params = request.get('params', {})
            
            if tool_name == 'search_transcripts':
                result = handle_search_transcripts(params)
            elif tool_name == 'fetch_transcripts':
                result = handle_fetch_transcripts(params)
            elif tool_name == 'query_transcripts':
                result = handle_query_transcripts(params)
            else:
                result = {'error': f'Unknown tool: {tool_name}'}
            
            print(json.dumps(result))
            sys.stdout.flush()
            
        except Exception as e:
            error_response = {'error': str(e), 'type': 'wrapper_error'}
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == '__main__':
    main()
EOF

# Content for cli/app.py (complete version)
read -r -d '' APP_PY << 'EOF' || true
# youtube_transcripts/cli/app.py
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import track
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from youtube_transcripts.config import DEFAULT_CHANNEL, DEFAULT_DATE_CUTOFF, DEFAULT_CLEANUP_MONTHS
from youtube_transcripts.core.database import initialize_database, search_transcripts
from youtube_transcripts.core.transcript import process_channels
from youtube_transcripts.core.validators import validate_youtube_url, validate_date_cutoff
from youtube_transcripts.mcp.formatters import format_transcript_for_llm

app = typer.Typer(name='youtube-transcripts')
console = Console()

@app.command()
def fetch(
    channels: str = typer.Option(DEFAULT_CHANNEL, help='Comma-separated YouTube channel URLs'),
    date_cutoff: str = typer.Option(DEFAULT_DATE_CUTOFF, help='Date cutoff (e.g., 2025-01-01 or 6 months)'),
    cleanup_months: int = typer.Option(DEFAULT_CLEANUP_MONTHS, help='Remove transcripts older than this many months')
):
    """Fetch and store YouTube transcripts with a date cutoff"""
    initialize_database()
    
    # Parse and validate channels
    channel_list = [url.strip() for url in channels.split(',')]
    invalid_channels = [url for url in channel_list if not validate_youtube_url(url)]
    
    if invalid_channels:
        console.print(f"[red]Invalid channel URLs: {', '.join(invalid_channels)}[/red]")
        raise typer.Exit(1)
    
    # Validate date cutoff
    if not validate_date_cutoff(date_cutoff):
        console.print(f"[red]Invalid date cutoff: {date_cutoff}[/red]")
        console.print("Use format: YYYY-MM-DD or 'N months'")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Fetching transcripts from {len(channel_list)} channel(s)...[/cyan]")
    console.print(f"Date cutoff: {date_cutoff}")
    
    try:
        processed, deleted = process_channels(channel_list, date_cutoff, cleanup_months)
        
        console.print(f"[green]✓ Processed {processed} transcripts[/green]")
        if deleted > 0:
            console.print(f"[yellow]✓ Cleaned up {deleted} old transcripts[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def search(
    query: str = typer.Argument(..., help='Search query'),
    channels: str = typer.Option('', help='Comma-separated YouTube channel URLs to filter'),
    limit: int = typer.Option(10, help='Maximum number of results')
):
    """Search through stored transcripts"""
    initialize_database()
    
    # Parse channels if provided
    channel_list = None
    if channels:
        channel_list = [url.strip() for url in channels.split(',')]
    
    results = search_transcripts(query, channel_list, limit)
    
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    # Create results table
    table = Table(title=f"Search Results for: {query}")
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
    except Exception as e:
        console.print("[red]Error: Gemini API not configured[/red]")
        console.print("Please set GEMINI_API_KEY environment variable")
        raise typer.Exit(1)
    
    # Parse channels
    channel_list = None
    if channels:
        channel_list = [url.strip() for url in channels.split(',')]
    
    console.print(f"[cyan]Searching for relevant content...[/cyan]")
    
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
        console.print(f"[red]Error generating response: {str(e)}[/red]")
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
EOF

# Content for fetch_transcripts_cron.py
read -r -d '' CRON_SCRIPT_PY << 'EOF' || true
#!/usr/bin/env python3
# fetch_transcripts_cron.py
"""
Cron script to fetch YouTube transcripts daily
Add to crontab: 0 2 * * * /usr/bin/python3 /path/to/fetch_transcripts_cron.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
log_file = Path(__file__).parent / 'cron.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add project to path
sys.path.append(str(Path(__file__).parent))

from youtube_transcripts.config import DEFAULT_CHANNEL, DEFAULT_CLEANUP_MONTHS
from youtube_transcripts.core.database import initialize_database
from youtube_transcripts.core.transcript import process_channels

def main():
    """Main cron job function"""
    logging.info("Starting transcript fetch job")
    
    try:
        # Initialize database
        initialize_database()
        
        # Process default channels with 6-month cutoff
        channels = [DEFAULT_CHANNEL]
        date_cutoff = "6 months"
        
        logging.info(f"Processing channels: {channels}")
        processed, deleted = process_channels(
            channels, 
            date_cutoff, 
            DEFAULT_CLEANUP_MONTHS
        )
        
        logging.info(f"Processed {processed} transcripts, deleted {deleted} old ones")
        
    except Exception as e:
        logging.error(f"Error in cron job: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
EOF

# Debug: Log variable contents
log_message "BASE_DIR: ${BASE_DIR}"
log_message "CONFIG_PY length: ${#CONFIG_PY}"

# Create files
log_message "Creating config.py"
create_file "${BASE_DIR}/config.py" "${CONFIG_PY}"
log_message "Creating database.py"
create_file "${BASE_DIR}/core/database.py" "${DATABASE_PY}"
log_message "Creating transcript.py"
create_file "${BASE_DIR}/core/transcript.py" "${TRANSCRIPT_PY}"
log_message "Creating validators.py"
create_file "${BASE_DIR}/core/validators.py" "${VALIDATORS_PY}"
log_message "Creating schemas.py"
create_file "${BASE_DIR}/mcp/schemas.py" "${SCHEMAS_PY}"
log_message "Creating formatters.py"
create_file "${BASE_DIR}/mcp/formatters.py" "${FORMATTERS_PY}"
log_message "Creating schema.py"
create_file "${BASE_DIR}/mcp/schema.py" "${SCHEMA_PY}"
log_message "Creating wrapper.py"
create_file "${BASE_DIR}/mcp/wrapper.py" "${WRAPPER_PY}"
log_message "Creating app.py"
create_file "${BASE_DIR}/cli/app.py" "${APP_PY}"
log_message "Creating fetch_transcripts_cron.py"
create_file "${BASE_DIR}/fetch_transcripts_cron.py" "${CRON_SCRIPT_PY}"
chmod +x "${BASE_DIR}/fetch_transcripts_cron.py"
log_message "Creating __init__.py files"
create_file "${BASE_DIR}/__init__.py" ""
create_file "${BASE_DIR}/core/__init__.py" ""
create_file "${BASE_DIR}/cli/__init__.py" ""
create_file "${BASE_DIR}/mcp/__init__.py" ""

# List of files to verify
files=(
    "${BASE_DIR}/config.py"
    "${BASE_DIR}/core/database.py"
    "${BASE_DIR}/core/transcript.py"
    "${BASE_DIR}/core/validators.py"
    "${BASE_DIR}/mcp/schemas.py"
    "${BASE_DIR}/mcp/formatters.py"
    "${BASE_DIR}/mcp/schema.py"
    "${BASE_DIR}/mcp/wrapper.py"
    "${BASE_DIR}/cli/app.py"
    "${BASE_DIR}/fetch_transcripts_cron.py"
    "${BASE_DIR}/__init__.py"
    "${BASE_DIR}/core/__init__.py"
    "${BASE_DIR}/cli/__init__.py"
    "${BASE_DIR}/mcp/__init__.py"
)

# Verify files
log_message "Verifying file creation..."
if verify_files "${files[@]}"; then
    log_message "All files created successfully!"
else
    log_message "ERROR: Some files were not created correctly."
    exit 1
fi

log_message "Setup complete. Check ${LOG_FILE} for details."
log_message "Next steps:"
log_message "1. Install dependencies: pip install youtube-transcript-api pytube google-generativeai typer rich pydantic"
log_message "2. Set GEMINI_API_KEY: export GEMINI_API_KEY='your-api-key'"
log_message "3. Run CLI: python -m youtube_transcripts.cli.app fetch"
log_message "4. For MCP: python -m youtube_transcripts.mcp.wrapper"