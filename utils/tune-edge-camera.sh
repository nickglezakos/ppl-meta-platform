#!/bin/bash
#
# Edge Camera Tuning Script - RPi5
# Controls camera settings without rebuilding Docker image
#

set -e

RPI_HOST="pi@192.168.1.77"
CAMERA_DEVICE="/dev/video0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Edge Camera Tuning Tool - Raspberry Pi 5${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Show current camera settings
show_current() {
    print_header
    echo ""
    echo -e "${YELLOW}Current Camera Settings:${NC}"
    echo ""
    
    # Get resolution/fps from container logs
    echo -e "${BLUE}Resolution & FPS:${NC}"
    ssh $RPI_HOST "docker compose -f ~/ppl-meta-deploy/docker-compose.yml logs edge-camera 2>/dev/null | grep 'Camera configured' | tail -1" || echo "Container not running"
    echo ""
    
    # Get camera controls
    echo -e "${BLUE}Camera Controls:${NC}"
    ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --get-ctrl=brightness,contrast,saturation,sharpness,focus_absolute,focus_automatic_continuous,auto_exposure,exposure_time_absolute,white_balance_automatic,white_balance_temperature"
    echo ""
}

# Show available resolutions
show_resolutions() {
    print_header
    echo ""
    echo -e "${YELLOW}Available Resolutions (MJPEG @ 30fps):${NC}"
    echo ""
    echo "  1. 640x480    (VGA)"
    echo "  2. 800x600    (SVGA)"
    echo "  3. 1024x768   (XGA)"
    echo "  4. 1280x720   (HD) - Current Default"
    echo "  5. 1600x1200  (UXGA)"
    echo "  6. 1920x1080  (Full HD)"
    echo "  7. 2048x1536  (QXGA)"
    echo "  8. 2592x1944  (5MP Max)"
    echo ""
}

# Change resolution
change_resolution() {
    show_resolutions
    read -p "Select resolution (1-8) or press Enter to cancel: " choice
    
    case $choice in
        1) WIDTH=640; HEIGHT=480; NAME="VGA" ;;
        2) WIDTH=800; HEIGHT=600; NAME="SVGA" ;;
        3) WIDTH=1024; HEIGHT=768; NAME="XGA" ;;
        4) WIDTH=1280; HEIGHT=720; NAME="HD" ;;
        5) WIDTH=1600; HEIGHT=1200; NAME="UXGA" ;;
        6) WIDTH=1920; HEIGHT=1080; NAME="Full HD" ;;
        7) WIDTH=2048; HEIGHT=1536; NAME="QXGA" ;;
        8) WIDTH=2592; HEIGHT=1944; NAME="5MP Max" ;;
        "") return ;;
        *) print_error "Invalid choice"; return ;;
    esac
    
    print_info "Changing resolution to $WIDTH x $HEIGHT ($NAME)..."
    
    # Update config in running container and restart
    ssh $RPI_HOST << EOF
        docker exec edge-camera sed -i "s/width: [0-9]*/width: $WIDTH/" /app/config/default.yaml
        docker exec edge-camera sed -i "s/height: [0-9]*/height: $HEIGHT/" /app/config/default.yaml
        docker restart edge-camera
EOF
    
    print_success "Resolution changed! Waiting for container to restart..."
    sleep 5
    show_current
}

# Set focus
set_focus() {
    echo ""
    echo -e "${YELLOW}Focus Settings:${NC}"
    echo "  1. Auto Focus (Continuous)"
    echo "  2. Manual Focus"
    echo ""
    read -p "Select (1-2): " choice
    
    case $choice in
        1)
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=focus_automatic_continuous=1"
            print_success "Auto-focus enabled"
            ;;
        2)
            read -p "Enter focus value (0-1023, default 68): " value
            value=${value:-68}
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=focus_automatic_continuous=0"
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=focus_absolute=$value"
            print_success "Manual focus set to $value"
            ;;
        *) print_error "Invalid choice" ;;
    esac
}

# Set exposure
set_exposure() {
    echo ""
    echo -e "${YELLOW}Exposure Settings:${NC}"
    echo "  1. Auto Exposure (Aperture Priority)"
    echo "  2. Manual Exposure"
    echo ""
    read -p "Select (1-2): " choice
    
    case $choice in
        1)
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=auto_exposure=3"
            print_success "Auto-exposure enabled"
            ;;
        2)
            read -p "Enter exposure time (2-625, default 156): " value
            value=${value:-156}
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=auto_exposure=1"
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=exposure_time_absolute=$value"
            print_success "Manual exposure set to $value"
            ;;
        *) print_error "Invalid choice" ;;
    esac
}

# Set white balance
set_white_balance() {
    echo ""
    echo -e "${YELLOW}White Balance Settings:${NC}"
    echo "  1. Auto White Balance"
    echo "  2. Manual White Balance"
    echo ""
    read -p "Select (1-2): " choice
    
    case $choice in
        1)
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=white_balance_automatic=1"
            print_success "Auto white balance enabled"
            ;;
        2)
            echo ""
            echo "Temperature presets:"
            echo "  2800K - Tungsten/Incandescent"
            echo "  3500K - Warm White LED"
            echo "  4600K - Default"
            echo "  5000K - Daylight"
            echo "  6500K - Cool White/Overcast"
            echo ""
            read -p "Enter temperature (2800-6500K, default 4600): " value
            value=${value:-4600}
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=white_balance_automatic=0"
            ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=white_balance_temperature=$value"
            print_success "White balance set to ${value}K"
            ;;
        *) print_error "Invalid choice" ;;
    esac
}

