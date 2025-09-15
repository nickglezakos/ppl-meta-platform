# 🗃️ PPL Meta Vision Service - Database Migrations

This directory contains database migration scripts for implementing **Workflow 4: Session-Based Face Detection with Traceability**.

## 📋 **Migration Files**

### **Migration 001: Session-Based Face Detection Schema**
- **File**: `001_session_based_face_detection_schema.sql`
- **Purpose**: Implement session-based tracking tables and modify existing schema
- **Rollback**: `001_rollback_session_based_face_detection_schema.sql`

**Changes Made**:
1. ✅ **face_detection_sessions** table - Track face detection sessions with complete traceability
2. ✅ **media_processing_status** table - Track processing status for optimized playback  
3. ✅ **session_uuid** column added to existing **face_detections** table
4. ✅ **Foreign key constraints** for referential integrity
5. ✅ **Performance indexes** for efficient querying
6. ✅ **Data validation constraints** for data integrity
7. ✅ **Automatic timestamp triggers** for tracking changes

## 🚀 **Usage**

### **Prerequisites**
- PostgreSQL database connection configured
- Python 3.7+ with psycopg2 installed
- Database environment variables set:
  ```bash
  export DB_HOST=localhost
  export DB_PORT=5432
  export DB_NAME=ppl_vision_db
  export DB_USER=nickgklezakos
  export DB_PASSWORD=your-password
  ```

### **Running Migrations**

```bash
# Navigate to migrations directory
cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vision/migrations

# Apply migration 001
python migration_runner.py apply 001

# Verify migration was applied correctly
python migration_runner.py verify 001

# Check migration status
python migration_runner.py status

# Rollback migration 001 (if needed)
python migration_runner.py rollback 001
```

### **Alternative: Direct SQL Execution**

You can also run the SQL files directly:

```bash
# Apply migration
psql -h localhost -U nickgklezakos -d ppl_vision_db -f 001_session_based_face_detection_schema.sql

# Rollback migration
psql -h localhost -U nickgklezakos -d ppl_vision_db -f 001_rollback_session_based_face_detection_schema.sql
```

## 📊 **Database Schema After Migration**

### **New Tables**

#### **face_detection_sessions**
```sql
session_uuid VARCHAR(36) PRIMARY KEY
media_uuid VARCHAR(36) NOT NULL
camera_device_uuid VARCHAR(36)  
session_type VARCHAR(20) NOT NULL DEFAULT 'streaming'
started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
ended_at TIMESTAMP NULL
total_faces_detected INTEGER DEFAULT 0
processing_status VARCHAR(20) NOT NULL DEFAULT 'active'
metadata JSONB
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

#### **media_processing_status**
```sql
media_uuid VARCHAR(36) PRIMARY KEY
face_detection_processed BOOLEAN DEFAULT FALSE
face_detection_session_uuid VARCHAR(36)
processing_completed_at TIMESTAMP NULL
total_frames_processed INTEGER
total_faces_detected INTEGER
processing_method VARCHAR(50)
last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### **Modified Tables**

#### **face_detections** (existing table)
- ✅ **Added**: `session_uuid VARCHAR(36)` - Links face detections to sessions

### **Indexes Created**

**Performance Indexes**:
- `idx_face_detection_sessions_media_uuid` - Fast session lookup by media
- `idx_face_detection_sessions_camera_device` - Fast session lookup by camera  
- `idx_face_detection_sessions_status` - Fast session status filtering
- `idx_face_detections_session_uuid` - Fast face lookup by session
- `idx_face_detections_session_frame` - Composite index for session+frame queries
- `idx_media_processing_status_processed` - Fast processing status lookup

### **Constraints Added**

**Data Validation**:
- Session type must be 'streaming' or 'bulk_processing'
- Processing status must be 'active', 'completed', or 'failed'  
- UUID format validation for session_uuid
- Time ordering: ended_at >= started_at
- Non-negative face counts

**Foreign Keys**:
- `face_detections.session_uuid` → `face_detection_sessions.session_uuid`
- `media_processing_status.face_detection_session_uuid` → `face_detection_sessions.session_uuid`

## 🔍 **Verification**

After applying migration 001, verify the changes:

```sql
-- Check new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('face_detection_sessions', 'media_processing_status')
AND table_schema = 'public';

-- Check session_uuid column was added
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'face_detections' AND column_name = 'session_uuid';

-- Check indexes were created
SELECT indexname, tablename FROM pg_indexes 
WHERE tablename IN ('face_detection_sessions', 'face_detections', 'media_processing_status')
ORDER BY tablename, indexname;

-- Check constraints were added
SELECT constraint_name, table_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name IN ('face_detection_sessions', 'face_detections', 'media_processing_status')
ORDER BY table_name, constraint_type;
```

## 🔄 **Rollback Process**

If you need to rollback the migration:

1. **Backup your data** first (migration removes session tracking data)
2. Run the rollback script: `python migration_runner.py rollback 001`
3. Verify rollback completed successfully

**⚠️ WARNING**: Rollback will permanently delete all session tracking data!

## 📈 **Performance Impact**

**Expected Performance Impact**:
- **Session Creation**: ~50ms per session
- **Face Storage**: ~10ms per face detection (with session context)
- **Session Queries**: ~100ms for full traceability lookup
- **Storage Overhead**: ~1KB per session + 200 bytes per face

**Optimization**:
- All critical queries are indexed for performance
- Foreign key constraints ensure referential integrity
- Automatic timestamp triggers minimize application logic

## 🛠️ **Troubleshooting**

### **Common Issues**

1. **Database Connection Failed**
   ```bash
   # Check environment variables
   echo $DB_HOST $DB_PORT $DB_NAME $DB_USER
   
   # Test connection
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT version();"
   ```

2. **Migration Already Applied**
   ```bash
   # Check migration status
   python migration_runner.py status
   
   # Force re-verify
   python migration_runner.py verify 001
   ```

3. **Permission Errors**
   ```bash
   # Ensure user has CREATE privileges
   GRANT CREATE ON DATABASE ppl_vision_db TO nickgklezakos;
   GRANT USAGE, CREATE ON SCHEMA public TO nickgklezakos;
   ```

4. **Index Creation Failed**
   ```sql
   -- Check existing indexes
   SELECT indexname FROM pg_indexes WHERE tablename = 'face_detections';
   
   -- Check for conflicting constraints
   SELECT constraint_name FROM information_schema.table_constraints 
   WHERE table_name = 'face_detections';
   ```

### **Recovery Steps**

If migration fails partway through:

1. **Check current state**: `python migration_runner.py status`
2. **Manual cleanup**: Run specific cleanup SQL if needed
3. **Re-run migration**: `python migration_runner.py apply 001`
4. **Verify completion**: `python migration_runner.py verify 001`

## 📚 **Next Steps**

After successfully applying Migration 001:

1. ✅ **Phase 1 Complete** - Database foundation ready
2. 🔄 **Phase 2 Next** - Implement session management APIs in Vision Service
3. 🔄 **Phase 3 Next** - Update Media Service for session-based face detection
4. 🔄 **Phase 4 Next** - Implement cross-service communication

---

**Migration Version**: 001  
**Created**: September 15, 2025  
**Status**: Ready for Implementation ✅