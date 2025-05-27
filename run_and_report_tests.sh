#!/bin/bash
# Script to run all tests and generate coverage reports

# Set up colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}===== NLLB Translation System: Test Runner =====${NC}"
echo "Running tests and collecting coverage for all components..."
echo ""

# Create reports directory
mkdir -p ${SCRIPT_DIR}/test_reports

# Check for required dependencies
check_server_dependencies() {
    echo -e "${YELLOW}Checking server dependencies...${NC}"
    if ! command -v pip &> /dev/null; then
        echo -e "${RED}Python pip is not installed. Please install Python and pip.${NC}"
        return 1
    fi

    echo -e "${YELLOW}Installing all required packages...${NC}"
    cd ${SCRIPT_DIR}/server
    pip install -r requirements.txt -r requirements-dev.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install dependencies.${NC}"
        return 1
    fi
    return 0
}

check_userscript_dependencies() {
    echo -e "${YELLOW}Checking userscript dependencies...${NC}"
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}npm is not installed. Please install Node.js and npm.${NC}"
        return 1
    fi

    if [ ! -d "${SCRIPT_DIR}/userscript/node_modules" ]; then
        echo -e "${YELLOW}Installing userscript dependencies...${NC}"
        cd ${SCRIPT_DIR}/userscript
        npm install
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to install npm dependencies.${NC}"
            return 1
        fi
    fi
    return 0
}

# Function to run tests with proper error handling
run_component_tests() {
    component=$1
    command=$2
    component_dir="${SCRIPT_DIR}/$3"

    echo -e "${YELLOW}===== Testing $component Component =====${NC}"
    
    # Verify the component directory exists
    if [ ! -d "$component_dir" ]; then
        echo -e "${RED}Component directory does not exist: $component_dir${NC}"
        return 1
    fi
    
    # Navigate to component directory
    cd "$component_dir" || { echo -e "${RED}Failed to navigate to $component_dir${NC}"; return 1; }
    
    # Run the command
    eval "$command"
    local result=$?
    
    # Check exit status
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓ $component tests passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $component tests failed${NC}"
        return 1
    fi
}

# Variable to track overall success
TESTS_PASSED=true

# Prepare server tests
if check_server_dependencies; then
    # 1. Server Component Tests
    SERVER_CMD="python -m pytest tests/ --cov=app --cov-report=term --cov-report=html:${SCRIPT_DIR}/test_reports/server_coverage"
    if run_component_tests "Server" "$SERVER_CMD" "server"; then
        echo "Server coverage report saved to test_reports/server_coverage/"
    else
        TESTS_PASSED=false
    fi
else
    echo -e "${RED}Skipping Server tests due to missing dependencies${NC}"
    TESTS_PASSED=false
fi

echo ""

# Prepare userscript tests
if check_userscript_dependencies; then
    # 2. Browser UserScript Tests
    USERSCRIPT_CMD="npm test -- --config=jest.config.js --coverage --coverageDirectory=${SCRIPT_DIR}/test_reports/userscript_coverage"
    if run_component_tests "UserScript" "$USERSCRIPT_CMD" "userscript"; then
        echo "UserScript coverage report saved to test_reports/userscript_coverage/"
    else
        TESTS_PASSED=false
    fi
else
    echo -e "${RED}Skipping UserScript tests due to missing dependencies${NC}"
    TESTS_PASSED=false
fi

echo ""

# 3. AutoHotkey Tests (if on Windows)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    AHK_CMD='"C:\Program Files\AutoHotkey\AutoHotkey.exe" tests/run_tests.ahk > ${SCRIPT_DIR}/test_reports/ahk_test_results.txt'
    if run_component_tests "AutoHotkey" "$AHK_CMD" "ahk"; then
        echo "AutoHotkey test results saved to test_reports/ahk_test_results.txt"
    else
        TESTS_PASSED=false
    fi
else
    echo -e "${YELLOW}Skipping AutoHotkey tests - requires Windows${NC}"
fi

# Navigate back to the root directory
cd "$SCRIPT_DIR" || exit 1

echo ""
echo -e "${YELLOW}===== Test Summary =====${NC}"
if [ "$TESTS_PASSED" = true ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo "Coverage reports are available in the test_reports directory"
    echo -e "${YELLOW}Server:${NC} test_reports/server_coverage/"
    echo -e "${YELLOW}UserScript:${NC} test_reports/userscript_coverage/"
    
    # Generate summary file
    cat > test_reports/test_summary.txt << EOF
NLLB Translation System Test Results
====================================
Date: $(date)

✓ Server Component: Tests Passed
  - Coverage report: ./server_coverage/index.html

✓ Browser UserScript Component: Tests Passed
  - Coverage report: ./userscript_coverage/index.html

EOF

    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
        echo -e "✓ AutoHotkey Component: Tests Passed" >> test_reports/test_summary.txt
        echo -e "  - Test results: ./ahk_test_results.txt" >> test_reports/test_summary.txt
    else
        echo -e "⚠ AutoHotkey Component: Tests Skipped (requires Windows)" >> test_reports/test_summary.txt
    fi

    echo -e "\nRecommended next steps:" >> test_reports/test_summary.txt
    echo -e "1. Check the code coverage reports to identify any gaps" >> test_reports/test_summary.txt
    echo -e "2. Improve test coverage for areas below targets (Server: 95%, UserScript: 90%, AutoHotkey: 85%)" >> test_reports/test_summary.txt
    echo -e "3. Document any known issues or edge cases that are difficult to test" >> test_reports/test_summary.txt
    
    echo "Summary saved to test_reports/test_summary.txt"
else
    echo -e "${RED}Some tests failed. Please check the output above for details.${NC}"
    
    # Generate summary file for failures
    cat > test_reports/test_summary.txt << EOF
NLLB Translation System Test Results
====================================
Date: $(date)

⚠ Test execution failed. Some components didn't pass all tests.

Please check the individual component test outputs for specific failures.
EOF
    
    echo "Summary saved to test_reports/test_summary.txt"
    exit 1
fi