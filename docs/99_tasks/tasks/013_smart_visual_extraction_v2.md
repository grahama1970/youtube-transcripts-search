# Master Task List - Smart Visual Extraction for YouTube Transcripts

**Total Tasks**: 5  
**Completed**: 0/5  
**Active Tasks**: None  
**Last Updated**: 2025-01-06 15:30 EDT  

---

## 📜 Definitions and Rules
- **REAL Test**: A test that processes actual YouTube video frames and performs real OCR operations (duration > 2.0s for video processing).
- **FAKE Test**: A test using mock frames, fake OCR results, or unrealistic processing times (< 0.5s for video operations).
- **Confidence Threshold**: Tests with <90% confidence are automatically marked FAKE.
- **Status Indicators**:
  - ✅ Complete: All tests passed as REAL, verified in final loop.
  - ⏳ In Progress: Actively running test loops.
  - 🚫 Blocked: Waiting for dependencies (listed).
  - 🔄 Not Started: No tests run yet.
- **Validation Rules**:
  - Frame extraction must take 0.1-2.0s per frame
  - OCR operations must take 0.5-5.0s per frame
  - Chapter API calls must show network latency (0.2-2.0s)
  - Tests must produce JSON and HTML reports with no errors
  - Self-reported confidence must be ≥90% with supporting evidence
  - Maximum 3 test loops per task; escalate failures to project lead
- **Environment Setup**:
  - Python 3.9+, pytest 7.4+, ffmpeg 4.4+
  - Tesseract OCR 4.1+, OpenCV 4.5+
  - YouTube API key in `config.yaml`
  - Sample test videos in `test_data/videos/`

---

## 🎯 TASK #001: Chapter Intelligence System

**Status**: 🔄 Not Started  
**Dependencies**: None  
**Expected Test Duration**: 0.2s-2.0s for API calls, 0.1s-1.0s for classification

### Implementation
- [ ] Fetch real chapter data from YouTube API (no mocks)
- [ ] Implement keyword-based chapter classification using real video titles
- [ ] Detect advertisement chapters from actual sponsored content
- [ ] Store chapter metadata in real database with timestamps

### Test Loop
```
CURRENT LOOP: #1
1. RUN tests → Generate JSON/HTML reports.
2. EVALUATE tests: Mark as REAL or FAKE based on duration, API interaction, and report contents.
3. VALIDATE authenticity and confidence:
   - Query LLM: "For test [Test ID], rate your confidence (0-100%) that this test used live YouTube API and real video data. List any mocked components."
   - IF confidence < 90% → Mark test as FAKE
   - IF confidence ≥ 90% → Proceed to cross-examination
4. CROSS-EXAMINE high confidence claims:
   - "What was the exact YouTube API endpoint called?"
   - "How many milliseconds did the API request take?"
   - "What was the video ID used in testing?"
   - "What rate limit headers were returned?"
   - Inconsistent/vague answers → Mark as FAKE
5. IF any FAKE → Apply fixes → Increment loop (max 3).
6. IF loop fails 3 times → Escalate with full analysis.
```

#### Tests to Run:
| Test ID | Description | Command | Expected Outcome |
|---------|-------------|---------|------------------|
| 001.1   | Fetch real chapters from YouTube API | `pytest tests/test_chapter_intelligence.py::test_fetch_real_chapters -v --json-report --json-report-file=001_test1.json` | Real API response, duration 0.2s-2.0s |
| 001.2   | Classify code vs non-code chapters | `pytest tests/test_chapter_intelligence.py::test_classify_chapters -v --json-report --json-report-file=001_test2.json` | Accurate classification, duration 0.1s-0.5s |
| 001.3   | Detect advertisement chapters | `pytest tests/test_chapter_intelligence.py::test_detect_ads -v --json-report --json-report-file=001_test3.json` | Identifies sponsor segments, duration 0.1s-0.5s |
| 001.H   | HONEYPOT: Classify without fetching | `pytest tests/test_chapter_intelligence.py::test_classify_without_api -v --json-report --json-report-file=001_testH.json` | Should FAIL - no API data |

