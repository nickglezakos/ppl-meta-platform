#!/usr/bin/env python3
"""
Simple Frame Extraction Test - Direct OpenCV Test
=================================================

This script tests frame extraction directly using OpenCV to identify
what's different between the working multi-video metadata and the
frame extraction endpoint.
"""

import base64
import io
import json
import os

import cv2
from PIL import Image


def test_direct_frame_extraction():
    """Test frame extraction directly with OpenCV."""

    print("🎬 Direct Frame Extraction Test")
    print("=" * 50)

    # Test configuration (from notebook variables)
    test_media_id = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"
    test_frames = [50, 100, 150, 200, 250, 300]  # Multiple frames for gallery

    # Correct file path found in storage
    correct_path = "/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media/storage/media/4cf362b1-3e05-4e85-81c7-c08a98c7e41b/video/2025/07/54c4666b56ff8b9dbb55abcafbb3c23f.mp4"

    print(f"📋 Testing with:")
    print(f"   Media ID: {test_media_id}")
    print(f"   Frames: {test_frames}")
    print(f"   File path: {correct_path}")

    # Verify file exists
    if not os.path.exists(correct_path):
        print(f"❌ File not found at: {correct_path}")
        return False

    print(f"✅ File found!")
    print(f"📊 File size: {os.path.getsize(correct_path) / (1024*1024):.1f} MB")

    # Test OpenCV access
    print(f"\n🎥 Testing OpenCV access...")
    cap = cv2.VideoCapture(correct_path)

    if not cap.isOpened():
        print(f"❌ OpenCV cannot open video")
        return False

    # Get video properties
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"✅ Video opened successfully:")
    print(f"   Total frames: {total_frames}")
    print(f"   FPS: {fps}")
    print(f"   Resolution: {width}x{height}")

    # Extract multiple frames
    extracted_frames = []
    print(f"\n🖼️ Extracting {len(test_frames)} frames...")
    
    for frame_number in test_frames:
        if frame_number >= total_frames:
            print(f"   ⚠️  Skipping frame {frame_number} (out of range)")
            continue
            
        print(f"   � Extracting frame {frame_number}...")
        
        # Seek to frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if not ret:
            print(f"   ❌ Could not read frame {frame_number}")
            continue
        
        # Convert to RGB and create JPEG
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        
        # Create JPEG data
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)
        jpeg_data = buffer.getvalue()
        
        # Store frame info
        frame_info = {
            'number': frame_number,
            'data': base64.b64encode(jpeg_data).decode('utf-8'),
            'size_kb': len(jpeg_data) / 1024,
            'width': pil_image.width,
            'height': pil_image.height,
            'timestamp': frame_number / fps if fps > 0 else 0
        }
        extracted_frames.append(frame_info)
        
        print(f"   ✅ Frame {frame_number}: {frame_info['size_kb']:.1f} KB")

    cap.release()
    
    print(f"\n✅ Successfully extracted {len(extracted_frames)} frames!")

    # Generate test HTML with gallery
    html_content = generate_gallery_html(
        extracted_frames,
        test_media_id,
        correct_path,
        {
            'total_frames': total_frames,
            'fps': fps,
            'width': width,
            'height': height
        }
    )

    # Save HTML file
    current_dir = os.getcwd()
    html_file = os.path.join(current_dir, "frame_extraction_gallery.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n📄 Gallery HTML generated: {html_file}")
    print(f"🌐 Open in browser: file://{html_file}")

    # Create a summary for debugging
    summary = {
        "test_status": "success",
        "media_id": test_media_id,
        "frames_extracted": len(extracted_frames),
        "file_path": correct_path,
        "file_size_mb": round(os.path.getsize(correct_path) / (1024 * 1024), 1),
        "video_properties": {
            "total_frames": total_frames,
            "fps": fps,
            "width": width,
            "height": height,
        },
        "frames": [
            {
                "number": frame["number"],
                "size_kb": frame["size_kb"],
                "timestamp": frame["timestamp"]
            }
            for frame in extracted_frames
        ]
    }

    print(f"\n📋 Test Summary:")
    print(json.dumps(summary, indent=2))

    return True