# Adjust image quality
adjust_image() {
    echo ""
    echo -e "${YELLOW}Image Quality Adjustment:${NC}"
    echo ""
    
    read -p "Brightness (0-255, current 128, Enter to skip): " brightness
    read -p "Contrast (0-255, current 45, Enter to skip): " contrast
    read -p "Saturation (0-100, current 64, Enter to skip): " saturation
    read -p "Sharpness (0-7, current 0, Enter to skip): " sharpness
    
    CMDS=""
    [ -n "$brightness" ] && CMDS="$CMDS brightness=$brightness"
    [ -n "$contrast" ] && CMDS="$CMDS contrast=$contrast"
    [ -n "$saturation" ] && CMDS="$CMDS saturation=$saturation"
    [ -n "$sharpness" ] && CMDS="$CMDS sharpness=$sharpness"
    
    if [ -n "$CMDS" ]; then
        ssh $RPI_HOST "v4l2-ctl --device=$CAMERA_DEVICE --set-ctrl=$CMDS"
        print_success "Image settings updated"
    else
        print_info "No changes made"
    fi
}

# Quick presets
apply_preset() {
    echo ""
    echo -e "${YELLOW}Quick Presets:${NC}"
    echo ""
    echo "  1. Default (HD, Auto everything)"
    echo "  2. High Quality (Full HD, Enhanced)"
    echo "  3. Low Light (HD, Increased exposure)"
    echo "  4. Bright Environment (HD, Reduced exposure)"
    echo "  5. Sharp Focus (HD, Manual focus, High sharpness)"
    echo ""
    read -p "Select preset (1-5): " choice
    
    case $choice in
        1)
            print_info "Applying Default preset..."
            ssh $RPI_HOST << 'EOF'
                docker exec edge-camera sed -i "s/width: [0-9]*/width: 1280/" /app/config/default.yaml
                docker exec edge-camera sed -i "s/height: [0-9]*/height: 720/" /app/config/default.yaml
                docker restart edge-camera &
                v4l2-ctl --device=/dev/video0 --set-ctrl=focus_automatic_continuous=1
                v4l2-ctl --device=/dev/video0 --set-ctrl=auto_exposure=3
                v4l2-ctl --device=/dev/video0 --set-ctrl=white_balance_automatic=1
                v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=128,contrast=45,saturation=64,sharpness=0
EOF
            print_success "Default preset applied"
            ;;
        2)
            print_info "Applying High Quality preset..."
            ssh $RPI_HOST << 'EOF'
                docker exec edge-camera sed -i "s/width: [0-9]*/width: 1920/" /app/config/default.yaml
                docker exec edge-camera sed -i "s/height: [0-9]*/height: 1080/" /app/config/default.yaml
                docker restart edge-camera &
                v4l2-ctl --device=/dev/video0 --set-ctrl=focus_automatic_continuous=1
                v4l2-ctl --device=/dev/video0 --set-ctrl=auto_exposure=3
                v4l2-ctl --device=/dev/video0 --set-ctrl=white_balance_automatic=1
                v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=140,contrast=50,saturation=70,sharpness=4
EOF
            print_success "High Quality preset applied"
            ;;
        3)
            print_info "Applying Low Light preset..."
            ssh $RPI_HOST << 'EOF'
                v4l2-ctl --device=/dev/video0 --set-ctrl=auto_exposure=1
                v4l2-ctl --device=/dev/video0 --set-ctrl=exposure_time_absolute=400
                v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=150,contrast=50
EOF
            print_success "Low Light preset applied"
            ;;
        4)
            print_info "Applying Bright Environment preset..."
            ssh $RPI_HOST << 'EOF'
                v4l2-ctl --device=/dev/video0 --set-ctrl=auto_exposure=1
                v4l2-ctl --device=/dev/video0 --set-ctrl=exposure_time_absolute=50
                v4l2-ctl --device=/dev/video0 --set-ctrl=brightness=100,contrast=40
EOF
            print_success "Bright Environment preset applied"
            ;;
        5)
            print_info "Applying Sharp Focus preset..."
            ssh $RPI_HOST << 'EOF'
                v4l2-ctl --device=/dev/video0 --set-ctrl=focus_automatic_continuous=0
                v4l2-ctl --device=/dev/video0 --set-ctrl=focus_absolute=200
                v4l2-ctl --device=/dev/video0 --set-ctrl=sharpness=6,contrast=55
EOF
            print_success "Sharp Focus preset applied"
            ;;
        *) print_error "Invalid choice" ;;
    esac
}

# Test stream
test_stream() {
    print_info "Testing camera stream..."
    echo ""
    echo "Edge Camera URLs:"
    echo "  Local:    http://192.168.1.77:9001"
    echo "  Backend:  http://192.168.1.75:8005/api/v1/streaming/edge-camera-rpi5-001/video"
    echo "  Health:   http://192.168.1.77:9001/health"
    echo ""
    
    print_info "Checking health endpoint..."
    curl -s http://192.168.1.77:9001/health | python3 -m json.tool || print_error "Health check failed"
}

# Main menu
main_menu() {
    while true; do
        print_header
        echo ""
        echo "  1. Show current settings"
        echo "  2. Change resolution"
        echo "  3. Adjust focus"
        echo "  4. Adjust exposure"
        echo "  5. Adjust white balance"
        echo "  6. Adjust image quality (brightness, contrast, etc.)"
        echo "  7. Apply quick preset"
        echo "  8. Test camera stream"
        echo "  9. Exit"
        echo ""
        read -p "Select option (1-9): " option
        
        case $option in
            1) show_current ;;
            2) change_resolution ;;
            3) set_focus ;;
            4) set_exposure ;;
            5) set_white_balance ;;
            6) adjust_image ;;
            7) apply_preset ;;
            8) test_stream ;;
            9) print_info "Goodbye!"; exit 0 ;;
            *) print_error "Invalid option" ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main menu
main_menu
