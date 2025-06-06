# Task 011: Visual Enrichment Implementation for YouTube Transcripts

**Created**: 2025-01-06  
**Status**: TODO  
**Priority**: HIGH  
**Category**: Feature Enhancement  
**Owner**: Not Assigned  

## 📋 Overview

Implement a comprehensive visual content extraction system for YouTube transcripts that intelligently captures code snippets, terminal sessions, and technical diagrams while respecting video chapter markers and avoiding advertisements.

## 🎯 Objectives

1. Extract meaningful visual content from programming tutorial videos
2. Use intelligent sampling based on chapter markers and content detection
3. Apply OCR optimized for code extraction with high accuracy
4. Link visual content to transcript timestamps for enriched search
5. Skip advertisement segments automatically

## 📊 Context

Based on research findings:
- OCR accuracy improves significantly with higher resolution (720p+ preferred)
- LLMs (GPT-4V) outperform traditional OCR for code extraction
- Frame consolidation across multiple frames improves code reconstruction
- FFmpeg with proper frame selection filters provides optimal performance

## 🎯 Success Criteria

- [ ] 90%+ accuracy in code extraction from 720p+ videos
- [ ] Automatic ad detection and skipping with 95%+ accuracy
- [ ] Processing speed < 10% of video duration
- [ ] Storage < 100MB per hour of video content
- [ ] Chapter-aware extraction respecting video structure

## 📝 Task List

### Phase 1: Infrastructure & Chapter Support (Week 1)

#### 1.1 YouTube Chapter Integration
- [ ] Extend YouTube API client to fetch chapter markers
- [ ] Create `ChapterSegment` data model
- [ ] Store chapters in database with video metadata
- [ ] Implement chapter-based frame sampling logic

```python
@dataclass
class ChapterSegment:
    start_time: float
    end_time: float
    title: str
    is_advertisement: bool = False
    content_hints: List[str] = field(default_factory=list)
```

#### 1.2 Advertisement Detection
- [ ] Implement heuristic ad detection based on chapter titles
- [ ] Create keyword list for common ad markers ("sponsor", "ad", "promotion")
- [ ] Add manual override capability for false positives
- [ ] Store ad segments in database for skipping

#### 1.3 Enhanced FFmpeg Pipeline
- [ ] Implement resolution-aware extraction (prioritize 720p+)
- [ ] Add frame quality assessment before OCR
- [ ] Create parallel processing for multi-core systems
- [ ] Implement frame deduplication using perceptual hashing

### Phase 2: Intelligent Content Detection (Week 2)

#### 2.1 Multi-Model Detection System
- [ ] Integrate Claude Vision API for code/terminal detection
- [ ] Implement fallback to local OpenCV-based detection
- [ ] Create confidence scoring system
- [ ] Add support for diagram and chart detection

#### 2.2 Adaptive Sampling Algorithm
- [ ] Implement chapter-aware base sampling (1 frame/30s for non-code chapters)
- [ ] Dense sampling for code chapters (1 frame/5s)
- [ ] Scene change detection for dynamic sampling
- [ ] Skip frames during detected ad segments

```python
class AdaptiveChapterSampler:
    def get_sampling_rate(self, chapter: ChapterSegment) -> float:
        if chapter.is_advertisement:
            return 0  # Skip entirely
        
        if any(hint in ["code", "terminal", "demo"] 
               for hint in chapter.content_hints):
            return 5  # Dense sampling
        
        return 30  # Standard sampling
```

### Phase 3: Advanced OCR & Code Extraction (Week 3)

#### 3.1 Multi-Engine OCR System
- [ ] Implement Tesseract with code-optimized settings
- [ ] Add Google Vision API integration
- [ ] Integrate GPT-4V for complex code extraction
- [ ] Create voting system for consensus across engines

#### 3.2 Frame Consolidation
- [ ] Implement sliding window frame consolidation
- [ ] Merge partial code snippets across frames
- [ ] Handle scrolling code detection
- [ ] Reconstruct complete code blocks

#### 3.3 Code Enhancement
- [ ] Apply syntax highlighting detection
- [ ] Use language models for code correction
- [ ] Validate code syntax where possible
- [ ] Extract and preserve indentation

### Phase 4: Storage & Integration (Week 4)

#### 4.1 Optimized Storage
- [ ] Implement hierarchical storage with thumbnails
- [ ] Store only unique frames (perceptual hash deduplication)
- [ ] Compress frames with minimal quality loss
- [ ] Create efficient indexing for quick retrieval

#### 4.2 Database Schema Updates
```sql
-- Chapter support
CREATE TABLE video_chapters (
    id UUID PRIMARY KEY,
    video_id VARCHAR(20) REFERENCES transcripts(video_id),
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    title TEXT NOT NULL,
    is_advertisement BOOLEAN DEFAULT FALSE,
    content_hints TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhanced visual content
ALTER TABLE visual_contents 
ADD COLUMN chapter_id UUID REFERENCES video_chapters(id),
ADD COLUMN ocr_engines_used TEXT[],
ADD COLUMN consensus_score FLOAT,
ADD COLUMN frame_group_id UUID;  -- For consolidated frames
```

