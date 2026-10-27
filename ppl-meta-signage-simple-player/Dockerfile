# Signage Player Dockerfile for Raspberry Pi 5 (ARM64)
# Multi-stage: keep Flutter/Go toolchains out of the runtime image.

############################
# Build stage
############################
FROM ubuntu:22.04 AS build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    ca-certificates \
    clang \
    cmake \
    ninja-build \
    pkg-config \
    libgtk-3-dev \
    liblzma-dev \
    libstdc++-12-dev \
    libsqlite3-dev \
    libglu1-mesa \
    libasound2-dev \
    libmpv-dev \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Go toolchain for package:tailscale native asset hook (tsnet / cgo).
ARG GO_VERSION=1.25.5
RUN ARCH=$(dpkg --print-architecture) && \
    case "$ARCH" in \
      amd64) GO_ARCH=amd64 ;; \
      arm64) GO_ARCH=arm64 ;; \
      *) echo "unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac && \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz" \
      | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOTOOLCHAIN=auto
ENV GOPROXY=https://proxy.golang.org,direct

ENV FLUTTER_HOME=/opt/flutter
ENV PATH="$FLUTTER_HOME/bin:$PATH"

RUN git clone https://github.com/flutter/flutter.git -b stable --depth 1 $FLUTTER_HOME && \
    flutter precache --linux && \
    flutter config --enable-linux-desktop && \
    flutter doctor

WORKDIR /app

COPY pubspec.yaml pubspec.lock ./
RUN flutter pub get

COPY . .
# Force software decode + downscaled textures on Linux (RPi Docker).
# Default media_kit hwdec=auto → VDPAU → 1x1 black; full 4K S/W textures
# lag and segfault. Patches: hwdec=no, vf scale≤1280, SW max 1280x1280.
RUN python3 tool/patch_video_player_media_kit_linux.py && \
    python3 tool/patch_media_kit_sw_limits.py && \
    flutter build linux --release

############################
# Runtime stage
############################
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    libglu1-mesa \
    libgtk-3-0 \
    libglib2.0-0 \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    libmpv1 \
    mpv \
    xdotool \
    wmctrl \
    x11-utils \
    xvfb \
    libsqlite3-0 \
    libsqlite3-dev \
    libasound2 \
    libgles2 \
    libegl1 \
    libgl1 \
    libgl1-mesa-dri \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Linux release bundle (arm64 on RPi; x64 when built for amd64)
COPY --from=build /app/build/linux /app/build/linux
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    mkdir -p /root/.local/share/signage_simple_player && \
    chmod 700 /root/.local/share/signage_simple_player

EXPOSE 8009

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
