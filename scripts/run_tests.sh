#!/bin/bash
# Run YouTube Transcripts tests with Claude test reporter

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running YouTube Transcripts Tests with Claude Test Reporter${NC}"
echo "============================================================"

# Ensure we're in the virtual environment
source .venv/bin/activate

# Default values
MODEL_NAME="youtube-transcripts"
OUTPUT_DIR="docs/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_NAME="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --json)
            JSON_REPORT="--json-report --json-report-file=${OUTPUT_DIR}/test_report_${TIMESTAMP}.json"
            shift
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Run different test categories
echo -e "\n${YELLOW}1. Running unit tests...${NC}"
pytest tests/ -m "unit or not integration" \
    --claude-reporter \
    --claude-model="$MODEL_NAME" \
    --claude-output-dir="$OUTPUT_DIR" \
    $JSON_REPORT \
    $PYTEST_ARGS

UNIT_RESULT=$?

echo -e "\n${YELLOW}2. Running integration tests...${NC}"
pytest tests/ -m integration \
    --claude-reporter \
    --claude-model="$MODEL_NAME" \
    --claude-output-dir="$OUTPUT_DIR" \
    $PYTEST_ARGS

INTEGRATION_RESULT=$?

# Run all tests if specific test file is not provided
if [[ -z "$PYTEST_ARGS" ]]; then
    echo -e "\n${YELLOW}3. Running all tests with coverage...${NC}"
    pytest tests/ \
        --claude-reporter \
        --claude-model="$MODEL_NAME" \
        --claude-output-dir="$OUTPUT_DIR" \
        --cov=src/youtube_transcripts \
        --cov-report=html:${OUTPUT_DIR}/coverage_${TIMESTAMP} \
        --cov-report=term \
        $JSON_REPORT
    
    ALL_RESULT=$?
fi

# Summary
echo -e "\n${BLUE}============================================================${NC}"
echo -e "${BLUE}Test Summary:${NC}"
echo -e "Unit Tests: $([ $UNIT_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${YELLOW}FAILED${NC}")"
echo -e "Integration Tests: $([ $INTEGRATION_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${YELLOW}FAILED${NC}")"
if [[ -z "$PYTEST_ARGS" ]]; then
    echo -e "All Tests: $([ $ALL_RESULT -eq 0 ] && echo -e "${GREEN}PASSED${NC}" || echo -e "${YELLOW}FAILED${NC}")"
fi
echo -e "\nReports saved to: ${OUTPUT_DIR}/"
echo -e "  - Claude test report: ${OUTPUT_DIR}/${MODEL_NAME}_test_report.txt"
if [[ -n "$JSON_REPORT" ]]; then
    echo -e "  - JSON report: ${OUTPUT_DIR}/test_report_${TIMESTAMP}.json"
fi
echo -e "  - Coverage report: ${OUTPUT_DIR}/coverage_${TIMESTAMP}/index.html"