#!/usr/bin/env python3
"""
Frame Extraction Endpoint Test
==============================

This script tests the frame extraction functionality directly in the media service.
It helps debug issues with the frame extraction endpoint by testing it in isolation.
"""

import asyncio
import base64
import io
import json
import os
import sys
from pathlib import Path

import cv2
from PIL import Image

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config.settings import get_settings
from core.database import get_database
from services.media_service import MediaService


async def test_frame_extraction():
    """Test the frame extraction functionality directly."""

    print("🎬 Frame Extraction Test")
    print("=" * 50)

    # Test configuration
    test_media_id = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"  # UUID from notebook
    test_frame_number = 100

    try:
        # Initialize database and media service
        print("1️⃣ Initializing services...")
        settings = get_settings()
        db = await get_database()
        media_service = MediaService(db)

        # Test 1: Check if media exists in database
        print("\n2️⃣ Checking media in database...")
        media = await media_service.get_media_by_id(test_media_id)
        if media:
            print(f"   ✅ Media found in database:")
            print(f"   📁 File path: {media.file_path}")
            print(f"   📄 Filename: {media.filename}")
            print(f"   👤 User ID: {media.user_id}")
            print(f"   🎯 Media Type: {media.media_type}")
        else:
            print(f"   ❌ Media not found in database")
            return

        # Test 2: Check file system paths
        print("\n3️⃣ Checking file system...")

        # Try different path combinations
        file_paths_to_test = [
            media.file_path,  # Direct path from database
            os.path.join(settings.MEDIA_ROOT, media.file_path),  # With media root
            os.path.join(
                os.getcwd(), media.file_path
            ),  # With current working directory
            os.path.join(
                os.path.dirname(__file__), media.file_path
            ),  # Relative to this script
            os.path.join(
                os.path.dirname(__file__), "..", media.file_path
            ),  # One level up
        ]

        existing_path = None
        for path in file_paths_to_test:
            if os.path.exists(path):
                existing_path = path
                print(f"   ✅ File found at: {path}")
                break
            else:
                print(f"   ❌ Not found: {path}")

        if not existing_path:
            print("   ⚠️ File not found at any expected location")
            return

        # Test 3: Test OpenCV video access
        print("\n4️⃣ Testing OpenCV video access...")
        cap = cv2.VideoCapture(existing_path)

        if not cap.isOpened():
            print(f"   ❌ OpenCV cannot open video file")
            return

        # Get video info
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"   ✅ Video opened successfully:")
        print(f"   📊 Total frames: {total_frames}")
        print(f"   ⏱️ FPS: {fps}")
        print(f"   📐 Resolution: {width}x{height}")

        # Test 4: Extract specific frame
        print(f"\n5️⃣ Extracting frame {test_frame_number}...")

        if test_frame_number >= total_frames:
            print(
                f"   ⚠️ Frame {test_frame_number} exceeds total frames ({total_frames})"
            )
            test_frame_number = min(test_frame_number, total_frames - 1)
            print(f"   🔄 Using frame {test_frame_number} instead")

        # Set frame position
        cap.set(cv2.CAP_PROP_POS_FRAMES, test_frame_number)
        ret, frame = cap.read()

        if not ret:
            print(f"   ❌ Could not read frame {test_frame_number}")
            cap.release()
            return

        print(f"   ✅ Frame extracted successfully")
        print(f"   📐 Frame shape: {frame.shape}")

        # Test 5: Convert to different formats
        print("\n6️⃣ Testing format conversion...")

        # Convert to RGB (OpenCV uses BGR)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to PIL Image
        pil_image = Image.fromarray(frame_rgb)

        # Test different output formats
        formats_to_test = ["JPEG", "PNG", "WEBP"]
        for format_name in formats_to_test:
            try:
                buffer = io.BytesIO()
                if format_name == "JPEG":
                    pil_image.save(
                        buffer, format=format_name, quality=85, optimize=True
                    )
                else:
                    pil_image.save(buffer, format=format_name, optimize=True)
                buffer.seek(0)

                size_kb = len(buffer.getvalue()) / 1024
                print(f"   ✅ {format_name}: {size_kb:.1f} KB")

                # For JPEG, save a sample
                if format_name == "JPEG":
                    base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    sample_output = {
                        "frame_number": test_frame_number,
                        "format": format_name.lower(),
                        "size_kb": round(size_kb, 1),
                        "dimensions": f"{pil_image.width}x{pil_image.height}",
                        "base64_preview": base64_data[:100] + "...",  # First 100 chars
                    }
                    print(f"   📋 Sample output: {json.dumps(sample_output, indent=2)}")

            except Exception as e:
                print(f"   ❌ {format_name} failed: {e}")

        cap.release()

        # Test 6: Test the actual service method
        print("\n7️⃣ Testing MediaService.extract_video_frame method...")
        try:
            frame_result = await media_service.extract_video_frame(
                test_media_id,
                test_frame_number,
                format="jpeg",
                quality=85,
                size="medium",
            )

            print(f"   ✅ Service method succeeded:")
            print(f"   📊 Result keys: {list(frame_result.keys())}")
            print(
                f"   📐 Dimensions: {frame_result.get('width', 'N/A')}x{frame_result.get('height', 'N/A')}"
            )
            print(f"   📄 Format: {frame_result.get('format', 'N/A')}")
            print(f"   📦 Size: {len(frame_result.get('image_data', b''))} bytes")

            # Generate HTML output
            html_output = generate_test_html(
                frame_result, test_media_id, test_frame_number
            )
            html_file_path = os.path.join(
                os.path.dirname(__file__), "frame_extraction_test.html"
            )
            with open(html_file_path, "w") as f:
                f.write(html_output)
            print(f"   📄 HTML test file created: {html_file_path}")

        except Exception as e:
            print(f"   ❌ Service method failed: {e}")
            import traceback

            traceback.print_exc()

        print("\n✅ Frame extraction test completed!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


def generate_test_html(frame_result, media_id, frame_number):
    """Generate HTML test file to display the extracted frame."""

    base64_image = base64.b64encode(frame_result["image_data"]).decode("utf-8")

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Frame Extraction Test</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .success {{
            color: #10b981;
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .info-card {{
            background: #f8fafc;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }}
        .info-label {{
            font-weight: 600;
            color: #374151;
            margin-bottom: 5px;
        }}
        .info-value {{
            color: #6b7280;
            font-family: Monaco, 'Courier New', monospace;
        }}
        .frame-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .frame-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        }}
        .timestamp {{
            color: #6b7280;
            font-size: 14px;
            margin-top: 20px;
        }}
        .endpoint-info {{
            background: #f0f9ff;
            border: 1px solid #0ea5e9;
            border-radius: 8px;
            padding: 20px;
            margin-top: 30px;
        }}
        .endpoint-title {{
            font-weight: 600;
            color: #0369a1;
            margin-bottom: 10px;
        }}
        .endpoint-url {{
            font-family: Monaco, 'Courier New', monospace;
            background: #1e293b;
            color: #e2e8f0;
            padding: 10px;
            border-radius: 4px;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="success">✅ Frame Extraction Test Successful!</div>
            <p>Frame extraction endpoint is working correctly</p>
        </div>
        
        <div class="info-grid">
            <div class="info-card">
                <div class="info-label">Media ID</div>
                <div class="info-value">{media_id}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Frame Number</div>
                <div class="info-value">{frame_number}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Format</div>
                <div class="info-value">{frame_result.get('format', 'N/A').upper()}</div>
            </div>
            <div class="info-card">
                <div class="info-label">Dimensions</div>
                <div class="info-value">{frame_result.get('width', 'N/A')} × {frame_result.get('height', 'N/A')}</div>
            </div>
            <div class="info-card">
                <div class="info-label">File Size</div>
                <div class="info-value">{len(frame_result.get('image_data', b'')) / 1024:.1f} KB</div>
            </div>
            <div class="info-card">
                <div class="info-label">Timestamp</div>
                <div class="info-value">{frame_result.get('timestamp', 'N/A')}</div>
            </div>
        </div>
        
        <div class="frame-container">
            <h3>Extracted Frame</h3>
            <img src="data:image/{frame_result.get('format', 'jpeg')};base64,{base64_image}" 
                 alt="Extracted frame {frame_number}" 
                 class="frame-image">
        </div>
        
        <div class="endpoint-info">
            <div class="endpoint-title">API Endpoint Information</div>
            <p>This frame was extracted using the following endpoint:</p>
            <div class="endpoint-url">
                GET /api/v1/media/{media_id}/frame/{frame_number}?format=jpeg&quality=85&size=medium
            </div>
        </div>
        
        <div class="timestamp">
            Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

    return html_content


if __name__ == "__main__":
    asyncio.run(test_frame_extraction())
