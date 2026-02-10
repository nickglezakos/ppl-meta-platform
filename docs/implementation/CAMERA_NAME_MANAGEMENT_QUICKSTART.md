# Camera Name Management - Quick Setup Guide

## Status: ✅ Implementation Complete

All code changes are complete and ready to use. Migrations will apply automatically when you have existing data.

## For Fresh Installations (New Setup)

**No action needed!** The unique constraints are built into the models and will be created automatically when tables are initialized.

Just start your services normally:
```bash
./manage-services.sh start
```

## For Existing Installations (With Data)

### 1. Run Migrations

**Camera Service:**
```bash
cd ppl-meta-cameras
alembic upgrade head
```

**Media Service:**
```bash
cd ppl-meta-media  
alembic upgrade head
```

### 2. Restart Services
```bash
./manage-services.sh restart
```

### 3. Test the Feature

**Update a camera name:**
```bash
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' \
  | jq -r '.access_token')

curl -X PATCH "http://localhost:8005/api/v1/cameras/usb_camera_0/name" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Studio Camera"}'
```

**Verify collection synced:**
```bash
curl -X GET "http://localhost:8000/api/v1/media/collections/by-camera/usb_camera_0" \
  -H "Authorization: Bearer $TOKEN" | jq '.name'
```

Should return: `"Studio Camera"`

## New API Endpoints Available

- **PATCH** `/api/v1/cameras/{device_id}/name` - Update camera name
- **PATCH** `/api/v1/media/collections/{uuid}/name` - Update collection name

## What Changed

✅ Camera names must be unique  
✅ Collection names must be unique  
✅ Camera name updates auto-sync to collections  
✅ UUID-based identification preserved  
✅ All validations and error handling in place  

## Documentation

Full implementation guide: [CAMERA_NAME_MANAGEMENT_IMPLEMENTATION.md](CAMERA_NAME_MANAGEMENT_IMPLEMENTATION.md)

## Need Help?

Check the troubleshooting section in the full documentation.
