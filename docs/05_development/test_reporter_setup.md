# Test Reporter Setup and Usage

## Overview

The YouTube Transcripts project uses the `claude-test-reporter` pytest plugin to generate comprehensive test reports. This document explains how to use it effectively.

## Fixed Issues

The following issues have been resolved:
1. ✅ Added `pytest-json-report` to dev dependencies (required by claude-test-reporter)
2. ✅ Fixed pytest configuration in both `pyproject.toml` and `pytest.ini`
3. ✅ Added proper pythonpath configuration to resolve import issues
4. ✅ Fixed asyncio configuration warnings
5. ✅ Created convenient test runner script

## Basic Usage

### Run tests with Claude test reporter:
```bash
# Activate virtual environment first
source .venv/bin/activate

# Basic usage
pytest --claude-reporter --claude-model=youtube-transcripts --claude-output-dir=docs/reports

# Run specific test file
pytest tests/test_specific.py --claude-reporter --claude-model=youtube-transcripts

# Run with JSON output
pytest --claude-reporter --claude-model=youtube-transcripts --json-report
```

### Using the test runner script:
```bash
# Run all tests with reporter
./scripts/run_tests.sh

# Run with JSON output
./scripts/run_tests.sh --json

# Run specific test file
./scripts/run_tests.sh tests/test_specific.py

# Custom output directory
./scripts/run_tests.sh --output-dir custom/reports
```

## Configuration

### pytest.ini
```ini
[pytest]
testpaths = tests
pythonpath = src
python_files = test_*.py *_test.py
addopts = -v --tb=short --strict-markers
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### pyproject.toml
The following dev dependencies are required:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "pytest-json-report>=1.5.0",  # Required by claude-test-reporter
    "ruff>=0.3.0",
    "ipython>=8.0.0",
]
```

## Test Markers

Use markers to categorize tests:
```python
import pytest

@pytest.mark.unit
def test_unit_example():
    """Fast unit test"""
    assert True

@pytest.mark.integration
def test_integration_example():
    """Test requiring external services"""
    # Test with real database, API, etc.
    pass

@pytest.mark.slow
def test_slow_operation():
    """Test that takes a long time"""
    pass
```

## Report Output

Reports are saved to `docs/reports/` by default:
- Text report: `youtube-transcripts_test_report.txt`
- JSON report: `test_report_TIMESTAMP.json` (if --json flag used)
- Coverage report: `coverage_TIMESTAMP/index.html`

## Example Test Report

```
Test Report for youtube-transcripts
==================================================

Total Tests: 6
Passed: 5
Failed: 1
Success Rate: 83.3%

Failed Tests:
  - tests/test_example.py::test_failure
    Error: AssertionError: Expected 5 but got 4
```

## Integration with Granger Ecosystem

The claude-test-reporter integrates with the Granger project's testing standards:
1. Generates reports compatible with the claude-module-communicator
2. Supports real vs. fake test detection
3. Provides JSON output for programmatic analysis
4. Tracks test durations and performance metrics

## Troubleshooting

### Import errors
Ensure PYTHONPATH is set correctly:
```bash
export PYTHONPATH=./src:$PYTHONPATH
pytest tests/
```

### Plugin not found
Verify installation:
```bash
pip list | grep claude-test-reporter
# Should show: claude-test-reporter         0.2.1
```

### Missing JSON reports
Install pytest-json-report:
```bash
uv pip install pytest-json-report
```

## Best Practices

1. **Always use markers** to categorize tests (unit, integration, slow)
2. **Run tests regularly** with the reporter to track trends
3. **Review failed tests** in the generated reports
4. **Use the test runner script** for consistency
5. **Commit test reports** to track progress over time

## Next Steps

Now that the test reporter is working, you can:
1. Run existing tests with proper reporting
2. Add new tests following the marker conventions
3. Integrate test results with the Granger hub
4. Use reports to track code quality over time