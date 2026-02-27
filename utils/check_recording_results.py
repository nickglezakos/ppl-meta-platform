#!/usr/bin/env python3
"""Check results of the latest recording session."""

import requests
from datetime import datetime, timezone

# Get auth token
print("🔐 Authenticating...")
login_response = requests.post(
    'http://localhost:8001/api/v1/users/login',
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    data='username=fresh.user@example.com&password=NewPassword234!'
)
token = login_response.json()['access_token']
print(f"✅ Token: {token[:20]}...\n")

headers = {'Authorization': f'Bearer {token}'}

# Check today's date
today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
print(f"📅 Checking data for: {today}\n")

# 1. Check MVR people created today
print("=" * 70)
print("1. MVR PEOPLE CREATED TODAY")
print("=" * 70)
mvr_response = requests.post(
    'http://localhost:8008/api/v1/mvr-people/search/by-collection',
    headers={**headers, 'Content-Type': 'application/json'},
    json={
        'collection_name': 'usb_camera_0',
        'start_time': f'{today}T00:00:00.000Z',
        'end_time': f'{today}T23:59:59.999Z',
        'limit': 500
    }
)
mvr_data = mvr_response.json()
if mvr_data.get('success'):
    mvr_count = len(mvr_data.get('data', {}).get('mvr_people', []))
    print(f"✅ MVR People found: {mvr_count}")
    if mvr_count > 0:
        print("\nMVR Details:")
        for mvr in mvr_data['data']['mvr_people'][:5]:  # Show first 5
            print(f"  - {mvr['mvr_people_id']}: {mvr['appearance_count']} appearances")
else:
    print(f"❌ Error: {mvr_data.get('message', 'Unknown error')}")

print()

# 2. Check individuals created today
print("=" * 70)
print("2. INDIVIDUALS CREATED TODAY")
print("=" * 70)
individuals_response = requests.get(
    f'http://localhost:8008/api/v1/individuals?created_after={today}T00:00:00.000Z&limit=100',
    headers=headers
)
if individuals_response.status_code == 200:
    ind_data = individuals_response.json()
    if ind_data.get('success'):
        ind_count = ind_data.get('data', {}).get('total_count', 0)
        print(f"✅ Individuals found: {ind_count}")
        if ind_count > 0:
            print("\nIndividual Details:")
            for ind in ind_data['data']['individuals'][:5]:  # Show first 5
                print(f"  - {ind['individual_id']}: confidence {ind['confidence_score']:.2f}")
    else:
        print(f"❌ Error: {ind_data.get('message', 'Unknown')}")
else:
    print(f"⚠️ Individuals endpoint returned: {individuals_response.status_code}")

print()

# 3. Check recent tracking sessions
print("=" * 70)
print("3. RECENT TRACKING SESSIONS (Last 10)")
print("=" * 70)
sessions_response = requests.get(
    'http://localhost:8008/api/v1/tracking/sessions?limit=10',
    headers=headers
)
if sessions_response.status_code == 200:
    sess_data = sessions_response.json()
    if sess_data.get('success'):
        sessions = sess_data.get('data', {}).get('sessions', [])
        print(f"✅ Sessions found: {len(sessions)}")
        print("\nRecent Sessions:")
        for sess in sessions[:5]:
            created = sess['created_at'][:19]
            status = sess['status']
            total_vids = sess.get('total_videos', 0)
            inds = sess.get('individuals_found', 0)
            mvrs = sess.get('unique_mvr_people_count', 0)
            print(f"  - {created} | {status:10} | {total_vids} videos | {inds} inds | {mvrs} MVRs")
    else:
        print(f"❌ Error: {sess_data.get('message', 'Unknown')}")
else:
    print(f"⚠️ Sessions endpoint returned: {sessions_response.status_code}")

print()

# 4. Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"📊 MVR People today: {mvr_count if mvr_data.get('success') else 'Unknown'}")
print(f"📊 Individuals today: {ind_count if 'ind_count' in locals() else 'Unknown'}")
print("\n✅ Check complete!")
