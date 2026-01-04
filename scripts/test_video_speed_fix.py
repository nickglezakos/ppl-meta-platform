#!/usr/bin/env python3
"""
Test script to verify RTSP video playback speed fix.

This script checks if a video has correct frame count matching declared FPS.
"""

import sys
import cv2
from pathlib import Path


def check_video_frame_accuracy(video_path: str) -> dict:
    """
    Check if video has correct frame count for its declared FPS.
    
    Returns dict with:
        - declared_fps: FPS from video metadata
        - actual_fps: Calculated from frame_count / duration
        - difference: Absolute difference between declared and actual
        - needs_correction: Whether frontend correction is needed
        - correction_factor: Playback speed correction (declared / actual)
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return {"error": f"Could not open video: {video_path}"}
    
    try:
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # Calculate actual FPS
        actual_fps = total_frames / duration if duration > 0 else 0
        
        # Calculate difference and correction
        difference = abs(actual_fps - fps)
        needs_correction = difference > 0.5  # More than 0.5 FPS difference
        correction_factor = fps / actual_fps if actual_fps > 0 else 1.0
        
        return {
            "video_path": video_path,
            "declared_fps": round(fps, 2),
            "total_frames": total_frames,
            "duration_seconds": round(duration, 2),
            "actual_fps": round(actual_fps, 2),
            "fps_difference": round(difference, 2),
            "needs_correction": needs_correction,
            "correction_factor": round(correction_factor, 4),
            "playback_speed_note": f"Play at {correction_factor:.4f}x to correct" if needs_correction else "Play at 1.0x (normal speed)",
        }
    finally:
        cap.release()


def print_results(results: dict):
    """Pretty print results."""
    print("\n" + "=" * 70)
    print("VIDEO PLAYBACK SPEED ANALYSIS")
    print("=" * 70)
    
    if "error" in results:
        print(f"❌ ERROR: {results['error']}")
        return
    
    print(f"📁 File: {Path(results['video_path']).name}")
    print(f"📊 Metadata:")
    print(f"   - Declared FPS: {results['declared_fps']}")
    print(f"   - Total Frames: {results['total_frames']}")
    print(f"   - Duration: {results['duration_seconds']}s")
    print()
    print(f"🔍 Analysis:")
    print(f"   - Actual FPS: {results['actual_fps']}")
    print(f"   - FPS Difference: {results['fps_difference']}")
    print()
    
    if results['needs_correction']:
        print(f"⚠️  CORRECTION NEEDED:")
        print(f"   - Video has {results['fps_difference']} FPS discrepancy")
        print(f"   - Frontend should apply: {results['correction_factor']}x playback speed")
        print(f"   - This will slow down from {results['actual_fps']} FPS to {results['declared_fps']} FPS")
    else:
        print(f"✅ VIDEO IS CORRECT:")
        print(f"   - Frame count matches declared FPS")
        print(f"   - No correction needed")
        print(f"   - Backend recording fix is working!")
    
    print("=" * 70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_video_speed_fix.py <video_path>")
        print("\nExample:")
        print("  python3 test_video_speed_fix.py /path/to/rtsp_video.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    if not Path(video_path).exists():
        print(f"❌ Error: Video file not found: {video_path}")
        sys.exit(1)
    
    print("🔍 Analyzing video...")
    results = check_video_frame_accuracy(video_path)
    print_results(results)
    
    # Exit code: 0 if correct, 1 if needs correction, 2 if error
    if "error" in results:
        sys.exit(2)
    elif results['needs_correction']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
