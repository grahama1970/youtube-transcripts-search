# YouTube Transcripts Test Suite

This directory contains the comprehensive test suite for the YouTube Transcripts project. The test structure mirrors the source code structure for easy navigation.

## Test Organization

```
tests/
├── agents/               # Agent system tests
│   └── test_agents.py   # Tests for async agent functionality
├── core/                # Core functionality tests
│   ├── test_database.py # Database operations tests
│   ├── test_youtube.py  # YouTube API and fetching tests
│   └── utils/          # Utility tests
│       └── test_scientific_extractors.py  # NLP extraction tests
├── cli/                 # CLI interface tests (if any)
├── mcp/                 # MCP integration tests (if any)
├── test_unified_search.py    # Main unified search tests
├── test_search_widening.py   # Progressive search widening tests
└── test_all_integrations.py  # Full integration test runner
```

## Running Tests

### Run All Tests
To run the complete test suite and ensure nothing is broken:

```bash
# From project root
pytest tests/ -v

# Or use the integration test runner for a comprehensive report
python tests/test_all_integrations.py

# With coverage report
pytest tests/ --cov=src/youtube_transcripts --cov-report=html
```

### Run Specific Test Categories

```bash
# Core functionality only
pytest tests/core/ -v

# Agent system only
pytest tests/agents/ -v

# Search functionality
pytest tests/test_unified_search.py tests/test_search_widening.py -v

# Scientific extractors
pytest tests/core/utils/test_scientific_extractors.py -v
```

### Run Individual Test Files

```bash
# Database tests
pytest tests/core/test_database.py -v

# YouTube functionality tests (requires API key)
pytest tests/core/test_youtube.py -v

# Agent system tests
pytest tests/agents/test_agents.py -v
```

## Test Requirements

1. **Environment Variables**
   - `YOUTUBE_API_KEY`: Required for YouTube API tests
   - Create a `.env` file in project root with your API key

2. **Dependencies**
   - All test dependencies are included in `pyproject.toml[dev]`
   - Install with: `pip install -e ".[dev]"`

3. **Database**
   - Tests use SQLite in-memory databases
   - No external database setup required

## Test Categories

### Unit Tests
- Database operations
- Utility functions
- Individual component tests

### Integration Tests
- End-to-end search functionality
- Agent system coordination
- YouTube API integration

### Scientific Extractor Tests
- SpaCy pipeline functionality
- Citation detection
- Speaker extraction
- Content classification

## Quick Health Check

To quickly verify the system is working:

```bash
# Run this command from project root
python -m pytest tests/test_all_integrations.py -v
```

This will:
1. Test database operations
2. Verify search functionality
3. Check agent system
4. Test scientific extractors
5. Generate a summary report

## Expected Test Results

When all tests pass, you should see:
- **Total Tests**: 70+
- **Coverage**: 94%+
- All major components working

## Troubleshooting

1. **Import Errors**: Ensure you're in the virtual environment
2. **API Key Issues**: Check `.env` file has valid YouTube API key
3. **SpaCy Models**: First run may download language models
4. **Timeout Errors**: Some tests fetch real data and may be slow

## Adding New Tests

When adding new functionality:
1. Create test file in appropriate directory matching source structure
2. Follow naming convention: `test_<module_name>.py`
3. Include both positive and negative test cases
4. Add integration test if feature affects multiple components

## CI/CD Integration

These tests are designed to work with CI/CD pipelines:
```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest tests/ --cov=src/youtube_transcripts --cov-report=xml
```