# Task 012: Smart Visual Extraction - Complete Code at Strategic Moments

**Created**: 2025-01-06  
**Status**: TODO  
**Priority**: HIGH  
**Category**: Feature Enhancement  
**Owner**: Not Assigned  

## 📋 Overview

Implement a pragmatic visual extraction system that captures complete code from YouTube videos at strategic moments, avoiding the complexity of merging partial code snippets.

## 🎯 Objectives

1. Extract complete code by targeting key moments when code is fully visible
2. Use chapter markers to identify when code sections are complete
3. Detect stable IDE states (no changes for several seconds)
4. Skip advertisements automatically using chapter analysis
5. Minimize processing by focusing only on high-value moments

## 💡 Core Insight

Instead of trying to reconstruct code from multiple partial frames, we focus on moments when complete, final code is naturally displayed:
- End of code implementation chapters
- Moments of IDE stability (3+ seconds without changes)
- Before transitions away from code screens
- After "let's run it" or "final code" verbal cues

## 🎯 Success Criteria

- [ ] Capture 95%+ of complete code examples from tutorials
- [ ] Process videos 10x faster than frame-by-frame analysis
- [ ] Zero captures from advertisement segments
- [ ] High-quality OCR results from complete code captures
- [ ] Accurate IDE/editor type detection

## 📝 Task List

### Phase 1: Chapter Intelligence (Days 1-2)

#### 1.1 YouTube Chapter Integration
```python
@dataclass
class ChapterAnalysis:
    chapter: VideoChapter
    code_probability: float  # 0-1 score
    completion_markers: List[str]  # "final", "complete", "working"
    ad_probability: float  # 0-1 score
```

- [ ] Fetch chapter data from YouTube API
- [ ] Implement intelligent chapter classification
- [ ] Detect code-related chapters by title keywords
- [ ] Identify advertisement chapters for skipping
- [ ] Store chapter metadata with videos

#### 1.2 Completion Detection Heuristics
- [ ] Identify phrases indicating complete code:
  - "Here's the final code"
  - "Let's run it"
  - "The complete implementation"
  - "Now it's working"
- [ ] Map verbal cues to timestamps
- [ ] Create completion confidence scores

### Phase 2: Strategic Frame Extraction (Days 3-4)

#### 2.1 Chapter-End Extraction
```python
async def extract_chapter_end_code(video_id: str, chapter: VideoChapter):
    # Focus on last 10-15 seconds of code chapters
    if chapter.code_probability > 0.7:
        # Extract frames from chapter end
        end_window = min(15, chapter.duration * 0.1)
        timestamps = get_timestamps(
            chapter.end_time - end_window,
            chapter.end_time,
            interval=2  # Every 2 seconds
        )
        return await extract_best_code_frame(video_id, timestamps)
```

- [ ] Implement chapter-end sampling logic
- [ ] Extract frames in final 10-15 seconds
- [ ] Select best frame based on code detection
- [ ] Handle chapter transitions gracefully

#### 2.2 IDE Stability Detection
```python
async def detect_stable_ide_states(video_id: str, timestamps: List[float]):
    stable_periods = []
    for ts in timestamps:
        # Check ±3 seconds for changes
        if await is_ide_stable(video_id, ts - 3, ts + 3):
            stable_periods.append(ts)
    return stable_periods
```

- [ ] Implement frame similarity comparison
- [ ] Detect periods of no IDE changes
- [ ] Extract frames during stable periods
- [ ] Optimize by sampling every 30 seconds

### Phase 3: Smart OCR Pipeline (Days 5-6)

#### 3.1 IDE-Specific OCR Optimization
```python
class IDEOptimizedOCR:
    def process(self, frame: Frame, ide_type: str):
        if ide_type == "vscode":
            return self.process_vscode(frame)
        elif ide_type == "terminal":
            return self.process_terminal(frame)
        elif ide_type == "jupyter":
            return self.process_jupyter(frame)
```

- [ ] Detect IDE/editor type from visual cues
- [ ] Apply IDE-specific preprocessing
- [ ] Use appropriate OCR settings per IDE
- [ ] Handle syntax highlighting removal

#### 3.2 Quality Validation
- [ ] Validate code syntax when possible
- [ ] Check for common OCR errors in code
- [ ] Score extraction quality
- [ ] Flag incomplete captures

