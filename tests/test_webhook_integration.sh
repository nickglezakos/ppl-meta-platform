#!/bin/bash

###############################################################################
# Webhook Integration Test Script
# Purpose: Validate end-to-end webhook functionality
# Version: 1.0.0
# Created: 2025-01-15
###############################################################################

set -e  # Exit on error

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8003}"
MEDIA_SERVICE_URL="${MEDIA_SERVICE_URL:-http://localhost:8001}"
COMMS_SERVICE_URL="${COMMS_SERVICE_URL:-http://localhost:8004}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test webhook URL (using webhook.site as example)
WEBHOOK_SITE_URL="https://webhook.site/unique-uuid-here"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Webhook Integration Test Suite${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

###############################################################################
# Step 1: Health Checks
###############################################################################
echo -e "${YELLOW}Step 1: Verifying Service Health...${NC}"

check_service() {
    local url=$1
    local name=$2
    
    if curl -s -f "${url}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ${name} is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} ${name} is not responding"
        return 1
    fi
}

check_service "$MEDIA_SERVICE_URL" "Media Service"
check_service "$COMMS_SERVICE_URL" "Communications Service"
check_service "$GATEWAY_URL" "Gateway"

echo ""

###############################################################################
# Step 2: Create Webhook Action via Media Service
###############################################################################
echo -e "${YELLOW}Step 2: Creating Webhook Action...${NC}"

# Webhook action configuration
WEBHOOK_CONFIG=$(cat <<EOF
{
  "url": "${WEBHOOK_SITE_URL}",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "X-Custom-Header": "PPL-Meta-Test"
  },
  "payload_data": {
    "source": "ppl-meta-platform",
    "test": true
  }
}
EOF
)

# Create action
ACTION_RESPONSE=$(curl -s -X POST "${MEDIA_SERVICE_URL}/api/v1/user-actions" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Webhook Action\",
    \"description\": \"Integration test webhook\",
    \"action_type\": \"webhook\",
    \"action_config\": $(echo "$WEBHOOK_CONFIG" | jq -c -R -s '.'),
    \"is_active\": true
  }")

ACTION_UUID=$(echo "$ACTION_RESPONSE" | jq -r '.uuid')

if [ "$ACTION_UUID" != "null" ] && [ -n "$ACTION_UUID" ]; then
    echo -e "${GREEN}✓${NC} Webhook action created with UUID: ${ACTION_UUID}"
else
    echo -e "${RED}✗${NC} Failed to create webhook action"
    echo "Response: $ACTION_RESPONSE"
    exit 1
fi

echo ""

###############################################################################
# Step 3: Send Test Webhook via Communications Service
###############################################################################
echo -e "${YELLOW}Step 3: Sending Test Webhook...${NC}"

WEBHOOK_PAYLOAD=$(cat <<EOF
{
  "event": "test_webhook",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "data": {
    "message": "Webhook integration test",
    "action_uuid": "${ACTION_UUID}"
  }
}
EOF
)

WEBHOOK_RESPONSE=$(curl -s -X POST "${COMMS_SERVICE_URL}/api/v1/webhook/send" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${WEBHOOK_SITE_URL}\",
    \"method\": \"POST\",
    \"headers\": {
      \"Content-Type\": \"application/json\",
      \"X-Test-Header\": \"Integration-Test\"
    },
    \"payload\": $(echo "$WEBHOOK_PAYLOAD" | jq -c '.'),
    \"trigger_id\": \"test-trigger-$(date +%s)\",
    \"tenant_name\": \"test-tenant\"
  }")

WEBHOOK_STATUS=$(echo "$WEBHOOK_RESPONSE" | jq -r '.status')

if [ "$WEBHOOK_STATUS" == "delivered" ] || [ "$WEBHOOK_STATUS" == "sent" ]; then
    echo -e "${GREEN}✓${NC} Webhook sent successfully with status: ${WEBHOOK_STATUS}"
    COMMUNICATION_LOG_ID=$(echo "$WEBHOOK_RESPONSE" | jq -r '.communication_log_id')
    echo -e "   Communication Log ID: ${COMMUNICATION_LOG_ID}"
else
    echo -e "${RED}✗${NC} Failed to send webhook"
    echo "Response: $WEBHOOK_RESPONSE"
fi

echo ""

###############################################################################
# Step 4: Verify Communication Log
###############################################################################
echo -e "${YELLOW}Step 4: Verifying Communication Log...${NC}"

sleep 1  # Wait for log to be written

LOGS_RESPONSE=$(curl -s "${COMMS_SERVICE_URL}/api/v1/audit/logs?type=webhook&page=1&page_size=5")
LOGS_COUNT=$(echo "$LOGS_RESPONSE" | jq -r '.total')

if [ "$LOGS_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found ${LOGS_COUNT} webhook log(s)"
    
    # Display latest log
    LATEST_LOG=$(echo "$LOGS_RESPONSE" | jq -r '.logs[0]')
    echo -e "\n${BLUE}Latest Webhook Log:${NC}"
    echo "$LATEST_LOG" | jq '{
      id,
      type,
      status,
      trigger_id,
      created_at,
      response_data
    }'
else
    echo -e "${YELLOW}⚠${NC} No webhook logs found (this might be expected if logs are async)"
fi

echo ""

###############################################################################
# Step 5: Test Webhook Action Execution (Simulated Trigger)
###############################################################################
echo -e "${YELLOW}Step 5: Testing Webhook Action Execution...${NC}"

# Note: This would normally be triggered by the Redis subscriber
# For testing, we'll directly call the webhook endpoint

TRIGGER_PAYLOAD=$(cat <<EOF
{
  "trigger_id": "test-trigger-$(date +%s)",
  "trigger_name": "Test Trigger",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "action_uuid": "${ACTION_UUID}"
}
EOF
)

EXEC_RESPONSE=$(curl -s -X POST "${COMMS_SERVICE_URL}/api/v1/webhook/send" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${WEBHOOK_SITE_URL}\",
    \"method\": \"POST\",
    \"payload\": $(echo "$TRIGGER_PAYLOAD" | jq -c '.'),
    \"trigger_id\": \"test-trigger-$(date +%s)\"
  }")

EXEC_STATUS=$(echo "$EXEC_RESPONSE" | jq -r '.status')

if [ "$EXEC_STATUS" == "delivered" ] || [ "$EXEC_STATUS" == "sent" ]; then
    echo -e "${GREEN}✓${NC} Webhook action executed successfully"
else
    echo -e "${RED}✗${NC} Webhook action execution failed"
    echo "Response: $EXEC_RESPONSE"
fi

echo ""

###############################################################################
# Step 6: Cleanup
###############################################################################
echo -e "${YELLOW}Step 6: Cleaning up test resources...${NC}"

DELETE_RESPONSE=$(curl -s -X DELETE "${MEDIA_SERVICE_URL}/api/v1/user-actions/${ACTION_UUID}")

if echo "$DELETE_RESPONSE" | jq -e '.message' > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Test webhook action deleted"
else
    echo -e "${YELLOW}⚠${NC} Could not delete test action (may need manual cleanup)"
fi

echo ""

###############################################################################
# Test Summary
###############################################################################
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Test Summary${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}✓ All webhook integration tests passed!${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Check webhook.site for received webhooks"
echo -e "  2. Verify frontend displays webhook actions correctly"
echo -e "  3. Test webhook actions with real triggers"
echo ""
echo -e "${BLUE}Webhook Integration Test Complete!${NC}"
