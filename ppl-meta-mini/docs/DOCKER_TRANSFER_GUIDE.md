# Docker Image Transfer Guide - PPL Meta Mini Beta081

## 📦 **Image Export Complete!**

**File**: `ppl-meta-mini-beta081.tar`  
**Size**: 587 MB  
**Location**: `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-mini/`

## 🚀 **Transfer Methods**

### Method 1: USB/External Drive
```bash
# Copy to USB drive
cp ppl-meta-mini-beta081.tar /Volumes/YOUR_USB_DRIVE/

# Or copy to external drive
cp ppl-meta-mini-beta081.tar /Volumes/YOUR_EXTERNAL_DRIVE/
```

### Method 2: Network Transfer (SCP)
```bash
# Transfer to another machine via SCP
scp ppl-meta-mini-beta081.tar username@target-machine-ip:/path/to/destination/
```

### Method 3: Cloud Storage
```bash
# Upload to cloud storage (example with AWS S3)
aws s3 cp ppl-meta-mini-beta081.tar s3://your-bucket/

# Or use any cloud service (Google Drive, Dropbox, etc.)
```

## 💻 **Loading on Target Machine**

### Step 1: Transfer the file
Transfer `ppl-meta-mini-beta081.tar` to your target machine using any method above.

### Step 2: Load the Docker image
```bash
# Load the image into Docker
docker load -i ppl-meta-mini-beta081.tar
```

### Step 3: Verify the image is loaded
```bash
# Check if image is available
docker images | grep ppl-meta-mini-beta081
```

### Step 4: Run the container
```bash
# Run the container (Windows, Linux, or macOS)
docker run -d --name ppl-meta-mini-dlib -p 8004:8004 nickglezakos/ppl-meta-mini-beta081:latest
```

### Step 5: Test the service
```bash
# Check if service is running
curl http://localhost:8004/health
```

## ✅ **Expected Output After Loading**

```bash
$ docker load -i ppl-meta-mini-beta081.tar
Loaded image: nickglezakos/ppl-meta-mini-beta081:latest

$ docker images | grep beta081
nickglezakos/ppl-meta-mini-beta081   latest    [image-id]   [size]   [time]

$ docker run -d --name ppl-meta-mini-dlib -p 8004:8004 nickglezakos/ppl-meta-mini-beta081:latest
[container-id]

$ curl http://localhost:8004/health
{"status": "healthy", "service": "ppl-meta-mini", ...}
```

## 🌍 **Platform Compatibility**

This image will automatically work on:
- ✅ **Windows** (Intel/AMD processors)
- ✅ **Linux** (Intel/AMD processors)
- ✅ **macOS** (Intel processors)
- ✅ **macOS** (Apple Silicon M1/M2/M3)
- ✅ **ARM64 Linux** (Raspberry Pi, ARM servers)

## 🔄 **Alternative: Direct Pull**

If the target machine has internet access, you can skip the transfer and directly pull:

```bash
# Direct pull from Docker Hub (requires internet)
docker pull nickglezakos/ppl-meta-mini-beta081:latest
docker run -d --name ppl-meta-mini-dlib -p 8004:8004 nickglezakos/ppl-meta-mini-beta081:latest
```

## 📝 **Notes**

- The tar file contains the complete Docker image with all dependencies
- No internet connection required on target machine after transfer
- Multi-architecture support ensures compatibility across platforms
- File size: 587 MB (compressed from ~2.5GB image)

## 🔧 **Troubleshooting**

If you encounter issues:

1. **"docker command not found"**: Install Docker on target machine
2. **Permission denied**: Run with `sudo` on Linux/macOS
3. **Port already in use**: Change port mapping: `-p 8005:8004`
4. **Out of disk space**: Free up space before loading

## 🎯 **Success Indicators**

- ✅ `docker load` completes without errors
- ✅ Image appears in `docker images` list
- ✅ Container starts successfully
- ✅ Health check responds on port 8004
- ✅ Face detection service is operational
