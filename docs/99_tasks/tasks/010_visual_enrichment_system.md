# Task 010: Visual Enrichment System for YouTube Transcripts

## Overview
Enhance YouTube transcripts with visual content extraction, focusing on code screenshots, terminal windows, and technical charts/diagrams.

## Recommended Approach

### 1. Hybrid Sampling Strategy

```python
class AdaptiveScreenshotSampler:
    """
    Intelligent screenshot sampling based on content type detection
    """
    
    def __init__(self):
        self.base_interval = 60  # Base: 1 screenshot per minute
        self.code_interval = 5   # Dense: Every 5 seconds for code
        self.transition_threshold = 0.8  # Confidence for scene changes
    
    async def sample_video(self, video_url: str) -> List[Screenshot]:
        # Phase 1: Quick survey (1 per minute)
        survey_shots = await self.extract_survey_screenshots(video_url)
        
        # Phase 2: Detect code/terminal regions
        code_regions = await self.detect_code_regions(survey_shots)
        
        # Phase 3: Dense sampling in code regions
        detailed_shots = await self.extract_detailed_screenshots(
            video_url, 
            code_regions,
            interval=self.code_interval
        )
        
        return self.merge_screenshots(survey_shots, detailed_shots)
```

### 2. Multi-Stage Pipeline

#### Stage 1: Initial Survey (1 screenshot/minute)
- Quick pass to identify content types
- Detect scene changes and transitions
- Mark regions of interest (ROI)

#### Stage 2: Content Detection
- Use vision models to classify frames:
  - Code/IDE windows
  - Terminal sessions
  - Technical diagrams/charts
  - Slides with code snippets
  - Whiteboards with algorithms

#### Stage 3: Adaptive Dense Sampling
- For detected code regions: 1 screenshot/5 seconds
- For transitions: Capture before/after
- For static diagrams: Single high-quality capture

### 3. Implementation Architecture

```yaml
# visual_enrichment_config.yaml
extraction:
  ffmpeg:
    survey_interval: 60  # seconds
    detail_interval: 5   # seconds
    quality: "high"      # -q:v 2
    format: "png"        # Better for text
    
detection:
  models:
    - name: "claude-vision"  # For code detection
      threshold: 0.85
    - name: "tesseract"      # For OCR
      languages: ["eng", "python", "javascript"]
    
storage:
  structure: "{video_id}/frames/{timestamp}_{type}.png"
  metadata: "{video_id}/visual_metadata.json"
```

### 4. Code Detection & Extraction

```python
@dataclass
class VisualContent:
    timestamp: float
    frame_path: str
    content_type: Literal["code", "terminal", "chart", "diagram"]
    confidence: float
    extracted_text: Optional[str] = None
    syntax_language: Optional[str] = None
    bounding_boxes: List[Box] = field(default_factory=list)

class CodeExtractor:
    async def extract_code_from_frame(self, frame_path: str) -> VisualContent:
        # 1. Detect code regions using vision model
        regions = await self.detect_code_regions(frame_path)
        
        # 2. OCR with code-specific preprocessing
        text = await self.ocr_code_optimized(frame_path, regions)
        
        # 3. Syntax detection and validation
        language = self.detect_language(text)
        
        # 4. Clean and format
        cleaned_code = self.clean_ocr_artifacts(text, language)
        
        return VisualContent(
            content_type="code",
            extracted_text=cleaned_code,
            syntax_language=language
        )
```

### 5. Integration with Transcript System

```python
class EnrichedTranscript:
    """Links visual content to transcript timestamps"""
    
    def __init__(self, transcript: Transcript, visual_contents: List[VisualContent]):
        self.transcript = transcript
        self.visual_contents = sorted(visual_contents, key=lambda x: x.timestamp)
        self.visual_index = self._build_index()
    
    def get_visuals_for_segment(self, start: float, end: float) -> List[VisualContent]:
        """Get all visual content within a transcript segment"""
        return [v for v in self.visual_contents 
                if start <= v.timestamp <= end]
    
    def get_code_blocks(self) -> List[CodeBlock]:
        """Extract all complete code blocks with context"""
        code_contents = [v for v in self.visual_contents 
                        if v.content_type in ["code", "terminal"]]
        return self._merge_continuous_code(code_contents)
```

### 6. Storage Schema Enhancement

```sql
-- New tables for visual content
CREATE TABLE visual_contents (
    id UUID PRIMARY KEY,
    video_id VARCHAR(20) REFERENCES transcripts(video_id),
    timestamp FLOAT NOT NULL,
    frame_path TEXT NOT NULL,
    content_type VARCHAR(20) NOT NULL,
    confidence FLOAT,
    extracted_text TEXT,
    syntax_language VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_video_timestamp (video_id, timestamp)
);

CREATE TABLE visual_segments (
    id UUID PRIMARY KEY,
    video_id VARCHAR(20) REFERENCES transcripts(video_id),
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    segment_type VARCHAR(20), -- 'code_demo', 'diagram_explanation', etc.
    visual_content_ids UUID[],
    transcript_segment_id UUID
);
```

### 7. Smart Features

#### A. Incremental Processing
- Skip already processed videos
- Resume from last processed timestamp
- Update only when transcript updates

#### B. Quality Optimization
- Detect and skip duplicate frames
- Merge similar code screenshots
- Prioritize frames with complete code

#### C. Context Preservation
- Link code to surrounding explanation
- Track code evolution through video
- Identify code corrections/iterations

### 8. Usage Patterns

```python
# Enhanced search with visual content
@mcp_prompt(name="youtube:search-with-code")
async def search_with_code(query: str, include_visuals: bool = True):
    # Search transcripts
    results = await search_transcripts(query)
    
    if include_visuals:
        # Enhance with visual content
        for result in results:
            visuals = await get_visual_contents(result.video_id)
            result.code_samples = extract_code_samples(visuals)
            result.diagrams = extract_diagrams(visuals)
    
    return format_enhanced_results(results)
```

## Implementation Priority

1. **Phase 1: Basic Extraction** (Week 1)
   - FFmpeg integration for screenshots
   - Simple interval-based extraction
   - Basic storage and retrieval

2. **Phase 2: Smart Detection** (Week 2)
   - Claude Vision API for code detection
   - Scene change detection
   - Adaptive sampling implementation

3. **Phase 3: Code Extraction** (Week 3)
   - OCR optimization for code
   - Syntax highlighting detection
   - Code block merging

4. **Phase 4: Integration** (Week 4)
   - Link to transcript segments
   - Enhanced search capabilities
   - MCP prompts for visual search

## Resource Requirements

- **Storage**: ~50-100MB per hour of video (compressed PNGs)
- **Processing**: ~2-5 minutes per hour of video
- **APIs**: Claude Vision API for detection, Local Tesseract for OCR

## Success Metrics

- Code extraction accuracy > 90%
- Processing speed < 0.1x video duration
- Storage efficiency < 100MB/hour
- User satisfaction with enriched content

## Next Steps

1. Prototype basic FFmpeg screenshot extraction
2. Test Claude Vision API for code detection
3. Design optimal storage structure
4. Create proof-of-concept for one video