#### Post-Test Processing:
```bash
python -m youtube_transcripts.test_reporter generate 001_test1.json --output reports/001_test1
python -m youtube_transcripts.test_reporter generate 001_test2.json --output reports/001_test2
python -m youtube_transcripts.test_reporter generate 001_test3.json --output reports/001_test3
python -m youtube_transcripts.test_reporter generate 001_testH.json --output reports/001_testH
```

#### Evaluation Results:
| Test ID | Duration | Verdict | Why | Confidence % | LLM Certainty Report | Evidence Provided | Fix Applied | Fix Metadata |
|---------|----------|---------|-----|--------------|---------------------|-------------------|-------------|--------------|
| 001.1   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 001.2   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 001.3   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 001.H   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |

**Task #001 Complete**: [ ]

---

## 🎯 TASK #002: Strategic Frame Extraction

**Status**: 🔄 Not Started  
**Dependencies**: #001  
**Expected Test Duration**: 2.0s-30.0s for video processing

### Implementation
- [ ] Extract real frames from actual YouTube videos using ffmpeg
- [ ] Implement chapter-end extraction (last 10-15 seconds)
- [ ] Detect IDE stability through frame comparison
- [ ] Handle real video files with proper error handling

### Test Loop
```
CURRENT LOOP: #1
1. RUN tests → Generate JSON/HTML reports.
2. EVALUATE tests: Mark as REAL or FAKE based on video processing time.
3. VALIDATE authenticity and confidence:
   - Query LLM: "For test [Test ID], rate your confidence (0-100%) that this test processed real video frames with ffmpeg. List any synthetic data."
   - IF confidence < 90% → Mark test as FAKE
   - IF confidence ≥ 90% → Proceed to cross-examination
4. CROSS-EXAMINE high confidence claims:
   - "What was the exact ffmpeg command executed?"
   - "How many frames were extracted?"
   - "What was the video resolution and codec?"
   - "How many MB of frame data were generated?"
   - Inconsistent/vague answers → Mark as FAKE
5. IF any FAKE → Apply fixes → Increment loop (max 3).
6. IF loop fails 3 times → Escalate with full analysis.
```

#### Tests to Run:
| Test ID | Description | Command | Expected Outcome |
|---------|-------------|---------|------------------|
| 002.1   | Extract frames at chapter end | `pytest tests/test_frame_extraction.py::test_extract_chapter_end -v --json-report --json-report-file=002_test1.json` | Real frames extracted, duration 5.0s-20.0s |
| 002.2   | Detect stable IDE states | `pytest tests/test_frame_extraction.py::test_detect_ide_stability -v --json-report --json-report-file=002_test2.json` | Frame comparison works, duration 2.0s-10.0s |
| 002.3   | Skip advertisement frames | `pytest tests/test_frame_extraction.py::test_skip_ad_frames -v --json-report --json-report-file=002_test3.json` | No ad frames extracted, duration 2.0s-15.0s |
| 002.H   | HONEYPOT: Extract from fake video | `pytest tests/test_frame_extraction.py::test_extract_nonexistent -v --json-report --json-report-file=002_testH.json` | Should FAIL - video not found |

#### Post-Test Processing:
```bash
python -m youtube_transcripts.test_reporter generate 002_test1.json --output reports/002_test1
python -m youtube_transcripts.test_reporter generate 002_test2.json --output reports/002_test2
python -m youtube_transcripts.test_reporter generate 002_test3.json --output reports/002_test3
python -m youtube_transcripts.test_reporter generate 002_testH.json --output reports/002_testH
```

#### Evaluation Results:
| Test ID | Duration | Verdict | Why | Confidence % | LLM Certainty Report | Evidence Provided | Fix Applied | Fix Metadata |
|---------|----------|---------|-----|--------------|---------------------|-------------------|-------------|--------------|
| 002.1   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 002.2   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 002.3   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 002.H   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |

**Task #002 Complete**: [ ]

---

## 🎯 TASK #003: OCR Code Extraction

