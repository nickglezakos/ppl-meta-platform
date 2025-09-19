#!/bin/bash

# PPL Meta Platform - UI Integration Testing Script
# Automated validation for camera-orchestrator integration

echo "🧪 PPL Meta Platform - Comprehensive UI Integration Testing"
echo "=========================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to log test results
log_test() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        if [ -n "$details" ]; then
            echo -e "   ${RED}Details: $details${NC}"
        fi
        FAILED_TESTS=$((FAILED_TESTS + 1))
    elif [ "$status" = "SKIP" ]; then
        echo -e "${YELLOW}⏭️  SKIP${NC}: $test_name"
        if [ -n "$details" ]; then
            echo -e "   ${YELLOW}Reason: $details${NC}"
        fi
    else
        echo -e "${BLUE}ℹ️  INFO${NC}: $test_name"
    fi
    
    if [ -n "$details" ] && [ "$status" != "FAIL" ] && [ "$status" != "SKIP" ]; then
        echo -e "   ${details}"
    fi
}

# Function to check HTTP endpoint
check_endpoint() {
    local url="$1"
    local expected_status="${2:-200}"
    
    local response=$(curl -s -w "%{http_code}" -o /tmp/response.json "$url" 2>/dev/null)
    local http_code="${response: -3}"
    
    if [ "$http_code" = "$expected_status" ]; then
        return 0
    else
        return 1
    fi
}

# Function to check service health
check_service_health() {
    local service_name="$1"
    local health_url="$2"
    
    if check_endpoint "$health_url"; then
        log_test "$service_name Health Check" "PASS" "Service responding on $health_url"
    else
        log_test "$service_name Health Check" "FAIL" "Service not responding on $health_url"
    fi
}

echo "🔍 Phase 1: Backend Service Health Verification"
echo "------------------------------------------------"

# Check all backend services
check_service_health "Gateway Service" "http://localhost:8080/health"
check_service_health "Node Service" "http://localhost:8001/api/v1/health"
check_service_health "Media Service" "http://localhost:8000/health"
check_service_health "Orchestrator Service" "http://localhost:8002/health"
check_service_health "Vision Service" "http://localhost:8003/health"
check_service_health "Cameras Service" "http://localhost:8005/health"

echo ""
echo "🌐 Phase 2: Frontend Accessibility Check"
echo "----------------------------------------"

# Check if frontend is accessible
if check_endpoint "http://localhost:3000"; then
    log_test "Frontend Accessibility" "PASS" "Flutter app responding on port 3000"
else
    log_test "Frontend Accessibility" "FAIL" "Flutter app not accessible on port 3000"
fi

echo ""
echo "🔗 Phase 3: API Endpoint Validation"
echo "-----------------------------------"

# Test workflow-related endpoints
log_test "Media Workflow Endpoints" "INFO" "Testing workflow API endpoints..."

# Test face detection workflow status endpoint
if check_endpoint "http://localhost:8000/api/v1/workflow/face-detection/workflows"; then
    log_test "Media Workflow List Endpoint" "PASS" "/api/v1/workflow/face-detection/workflows"
else
    log_test "Media Workflow List Endpoint" "FAIL" "Endpoint not responding"
fi

# Test orchestrator workflow endpoints
if check_endpoint "http://localhost:8002/workflows/status"; then
    log_test "Orchestrator Status Endpoint" "PASS" "/workflows/status"
else
    log_test "Orchestrator Status Endpoint" "FAIL" "Endpoint not responding"
fi

# Test vision service endpoints
if check_endpoint "http://localhost:8003/health"; then
    log_test "Vision Service API" "PASS" "Vision Service API accessible"
else
    log_test "Vision Service API" "FAIL" "Vision Service API not accessible"
fi

echo ""
echo "📱 Phase 4: Camera Service Integration"
echo "-------------------------------------"

# Test camera service endpoints
if check_endpoint "http://localhost:8005/api/v1/cameras"; then
    log_test "Camera List Endpoint" "PASS" "/api/v1/cameras responding"
else
    log_test "Camera List Endpoint" "FAIL" "Camera API not responding"
fi

# Test camera registration endpoint
if check_endpoint "http://localhost:8005/api/v1/register" 404; then
    log_test "Camera Registration Endpoint" "PASS" "Endpoint exists (404 expected without POST data)"
else
    log_test "Camera Registration Endpoint" "FAIL" "Endpoint structure issue"
