#!/bin/bash

# Script to clear all active camera streaming sessions using curl
echo "🧹 Clearing all active streaming sessions using curl..."

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU3Mjc0MzUwfQ.m_hPHk0fx2i1hk5WcjIevgS5OkP68M5TWG3Qh-kMD9U"
BASE_URL="http://localhost:8005"

# Get all session IDs and store them in a file
echo "📋 Getting all active sessions..."
curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/streaming-sessions" | \
python3 -c "
import sys, json
data = json.load(sys.stdin)
sessions = data['sessions']['sessions']
print(f'Found {len(sessions)} sessions to clear')
for session in sessions:
    print(session['session_id'])
" > /tmp/session_ids.txt

# Read the session count
SESSION_COUNT=$(head -1 /tmp/session_ids.txt | grep -o '[0-9]\+' || echo "0")
echo "Session count: $SESSION_COUNT"

# Skip the first line (which has the count) and process session IDs
if [ "$SESSION_COUNT" -gt 0 ]; then
    echo "🗑️ Deleting sessions..."
    tail -n +2 /tmp/session_ids.txt | while read -r session_id; do
        if [ ! -z "$session_id" ]; then
            echo "Deleting session: ${session_id:0:16}..."
            RESPONSE=$(curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/streaming-session/$session_id")
            if echo "$RESPONSE" | grep -q "successfully\|revoked"; then
                echo "✅ Success"
            else
                echo "❌ Failed: $RESPONSE"
            fi
        fi
    done
else
    echo "ℹ️ No sessions found to delete"
fi

# Check final count
echo ""
echo "📊 Final check..."
REMAINING=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/streaming-sessions" | \
python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data['sessions']['sessions']))
except:
    print('Error getting session count')
")

echo "Remaining sessions: $REMAINING"
echo "✅ Session cleanup complete!"

# Cleanup temp file
rm -f /tmp/session_ids.txt