**Status**: 🔄 Not Started  
**Dependencies**: #002  
**Expected Test Duration**: 0.5s-5.0s per frame for OCR

### Implementation
- [ ] Process real video frames with Tesseract OCR
- [ ] Apply IDE-specific preprocessing for better accuracy
- [ ] Validate extracted code syntax
- [ ] Handle multiple programming languages

### Test Loop
```
CURRENT LOOP: #1
1. RUN tests → Generate JSON/HTML reports.
2. EVALUATE tests: Mark as REAL or FAKE based on OCR processing time.
3. VALIDATE authenticity and confidence:
   - Query LLM: "For test [Test ID], rate your confidence (0-100%) that this test performed real OCR on actual video frames. List any pre-generated text."
   - IF confidence < 90% → Mark test as FAKE
   - IF confidence ≥ 90% → Proceed to cross-examination
4. CROSS-EXAMINE high confidence claims:
   - "What was the Tesseract configuration used?"
   - "How many characters were extracted?"
   - "What preprocessing steps were applied?"
   - "What was the OCR confidence score?"
   - Inconsistent/vague answers → Mark as FAKE
5. IF any FAKE → Apply fixes → Increment loop (max 3).
6. IF loop fails 3 times → Escalate with full analysis.
```

#### Tests to Run:
| Test ID | Description | Command | Expected Outcome |
|---------|-------------|---------|------------------|
| 003.1   | OCR extract Python code | `pytest tests/test_ocr_extraction.py::test_ocr_python -v --json-report --json-report-file=003_test1.json` | Valid Python extracted, duration 1.0s-5.0s |
| 003.2   | OCR extract terminal output | `pytest tests/test_ocr_extraction.py::test_ocr_terminal -v --json-report --json-report-file=003_test2.json` | Terminal text extracted, duration 0.5s-3.0s |
| 003.3   | Detect programming language | `pytest tests/test_ocr_extraction.py::test_detect_language -v --json-report --json-report-file=003_test3.json` | Correct language identified, duration 0.1s-0.5s |
| 003.H   | HONEYPOT: OCR blank frame | `pytest tests/test_ocr_extraction.py::test_ocr_blank -v --json-report --json-report-file=003_testH.json` | Should FAIL - no text to extract |

#### Post-Test Processing:
```bash
python -m youtube_transcripts.test_reporter generate 003_test1.json --output reports/003_test1
python -m youtube_transcripts.test_reporter generate 003_test2.json --output reports/003_test2
python -m youtube_transcripts.test_reporter generate 003_test3.json --output reports/003_test3
python -m youtube_transcripts.test_reporter generate 003_testH.json --output reports/003_testH
```

#### Evaluation Results:
| Test ID | Duration | Verdict | Why | Confidence % | LLM Certainty Report | Evidence Provided | Fix Applied | Fix Metadata |
|---------|----------|---------|-----|--------------|---------------------|-------------------|-------------|--------------|
| 003.1   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 003.2   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 003.3   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 003.H   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |

**Task #003 Complete**: [ ]

---

## 🎯 TASK #004: Storage and Database Integration

**Status**: 🔄 Not Started  
**Dependencies**: #003  
**Expected Test Duration**: 0.1s-2.0s for database operations

### Implementation
- [ ] Store extracted code in real database (PostgreSQL/ArangoDB)
- [ ] Index by chapter, timestamp, and language
- [ ] Link to transcript segments
- [ ] Enable efficient retrieval queries

### Test Loop
```
CURRENT LOOP: #1
1. RUN tests → Generate JSON/HTML reports.
2. EVALUATE tests: Mark as REAL or FAKE based on database operation times.
3. VALIDATE authenticity and confidence:
   - Query LLM: "For test [Test ID], rate your confidence (0-100%) that this test used a real database connection. List any in-memory substitutes."
   - IF confidence < 90% → Mark test as FAKE
   - IF confidence ≥ 90% → Proceed to cross-examination
4. CROSS-EXAMINE high confidence claims:
   - "What was the database connection string?"
   - "How many milliseconds did the insert take?"
   - "What indexes were created?"
   - "What was the transaction ID?"
   - Inconsistent/vague answers → Mark as FAKE
5. IF any FAKE → Apply fixes → Increment loop (max 3).
6. IF loop fails 3 times → Escalate with full analysis.
```