#### 4.3 Search Integration
- [ ] Extend search to include visual content
- [ ] Add filters for code language and content type
- [ ] Implement visual similarity search
- [ ] Create cross-reference between transcript and visuals

### Phase 5: MCP Prompts & UI (Week 5)

#### 5.1 Visual Search Prompts
- [ ] `/youtube:find-code` - Search for specific code snippets
- [ ] `/youtube:analyze-chapters` - Chapter-based analysis
- [ ] `/youtube:export-tutorial` - Generate complete tutorial
- [ ] `/youtube:compare-implementations` - Compare code across videos

#### 5.2 Enhanced UI Features
- [ ] Visual timeline with chapter markers
- [ ] Code snippet preview in search results
- [ ] Side-by-side transcript and code view
- [ ] Export options for code collections

## 🛠️ Technical Implementation

### Core Components

```python
class VisualEnrichmentPipeline:
    def __init__(self):
        self.chapter_analyzer = ChapterAnalyzer()
        self.ad_detector = AdvertisementDetector()
        self.frame_extractor = IntelligentFrameExtractor()
        self.code_detector = MultiModelCodeDetector()
        self.ocr_ensemble = OCREnsemble([
            TesseractEngine(),
            GoogleVisionEngine(),
            GPT4VisionEngine()
        ])
        self.storage = OptimizedVisualStorage()
    
    async def process_video(self, video_id: str):
        # 1. Get chapters and metadata
        chapters = await self.chapter_analyzer.get_chapters(video_id)
        
        # 2. Filter out advertisements
        content_chapters = [c for c in chapters if not c.is_advertisement]
        
        # 3. Adaptive frame extraction
        frames = await self.frame_extractor.extract_adaptive(
            video_id, content_chapters
        )
        
        # 4. Detect code regions
        code_frames = await self.code_detector.detect_code(frames)
        
        # 5. OCR with ensemble
        extracted_code = await self.ocr_ensemble.extract_code(code_frames)
        
        # 6. Store and index
        await self.storage.store_visual_content(video_id, extracted_code)
```

### Performance Optimizations

1. **Parallel Processing**
   ```python
   async def parallel_frame_extraction(video_path, timestamps):
       tasks = []
       for ts in timestamps:
           task = extract_frame_async(video_path, ts)
           tasks.append(task)
       
       # Process in batches to avoid memory issues
       batch_size = cpu_count()
       for i in range(0, len(tasks), batch_size):
           batch = tasks[i:i+batch_size]
           await asyncio.gather(*batch)
   ```

2. **Smart Caching**
   - Cache OCR results by frame hash
   - Skip reprocessing of known ad segments
   - Incremental processing for updated videos

3. **Quality-First Approach**
   - Prefer higher resolution streams
   - Pre-filter blurry frames using FFT
   - Validate OCR output quality before storage

## 📈 Monitoring & Metrics

- Processing time per video hour
- OCR accuracy by resolution and engine
- Storage efficiency (MB per hour)
- Ad detection accuracy
- Code extraction completeness

## 🔍 Testing Strategy

1. **Unit Tests**
   - Chapter parsing accuracy
   - Ad detection heuristics
   - Frame extraction timing
   - OCR output validation

2. **Integration Tests**
   - End-to-end pipeline processing
   - Database storage and retrieval
   - Search functionality with visuals

3. **Performance Tests**
   - Processing speed benchmarks
   - Memory usage under load
   - Storage growth projections

## 📚 References

- [Optimizing OCR Performance for Programming Videos (2024)](https://www.mdpi.com/2227-7390/12/7/1036)
- [Extracting code from programming tutorial videos (ACM 2016)](https://dl.acm.org/doi/10.1145/2986012.2986021)
- [FFmpeg Frame Extraction Best Practices](https://ffmpeg.org/ffmpeg-filters.html)
- [OCR'ing Video Streams - PyImageSearch](https://pyimagesearch.com/2022/03/07/ocring-video-streams/)

## ✅ Completion Checklist

- [ ] All chapter-aware extraction working
- [ ] Advertisement detection and skipping implemented
- [ ] Multi-engine OCR with consensus
- [ ] Frame consolidation for complete code
- [ ] Visual search integration complete
- [ ] Performance metrics meeting targets
- [ ] Documentation and examples updated
- [ ] All tests passing with >90% coverage

## 🎉 Definition of Done

The visual enrichment system successfully extracts code and technical content from YouTube programming tutorials with high accuracy, intelligently handles video structure through chapter markers, automatically skips advertisements, and provides a seamless search experience that combines transcript and visual content.