### Phase 4: Efficient Storage (Days 7-8)

#### 4.1 Minimalist Storage Approach
```python
@dataclass
class CodeCapture:
    video_id: str
    chapter_title: str
    timestamp: float
    ide_type: str
    language: str
    code_text: str
    thumbnail_path: Path  # Small preview
    quality_score: float
```

- [ ] Store only complete code captures
- [ ] Save small thumbnails for reference
- [ ] Index by chapter and timestamp
- [ ] Enable quick retrieval

#### 4.2 Database Schema
```sql
CREATE TABLE code_captures (
    id UUID PRIMARY KEY,
    video_id VARCHAR(20) REFERENCES transcripts(video_id),
    chapter_id UUID REFERENCES video_chapters(id),
    timestamp FLOAT NOT NULL,
    ide_type VARCHAR(20),
    language VARCHAR(50),
    code_text TEXT NOT NULL,
    thumbnail_path TEXT,
    quality_score FLOAT,
    extraction_method VARCHAR(50), -- 'chapter_end', 'stable_ide'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_video_chapter (video_id, chapter_id),
    INDEX idx_language (language)
);
```

### Phase 5: Integration & UI (Days 9-10)

#### 5.1 Search Integration
- [ ] Extend search to include complete code captures
- [ ] Add language and IDE type filters
- [ ] Link captures to transcript context
- [ ] Show code preview in results

#### 5.2 MCP Prompts
```python
@mcp_prompt(name="youtube:get-complete-code")
async def get_complete_code(video_id: str, language: Optional[str] = None):
    """Get all complete code examples from a video"""
    
@mcp_prompt(name="youtube:find-implementations")  
async def find_implementations(topic: str, language: str):
    """Find complete implementations of a topic"""
```

## 🛠️ Implementation Example

```python
class SmartCodeExtractor:
    """
    Extract complete code at strategic moments rather than 
    attempting to merge partials
    """
    
    async def process_video(self, video_id: str):
        # 1. Get chapters with intelligent classification
        chapters = await self.get_chapters_with_classification(video_id)
        
        # 2. Skip ads, focus on code chapters
        code_chapters = [c for c in chapters 
                        if c.code_probability > 0.7 
                        and c.ad_probability < 0.1]
        
        captures = []
        
        for chapter in code_chapters:
            # 3. Extract at chapter end (complete implementation)
            end_capture = await self.extract_chapter_end(
                video_id, chapter
            )
            if end_capture:
                captures.append(end_capture)
            
            # 4. Find stable IDE moments throughout chapter
            stable_captures = await self.extract_stable_states(
                video_id, chapter,
                check_interval=30  # Check every 30 seconds
            )
            captures.extend(stable_captures)
        
        # 5. Deduplicate and keep best quality
        return self.select_best_captures(captures)
```

## 📈 Benefits Over Partial Merging

1. **Simplicity**: No complex merging algorithms needed
2. **Accuracy**: Complete code is more accurate than merged partials  
3. **Efficiency**: 10x fewer frames to process
4. **Quality**: Better OCR results from complete, stable images
5. **Storage**: Only store valuable, complete captures

## 🔍 Testing Strategy

1. **Accuracy Tests**
   - Verify complete code capture rate
   - Test IDE detection accuracy
   - Validate OCR quality scores

2. **Performance Tests**  
   - Processing time vs. traditional extraction
   - Storage requirements comparison
   - Query performance with indexes

3. **Edge Cases**
   - Videos without chapters
   - Live coding with no stable states
   - Multiple IDEs in one video

## 📚 References

- YouTube Data API - Chapters: https://developers.google.com/youtube/v3
- Frame similarity algorithms: OpenCV structural similarity
- IDE detection patterns: Color histogram analysis

## ✅ Completion Checklist

- [ ] Chapter intelligence working with ad detection
- [ ] Strategic extraction at key moments
- [ ] IDE-specific OCR optimization  
- [ ] Complete code validation
- [ ] Efficient storage with quick retrieval
- [ ] Search integration with previews
- [ ] MCP prompts for code discovery
- [ ] Performance metrics meeting targets

## 🎉 Definition of Done

The smart visual extraction system successfully captures complete code examples from YouTube programming tutorials by intelligently identifying key moments when code is fully visible, avoiding the complexity of partial code reconstruction while delivering high-quality, searchable code content with minimal processing overhead.