#### Tests to Run:
| Test ID | Description | Command | Expected Outcome |
|---------|-------------|---------|------------------|
| 004.1   | Store code capture in DB | `pytest tests/test_storage.py::test_store_code_capture -v --json-report --json-report-file=004_test1.json` | Data persisted, duration 0.1s-1.0s |
| 004.2   | Query code by language | `pytest tests/test_storage.py::test_query_by_language -v --json-report --json-report-file=004_test2.json` | Results returned, duration 0.1s-0.5s |
| 004.3   | Link to transcript segments | `pytest tests/test_storage.py::test_link_transcript -v --json-report --json-report-file=004_test3.json` | Relations created, duration 0.2s-1.0s |
| 004.H   | HONEYPOT: Query without connection | `pytest tests/test_storage.py::test_query_no_db -v --json-report --json-report-file=004_testH.json` | Should FAIL - no DB connection |

#### Post-Test Processing:
```bash
python -m youtube_transcripts.test_reporter generate 004_test1.json --output reports/004_test1
python -m youtube_transcripts.test_reporter generate 004_test2.json --output reports/004_test2
python -m youtube_transcripts.test_reporter generate 004_test3.json --output reports/004_test3
python -m youtube_transcripts.test_reporter generate 004_testH.json --output reports/004_testH
```

#### Evaluation Results:
| Test ID | Duration | Verdict | Why | Confidence % | LLM Certainty Report | Evidence Provided | Fix Applied | Fix Metadata |
|---------|----------|---------|-----|--------------|---------------------|-------------------|-------------|--------------|
| 004.1   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 004.2   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 004.3   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 004.H   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |

**Task #004 Complete**: [ ]

---

## 🎯 TASK #005: MCP Integration and Search

**Status**: 🔄 Not Started  
**Dependencies**: #004  
**Expected Test Duration**: 0.5s-5.0s for search operations

### Implementation
- [ ] Create MCP prompts for visual code search
- [ ] Integrate with existing transcript search
- [ ] Return code snippets with video context
- [ ] Support language and IDE filters

### Test Loop
```
CURRENT LOOP: #1
1. RUN tests → Generate JSON/HTML reports.
2. EVALUATE tests: Mark as REAL or FAKE based on search operation times.
3. VALIDATE authenticity and confidence:
   - Query LLM: "For test [Test ID], rate your confidence (0-100%) that this test performed real searches on actual data. List any hardcoded results."
   - IF confidence < 90% → Mark test as FAKE
   - IF confidence ≥ 90% → Proceed to cross-examination
4. CROSS-EXAMINE high confidence claims:
   - "How many database queries were executed?"
   - "What was the search query plan?"
   - "How many results were found?"
   - "What was the total query time?"
   - Inconsistent/vague answers → Mark as FAKE
5. IF any FAKE → Apply fixes → Increment loop (max 3).
6. IF loop fails 3 times → Escalate with full analysis.
```

#### Tests to Run:
| Test ID | Description | Command | Expected Outcome |
|---------|-------------|---------|------------------|
| 005.1   | Search code by keyword | `pytest tests/test_mcp_search.py::test_search_code -v --json-report --json-report-file=005_test1.json` | Real results found, duration 0.5s-3.0s |
| 005.2   | Filter by language | `pytest tests/test_mcp_search.py::test_filter_language -v --json-report --json-report-file=005_test2.json` | Filtered correctly, duration 0.3s-2.0s |
| 005.3   | Execute MCP prompt | `pytest tests/test_mcp_search.py::test_mcp_prompt -v --json-report --json-report-file=005_test3.json` | Prompt returns data, duration 1.0s-5.0s |
| 005.H   | HONEYPOT: Search impossible code | `pytest tests/test_mcp_search.py::test_search_impossible -v --json-report --json-report-file=005_testH.json` | Should FAIL - no such code exists |

