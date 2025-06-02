# youtube_transcripts/core/query.py
import sqlite3
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from pathlib import Path
from ..config import GEMINI_API_KEY, DB_PATH

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def summarize_transcript(transcript: str, skip_summary: bool = False) -> str:
    """Summarize transcript using Gemini 2.5 Flash."""
    if skip_summary:
        return "Summary skipped."
    try:
        prompt = f"Summarize the following transcript in 100 words or less:
{transcript[:4000]}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error summarizing transcript: {e}")
        return "Summary not available."

def prefilter_transcripts(query: str, db_path: Path = DB_PATH, bm25_limit: int = 5) -> List[Dict[str, Any]]:
    """Prefilter transcripts with keyword search and BM25 ranking."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Step 1: Keyword search
    keywords = query.lower().split()
    keyword_conditions = " OR ".join([f"transcript LIKE '%{kw}%' OR enhanced_transcript LIKE '%{kw}%'" for kw in keywords])
    cursor.execute(f'''
        SELECT video_id, title, channel_name, publish_date, transcript, enhanced_transcript
        FROM transcripts
        WHERE {keyword_conditions}
    ''')
    keyword_results = cursor.fetchall()
    
    # Step 2: BM25 ranking on keyword-filtered results
    if not keyword_results:
        conn.close()
        return []
    
    video_ids = [row[0] for row in keyword_results]
    video_id_filter = " OR ".join([f"video_id = '{vid}'" for vid in video_ids])
    cursor.execute(f'''
        SELECT video_id, title, channel_name, publish_date, transcript, enhanced_transcript, rank
        FROM transcripts
        WHERE ({video_id_filter}) AND transcripts MATCH ?
        ORDER BY rank LIMIT ?
    ''', (query, bm25_limit))
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            "video_id": row[0],
            "title": row[1],
            "channel_name": row[2],
            "publish_date": row[3],
            "transcript": row[4],
            "enhanced_transcript": row[5],
            "rank": row[6]
        }
        for row in results
    ]

def query_gemini(query: str, transcripts: List[Dict[str, Any]]) -> tuple[str, List[str]]:
    """Query Gemini with filtered transcripts to answer the question."""
    try:
        context = "

".join([
            f"Video: {t['title']} (Channel: {t['channel_name']}, Published: {t['publish_date']})
"
            f"Transcript: {t['enhanced_transcript'][:2000]}"  # Limit per transcript
            for t in transcripts
        ])
        prompt = f"""
        Question: {query}
        Context: The following are YouTube video transcripts from the specified channel. Use them to answer the question concisely, citing relevant videos by title if applicable. If the information is not in the transcripts, state that clearly and provide a general answer based on your knowledge.
        
        {context}
        
        Answer in 200 words or less:
        """
        response = model.generate_content(prompt)
        return response.text, [t['video_id'] for t in transcripts]
    except Exception as e:
        print(f"Error querying Gemini: {e}")
        return "Unable to generate answer.", []

if __name__ == "__main__":
    import sys
    all_validation_failures = []
    total_tests = 0

    # Test 1: Summarize transcript
    total_tests += 1
    try:
        summary = summarize_transcript("This is a test transcript for summarization.", skip_summary=True)
        if summary != "Summary skipped.":
            all_validation_failures.append("Skip summary not working")
    except Exception as e:
        all_validation_failures.append(f"Summarize transcript failed: {str(e)}")

    # Test 2: Prefilter transcripts (requires database setup)
    total_tests += 1
    try:
        from .database import initialize_database
        initialize_database()
        results = prefilter_transcripts("test query")
        if not isinstance(results, list):
            all_validation_failures.append("Prefilter did not return a list")
    except Exception as e:
        all_validation_failures.append(f"Prefilter transcripts failed: {str(e)}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        sys.exit(0)