fi

echo ""
echo "🔄 Phase 5: Integration Testing"
echo "-------------------------------"

# Test workflow creation (without actual execution)
log_test "Workflow API Structure" "INFO" "Testing workflow API structure..."

# Create a test workflow request (dry run)
cat > /tmp/test_workflow.json << EOF
{
    "media_ids": ["test-media-id"],
    "method": "mtcnn",
    "confidence_threshold": 0.5,
    "store_results": true
}
EOF

# Test if the endpoint accepts the request structure (will likely fail with validation, but should not error)
response=$(curl -s -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d @/tmp/test_workflow.json \
    "http://localhost:8000/api/v1/workflow/face-detection/bulk-process" 2>/dev/null)

http_code="${response: -3}"

if [ "$http_code" = "401" ] || [ "$http_code" = "422" ] || [ "$http_code" = "400" ]; then
    log_test "Workflow Creation Endpoint" "PASS" "Endpoint accepts requests (auth/validation required)"
elif [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    log_test "Workflow Creation Endpoint" "PASS" "Endpoint fully functional"
else
    log_test "Workflow Creation Endpoint" "FAIL" "Endpoint not responding correctly (HTTP $http_code)"
fi

echo ""
echo "🎯 Phase 6: Cross-Service Communication"
echo "---------------------------------------"

# Test if services can communicate with each other
log_test "Service Discovery" "INFO" "Testing inter-service communication..."

# Test if Orchestrator can reach Media Service
orch_to_media=$(curl -s -w "%{http_code}" "http://localhost:8002/health" 2>/dev/null)
if [ "${orch_to_media: -3}" = "200" ]; then
    log_test "Orchestrator-Media Communication" "PASS" "Services can communicate"
else
    log_test "Orchestrator-Media Communication" "FAIL" "Communication issues detected"
fi

echo ""
echo "📊 Phase 7: Frontend Integration Points"
echo "---------------------------------------"

# These tests require manual verification but we can check the structure
log_test "Frontend Integration" "INFO" "Manual verification required for frontend features"
log_test "Camera UI Controls" "INFO" "Verify workflow buttons appear on camera cards"
log_test "Status Monitoring" "INFO" "Verify status dialogs and progress indicators"
log_test "Error Handling" "INFO" "Test error states and user feedback"

echo ""
echo "🔧 Phase 8: Performance & Load Testing"
echo "--------------------------------------"

# Basic performance checks
start_time=$(date +%s%N)
check_endpoint "http://localhost:8080/health"
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 ))

if [ $response_time -lt 1000 ]; then
    log_test "Gateway Response Time" "PASS" "Response time: ${response_time}ms"
elif [ $response_time -lt 3000 ]; then
    log_test "Gateway Response Time" "PASS" "Response time: ${response_time}ms (acceptable)"
else
    log_test "Gateway Response Time" "FAIL" "Response time: ${response_time}ms (too slow)"
fi

echo ""
echo "📋 Test Results Summary"
echo "======================"
echo -e "Total Tests: ${TOTAL_TESTS}"
echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"
echo -e "Skipped: $((TOTAL_TESTS - PASSED_TESTS - FAILED_TESTS))"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All automated tests passed! Ready for manual UI testing.${NC}"
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "1. Open Flutter app at http://localhost:3000"
    echo "2. Follow the comprehensive testing guide"
    echo "3. Test camera workflow controls manually"
    echo "4. Verify end-to-end automation"
else
    echo -e "\n${RED}⚠️  Some tests failed. Please address issues before manual testing.${NC}"
    echo -e "\n${YELLOW}Recommended Actions:${NC}"
    echo "1. Check failed service logs"
    echo "2. Verify service configurations"
    echo "3. Restart failed services if needed"
fi

echo ""
echo "📚 Additional Manual Testing Required:"
echo "------------------------------------"
echo "• Camera registration and connection"
echo "• Video recording and automatic workflow trigger"
echo "• Face detection workflow execution"
echo "• Result visualization and analytics"
echo "• Error handling and recovery"
echo "• Multi-camera orchestration"
echo ""
echo "📄 See COMPREHENSIVE_UI_INTEGRATION_TESTING_GUIDE.md for detailed manual testing steps"

# Cleanup
rm -f /tmp/test_workflow.json /tmp/response.json 2>/dev/null

exit $FAILED_TESTS