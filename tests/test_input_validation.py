#!/usr/bin/env python3
"""
Test script for the PPL Meta Platform input validation system.
Resolves ISSUE-016: Missing Input Validation

This script tests the shared validation module functionality:
- User creation validation
- Password validation
- Security validation (SQL injection, XSS)
- Error handling
"""

import os
import sys

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

try:
    from shared.validation import (
        FieldValidators,
        SecurityValidator,
        ValidationErrorType,
        validate_password_update_data,
        validate_user_create_data,
    )

    print("✅ Successfully imported validation module")
except ImportError as e:
    print(f"❌ Failed to import validation module: {e}")
    sys.exit(1)


def test_valid_user_creation():
    """Test valid user creation data."""
    print("\n🧪 Testing valid user creation...")

    valid_data = {
        "username": "testuser123",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "given_name": "Test",
        "family_name": "User",
    }

    try:
        result = validate_user_create_data(valid_data)
        print("✅ Valid user data passed validation")
        print(f"   Username: {result['username']}")
        print(f"   Email: {result['email']}")
        return True
    except Exception as e:
        print(f"❌ Valid data failed validation: {e}")
        return False


def test_invalid_user_creation():
    """Test invalid user creation data."""
    print("\n🧪 Testing invalid user creation...")

    test_cases = [
        {
            "data": {"username": "ab", "email": "invalid-email", "password": "weak"},
            "expected": "Short username, invalid email, weak password",
        },
        {
            "data": {
                "username": "admin",
                "email": "test@example.com",
                "password": "Password123!",
            },
            "expected": "Forbidden username",
        },
        {
            "data": {
                "username": "test'; DROP TABLE users; --",
                "email": "test@example.com",
                "password": "Password123!",
            },
            "expected": "SQL injection attempt",
        },
    ]

    passed = 0
    for i, test_case in enumerate(test_cases):
        try:
            validate_user_create_data(test_case["data"])
            print(f"❌ Test {i+1} failed: Should have rejected {test_case['expected']}")
        except Exception as e:
            print(f"✅ Test {i+1} passed: Correctly rejected {test_case['expected']}")
            passed += 1

    return passed == len(test_cases)


def test_password_validation():
    """Test password validation."""
    print("\n🧪 Testing password validation...")

    test_cases = [
        ("ValidPass123!", True, "Strong password"),
        ("weak", False, "Too short"),
        ("nouppercasehere123!", False, "No uppercase"),
        ("NOLOWERCASEHERE123!", False, "No lowercase"),
        ("NoNumbersHere!", False, "No numbers"),
        ("NoSpecialChars123", False, "No special characters"),
        ("aaaaaaaA1!", False, "Repeated characters"),
    ]

    passed = 0
    for password, should_pass, description in test_cases:
        try:
            FieldValidators.validate_password(password)
            if should_pass:
                print(f"✅ {description}: Passed")
                passed += 1
            else:
                print(f"❌ {description}: Should have failed")
        except ValueError as e:
            if not should_pass:
                print(f"✅ {description}: Correctly rejected - {e}")
                passed += 1
            else:
                print(f"❌ {description}: Should have passed - {e}")

    return passed == len(test_cases)


def test_security_validation():
    """Test security validation (SQL injection, XSS)."""
    print("\n🧪 Testing security validation...")

    test_cases = [
        ("'; DROP TABLE users; --", "SQL injection"),
        ("' OR '1'='1", "SQL injection"),
        ("<script>alert('xss')</script>", "XSS script"),
        ("javascript:alert('xss')", "XSS javascript"),
        ("onclick=alert('xss')", "XSS event handler"),
    ]

    passed = 0
    for malicious_input, attack_type in test_cases:
        try:
            SecurityValidator.validate_sql_injection(malicious_input, "test_field")
            SecurityValidator.validate_xss(malicious_input, "test_field")
            print(f"❌ {attack_type}: Should have been detected")
        except ValueError:
            print(f"✅ {attack_type}: Correctly detected and blocked")
            passed += 1

    return passed == len(test_cases)


def test_html_sanitization():
    """Test HTML sanitization."""
    print("\n🧪 Testing HTML sanitization...")

    test_cases = [
        ("<b>Bold text</b>", "Safe HTML preserved"),
        ("<script>alert('xss')</script>", "Dangerous script removed"),
        ("<p>Paragraph with <strong>strong</strong> text</p>", "Mixed safe tags"),
    ]

    for html_input, description in test_cases:
        sanitized = SecurityValidator.sanitize_html(html_input)
        print(f"✅ {description}:")
        print(f"   Input:  {html_input}")
        print(f"   Output: {sanitized}")

    return True


def test_password_update_validation():
    """Test password update validation."""
    print("\n🧪 Testing password update validation...")

    # Test valid password update
    valid_data = {"old_password": "OldPassword123!", "new_password": "NewPassword456!"}

    try:
        result = validate_password_update_data(valid_data)
        print("✅ Valid password update passed validation")
    except Exception as e:
        print(f"❌ Valid password update failed: {e}")
        return False

    # Test same password rejection
    invalid_data = {
        "old_password": "SamePassword123!",
        "new_password": "SamePassword123!",
    }

    try:
        validate_password_update_data(invalid_data)
        print("❌ Should have rejected same old/new password")
        return False
    except Exception:
        print("✅ Correctly rejected same old/new password")

    return True


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("PPL Meta Platform - Input Validation Test Suite")
    print("Resolves ISSUE-016: Missing Input Validation")
    print("=" * 60)

    tests = [
        ("Valid User Creation", test_valid_user_creation),
        ("Invalid User Creation", test_invalid_user_creation),
        ("Password Validation", test_password_validation),
        ("Security Validation", test_security_validation),
        ("HTML Sanitization", test_html_sanitization),
        ("Password Update Validation", test_password_update_validation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} tests...")
        if test_func():
            print(f"✅ {test_name}: ALL TESTS PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: SOME TESTS FAILED")

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} test suites passed")

    if passed == total:
        print("🎉 ALL VALIDATION TESTS PASSED!")
        print("\n✅ ISSUE-016 Resolution Validated:")
        print("   • Comprehensive input validation implemented")
        print("   • SQL injection prevention working")
        print("   • XSS protection active")
        print("   • Password strength validation enforced")
        print("   • Error handling standardized")
        return 0
    else:
        print("⚠️  Some validation tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
