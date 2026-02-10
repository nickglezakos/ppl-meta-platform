# Signage Player Dockerfile for Raspberry Pi 5 (ARM64)
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
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
    clang \
    cmake \
    ninja-build \
    pkg-config \
    libgtk-3-dev \
    liblzma-dev \
    libstdc++-12-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter
ENV FLUTTER_HOME=/opt/flutter
ENV PATH="$FLUTTER_HOME/bin:$PATH"

RUN git clone https://github.com/flutter/flutter.git -b stable --depth 1 $FLUTTER_HOME && \
    flutter precache --linux && \
    flutter config --enable-linux-desktop && \
    flutter doctor

# Set working directory
WORKDIR /app

# Copy pubspec files
COPY pubspec.yaml pubspec.lock ./

# Get dependencies
RUN flutter pub get

# Copy application files
COPY . .

# Build Flutter application for Linux
RUN flutter build linux --release

# Expose port
EXPOSE 8009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Create entrypoint script that detects architecture
RUN echo '#!/bin/bash\n\
ARCH=$(uname -m)\n\
if [ "$ARCH" = "aarch64" ]; then\n\
  exec /app/build/linux/arm64/release/bundle/signage_simple_player "$@"\n\
else\n\
  exec /app/build/linux/x64/release/bundle/signage_simple_player "$@"\n\
fi' > /entrypoint.sh && chmod +x /entrypoint.sh

# Run application via entrypoint
ENTRYPOINT ["/entrypoint.sh"]
