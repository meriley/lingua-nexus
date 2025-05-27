#!/bin/bash
# Comprehensive test runner for all test suites

set -e  # Exit on error

echo "============================================="
echo "Running All Tests for TG Text Translate"
echo "============================================="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local test_command=$2
    local test_dir=$3
    
    echo -e "${YELLOW}Running $suite_name...${NC}"
    cd "$test_dir"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ $suite_name passed${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ $suite_name failed${NC}"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    echo
}

# Start time
START_TIME=$(date +%s)

# 1. Server Unit Tests
run_test_suite "Server Unit Tests" \
    "python -m pytest tests/unit/ -v --tb=short -q" \
    "server"

# 2. Server Integration Tests (API endpoints only for now)
run_test_suite "Server Integration Tests (API Endpoints)" \
    "python -m pytest tests/integration/test_api_endpoints.py -v --tb=short -q" \
    "server"

# 3. UserScript Tests
run_test_suite "UserScript Tests" \
    "npm test -- --silent" \
    "userscript"

# 4. E2E Tests (simple test that doesn't require full model loading)
run_test_suite "E2E Framework Tests" \
    "python -m pytest tests/e2e/test_simple_e2e.py -v --tb=short -q" \
    "."

# End time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Summary
echo "============================================="
echo "Test Summary"
echo "============================================="
echo "Total Test Suites: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo "Duration: ${DURATION}s"
echo

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi