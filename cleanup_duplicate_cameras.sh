#!/bin/bash

# PPL Meta Mobile Camera Duplicate Cleanup Script
# Removes duplicate mobile camera registrations, keeping only the latest one

CAMERAS_SERVICE_URL="http://localhost:8005"
JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU2ODU3NjIxfQ.RJIaFDBuOPFL0XqQwIFY7UJnHO0SMz_uXxwM73nKwAw"

echo "🧹 PPL Meta Mobile Camera Duplicate Cleanup Tool"
echo "================================================"

# Check if we should actually execute deletions
DRY_RUN=true
if [[ "$1" == "--execute" ]]; then
    DRY_RUN=false
    echo "⚠️  EXECUTION mode - will actually delete duplicates!"
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo "❌ Cleanup cancelled"
        exit 0
    fi
else
    echo "🔍 Running in DRY RUN mode (no actual deletions)"
    echo "💡 Add --execute flag to perform actual cleanup"
fi

echo
echo "📱 Getting current mobile cameras..."

# Get mobile cameras and analyze duplicates
curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Accept: application/json" \
     "$CAMERAS_SERVICE_URL/api/v1/cameras/mobile" | \
python3 -c "
import sys, json
from datetime import datetime
from collections import defaultdict

try:
    cameras = json.load(sys.stdin)
    print(f'📱 Found {len(cameras)} mobile cameras total')
    print()
    
    # Group cameras by base device ID (removing mobile_ prefix and timestamp suffix)
    groups = defaultdict(list)
    
    for camera in cameras:
        device_id = camera.get('device_id', '')
        
        # Extract base device ID
        base_device_id = device_id
        if base_device_id.startswith('mobile_'):
            base_device_id = base_device_id[7:]  # Remove 'mobile_' prefix
        
        # Remove timestamp suffix if present
        parts = base_device_id.split('_')
        if len(parts) > 1 and parts[-1].isdigit():
            base_device_id = '_'.join(parts[:-1])
        
        groups[base_device_id].append(camera)
    
    print('📋 Camera groups by device:')
    duplicates_found = False
    total_to_delete = 0
    
    for base_device_id, camera_group in groups.items():
        print(f'\\n🔍 Device: {base_device_id}')
        
        if len(camera_group) == 1:
            camera = camera_group[0]
            print(f'  ✅ Single camera: ID {camera[\"id\"]} - {camera[\"device_id\"]}')
        else:
            duplicates_found = True
            print(f'  🔴 {len(camera_group)} duplicate cameras found:')
            
            # Sort by created_at (newest first)
            sorted_cameras = sorted(
                camera_group,
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            # First camera to keep, rest to delete
            keep_camera = sorted_cameras[0]
            delete_cameras = sorted_cameras[1:]
            
            print(f'    ✅ KEEP:   ID {keep_camera[\"id\"]} - {keep_camera[\"device_id\"]} (created: {keep_camera.get(\"created_at\", \"unknown\")})')
            
            for camera in delete_cameras:
                print(f'    🗑️  DELETE: ID {camera[\"id\"]} - {camera[\"device_id\"]} (created: {camera.get(\"created_at\", \"unknown\")})')
                total_to_delete += 1
    
    if not duplicates_found:
        print('\\n✅ No duplicates found! All cameras are unique.')
    else:
        print(f'\\n📊 Summary: {total_to_delete} duplicate cameras need to be removed')
        
        # Output deletion commands for bash script
        if total_to_delete > 0:
            print('\\n# DELETION_COMMANDS_START')
            for base_device_id, camera_group in groups.items():
                if len(camera_group) > 1:
                    sorted_cameras = sorted(
                        camera_group,
                        key=lambda x: x.get('created_at', ''),
                        reverse=True
                    )
                    delete_cameras = sorted_cameras[1:]
                    for camera in delete_cameras:
                        print(f'DELETE:{camera[\"id\"]}:{camera[\"device_id\"]}')
            print('# DELETION_COMMANDS_END')

except Exception as e:
    print(f'❌ Error processing cameras: {e}')
    sys.exit(1)
" > /tmp/camera_analysis.txt

# Check the analysis results
if grep -q "DELETION_COMMANDS_START" /tmp/camera_analysis.txt; then
    # Show analysis
    grep -v "^DELETE:" /tmp/camera_analysis.txt | grep -v "^# DELETION"
    
    # Extract deletion commands
    deletion_count=$(grep "^DELETE:" /tmp/camera_analysis.txt | wc -l)
    
    if [[ $deletion_count -gt 0 ]]; then
        echo
        if [[ $DRY_RUN == "true" ]]; then
            echo "🔍 Would delete the following cameras:"
            grep "^DELETE:" /tmp/camera_analysis.txt | while IFS=':' read -r cmd camera_id device_id; do
                echo "  • Camera ID $camera_id: $device_id"
            done
            echo
            echo "💡 Run with --execute to actually perform deletions"
        else
            echo "🗑️ Deleting duplicate cameras..."
            deleted_count=0
            
            grep "^DELETE:" /tmp/camera_analysis.txt | while IFS=':' read -r cmd camera_id device_id; do
                echo "  Deleting camera ID $camera_id ($device_id)..."
                
                response=$(curl -s -w "HTTP_STATUS:%{http_code}" \
                    -X DELETE \
                    -H "Authorization: Bearer $JWT_TOKEN" \
                    "$CAMERAS_SERVICE_URL/api/v1/cameras/$camera_id")
                
                http_status=$(echo "$response" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
                
                if [[ "$http_status" == "200" || "$http_status" == "204" ]]; then
                    echo "    ✅ Successfully deleted camera $camera_id"
                    ((deleted_count++))
                else
                    echo "    ❌ Failed to delete camera $camera_id (HTTP $http_status)"
                fi
            done
            
            echo
            echo "✅ Cleanup complete: Attempted to delete $deletion_count cameras"
        fi
    fi
else
    # No deletions needed, just show analysis
    cat /tmp/camera_analysis.txt
fi

# Cleanup
rm -f /tmp/camera_analysis.txt

echo
echo "🏁 Cleanup script finished"
