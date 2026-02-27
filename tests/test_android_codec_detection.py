#!/usr/bin/env python3
"""
Test Android device detection and codec handling in media streaming.
"""

import re
from pathlib import Path

# Simulate the detection functions
def _is_android_client(user_agent: str) -> bool:
    if not user_agent:
        return False
    
    user_agent_lower = user_agent.lower()
    is_android = "android" in user_agent_lower
    is_flutter = "flutter" in user_agent_lower or "ppl" in user_agent_lower
    is_mobile_app = any(pattern in user_agent_lower for pattern in [
        "dalvik",
        "okhttp",
        "exoplayer",
        "mobile",
    ])
    
    return is_android and (is_flutter or is_mobile_app)


def _has_codec_issues(user_agent: str) -> bool:
    if not user_agent:
        return False
    
    user_agent_lower = user_agent.lower()
    
    problematic_patterns = [
        "samsung.*galaxy.*j",
        "sgh-j",
        "galaxy.*a[0-6]",
        "sm-a[0-6]0",
        "redmi.*4",
        "mido",
        "lenovo",
        "honor.*5",
        "honor.*6",
        "mt6735",
        "snapdragon.*40[01]",
    ]
    
    for pattern in problematic_patterns:
        if re.search(pattern, user_agent_lower):
            return True
    
    return False


# Test cases
test_cases = [
    # Normal modern Android
    ("Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36", 
     {"is_android": True, "has_codec_issues": False, "should_transcode": False}),
    
    # Flutter app on modern phone
    ("Dalvik/2.1.0 (Linux; U; Android 11; SM-G971B Build/RQ1A.201105.003) FlutterApp+PPL", 
     {"is_android": True, "has_codec_issues": False, "should_transcode": False}),
    
    # Galaxy J series (problematic)
    ("Mozilla/5.0 (Linux; Android 8; Samsung Galaxy J3) AppleWebKit/537.36", 
     {"is_android": True, "has_codec_issues": True, "should_transcode": True}),
    
    # Galaxy A5 (problematic old model)
    ("Dalvik/2.1.0 (Linux; Android 6; SM-A500F) OkHttp", 
     {"is_android": True, "has_codec_issues": True, "should_transcode": True}),
    
    # Xiaomi Redmi 4 (problematic)
    ("Mozilla/5.0 (Linux; Android 6; Redmi 4) AppleWebKit/537.36", 
     {"is_android": True, "has_codec_issues": True, "should_transcode": True}),
    
    # Lenovo device
    ("Dalvik/2.1.0 (Linux; Android 10; Lenovo Tab M10) OkHttp", 
     {"is_android": True, "has_codec_issues": True, "should_transcode": True}),
    
    # Desktop/web browser (not Android)
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0", 
     {"is_android": False, "has_codec_issues": False, "should_transcode": False}),
    
    # iOS (not Android)
    ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15", 
     {"is_android": False, "has_codec_issues": False, "should_transcode": False}),
    
    # Empty user agent
    ("", 
     {"is_android": False, "has_codec_issues": False, "should_transcode": False}),
]

print("=" * 80)
print("ANDROID DEVICE CODEC DETECTION TEST")
print("=" * 80)

passed = 0
failed = 0

for user_agent, expected in test_cases:
    is_android = _is_android_client(user_agent)
    has_codec_issues = _has_codec_issues(user_agent) if is_android else False
    should_transcode = has_codec_issues  # When android_compatible=false (default)
    
    # Check expectations
    is_android_match = is_android == expected["is_android"]
    codec_issues_match = has_codec_issues == expected["has_codec_issues"]
    transcode_match = should_transcode == expected["should_transcode"]
    
    all_match = is_android_match and codec_issues_match and transcode_match
    
    status = "✅ PASS" if all_match else "❌ FAIL"
    
    print(f"\n{status}")
    print(f"User-Agent: {user_agent[:70]}...")
    print(f"  Is Android Client: {is_android} (expected {expected['is_android']})")
    print(f"  Has Codec Issues: {has_codec_issues} (expected {expected['has_codec_issues']})")
    print(f"  Should Transcode (auto): {should_transcode} (expected {expected['should_transcode']})")
    
    if all_match:
        passed += 1
    else:
        failed += 1

print("\n" + "=" * 80)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 80)

# Exit with appropriate code
exit(0 if failed == 0 else 1)
