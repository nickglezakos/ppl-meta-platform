# Docker I/O Error Fix Guide - Beta083 Build

## 🚨 **Issue Detected: Docker I/O Corruption**

Your Docker daemon has metadata database corruption. Here's how to fix it:

## 🔧 **Quick Fix Steps:**

### Step 1: Restart Docker Desktop
```bash
# Option A: Through GUI
# 1. Right-click Docker Desktop icon in system tray
# 2. Select "Restart Docker Desktop"
# 3. Wait for complete restart

# Option B: Command line (macOS)
killall Docker\ Desktop
open -a Docker\ Desktop
```

### Step 2: If restart doesn't work, reset Docker
```bash
# WARNING: This will delete all local images and containers
# macOS Docker Desktop:
# 1. Docker Desktop -> Preferences -> Troubleshoot -> Reset to factory defaults
# 2. Or delete Docker Desktop and reinstall
```

### Step 3: Alternative - Use existing image
```bash
# Since you have beta081 working, we can tag it as beta083
docker pull nickglezakos/ppl-meta-mini-beta081:latest
docker tag nickglezakos/ppl-meta-mini-beta081:latest nickglezakos/ppl-meta-mini-beta083:latest
docker push nickglezakos/ppl-meta-mini-beta083:latest
```

## 🎯 **Immediate Solution: Copy Beta081 to Beta083**

Since your requirements file now has DeepFace and beta081 might work, let's copy it:

```bash
# After Docker is fixed:
docker pull nickglezakos/ppl-meta-mini-beta081:latest
docker tag nickglezakos/ppl-meta-mini-beta081:latest nickglezakos/ppl-meta-mini-beta083:latest
docker tag nickglezakos/ppl-meta-mini-beta081:latest nickglezakos/ppl-meta-mini-beta083:arm64
docker push nickglezakos/ppl-meta-mini-beta083:latest
docker push nickglezakos/ppl-meta-mini-beta083:arm64
```

## 🐧 **For Linux/Windows Users:**

Since your Mac has corruption, you can:

### Option 1: Build on Linux machine
```bash
# On a Linux machine or Windows WSL:
git clone your-repo
cd ppl-meta-mini
chmod +x build_beta083_simple.sh
./build_beta083_simple.sh
```

### Option 2: Use GitHub Actions
Create `.github/workflows/docker-build.yml`:
```yaml
name: Build Docker Image
on:
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      - name: Log in to Docker Hub
        uses: docker/login-action@v2
        with:
          username: nickglezakos
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: ./ppl-meta-mini
          file: ./ppl-meta-mini/Dockerfile.cython.dlib
          platforms: linux/amd64,linux/arm64
          push: true
          tags: nickglezakos/ppl-meta-mini-beta083:latest
```

## 🔄 **Test Commands After Fix:**

```bash
# Test the image
docker run -d --name test-beta083 -p 8004:8004 nickglezakos/ppl-meta-mini-beta083:latest

# Test age detection
curl -X POST http://localhost:8004/api/v1/analyze-faces \
     -F 'file=@test-image.jpg' \
     -F 'include_age=true'
```

## 📝 **Next Steps:**

1. **Restart Docker Desktop** completely
2. **Try the tag/push approach** to create beta083 from beta081
3. **If that fails**, use a Linux machine or GitHub Actions
4. **Test age detection** to ensure DeepFace works

The I/O error suggests disk corruption or Docker Desktop needs a complete restart/reset.
