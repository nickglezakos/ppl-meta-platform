import re
from pathlib import Path
from datetime import datetime, timedelta

log_path = Path('logs/ppl-meta-media.log')
if not log_path.exists():
    print('missing logs/ppl-meta-media.log')
    raise SystemExit(1)

lines = log_path.read_text(errors='ignore').splitlines()
rows = []
for line in lines:
    if "'trigger_name': 'ppl-match'" not in line:
        continue

    evaluated = re.search(r"'evaluated_at': datetime\.datetime\(([^\)]*)\)", line)
    source = re.search(r"'source_mvr_uuid': '([^']*)'", line)
    reason = re.search(r"'reason': '([^']*)'", line)
    passed = re.search(r"'passed': (True|False)", line)
    action = re.search(r"'action_executed': (True|False)", line)
    score = re.search(r"'similarity_score': ([^,}]+)", line)
    member = re.search(r"'matched_member_uuid': '([^']*)'", line)

    timestamp = None
    if evaluated:
        numbers = []
        for part in evaluated.group(1).split(',')[:7]:
            token = part.strip()
            if token.isdigit():
                numbers.append(int(token))
        if len(numbers) >= 6:
            while len(numbers) < 7:
                numbers.append(0)
            year, month, day, hour, minute, second, microsecond = numbers[:7]
            try:
                timestamp = datetime(year, month, day, hour, minute, second, microsecond)
            except Exception:
                timestamp = None

    if timestamp is None:
        continue

    rows.append({
        'timestamp': timestamp,
        'source_mvr_uuid': source.group(1) if source else '',
        'similarity_score': score.group(1).strip() if score else '',
        'matched_member_uuid': member.group(1) if member else '',
        'passed': passed.group(1) if passed else '',
        'action_executed': action.group(1) if action else '',
        'reason': reason.group(1) if reason else '',
    })

rows.sort(key=lambda item: item['timestamp'])

if rows:
    cutoff = rows[-1]['timestamp'] - timedelta(minutes=10)
    recent = [item for item in rows if item['timestamp'] >= cutoff]
    if len(recent) < 10:
        recent = rows[-20:]
else:
    recent = []

print('timestamp_utc | passed | action_executed | similarity_score | source_mvr_uuid | matched_member_uuid | reason')
print('-' * 170)
for item in recent:
    print(
        f"{item['timestamp'].isoformat()}Z | {item['passed']:5} | {item['action_executed']:14} | "
        f"{item['similarity_score']:16} | {item['source_mvr_uuid']} | {item['matched_member_uuid']} | {item['reason']}"
    )

fired = sum(1 for item in recent if item['passed'] == 'True')
print(f"\nsummary: events={len(recent)} fired={fired} skipped={len(recent) - fired}")
