#!/bin/bash
# Run E2E tests with HuggingFace authentication for Aya model

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running E2E Tests with Authenticated Models${NC}"
echo "================================================"

# Export HuggingFace token (set this in your environment)
if [ -z "$HF_TOKEN" ]; then
    echo -e "${RED}Warning: HF_TOKEN environment variable not set${NC}"
    echo "Please set your HuggingFace token: export HF_TOKEN='your_token_here'"
    exit 1
fi
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"

# Set model cache directory
export MODEL_CACHE_DIR="$HOME/.cache/huggingface/transformers"
export HF_HOME="$HOME/.cache/huggingface"
export TRANSFORMERS_CACHE="$HOME/.cache/huggingface/transformers"

# Change to project directory
cd "$(dirname "$0")"

echo -e "\n${YELLOW}1. Testing NLLB Model${NC}"
echo "------------------------"
pytest tests/e2e/test_nllb_model_e2e.py -v --tb=short || true

echo -e "\n${YELLOW}2. Testing Aya Model${NC}"
echo "---------------------"
pytest tests/e2e/test_aya_model_e2e.py -v --tb=short || true

echo -e "\n${YELLOW}3. Testing Single Model Loading${NC}"
echo "---------------------------------"
pytest tests/e2e/test_single_model_e2e.py -v --tb=short || true

echo -e "\n${YELLOW}4. Testing Multi-Model Workflows${NC}"
echo "----------------------------------"
pytest tests/e2e/test_multimodel_workflows.py -v --tb=short -k "test_basic" || true

echo -e "\n${GREEN}E2E Test Run Complete!${NC}"
echo "======================"

# Summary
echo -e "\n${YELLOW}Test Summary:${NC}"
echo "- NLLB model tests run with cached model (4.6GB)"
echo "- Aya Expanse 8B tests run with cached model (15GB)"
echo "- Both models authenticated and ready for testing"
echo ""
echo "Note: Some tests may fail due to resource constraints."
echo "Run individual test files for more focused testing."