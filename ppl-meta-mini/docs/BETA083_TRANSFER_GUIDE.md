# Beta083 Transfer Guide - Windows Manual Installation

## 📦 **Beta083 Image Export Complete!**

**File**: `ppl-meta-mini-beta083.tar`  
**Size**: 587 MB  
**Location**: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-mini/`  
**Features**: ✅ DeepFace (age detection) ✅ ARM64/Linux optimized

## 🚀 **Transfer to Windows Machine**

### Method 1: USB/External Drive
```bash
# Copy to USB drive
cp ppl-meta-mini-beta083.tar /Volumes/YOUR_USB_DRIVE/

# Or copy to external drive
cp ppl-meta-mini-beta083.tar /Volumes/YOUR_EXTERNAL_DRIVE/
```

### Method 2: Cloud Storage (Google Drive, Dropbox, etc.)
```bash
# Copy to Downloads for easy cloud upload
cp ppl-meta-mini-beta083.tar ~/Downloads/
# Then upload to your preferred cloud service
```

### Method 3: Network Transfer
```bash
# SCP to Windows machine (if accessible)
scp ppl-meta-mini-beta083.tar username@windows-machine-ip:/path/to/destination/
```

## 💻 **Loading on Windows Machine**

### Step 1: Transfer the file
Get `ppl-meta-mini-beta083.tar` onto your Windows machine using any method above.

### Step 2: Load the Docker image

**Windows Command Prompt:**
```cmd
docker load < ppl-meta-mini-beta083.tar
```

**Windows PowerShell:**
```powershell
Get-Content ppl-meta-mini-beta083.tar | docker load
```

**Alternative (if above fails):**
```cmd
docker load --input ppl-meta-mini-beta083.tar
```

### Step 3: Verify the image is loaded
```cmd
docker images | findstr beta083
```

### Step 4: Run the container
```cmd
docker run -d --name ppl-meta-mini-dlib -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest
```

### Step 5: Test the service
```cmd
curl http://localhost:8004/health
```

## 🧪 **Test Age Detection on Windows**

```cmd
curl -X POST http://localhost:8004/api/v1/analyze-faces ^
     -F "file=@test-image.jpg" ^
     -F "include_age=true"
```

## ✅ **Expected Results**

**After loading:**
```
Loaded image: nickglezakos/ppl-meta-mini-beta083:latest
```

**After running:**
```
{"status":"healthy","service":"ppl-meta-mini","version":"1.1.0"}
```

**Age detection response should include:**
```json
{
  "faces": [
    {
      "age": 25,
      "confidence": 0.95,
      "bbox": [x, y, width, height]
    }
  ]
}
```

## 🎯 **Key Benefits of Beta083**

- ✅ **DeepFace included** - Age detection works
- ✅ **587 MB** - Same size as beta081 but with fixes
- ✅ **Linux containers** - Works on Windows Docker Desktop
- ✅ **No internet required** - Complete offline deployment
- ✅ **Raspberry Pi compatible** - ARM64 support

## 🔧 **Troubleshooting**

**If "docker command not found":**
- Install Docker Desktop on Windows

**If load fails:**
- Try: `docker load --input ppl-meta-mini-beta083.tar`

**If port 8004 is busy:**
- Use different port: `-p 8005:8004`

## 📁 **Files Available for Transfer**

1. **ppl-meta-mini-beta081.tar** (587MB) - Multi-arch (AMD64 + ARM64)
2. **ppl-meta-mini-beta083.tar** (587MB) - ARM64 with DeepFace fixes

**Recommendation**: Use **beta083** for latest DeepFace fixes!
