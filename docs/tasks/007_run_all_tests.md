# Task 007: Run All Tests with Test Report Generation

**Goal**: Execute all tests and generate comprehensive test reports
**Focus**: Get all tests running and generating reports

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
import subprocess
from datetime import datetime
from pathlib import Path

def run_all_tests():
    """Run all test suites and generate reports"""
    test_suites = [
        ("Entity Extraction", "tests/test_entity_extraction.py"),
        ("Relationship Extraction", "tests/test_relationship_extraction.py"),
        ("Hybrid Search", "tests/test_hybrid_search.py")
    ]
    
    results = []
    for name, test_file in test_suites:
        print(f"\n{'='*60}")
        print(f"Running {name} Tests...")
        print('='*60)
        
        result = subprocess.run(
            ["python", test_file],
            capture_output=True,
            text=True,
            cwd="/home/graham/workspace/experiments/youtube_transcripts"
        )
        
        results.append({
            "suite": name,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    
    return results

# Run it:
if __name__ == "__main__":
    results = run_all_tests()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for r in results:
        status = "✅ PASS" if r["returncode"] == 0 else "❌ FAIL"
        print(f"{r['suite']}: {status}")
```

## Run Command

```bash
cd /home/graham/workspace/experiments/youtube_transcripts
python docs/tasks/run_all_tests.py
```

## Expected Output Structure

```
==============================================================
Running Entity Extraction Tests...
==============================================================
🚀 Starting Entity Extraction Tests
...
📊 Test report saved to: docs/reports/entity_extraction_test_report_[timestamp].md
✨ Test Summary:
   Total: 4
   Passed: X
   Success Rate: X%

==============================================================
Running Relationship Extraction Tests...
==============================================================
...

==============================================================
Running Hybrid Search Tests...
==============================================================
...

==============================================================
TEST SUMMARY
==============================================================
Entity Extraction: ✅ PASS
Relationship Extraction: ✅ PASS
Hybrid Search: ✅ PASS
```

## Common Issues & Solutions

### Issue 1: Import Errors
```python
# Solution: Ensure proper Python path
import sys
sys.path.insert(0, '/home/graham/workspace/experiments/youtube_transcripts')
```

### Issue 2: ArangoDB Connection Errors
```bash
# Solution: Verify ArangoDB is running
sudo systemctl status arangodb3
# If not running:
sudo systemctl start arangodb3
```

### Issue 3: Missing Test Reports Directory
```python
# Solution: Create directory if missing
from pathlib import Path
Path("docs/reports").mkdir(parents=True, exist_ok=True)
```

## Validation Requirements

```python
# All test suites must:
assert all(r["returncode"] == 0 for r in results), "All tests must pass"
assert len(results) == 3, "Must run all 3 test suites"

# Each suite must generate a report:
import glob
reports = glob.glob("docs/reports/*_test_report_*.md")
assert len(reports) >= 3, "Must generate at least 3 test reports"
```

## Report Locations

After successful execution, find reports at:
- `docs/reports/entity_extraction_test_report_[timestamp].md`
- `docs/reports/relationship_extraction_test_report_[timestamp].md`
- `docs/reports/hybrid_search_test_report_[timestamp].md`