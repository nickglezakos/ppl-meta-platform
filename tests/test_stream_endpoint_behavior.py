#!/usr/bin/env python3
"""
Test the actual streaming endpoint logic with various Android User-Agents.

This simulates how the /stream endpoint will behave with different clients.
"""

import re

def _is_android_client(user_agent: str) -> bool:
    """Copied from ppl-meta-media/src/api/v1/media.py"""
    if not user_agent:
        return False
    user_agent_lower = user_agent.lower()
    is_android = "android" in user_agent_lower
    is_flutter = "flutter" in user_agent_lower or "ppl" in user_agent_lower
    is_mobile_app = any(pattern in user_agent_lower for pattern in [
        "dalvik", "okhttp", "exoplayer", "mobile",
    ])
    return is_android and (is_flutter or is_mobile_app)

def _has_codec_issues(user_agent: str) -> bool:
    """Copied from ppl-meta-media/src/api/v1/media.py"""
    if not user_agent:
        return False
    user_agent_lower = user_agent.lower()
    problematic_patterns = [
        "samsung.*galaxy.*j", "sgh-j", "galaxy.*a[0-6]", "sm-a[0-6]0",
        "redmi.*4", "mido", "lenovo", "honor.*5", "honor.*6",
        "mt6735", "snapdragon.*40[01]",
    ]
    for pattern in problematic_patterns:
        if re.search(pattern, user_agent_lower):
            return True
    return False

def simulate_stream_request(user_agent: str, android_compatible_param: bool = False):
    """Simulate the /stream endpoint logic"""
    is_android = _is_android_client(user_agent)
    has_codec_issues = _has_codec_issues(user_agent) if is_android else False
    should_transcode = android_compatible_param or (is_android and has_codec_issues)
    
    return {
        "detected_as_android": is_android,
        "detected_codec_issues": has_codec_issues,
        "request_param_android_compatible": android_compatible_param,
        "will_transcode": should_transcode,
    }

# Real-world test scenarios
scenarios = [
    {
        "name": "Pixel 6 - Modern Android",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6 Build/SQ1A.220105.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile",
        "android_compatible_param": False,
        "expected_transcode": False,
        "reason": "Modern device, no codec issues"
    },
    {
        "name": "PPL App on Pixel 6",
        "user_agent": "Dalvik/2.1.0 (Linux; U; Android 12; Pixel 6 Build/SQ1A.220105.002) ppl-meta-frontend/1.0.0 OkHttp/4.10.0",
        "android_compatible_param": False,
        "expected_transcode": False,
        "reason": "PPL app on modern device"
    },
    {
        "name": "Samsung Galaxy J3 (2016) - Problematic",
        "user_agent": "Mozilla/5.0 (Linux; Android 6.0.1; Samsung Galaxy J3 Build/MMB29K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.89 Mobile",
        "android_compatible_param": False,
        "expected_transcode": True,
        "reason": "Auto-detected as problematic, will transcode"
    },
    {
        "name": "Xiaomi Redmi 4 - Problematic",
        "user_agent": "Dalvik/2.1.0 (Linux; U; Android 6.0; Redmi 4 Build/MRA58K) OkHttp/4.9.0",
        "android_compatible_param": False,
        "expected_transcode": True,
        "reason": "Auto-detected as problematic, will transcode"
    },
    {
        "name": "Lenovo Tab M10 - Problematic",
        "user_agent": "Mozilla/5.0 (Linux; Android 10; Lenovo Tab M10 10.1-X306F Build/QP6A.180720.075) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.109 Mobile",
        "android_compatible_param": False,
        "expected_transcode": True,
        "reason": "Lenovo is in problematic list"
    },
    {
        "name": "Browser on Desktop (Windows)",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        "android_compatible_param": False,
        "expected_transcode": False,
        "reason": "Not Android"
    },
    {
        "name": "iPhone with Web Browser",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1",
        "android_compatible_param": False,
        "expected_transcode": False,
        "reason": "iOS, not Android"
    },
    {
        "name": "Pixel 6 - Explicit transcode request",
        "user_agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36",
        "android_compatible_param": True,
        "expected_transcode": True,
        "reason": "Explicit ?android_compatible=true parameter"
    },
]

print("\n" + "=" * 120)
print("STREAMING ENDPOINT BEHAVIOR SIMULATION")
print("=" * 120)

passed = 0
failed = 0

for scenario in scenarios:
    result = simulate_stream_request(
        scenario["user_agent"],
        scenario["android_compatible_param"]
    )
    
    will_transcode = result["will_transcode"]
    expected_transcode = scenario["expected_transcode"]
    matches = will_transcode == expected_transcode
    
    status = "✅ PASS" if matches else "❌ FAIL"
    
    print(f"\n{status} | {scenario['name']}")
    print(f"   Reason: {scenario['reason']}")
    print(f"   User-Agent: {scenario['user_agent'][:80]}...")
    print(f"   ?android_compatible={scenario['android_compatible_param']}")
    print(f"   Detected: Android={result['detected_as_android']}, CodecIssues={result['detected_codec_issues']}")
    print(f"   Will transcode: {will_transcode} (expected {expected_transcode})")
    
    if matches:
        passed += 1
    else:
        failed += 1

print("\n" + "=" * 120)
print(f"STREAMING ENDPOINT TEST: {passed} passed, {failed} failed out of {len(scenarios)} scenarios")
print("=" * 120 + "\n")

# Test matrix summary
print("BEHAVIOR MATRIX")
print("-" * 120)
print("Device Type          | Auto-Detect | Param Explicit | Result")
print("-" * 120)
print("Modern Android       |     No      |      No        | ✅ No transcode (serve original)")
print("Modern Android       |     No      |      Yes       | ✅ Transcode to Baseline")
print("Old/Budget Android   |     Yes     |      No        | ✅ Auto-transcode to Baseline")
print("Old/Budget Android   |     Yes     |      Yes       | ✅ Transcode to Baseline")
print("Desktop/Web Browser  |     No      |      No        | ✅ No transcode (not Android)")
print("iOS Mobile           |     No      |      No        | ✅ No transcode (not Android)")
print("-" * 120)

exit(0 if failed == 0 else 1)
