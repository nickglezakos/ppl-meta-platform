#!/usr/bin/env python3
"""
Test frame extraction after fixing the file path issue.
"""

import time
from pathlib import Path

import requests


def test_frame_extraction():
    """Test the fixed frame extraction endpoint."""

    # Test configuration
    BASE_URL = "http://localhost"
    TARGET_VIDEO_UUID = "170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e"

    print("🧪 Testing Fixed Frame Extraction Endpoint")
    print("=" * 50)

    # Step 1: Get authentication token
    print("1️⃣ Getting auth token...")
    auth_response = requests.post(
        f"{BASE_URL}/api/v1/auth/token",
        json={"email": "test@example.com", "password": "password123"},
        timeout=10,
    )

    if auth_response.status_code != 200:
        print(f"   ❌ Auth failed: {auth_response.status_code}")
        return False

    auth_token = auth_response.json()["access_token"]
    print(f"   ✅ Got auth token")

    # Step 2: Test frame extraction
    print("\n2️⃣ Testing frame extraction...")

    headers = {"Authorization": f"Bearer {auth_token}"}

    # Test extracting frame 100
    frame_response = requests.get(
        f"{BASE_URL}/api/v1/media/{TARGET_VIDEO_UUID}/frame/100",
        headers=headers,
        params={"format": "jpeg", "quality": 85, "size": "medium"},
        timeout=30,
    )

    print(f"   Status: {frame_response.status_code}")

    if frame_response.status_code == 200:
        print(f"   ✅ SUCCESS! Frame extracted successfully")
        print(f"   📊 Response size: {len(frame_response.content)} bytes")
        print(
            f"   🖼️  Content type: {frame_response.headers.get('content-type', 'N/A')}"
        )

        # Save frame to file for verification
        output_file = Path("test_frame_100.jpg")
        with open(output_file, "wb") as f:
            f.write(frame_response.content)
        print(f"   💾 Frame saved to: {output_file}")

        return True
    else:
        print(f"   ❌ FAILED: {frame_response.text}")
        return False


def create_test_html():
    """Create a simple HTML file to test frame extraction in browser."""

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Frame Extraction Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .test-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .frame-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .frame-item {
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            background: white;
        }
        .frame-item img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .frame-info {
            padding: 10px;
            font-size: 14px;
        }
        .btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
        }
        .btn:hover {
            background-color: #0056b3;
        }
        .status {
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .status.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 PPL Meta Frame Extraction Test</h1>
        <p>Test the video frame extraction endpoint</p>
    </div>

    <div class="test-section">
        <h2>Authentication</h2>
        <button class="btn" onclick="authenticate()">🔐 Get Auth Token</button>
        <div id="auth-status"></div>
    </div>

    <div class="test-section">
        <h2>Frame Extraction Test</h2>
        <p><strong>Video UUID:</strong> 170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e</p>
        
        <div>
            <label for="frame-number">Frame Number:</label>
            <input type="number" id="frame-number" value="100" min="0" max="380">
            <button class="btn" onclick="extractFrame()">🖼️ Extract Frame</button>
            <button class="btn" onclick="extractMultipleFrames()">🎞️ Extract Multiple Frames</button>
        </div>
        
        <div id="extraction-status"></div>
        <div id="frames-container" class="frame-grid"></div>
    </div>

    <script>
        let authToken = null;
        const BASE_URL = 'http://localhost';
        const VIDEO_UUID = '170d0c97-8fa3-4895-a4d1-7c5aaa1d0b8e';

        async function authenticate() {
            const statusDiv = document.getElementById('auth-status');
            statusDiv.innerHTML = 'Authenticating...';
            
            try {
                const response = await fetch(`${BASE_URL}/api/v1/auth/token`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: 'test@example.com',
                        password: 'password123'
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    authToken = data.access_token;
                    statusDiv.innerHTML = '<div class="status success">✅ Authentication successful!</div>';
                } else {
                    statusDiv.innerHTML = '<div class="status error">❌ Authentication failed</div>';
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="status error">❌ Auth error: ${error.message}</div>`;
            }
        }

        async function extractFrame() {
            if (!authToken) {
                alert('Please authenticate first');
                return;
            }
            
            const frameNumber = document.getElementById('frame-number').value;
            const statusDiv = document.getElementById('extraction-status');
            const framesContainer = document.getElementById('frames-container');
            
            statusDiv.innerHTML = `Extracting frame ${frameNumber}...`;
            
            try {
                const response = await fetch(
                    `${BASE_URL}/api/v1/media/${VIDEO_UUID}/frame/${frameNumber}?format=jpeg&quality=85&size=medium`,
                    {
                        headers: {
                            'Authorization': `Bearer ${authToken}`
                        }
                    }
                );
                
                if (response.ok) {
                    const blob = await response.blob();
                    const imageUrl = URL.createObjectURL(blob);
                    
                    const frameItem = document.createElement('div');
                    frameItem.className = 'frame-item';
                    frameItem.innerHTML = `
                        <img src="${imageUrl}" alt="Frame ${frameNumber}">
                        <div class="frame-info">
                            <strong>Frame ${frameNumber}</strong><br>
                            Size: ${(blob.size / 1024).toFixed(1)} KB<br>
                            Type: ${blob.type}
                        </div>
                    `;
                    
                    framesContainer.appendChild(frameItem);
                    statusDiv.innerHTML = '<div class="status success">✅ Frame extracted successfully!</div>';
                } else {
                    const errorText = await response.text();
                    statusDiv.innerHTML = `<div class="status error">❌ Frame extraction failed: ${errorText}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="status error">❌ Extraction error: ${error.message}</div>`;
            }
        }

        async function extractMultipleFrames() {
            if (!authToken) {
                alert('Please authenticate first');
                return;
            }
            
            const frames = [50, 100, 150, 200, 250, 300];
            const statusDiv = document.getElementById('extraction-status');
            
            statusDiv.innerHTML = 'Extracting multiple frames...';
            
            for (const frameNumber of frames) {
                document.getElementById('frame-number').value = frameNumber;
                await extractFrame();
                await new Promise(resolve => setTimeout(resolve, 500)); // Small delay
            }
        }
    </script>
</body>
</html>"""

    output_file = Path("frame_extraction_test.html")
    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"📄 HTML test file created: {output_file}")
    print(f"🌐 Open in browser: file://{output_file.absolute()}")


if __name__ == "__main__":
    print("🚀 Starting Frame Extraction Test")
    print()

    # Run the test
    success = test_frame_extraction()

    # Create HTML test file
    print("\n" + "=" * 50)
    create_test_html()

    print(f"\n🏁 Test completed: {'✅ SUCCESS' if success else '❌ FAILED'}")
