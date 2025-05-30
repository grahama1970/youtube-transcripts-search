# Task 008: Scientific Metadata Extraction for YouTube Transcripts

## Overview
Implement robust scientific metadata extraction features using existing NLP infrastructure (SpaCy, Transformers, Ollama) to enhance the YouTube transcript system for research use cases.

## Context
- The system already has SpaCy, HuggingFace Transformers, and Ollama integrated
- Current entity extraction uses brittle regex patterns
- Need to leverage existing NLP tools for more accurate academic metadata extraction
- Claude-module-communicator is available for module coordination but not for extraction

## Success Criteria
- [ ] Extract academic metadata (URLs, institutions, keywords) with 95%+ accuracy using NLP models
- [ ] Detect citations (arXiv IDs, DOIs, author-year) with 90%+ precision
- [ ] Extract speaker information using SpaCy NER
- [ ] Categorize content types using existing Ollama integration
- [ ] Leverage existing SpaCy and Transformer infrastructure
- [ ] Maintain existing test coverage above 94%
- [ ] Add at least 20 new tests for scientific features

## Implementation Tasks

### Phase 1: Enhanced NLP Infrastructure
1. **Upgrade SpaCy pipeline** (`src/youtube_transcripts/core/utils/spacy_scientific.py`)
   - [ ] Load SpaCy with sci-spacy models for scientific text
   - [ ] Add custom entity recognizer for academic institutions
   - [ ] Configure SpaCy pipeline for scientific domain
   - [ ] Integrate with existing spacy_utils.py

2. **Create scientific metadata extractor** (`src/youtube_transcripts/metadata_extractor.py`)
   - [ ] Use SpaCy for institution and person extraction
   - [ ] Extract URLs using SpaCy's built-in URL detection
   - [ ] Use Transformers (BAAI/bge-large-en-v1.5) for keyword extraction
   - [ ] Coordinate extraction modules using claude-module-communicator

3. **Update database schema**
   - [ ] Add `metadata` JSON column to transcripts table
   - [ ] Create migration script
   - [ ] Update `core/database.py` with metadata fields

### Phase 2: Citation Detection with NLP
4. **Create citation detector** (`src/youtube_transcripts/citation_detector.py`)
   - [ ] Use SpaCy patterns for citation detection (more robust than regex)
   - [ ] Fine-tune existing BERT model for citation extraction
   - [ ] Integrate Ollama (qwen2.5:3b) for context-aware citation detection
   - [ ] Extract paper titles using NER instead of quote patterns

5. **Store and index citations**
   - [ ] Add `citations` JSON field to database
   - [ ] Create citation relationship type in ArangoDB
   - [ ] Link transcripts that cite same papers

### Phase 3: Speaker Information with SpaCy NER
6. **Extract speaker metadata** (`src/youtube_transcripts/speaker_extractor.py`)
   - [ ] Use SpaCy's PERSON entity recognition
   - [ ] Extract titles using SpaCy's dependency parsing
   - [ ] Link persons to ORG entities for affiliations
   - [ ] Use coreference resolution for tracking multiple speakers

7. **Update transcript model**
   - [ ] Add `speakers` field to transcript schema
   - [ ] Store speaker info with timestamps
   - [ ] Link speakers to their mentioned affiliations

### Phase 4: Content Categorization with Ollama
8. **Implement content classifier** (`src/youtube_transcripts/content_classifier.py`)
   - [ ] Use existing Ollama integration (qwen2.5:3b) for categorization
   - [ ] Leverage existing content_analyzer_agent.py patterns
   - [ ] Use Transformer embeddings for topic clustering
   - [ ] Add confidence scores from model outputs

9. **Create quality indicators**
   - [ ] Use SpaCy for technical term density (better than regex)
   - [ ] Measure citation frequency from NLP extraction
   - [ ] Use Transformers to detect content structure
   - [ ] Score using existing embedding similarity measures

### Phase 5: Integration and Export
10. **Update search functionality**
    - [ ] Add filters for content type, academic level
    - [ ] Enable citation-based search
    - [ ] Search by speaker or institution
    - [ ] Add metadata to search results

11. **Create export functionality**
    - [ ] Export citations in BibTeX format
    - [ ] Generate markdown summaries with metadata
    - [ ] Create CSV export with all extracted fields
    - [ ] Add export commands to CLI

### Phase 6: Testing and Documentation
12. **Create comprehensive tests**
    - [ ] Test SpaCy pipeline with real transcript samples
    - [ ] Verify NLP model outputs vs ground truth
    - [ ] Test database schema changes
    - [ ] Benchmark NLP performance vs regex baseline

13. **Update documentation**
    - [ ] Document new CLI commands
    - [ ] Add examples of scientific queries
    - [ ] Update README with new features
    - [ ] Create tutorial for researchers

## Technical Specifications

### Metadata Schema
```python
{
    "urls": ["https://arxiv.org/abs/2301.00001", ...],
    "institutions": ["MIT", "Stanford", ...],
    "keywords": ["reinforcement learning", "VERL", ...],
    "technical_terms": ["gradient descent", "neural network", ...]
}
```

### Citation Schema
```python
{
    "arxiv": ["2301.00001", "2302.00002"],
    "doi": ["10.1038/nature12373"],
    "author_year": ["Smith et al. 2023", "Johnson 2022"],
    "titles": ["Attention is All You Need", ...]
}
```

### Speaker Schema
```python
{
    "speakers": [
        {
            "name": "Dr. Jane Smith",
            "title": "Assistant Professor",
            "affiliation": "MIT CSAIL",
            "timestamp": "00:00:15"
        }
    ]
}
```

## Dependencies
- **Already available**: SpaCy (3.8.7+), Transformers, Ollama, claude-module-communicator
- **To add**: sci-spacy for scientific NER models
- **Existing**: SQLite, ArangoDB, Click/Typer
- **Optional**: BibTeX export library (if needed)

## Risks and Mitigations
- **Risk**: NLP models may be slower than regex
  - **Mitigation**: Use SpaCy's efficient pipeline, cache results
- **Risk**: Model size and memory usage
  - **Mitigation**: Use existing loaded models, share resources
- **Risk**: Schema changes break existing code
  - **Mitigation**: Use backward-compatible JSON fields

## Rollback Plan
1. All new fields are optional JSON columns
2. Feature flags for each extractor
3. Can disable via config without breaking core functionality
4. Database migrations are reversible

## Definition of Done
- [ ] All extractors implemented and tested
- [ ] Database schema updated with migrations
- [ ] CLI commands added and documented
- [ ] 95%+ test coverage on new code
- [ ] Performance impact < 10% on indexing
- [ ] README updated with examples
- [ ] No regression in existing functionality