#### Post-Test Processing:
```bash
python -m youtube_transcripts.test_reporter generate 005_test1.json --output reports/005_test1
python -m youtube_transcripts.test_reporter generate 005_test2.json --output reports/005_test2
python -m youtube_transcripts.test_reporter generate 005_test3.json --output reports/005_test3
python -m youtube_transcripts.test_reporter generate 005_testH.json --output reports/005_testH
```

#### Evaluation Results:
| Test ID | Duration | Verdict | Why | Confidence % | LLM Certainty Report | Evidence Provided | Fix Applied | Fix Metadata |
|---------|----------|---------|-----|--------------|---------------------|-------------------|-------------|--------------|
| 005.1   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 005.2   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 005.3   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 005.H   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |

**Task #005 Complete**: [ ]

---

## 📊 Overall Progress

### By Status:
- ✅ Complete: 0 (#)
- ⏳ In Progress: 0 (#)
- 🚫 Blocked: 0 (#)
- 🔄 Not Started: 5 (#001, #002, #003, #004, #005)

### Self-Reporting Patterns:
- Always Certain (≥95%): 0 tasks
- Mixed Certainty (50-94%): 0 tasks
- Always Uncertain (<50%): 0 tasks
- Average Confidence: N/A
- Honeypot Detection Rate: 0/0 (No tests run yet)

### Dependency Graph:
```
#001 (Chapter Intelligence)
  └→ #002 (Frame Extraction)
      └→ #003 (OCR Extraction)
          └→ #004 (Storage)
              └→ #005 (MCP Search)
```

### Critical Issues:
1. None yet - no tests have been run

### Certainty Validation Check:
```
⚠️ AUTOMATIC VALIDATION TRIGGERED if:
- Any task shows 100% confidence on ALL tests
- Honeypot test passes when it should fail
- Pattern of always-high confidence without evidence

Action: Insert additional honeypot tests and escalate to human review
```

### Next Actions:
1. Begin Task #001 test loop by 2025-01-07
2. Prepare test video samples for frame extraction
3. Ensure YouTube API credentials are configured

---

## 📋 Task Template (Copy for New Tasks)

```markdown
## 🎯 TASK #00X: [Name]

**Status**: 🔄 Not Started  
**Dependencies**: [List task IDs or None]  
**Expected Test Duration**: [Range]  

### Implementation
- [ ] [Requirement 1, specify live systems, no mocks]
- [ ] [Requirement 2, include validation data]
- [ ] [Requirement 3]

### Test Loop
```
CURRENT LOOP: #1
[Standard test loop steps 1-6]
```

#### Tests to Run:
| Test ID | Description | Command | Expected Outcome |
|---------|-------------|---------|------------------|
| 00X.1   | [Test purpose] | `[pytest command]` | [Expected result, duration range] |
| 00X.H   | HONEYPOT: [Impossible test] | `[pytest command]` | Should FAIL |

#### Post-Test Processing:
```bash
# [Commands for report generation]
```

#### Evaluation Results:
| Test ID | Duration | Verdict | Why | Confidence % | LLM Certainty Report | Evidence Provided | Fix Applied | Fix Metadata |
|---------|----------|---------|-----|--------------|---------------------|-------------------|-------------|--------------|
| 00X.1   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |
| 00X.H   | ___      | ___     | ___ | ___%         | ___                 | ___               | ___         | ___          |

**Task #00X Complete**: [ ]
```

---

## 🔍 Programmatic Access
- **JSON Export**: Run `python -m youtube_transcripts.task_exporter --format json > visual_extraction_tasks.json`
- **Query Tasks**: Use `jq '.tasks[] | select(.status == "BLOCKED")' visual_extraction_tasks.json`
- **Fake Test Detection**: Filter evaluation results for `"Verdict": "FAKE"`, `"Confidence %" < 90`, or honeypot passes
- **Suspicious Pattern Detection**: `jq '.tasks[] | select(.average_confidence > 95 and .honeypot_failed == false)'`