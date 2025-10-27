#!/bin/bash
# Universal CMake Installation Script for PPL Meta Mini
# Supports both Debian Bookworm and Bullseye with all architectures (AMD64/ARM64)
# Guarantees CMake 3.24+ for dlib compilation

set -euo pipefail

# Configuration
CMAKE_MIN_VERSION="3.24"
CMAKE_INSTALL_VERSION="3.24.3"
TEMP_DIR="/tmp/cmake_install"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect system information
detect_system() {
    log_info "Detecting system information..."
    
    # Architecture detection
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            CMAKE_ARCH="linux-x86_64"
            ;;
        aarch64|arm64)
            CMAKE_ARCH="linux-aarch64"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    # Debian version detection
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DEBIAN_VERSION=$VERSION_CODENAME
    else
        log_warning "Cannot detect Debian version, assuming Bookworm"
        DEBIAN_VERSION="bookworm"
    fi
    
    log_info "Architecture: $ARCH -> $CMAKE_ARCH"
    log_info "Debian Version: $DEBIAN_VERSION"
}

# Check current CMake version
check_current_cmake() {
    log_info "Checking current CMake installation..."
    
    if command -v cmake >/dev/null 2>&1; then
        CURRENT_VERSION=$(cmake --version | head -n1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        log_info "Current CMake version: $CURRENT_VERSION"
        
        # Version comparison
        if printf '%s\n%s\n' "$CMAKE_MIN_VERSION" "$CURRENT_VERSION" | sort -V -C; then
            log_success "CMake version $CURRENT_VERSION meets minimum requirement ($CMAKE_MIN_VERSION)"
            return 0
        else
            log_warning "CMake version $CURRENT_VERSION is below minimum requirement ($CMAKE_MIN_VERSION)"
            return 1
        fi
    else
        log_info "CMake not found, installation required"
        return 1
    fi
}

# Install CMake from package manager (for Bookworm)
install_cmake_apt() {
    log_info "Installing CMake via apt package manager..."
    
    # Update package list
    apt-get update
    
    # Try to install cmake from backports for Bullseye
    if [ "$DEBIAN_VERSION" = "bullseye" ]; then
        log_info "Adding backports for Bullseye..."
        echo "deb http://deb.debian.org/debian bullseye-backports main" >> /etc/apt/sources.list
        apt-get update
        apt-get install -y -t bullseye-backports cmake || {
            log_warning "Backports installation failed, falling back to binary installation"
            return 1
        }
    else
        apt-get install -y cmake
    fi
    
    # Verify installation
    if check_current_cmake; then
        log_success "CMake successfully installed via apt"
        return 0
    else
        log_warning "CMake version from apt is insufficient"
        return 1
    fi
}

# Install CMake from binary distribution
install_cmake_binary() {
    log_info "Installing CMake $CMAKE_INSTALL_VERSION from binary distribution..."
    
    # Create temporary directory
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # Download URL
    CMAKE_URL="https://github.com/Kitware/CMake/releases/download/v${CMAKE_INSTALL_VERSION}/cmake-${CMAKE_INSTALL_VERSION}-${CMAKE_ARCH}.tar.gz"
    
    log_info "Downloading: $CMAKE_URL"
    
    # Download with retry logic
    for attempt in 1 2 3; do
        if wget -q --show-progress "$CMAKE_URL" -O cmake.tar.gz; then
            log_success "Download successful on attempt $attempt"
            break
        else
            log_warning "Download attempt $attempt failed"
            if [ $attempt -eq 3 ]; then
                log_error "Failed to download CMake after 3 attempts"
                exit 1
            fi
            sleep 2
        fi
    done
    
    # Extract to /opt
    log_info "Extracting CMake to /opt..."
    tar -xzf cmake.tar.gz -C /opt/
    
    # Create symlinks
    log_info "Creating symlinks in /usr/local/bin..."
    ln -sf /opt/cmake-${CMAKE_INSTALL_VERSION}-${CMAKE_ARCH}/bin/* /usr/local/bin/
    
    # Cleanup
    cd /
    rm -rf "$TEMP_DIR"
    
    # Verify installation
    if check_current_cmake; then
        log_success "CMake $CMAKE_INSTALL_VERSION successfully installed from binary"
        return 0
    else
        log_error "Binary installation verification failed"
        exit 1
    fi
}

# Main installation logic
main() {
    log_info "PPL Meta Mini - Universal CMake Installation"
    log_info "============================================="
    
    # Detect system
    detect_system
    
    # Check if CMake is already sufficient
    if check_current_cmake; then
        log_success "CMake installation is already sufficient"
        exit 0
    fi
    
    log_info "CMake installation/upgrade required"
    
    # Try apt installation first (faster for Bookworm)
    if [ "$DEBIAN_VERSION" = "bookworm" ]; then
        log_info "Attempting apt installation for Bookworm..."
        if install_cmake_apt; then
            exit 0
        fi
    fi
    
    # Fall back to binary installation
    log_info "Proceeding with binary installation..."
    install_cmake_binary
    
    # Final verification
    log_info "Final verification..."
    if check_current_cmake; then
        log_success "CMake installation completed successfully!"
        log_info "Ready for dlib compilation with guaranteed CMake 3.24+ support"
    else
        log_error "Installation verification failed"
        exit 1
    fi
}

# Execute main function
main "$@"