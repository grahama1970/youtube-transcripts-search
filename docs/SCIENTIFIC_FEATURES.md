# Scientific Metadata Extraction Features

This document describes the scientific metadata extraction features added to the YouTube Transcripts system.

## Overview

The system now includes advanced NLP-based extraction capabilities specifically designed for academic and scientific content. These features leverage SpaCy, HuggingFace Transformers, and Ollama to provide robust extraction without relying on brittle regex patterns.

## Components

### 1. SpaCy Scientific Pipeline (`spacy_scientific.py`)

Enhanced SpaCy pipeline with custom components for scientific text:

- **Citation Detector**: Extracts arXiv IDs, DOIs, and author-year citations
- **Institution Recognizer**: Identifies academic institutions and research organizations  
- **Technical Term Extractor**: Finds technical terms, acronyms, and domain-specific vocabulary
- **Speaker Extractor**: Extracts speaker names with titles and affiliations

```python
from src.youtube_transcripts.core.utils.spacy_scientific import ScientificPipeline

pipeline = ScientificPipeline()
results = pipeline.process_transcript(text)
# Returns: people, institutions, citations, technical_terms, speakers, conferences
```

### 2. Citation Detector (`citation_detector.py`)

Advanced citation detection using SpaCy patterns and optional Ollama enhancement:

- Detects multiple citation formats (arXiv, DOI, ISBN, author-year)
- Extracts citation context
- Exports to BibTeX, JSON, or Markdown formats

```python
from src.youtube_transcripts.citation_detector import CitationDetector

detector = CitationDetector(use_ollama=True)
citations = detector.detect_citations(text)
bibtex = detector.format_for_export(citations, 'bibtex')
```

### 3. Speaker Extractor (`speaker_extractor.py`) 

Identifies speakers using SpaCy NER and dependency parsing:

- Extracts from introductions ("I'm Dr. Smith from MIT")
- Handles labeled speakers ("Speaker 1: Jane Doe")
- Links speakers to affiliations and titles
- Deduplicates multiple mentions

```python
from src.youtube_transcripts.speaker_extractor import SpeakerExtractor

extractor = SpeakerExtractor()
speakers = extractor.extract_speakers(text)
# Returns: [Speaker(name="Dr. Smith", title="Dr.", affiliation="MIT")]
```

### 4. Content Classifier (`content_classifier.py`)

Classifies academic content using embeddings and Ollama:

- **Content Type**: lecture, tutorial, conference, demo, discussion
- **Academic Level**: undergraduate, graduate, research, professional  
- **Topics**: Extracted using embedding similarity with predefined categories
- **Quality Indicators**: Technical density, citation frequency, structure score

```python
from src.youtube_transcripts.content_classifier import ContentClassifier

classifier = ContentClassifier()
result = classifier.classify_content(transcript)
# Returns: ContentClassification with type, level, topics, quality scores
```

### 5. Metadata Extractor (`metadata_extractor.py`)

Coordinates all extraction components:

- Integrates SpaCy pipeline, embeddings, and citation detection
- Extracts URLs, keywords, and comprehensive metadata
- Supports batch processing
- Optional progress tracking via claude-module-communicator

```python
from src.youtube_transcripts.metadata_extractor import MetadataExtractor

extractor = MetadataExtractor()
metadata = extractor.extract_metadata(transcript)
# Returns: urls, institutions, keywords, citations, speakers, etc.
```

### 6. Enhanced Search (`search_enhancements.py`)

Advanced search capabilities with metadata filters:

- Filter by content type, academic level, institution
- Search by citation or speaker
- Export results to CSV, Markdown, or JSON
- Build citation networks

```python
from src.youtube_transcripts.search_enhancements import EnhancedSearch

search = EnhancedSearch()
results = search.search(
    query="transformers",
    content_type="lecture",
    academic_level="graduate",
    has_citations=True
)
```

### 7. Scientific CLI Commands (`cli/app_scientific.py`)

New CLI commands for scientific search:

```bash
# Advanced search with filters
youtube-transcripts sci search-advanced "machine learning" \
    --type lecture --level graduate --has-citations

# Find videos citing a paper
youtube-transcripts sci find-citations "arXiv:2301.00234" --bibtex

# Find videos with a specific speaker
youtube-transcripts sci find-speaker "Yann LeCun" --affiliations

# Export citations from videos
youtube-transcripts sci export-citations "video1,video2" \
    --format bibtex --output citations.bib

# Show statistics
youtube-transcripts sci stats --institutions --limit 20
```

## Database Schema

The database has been upgraded to v2 with JSON fields for metadata:

```sql
CREATE TABLE transcripts_metadata (
    video_id TEXT PRIMARY KEY,
    -- ... existing fields ...
    metadata JSON,      -- General metadata (keywords, urls, etc.)
    citations JSON,     -- Extracted citations
    speakers JSON,      -- Speaker information
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Usage Example

```python
# Complete extraction pipeline
from src.youtube_transcripts.core.models import Transcript
from src.youtube_transcripts.metadata_extractor import MetadataExtractor
from src.youtube_transcripts.content_classifier import ContentClassifier

# Create transcript
transcript = Transcript(
    video_id="abc123",
    title="Deep Learning Lecture - MIT",
    channel_name="MIT OpenCourseWare",
    text="Professor Smith discusses transformers...",
    publish_date="2024-01-15",
    duration=3600
)

# Extract metadata
extractor = MetadataExtractor()
metadata = extractor.extract_metadata(transcript)

# Classify content
classifier = ContentClassifier()
classification = classifier.classify_content(transcript)

# metadata now contains:
# - citations with arXiv/DOI links
# - speaker information with affiliations
# - institution mentions
# - technical keywords
# - quality indicators
```

## Testing

Comprehensive tests are provided in `tests/test_scientific_extractors.py`:

```bash
# Run all scientific extractor tests
pytest tests/test_scientific_extractors.py -v

# Or use the simple test script
python test_scientific_simple.py
```

## Performance Considerations

- SpaCy models are loaded once and reused
- Embeddings are cached when possible
- Ollama is optional and can be disabled for faster processing
- Batch processing is supported for multiple transcripts

## Future Enhancements

1. Integration with sci-spacy for biomedical content
2. arXiv API integration for citation metadata
3. Conference and journal detection
4. Research topic clustering
5. Citation graph visualization
6. Export to reference managers (Zotero, Mendeley)