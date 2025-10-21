#!/usr/bin/env python3
"""
Test script for PPL Meta Mini Upgrade 1 - Enhanced Age Estimation Logic
Tests the new age classification functionality.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.face_grouping import FaceGroupingEngine

def test_age_estimation_logic():
    """Test the enhanced age estimation logic with various scenarios."""
    
    engine = FaceGroupingEngine()
    
    # Test scenarios from the upgrade specifications
    test_cases = [
        # Scenario, unprocessed_age, distance, quality_score, expected_result
        ("High-quality adult", 35, 5.2, 0.421, "passed"),
        ("Low-quality adult (poor distance)", 32, 15.0, 0.421, "passed repeat"),
        ("Low-quality adult (poor quality)", 32, 5.0, 0.180, "passed repeat"),
        ("High-quality minor", 22, 4.1, 0.380, "check"),
        ("Low-quality minor (poor distance)", 19, 1.8, 0.380, "check repeat"),
        ("Low-quality minor (poor quality)", 19, 5.0, 0.120, "check repeat"),
        ("Borderline adult", 30, 5.0, 0.300, "passed"),
        ("Borderline minor", 29, 5.0, 0.300, "check"),
        ("Edge case - distance too low", 35, 2.0, 0.400, "passed repeat"),
        ("Edge case - distance too high", 35, 10.1, 0.400, "passed repeat"),
        ("Edge case - quality too low", 35, 5.0, 0.250, "passed repeat"),
    ]
    
    print("🧪 Testing PPL Meta Mini Upgrade 1 - Enhanced Age Estimation Logic")
    print("=" * 70)
    
    all_passed = True
    
    for i, (scenario, age, distance, quality, expected) in enumerate(test_cases, 1):
        result = engine.calculate_enhanced_age_estimate(age, distance, quality)
        actual = result["age_estimate"]
        
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        if actual != expected:
            all_passed = False
            
        print(f"{i:2d}. {scenario:<30} | Age: {age:2.0f} | Dist: {distance:4.1f} | Quality: {quality:.3f}")
        print(f"    Expected: {expected:<15} | Actual: {actual:<15} | {status}")
        
        if actual != expected:
            print(f"    Validation: {result['validation_details']}")
        print()
    
    print("=" * 70)
    if all_passed:
        print("🎉 All tests PASSED! Enhanced age estimation logic is working correctly.")
    else:
        print("❌ Some tests FAILED. Please review the implementation.")
    
    return all_passed

def test_validation_criteria():
    """Test the individual validation criteria."""
    
    engine = FaceGroupingEngine()
    
    print("\n🔍 Testing Validation Criteria")
    print("=" * 40)
    
    # Test distance validation
    test_distances = [1.5, 2.0, 2.1, 5.0, 10.0, 10.1, 15.0]
    print("Distance Validation (valid range: 2.0 < distance <= 10.0):")
    for dist in test_distances:
        result = engine.calculate_enhanced_age_estimate(25, dist, 0.300)
        is_valid = result["validation_details"]["distance_valid"]
        print(f"  Distance {dist:4.1f}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test quality validation
    test_qualities = [0.100, 0.250, 0.251, 0.300, 0.500, 0.800]
    print(f"\nQuality Validation (valid: quality > 0.250):")
    for qual in test_qualities:
        result = engine.calculate_enhanced_age_estimate(25, 5.0, qual)
        is_valid = result["validation_details"]["quality_valid"]
        print(f"  Quality {qual:.3f}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test age threshold
    test_ages = [18, 25, 29, 29.9, 30, 30.1, 35, 50]
    print(f"\nAge Threshold (adult: age >= 30):")
    for age in test_ages:
        result = engine.calculate_enhanced_age_estimate(age, 5.0, 0.300)
        is_adult = result["validation_details"]["age_threshold_met"]
        print(f"  Age {age:4.1f}: {'👤 Adult' if is_adult else '👶 Minor'}")

if __name__ == "__main__":
    print("🚀 PPL Meta Mini - Enhanced Age Estimation Testing")
    print("Starting Phase 1.1 implementation tests...\n")
    
    # Test the main logic
    success = test_age_estimation_logic()
    
    # Test validation criteria
    test_validation_criteria()
    
    print(f"\n{'🎯 Implementation Test Result: SUCCESS' if success else '❌ Implementation Test Result: FAILED'}")