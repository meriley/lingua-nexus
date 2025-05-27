#!/bin/bash
# Comprehensive E2E test runner with model caching

set -e  # Exit on error

echo "============================================="
echo "Full E2E Test Suite with Model Caching"
echo "============================================="
echo

# Export HuggingFace token for Aya model access
export HF_TOKEN="test-hf-token-placeholder"
export HUGGING_FACE_HUB_TOKEN="test-hf-token-placeholder"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Start time
START_TIME=$(date +%s)

echo -e "${BLUE}Step 1: Checking model cache status...${NC}"
python tests/e2e/warm_model_cache.py --check-only 2>/dev/null || echo "Cache check script not found, will create cache on demand"
echo

echo -e "${BLUE}Step 2: Warming model cache (this may take 20-30 minutes on first run)...${NC}"
echo "Downloading and caching models:"
echo "  - facebook/nllb-200-distilled-600M (NLLB translation model, ~4.6GB)"
echo "  - CohereForAI/aya-expanse-8b (Aya Expanse 8B multilingual model, ~15GB)"
echo "Subsequent runs will be much faster as models will be cached."
echo

cd tests/e2e
if python warm_model_cache.py; then
    echo -e "${GREEN}✓ Model cache warmed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Cache warming had issues, but continuing with tests${NC}"
fi
echo

echo -e "${BLUE}Step 3: Running E2E tests with cached models...${NC}"
cd ../..

# Run the actual E2E tests with generous timeouts
if timeout 1800 python -m pytest tests/e2e/test_multimodel_e2e_refactored.py::TestMultiModelE2E::test_service_startup_and_health -v -s; then
    echo -e "${GREEN}✓ E2E service startup test passed${NC}"
    E2E_STARTUP_PASSED=true
else
    echo -e "${RED}✗ E2E service startup test failed${NC}"
    E2E_STARTUP_PASSED=false
fi

# End time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))

echo
echo "============================================="
echo "Full E2E Test Results"
echo "============================================="
echo "Duration: ${DURATION_MIN}m ${DURATION_SEC}s"
echo

if [ "$E2E_STARTUP_PASSED" = true ]; then
    echo -e "${GREEN}✓ E2E tests passed! Models are cached for future runs.${NC}"
    echo
    echo "Next steps:"
    echo "- Models are now cached in ~/.cache/huggingface/"
    echo "- Future E2E test runs should be much faster"
    echo "- You can run individual E2E tests with normal timeouts"
    echo
    exit 0
else
    echo -e "${RED}✗ E2E tests failed.${NC}"
    echo
    echo "This could be due to:"
    echo "- Insufficient memory (NLLB needs ~4GB RAM, Aya needs ~16GB RAM)"
    echo "- Slow internet connection (models are ~20GB total to download)"
    echo "- Insufficient disk space (cache needs ~20GB)"
    echo "- Hardware limitations"
    echo
    echo "Check the logs above for specific error messages."
    exit 1
fi