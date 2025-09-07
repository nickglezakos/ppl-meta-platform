#!/bin/bash

# Clear all active streaming sessions

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU3Mjc0MzUwfQ.m_hPHk0fx2i1hk5WcjIevgS5OkP68M5TWG3Qh-kMD9U"
BASE_URL="http://localhost:8005"

echo "🧹 Clearing all active streaming sessions..."

# Get session IDs and store in array
SESSION_IDS=($(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/streaming-sessions" | python3 -c "
import sys, json
data = json.load(sys.stdin)
sessions = data['sessions']['sessions']
for session in sessions:
    print(session['session_id'])
"))

echo "Found ${#SESSION_IDS[@]} sessions to clear"

# Revoke each session
for session_id in "${SESSION_IDS[@]}"; do
    echo "Revoking session: ${session_id:0:16}..."
    curl -s -X DELETE -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/streaming-session/$session_id" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Success"
    else
        echo "❌ Failed"
    fi
done

# Check final count
REMAINING=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/auth/streaming-sessions" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data['sessions']['sessions']))
")

echo "📊 Remaining sessions: $REMAINING"
echo "✅ Session cleanup complete!"