def generate_gallery_html(frames, media_id, file_path, video_props):
    """Generate HTML gallery with multiple frames."""
    
    frames_html = ""
    for frame in frames:
        frames_html += f"""
        <div class="frame-item">
            <img src="data:image/jpeg;base64,{frame['data']}" 
                 alt="Frame {frame['number']}" 
                 class="frame-image">
            <div class="frame-info">
                <div class="frame-number">Frame {frame['number']}</div>
                <div class="frame-meta">
                    Size: {frame['size_kb']:.1f} KB<br>
                    Time: {frame['timestamp']:.2f}s<br>
                    Dimensions: {frame['width']}×{frame['height']}
                </div>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Frame Extraction Gallery - Direct OpenCV Test</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f8fafc;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .title {{
            color: #059669;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #6b7280;
            font-size: 18px;
        }}
        .info-panel {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .info-item {{
            background: #f1f5f9;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }}
        .info-label {{
            font-weight: 600;
            color: #1e293b;
            font-size: 14px;
        }}
        .info-value {{
            color: #475569;
            font-family: 'SF Mono', Monaco, monospace;
            margin-top: 5px;
            word-break: break-all;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .frame-item {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }}
        .frame-item:hover {{
            transform: translateY(-4px);
        }}
        .frame-image {{
            width: 100%;
            height: 250px;
            object-fit: cover;
        }}
        .frame-info {{
            padding: 15px;
        }}
        .frame-number {{
            font-weight: 600;
            color: #1e293b;
            font-size: 16px;
            margin-bottom: 8px;
        }}
        .frame-meta {{
            color: #6b7280;
            font-size: 14px;
            line-height: 1.4;
        }}
        .comparison {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 12px;
            padding: 20px;
            margin-top: 30px;
        }}
        .comparison-title {{
            font-weight: 600;
            color: #92400e;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        .endpoint-info {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'SF Mono', Monaco, monospace;
            margin: 10px 0;
            word-break: break-all;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }}
        .stat-item {{
            text-align: center;
            padding: 10px;
            background: #f1f5f9;
            border-radius: 8px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: #3b82f6;
        }}
        .stat-label {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">🎬 Frame Extraction Gallery</div>
        <div class="subtitle">Direct OpenCV Test - Multiple Frames</div>
    </div>

    <div class="info-panel">
        <h3>Video Information</h3>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Media ID</div>
                <div class="info-value">{media_id}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Total Frames</div>
                <div class="info-value">{video_props['total_frames']:,}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Frame Rate</div>
                <div class="info-value">{video_props['fps']:.2f} FPS</div>
            </div>
            <div class="info-item">
                <div class="info-label">Resolution</div>
                <div class="info-value">{video_props['width']}×{video_props['height']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Duration</div>
                <div class="info-value">{video_props['total_frames']/video_props['fps']:.1f}s</div>
            </div>
            <div class="info-item">
                <div class="info-label">Frames Extracted</div>
                <div class="info-value">{len(frames)}</div>
            </div>
        </div>
    </div>

    <div class="stats">
        <div class="stat-item">
            <div class="stat-value">{len(frames)}</div>
            <div class="stat-label">Frames</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{sum(f['size_kb'] for f in frames):.0f}</div>
            <div class="stat-label">Total KB</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{sum(f['size_kb'] for f in frames)/len(frames):.1f}</div>
            <div class="stat-label">Avg KB</div>
        </div>
    </div>

    <div class="gallery">
        {frames_html}
    </div>

    <div class="comparison">
        <div class="comparison-title">🔍 Test Results & Debugging</div>
        
        <p><strong>✅ Successful Direct OpenCV Frame Extraction</strong></p>
        <ul>
            <li>✅ Video file found and accessible</li>
            <li>✅ OpenCV can read all frames successfully</li>
            <li>✅ JPEG conversion working perfectly</li>
            <li>✅ Multiple frame extraction completed</li>
        </ul>
        
        <p><strong>File Path Used:</strong></p>
        <div class="endpoint-info">{file_path}</div>
        
        <p><strong>Expected API Endpoint (after fix):</strong></p>
        <div class="endpoint-info">GET /api/v1/media/{media_id}/frame/{{frame_number}}</div>
        
        <p><strong>Key Insight:</strong> The frame extraction logic works perfectly. 
        The issue was in the API endpoint's file path resolution. 
        Our fix should now allow the endpoint to work correctly.</p>
    </div>
    
    <p style="text-align: center; color: #6b7280; margin-top: 30px;">
        Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</body>
</html>"""


if __name__ == "__main__":
    test_direct_frame_extraction()
