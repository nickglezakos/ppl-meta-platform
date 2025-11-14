#!/bin/bash
# Test runner for event subscription unit tests

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Event Subscription Unit Tests ===${NC}\n"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment not found${NC}"
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta

# Test suites
declare -a test_files=(
    "tests/unit/test_event_router.py"
    "tests/unit/test_websocket_subscriber.py"
    "tests/unit/test_polling_subscriber.py"
    "tests/unit/test_subscription_manager.py"
)

# Run each test suite
echo -e "${YELLOW}Running test suites...${NC}\n"

for test_file in "${test_files[@]}"; do
    echo -e "${GREEN}▶ Running: $test_file${NC}"
    pytest "$test_file" -v --tb=short || {
        echo -e "${RED}✗ Tests failed in $test_file${NC}"
        exit 1
    }
    echo ""
done

# Run all tests with coverage
echo -e "\n${GREEN}=== Running all tests with coverage ===${NC}\n"
pytest tests/unit/test_event_router.py \
       tests/unit/test_websocket_subscriber.py \
       tests/unit/test_polling_subscriber.py \
       tests/unit/test_subscription_manager.py \
       -v --cov=src/services --cov-report=term-missing || {
    echo -e "${RED}✗ Coverage tests failed${NC}"
    exit 1
}

echo -e "\n${GREEN}✓ All tests passed!${NC}"
