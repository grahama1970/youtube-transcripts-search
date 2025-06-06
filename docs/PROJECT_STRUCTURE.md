# YouTube Transcripts Project Structure

This document provides an overview of the project organization after cleanup.

## Directory Structure

```
youtube_transcripts/
├── src/                      # Source code
│   └── youtube_transcripts/
│       ├── agents/          # Async agent system
│       ├── cli/             # Command-line interface
│       ├── core/            # Core functionality
│       │   ├── utils/       # Utility modules
│       │   ├── database.py  # SQLite operations
│       │   ├── database_v2.py # Enhanced DB with metadata
│       │   ├── models.py    # Data models
│       │   ├── transcript.py # YouTube fetching
│       │   └── validators.py # Input validation
│       ├── mcp/             # Model Context Protocol
│       ├── verl_config/     # VERL configuration
│       ├── citation_detector.py      # Citation extraction
│       ├── content_classifier.py     # Content categorization
│       ├── metadata_extractor.py     # Metadata coordination
│       ├── search_enhancements.py    # Advanced search
│       ├── search_widener.py         # Query expansion
│       ├── speaker_extractor.py      # Speaker identification
│       ├── unified_search.py         # Main search system
│       └── youtube_search.py         # YouTube API client
│
├── tests/                    # Test suite (mirrors src structure)
│   ├── agents/              # Agent system tests
│   ├── core/                # Core functionality tests
│   │   └── utils/           # Utility tests
│   ├── cli/                 # CLI tests
│   ├── mcp/                 # MCP tests
│   ├── test_unified_search.py    # Main search tests
│   ├── test_search_widening.py   # Query expansion tests
│   ├── test_all_integrations.py  # Test runner
│   └── README.md            # Test documentation
│
├── docs/                     # Documentation
│   ├── guides/              # Implementation guides
│   ├── tasks/               # Task tracking
│   ├── reports/             # Test reports
│   └── SCIENTIFIC_FEATURES.md # NLP features docs
│
├── scripts/                  # Utility scripts
│   ├── install.sh           # Installation script
│   ├── migrate_to_v2.py     # Database migration
│   └── train_deep_retrieval.py # Training script
│
├── archive/                  # Archived/old files
├── logs/                     # Log files
│
├── pyproject.toml           # Project configuration
├── pytest.ini               # Test configuration
├── README.md                # Main documentation
├── CLAUDE.md                # Coding standards
└── .gitignore               # Git ignore rules
```

## Key Components

### Source Code (`src/youtube_transcripts/`)
- **agents/**: Asynchronous agent system for background processing
- **cli/**: Command-line interface with regular and scientific commands
- **core/**: Core functionality including database, models, and YouTube integration
- **mcp/**: Model Context Protocol for LLM integration
- **Scientific extractors**: NLP-based extraction using SpaCy and Transformers

### Tests (`tests/`)
- Mirrors source structure for easy navigation
- Comprehensive test coverage (94%+)
- Integration test runner for quick health checks

### Documentation (`docs/`)
- **guides/**: Implementation and architecture guides
- **tasks/**: Completed task documentation
- **reports/**: Test execution reports
- **SCIENTIFIC_FEATURES.md**: Guide to NLP features

### Scripts (`scripts/`)
- Installation and setup utilities
- Database migration tools
- Training scripts for models

## Archived Files

The following have been moved to `archive/`:
- Old test iterations (test_entity_extraction.py, etc.)
- Backup source files (*_backup.py, *_v2.py)
- External repositories (repos/)
- Test result files (*.json)
- Configuration backups (*.bak)

## Running the Project

1. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Run tests**:
   ```bash
   # All tests
   pytest tests/ -v
   
   # Quick integration check
   python tests/test_all_integrations.py
   ```

3. **Use the CLI**:
   ```bash
   # Regular commands
   youtube-transcripts search "query"
   
   # Scientific commands
   youtube-transcripts sci search-advanced "query" --type lecture
   ```

## Development Guidelines

1. Follow the structure when adding new features
2. Create tests that mirror source structure
3. Use type hints and docstrings
4. Run tests before committing
5. Keep documentation updated

## Clean Development Environment

The project is now organized with:
- ✅ No stray files in root
- ✅ Tests properly organized
- ✅ Clear separation of concerns
- ✅ Archived old iterations
- ✅ Comprehensive documentation