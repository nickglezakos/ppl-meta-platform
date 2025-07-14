# 🚀 PPL Meta Platform User Guide

## Overview
This comprehensive guide walks you through the complete user registration and authentication process for the PPL Meta Platform - a device-aware media management system with comprehensive upload, search, analytics, collections, and sharing capabilities.

---

## **Prerequisites**
✅ All services must be running (confirmed by health check):
- **Node Service** (8001): User management and authentication
- **Media Service** (8000): Media operations  
- **Gateway Service** (8080): API gateway
- **Orchestrator Service** (8002): Workflow coordination

### **Starting Services**
Use VS Code tasks to start the platform:
```bash
# Option 1: Start all services
🚀 Start All Local Python Services

# Option 2: Start individual services
🐍 Start Node Service (Local Python)
🎨 Start Media Service (Local Python)
🌐 Start Gateway Service (Local Python)
🎼 Start Orchestrator Service (Local Python)
```

### **Health Check**
Verify all services are running:
```bash
🏥 Local Python Health Check - All Services
```

---

## **Step-by-Step User Registration Process**

### **Option 1: Direct Registration via Node Service (Recommended)**

#### **1. Register a New User**
```bash
curl -X POST http://localhost:8001/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "email": "your_email@example.com", 
    "password": "YourSecurePassword123"
  }'
```

**Expected Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "guid": "generated-uuid",
    "username": "your_username",
    "email": "your_email@example.com",
    "email_verified": false,
    "is_active": true,
    "created_at": "2025-07-14T19:22:44.200000"
  }
}
```

#### **2. Login to Get Access Token**
```bash
curl -X POST http://localhost:8001/api/v1/users/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_email@example.com&password=YourSecurePassword123"
```

**Expected Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

#### **3. Access Your Profile (with Token)**
```bash
curl -X GET http://localhost:8001/api/v1/users/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Expected Response:**
```json
{
  "id": 1,
  "guid": "generated-uuid",
  "username": "your_username",
  "email": "your_email@example.com",
  "email_verified": false,
  "is_active": true,
  "created_at": "2025-07-14T19:22:44.200000",
  "updated_at": null
}
```

### **Option 2: Registration via Nginx Proxy (Production-like)**

If you want to test through the nginx proxy setup:

#### **1. Start Nginx Proxy** (if not already running):
```bash
# Run this task from VS Code
🌐 Start Nginx Proxy (Local Dev)
```

#### **2. Register via Nginx** (port 80):
```bash
curl -X POST http://localhost/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "nginx_user",
    "email": "nginx_test@example.com", 
    "password": "SecurePassword123"
  }'
```

#### **3. Login via Nginx:**
```bash
curl -X POST http://localhost/api/v1/users/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=nginx_test@example.com&password=SecurePassword123"
```

### **Option 3: Using the Flutter Frontend (Recommended)**

#### **1. Start the Frontend**:
```bash
# Run this task from VS Code
📱 Start Frontend (Web)
```

#### **2. Open Browser and Register**:
- Navigate to `http://localhost:3000`
- Click "Create Account" to access the registration form
- Fill out the registration form with validation feedback
- Submit registration and receive confirmation

#### **3. Complete Registration Process**:
1. **Registration Form:** Modern Flutter interface with real-time validation
2. **Account Creation:** Automatic backend user creation
3. **Email Verification:** Optional email verification process
4. **Automatic Login:** Seamless transition to authenticated state
5. **Dashboard Access:** Immediate access to full platform features

#### **4. Frontend Registration Features**:

**Real-time Form Validation:**
- Username: Minimum 3 characters, availability checking
- Email: Valid format validation with domain verification
- Password: Strength indicator with complexity requirements
- Confirm Password: Live matching validation

**User Experience:**
- Loading states during registration process
- Success/error messages with detailed feedback
- Responsive design for all screen sizes
- Accessibility support for screen readers

**Post-Registration Flow:**
- Automatic navigation to dashboard
- Welcome message with platform overview
- Quick start guide for first-time users
- Integration with device-aware upload system

---

## 5. PPL Meta Flutter Frontend - Complete Interface Guide

The PPL Meta Flutter Frontend is a modern, responsive web application built with Flutter that provides a comprehensive user interface for the PPL Meta Platform. It features device-aware upload capabilities, advanced media management, analytics dashboards, and collection organization.

### 5.1 Authentication Interface

#### 5.1.1 User Registration Screen

**Features:**
- **Form Validation:** Real-time input validation with error messages
- **Password Strength:** Visual password strength indicator
- **Responsive Design:** Adapts to different screen sizes
- **Loading States:** Visual feedback during registration process

**Access:**
- **URL:** `http://localhost:3000/register`
- **Navigation:** Available from login screen via "Create Account" link

**Registration Process:**
1. **Username Field:** Minimum 3 characters, alphanumeric with underscores
2. **Email Field:** Valid email format with domain validation
3. **Password Field:** Minimum 8 characters with complexity requirements
4. **Confirm Password:** Must match the password field
5. **Submit:** Automatic validation and backend registration

**UI Components:**
```dart
// Registration form with validation
TextFormField(
  controller: _usernameController,
  decoration: InputDecoration(
    labelText: 'Username',
    prefixIcon: Icon(Icons.person),
    errorText: usernameError,
  ),
  validator: (value) => validateUsername(value),
)
```

#### 5.1.2 Login Screen

**Features:**
- **Email/Password Authentication:** Secure login with JWT tokens
- **Remember Me:** Optional persistent login state
- **Password Visibility Toggle:** Show/hide password option
- **Forgot Password Link:** Redirects to password recovery

**Access:**
- **URL:** `http://localhost:3000/login`
- **Default Route:** Automatic redirect if not authenticated

**Login Process:**
1. **Email Field:** Valid email address
2. **Password Field:** User's password with visibility toggle
3. **Authentication:** JWT token generation and storage
4. **Redirect:** Automatic navigation to home screen on success

#### 5.1.3 Authentication State Management

**Provider-Based Authentication:**
```dart
// Auth state provider with Riverpod
final authNotifierProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);

// Current user provider
final currentUserProvider = Provider<User?>((ref) {
  final authState = ref.watch(authNotifierProvider);
  return authState.user;
});
```

**Authentication Features:**
- **JWT Token Management:** Automatic token storage and refresh
- **Session Persistence:** Login state maintained across app restarts
- **Auto-Logout:** Automatic logout on token expiration
- **Route Protection:** Authenticated route guards

### 5.2 Home Dashboard

#### 5.2.1 Main Navigation

**Features:**
- **App Bar:** User profile access and logout functionality
- **Navigation Drawer:** Quick access to all major features
- **Bottom Navigation:** Primary feature navigation (mobile)
- **Responsive Layout:** Adapts to desktop, tablet, and mobile

**Navigation Structure:**
```dart
// Main navigation routes
const routes = [
  {'name': 'Home', 'icon': Icons.home, 'route': '/home'},
  {'name': 'Upload', 'icon': Icons.cloud_upload, 'route': '/upload'},
  {'name': 'Gallery', 'icon': Icons.photo_library, 'route': '/gallery'},
  {'name': 'Collections', 'icon': Icons.collections, 'route': '/collections'},
  {'name': 'Analytics', 'icon': Icons.analytics, 'route': '/analytics'},
];
```

#### 5.2.2 Quick Actions

**Dashboard Features:**
- **Recent Uploads:** Display of recently uploaded media
- **Quick Upload:** Drag-and-drop upload zone
- **Storage Overview:** Visual storage usage statistics
- **Activity Feed:** Recent user activity and notifications

### 5.3 Device-Aware Media Upload

#### 5.3.1 Advanced Upload Interface

**Features:**
- **Multi-File Upload:** Batch upload with progress tracking
- **Drag-and-Drop:** Intuitive file selection
- **File Preview:** Thumbnail previews before upload
- **Progress Tracking:** Real-time upload progress per file
- **Error Handling:** Detailed error messages and retry options

**Access:**
- **URL:** `http://localhost:3000/upload`
- **Quick Access:** Upload button in app bar or home dashboard

**Upload Capabilities:**
```dart
// Device-aware upload widget
DeviceAwareUploadWidget(
  enableBatchUpload: true,
  showPreview: true,
  maxFileSizeBytes: 100 * 1024 * 1024, // 100MB
  allowedExtensions: ['jpg', 'png', 'mp4', 'pdf'],
  onUploadComplete: (response) => handleUploadSuccess(response),
  onUploadError: (error) => handleUploadError(error),
)
```

#### 5.3.2 Device Metadata Integration

**Automatic Device Detection:**
- **Device Information:** Automatic detection of device name, model, OS
- **Location Data:** GPS coordinates (with user permission)
- **Camera Settings:** EXIF data extraction for photos
- **App Context:** App version and upload context

**Metadata Collection:**
```dart
// Device info collection
final deviceInfo = await DeviceInfo.collect();
final uploadMetadata = {
  'device_name': deviceInfo.deviceName,
  'device_model': deviceInfo.model,
  'device_os_version': deviceInfo.osVersion,
  'app_version': AppConfig.version,
  'location': await getCurrentLocation(),
};
```

#### 5.3.3 Upload Progress and Status

**Visual Feedback:**
- **Progress Bars:** Individual file upload progress
- **Status Indicators:** Success, error, and pending states
- **Upload Queue:** Multiple file upload management
- **Retry Mechanism:** Failed upload retry functionality

### 5.4 Media Gallery and Search

#### 5.4.1 Responsive Media Gallery

**Features:**
- **Grid Layout:** Responsive grid with adjustable columns
- **Infinite Scroll:** Lazy loading for large media collections
- **Selection Mode:** Multi-select for batch operations
- **Media Preview:** Quick view with zoom and navigation
- **Sorting Options:** Date, name, size, device, type sorting

**Access:**
- **URL:** `http://localhost:3000/gallery`
- **Navigation:** Gallery tab in main navigation

**Gallery Layout:**
```dart
// Responsive grid with media items
ResponsiveMediaGallery(
  filters: currentFilters,
  enableSelection: isSelectionMode,
  enableInfiniteScroll: true,
  columnCount: getColumnCount(screenWidth),
  onItemTap: (item) => showMediaPreview(item),
  onItemLongPress: (item) => enterSelectionMode(item),
)
```

#### 5.4.2 Advanced Search Interface

**Search Capabilities:**
- **Text Search:** Full-text search across filenames and descriptions
- **Filter Options:** Device, date range, media type, tags
- **Smart Filters:** Recent, favorites, shared items
- **Saved Searches:** Save and recall common search patterns

**Search Interface:**
```dart
// Advanced search with filters
AdvancedSearchInterface(
  initialFilters: currentFilters,
  onSearch: (filters) => applySearchFilters(filters),
  onClear: () => clearAllFilters(),
  availableTags: userTags,
  availableCollections: userCollections,
  availableDevices: userDevices,
)
```

**Filter Categories:**
- **Media Type:** Pictures, videos, documents
- **Device Filter:** Filter by specific devices or manufacturers
- **Date Range:** Custom date range selection
- **Location:** Search by GPS location (if available)
- **File Size:** Filter by file size ranges
- **Tags:** User-defined and auto-generated tags

#### 5.4.3 Media Preview and Interaction

**Preview Features:**
- **Image Viewer:** High-resolution image display with zoom
- **Video Player:** Built-in video player with controls
- **Document Viewer:** PDF and document preview
- **EXIF Data:** Camera settings and metadata display
- **Sharing Options:** Quick share and download options

### 5.5 Collections Management

#### 5.5.1 Collection Organization

**Features:**
- **Create Collections:** Custom collections with names and descriptions
- **Drag-and-Drop:** Easy media organization
- **Collection Views:** Grid and list views for collections
- **Nested Collections:** Sub-collections and hierarchical organization
- **Sharing:** Share entire collections with other users

**Access:**
- **URL:** `http://localhost:3000/collections`
- **Quick Creation:** Create collections from gallery selection

**Collection Interface:**
```dart
// Collection management widget
CollectionManagement(
  onCollectionSelected: (collection) => viewCollection(collection),
  onItemsAddedToCollection: (items, collection) => addToCollection(items, collection),
  selectedItems: selectedMediaItems,
  enableDragAndDrop: true,
)
```

#### 5.5.2 Collection Features

**Management Options:**
- **Rename Collections:** Edit collection names and descriptions
- **Cover Images:** Set custom cover images for collections
- **Privacy Settings:** Public/private collection visibility
- **Collaboration:** Share collections with other users
- **Export Options:** Download entire collections

### 5.6 Analytics Dashboard

#### 5.6.1 Usage Analytics

**Features:**
- **Storage Analytics:** Visual storage usage by type and device
- **Upload Trends:** Time-based upload activity charts
- **Device Breakdown:** Media distribution across devices
- **Popular Tags:** Most frequently used tags
- **Activity Timeline:** User activity over time

**Access:**
- **URL:** `http://localhost:3000/analytics`
- **Dashboard:** Comprehensive analytics overview

**Analytics Components:**
```dart
// Analytics dashboard with charts
AnalyticsDashboard(
  userId: currentUser.id,
  startDate: selectedStartDate,
  endDate: selectedEndDate,
  showCharts: true,
  enableExport: true,
)
```

#### 5.6.2 Visualization Features

**Chart Types:**
- **Storage Usage:** Pie charts for storage breakdown
- **Upload Trends:** Line charts for upload activity
- **Device Analytics:** Bar charts for device usage
- **Time-based Analytics:** Activity heatmaps
- **Comparative Analytics:** Multi-device comparisons

### 5.7 User Profile and Settings

#### 5.7.1 Profile Management

**Features:**
- **Profile Information:** Edit username, email, and personal details
- **Password Management:** Change password with current password verification
- **Account Settings:** Privacy and notification preferences
- **Device Management:** View and manage connected devices
- **Storage Overview:** Account storage usage and limits

#### 5.7.2 Application Settings

**Configuration Options:**
- **Theme Settings:** Light/dark mode toggle
- **Language Preferences:** Multi-language support
- **Upload Settings:** Default upload preferences
- **Privacy Settings:** Data sharing and visibility options
- **Notification Settings:** Email and in-app notifications

### 5.8 Responsive Design Features

#### 5.8.1 Multi-Platform Support

**Platform Adaptations:**
- **Web Browser:** Full-featured web interface
- **Desktop App:** Native desktop experience (via Flutter desktop)
- **Mobile Responsive:** Mobile-optimized layouts
- **Tablet Support:** Optimized for tablet screen sizes

**Responsive Breakpoints:**
```dart
// Responsive design breakpoints
const breakpoints = {
  'mobile': 600,
  'tablet': 1024,
  'desktop': 1440,
  'large': 1920,
};
```

#### 5.8.2 Adaptive UI Components

**Component Adaptations:**
- **Navigation:** Drawer on mobile, sidebar on desktop
- **Media Grid:** Adaptive column count based on screen size
- **Upload Interface:** Touch-friendly on mobile, drag-drop on desktop
- **Dialogs:** Full-screen on mobile, modal on desktop

### 5.9 Real-time Features

#### 5.9.1 Live Updates

**Real-time Capabilities:**
- **Upload Progress:** Live upload progress updates
- **Collection Changes:** Real-time collection updates
- **Shared Content:** Live updates for shared collections
- **Storage Usage:** Real-time storage usage updates

#### 5.9.2 Offline Support

**Offline Features:**
- **Cached Content:** Browse previously loaded media offline
- **Queue Uploads:** Queue uploads for when connection returns
- **Offline Analytics:** View cached analytics data
- **Local Storage:** Persistent local data storage

### 5.10 Frontend Integration Examples

#### 5.10.1 Complete User Workflow

**Registration to Upload Workflow:**
1. **Access Registration:** Navigate to `http://localhost:3000/register`
2. **Create Account:** Fill registration form and submit
3. **Email Verification:** Click verification link in email
4. **Login:** Use credentials to access platform
5. **Upload Media:** Drag-and-drop files in upload interface
6. **Organize Collections:** Create collections and organize media
7. **View Analytics:** Check upload statistics and device analytics

#### 5.10.2 Frontend API Integration

**Service Integration:**
```dart
// Media upload with frontend integration
final uploadResult = await MediaApiClient().uploadMedia(
  filePath: selectedFile.path,
  filename: selectedFile.name,
  metadata: deviceMetadata,
  onProgress: (sent, total) => updateProgress(sent / total),
);

if (uploadResult.isSuccess) {
  showSuccessMessage('Upload completed successfully');
  refreshGallery();
} else {
  showErrorMessage(uploadResult.error);
}
```

#### 5.10.3 State Management Integration

**Riverpod State Management:**
```dart
// Media state provider
final mediaProvider = StateNotifierProvider<MediaNotifier, MediaState>(
  (ref) => MediaNotifier(),
);

// Collection state provider
final collectionsProvider = StateNotifierProvider<CollectionsNotifier, CollectionsState>(
  (ref) => CollectionsNotifier(),
);

// Analytics state provider
final analyticsProvider = StateNotifierProvider<AnalyticsNotifier, AnalyticsState>(
  (ref) => AnalyticsNotifier(),
);
```

### 5.11 Frontend Development Features

#### 5.11.1 Development Tools

**Development Support:**
- **Hot Reload:** Real-time code changes during development
- **Debug Console:** Comprehensive debugging information
- **Performance Monitoring:** Frame rate and memory usage tracking
- **Error Handling:** Comprehensive error reporting and recovery

#### 5.11.2 Build and Deployment

**Build Options:**
```bash
# Web development
flutter run -d chrome --web-port 3000

# Desktop development
flutter run -d macos

# Production web build
flutter build web --release

# Production desktop build
flutter build macos --release
```

### 5.12 User Experience Features

#### 5.12.1 Accessibility

**Accessibility Features:**
- **Screen Reader Support:** Comprehensive screen reader compatibility
- **Keyboard Navigation:** Full keyboard navigation support
- **High Contrast:** High contrast mode for visibility
- **Font Scaling:** Adjustable font sizes
- **Focus Management:** Proper focus management for navigation

#### 5.12.2 Performance Optimizations

**Performance Features:**
- **Lazy Loading:** On-demand content loading
- **Image Caching:** Intelligent image caching strategy
- **Memory Management:** Efficient memory usage for large galleries
- **Network Optimization:** Optimized API calls and caching
- **Bundle Splitting:** Optimized web bundle loading

The PPL Meta Flutter Frontend provides a comprehensive, modern interface that leverages the full power of the backend services while delivering an exceptional user experience across all platforms and devices.

---
## **API Endpoints Summary**

### **Core Authentication Endpoints**
| **Endpoint** | **Method** | **Purpose** | **Port** | **Nginx Route** |
|-------------|-----------|-------------|----------|-----------------|
| `/api/v1/users/register` | POST | User registration | 8001 | `http://localhost/api/v1/users/register` |
| `/api/v1/users/login` | POST | User login | 8001 | `http://localhost/api/v1/users/login` |
| `/api/v1/users/logout` | POST | User logout | 8001 | `http://localhost/api/v1/users/logout` |
| `/api/v1/users/profile` | GET | Get user profile | 8001 | `http://localhost/api/v1/users/profile` |
| `/api/v1/users/verify-email` | GET | Email verification | 8001 | `http://localhost/api/v1/users/verify-email` |

### **User Management Endpoints**
| **Endpoint** | **Method** | **Purpose** | **Auth Required** |
|-------------|-----------|-------------|------------------|
| `/api/v1/users/` | GET | List all users | Yes |
| `/api/v1/users/{user_id}` | GET | Get user by ID | Yes |
| `/api/v1/users/guid/{guid}` | GET | Get user by GUID | Yes |
| `/api/v1/users/actions/` | GET | List user actions | Yes |
| `/api/v1/users/update-password` | POST | Update password | Yes |
| `/api/v1/users/forgot-password` | POST | Request password reset | No |
| `/api/v1/users/reset-password` | POST | Reset password with token | No |

### **Role & Permission Management**
| **Endpoint** | **Method** | **Purpose** | **Auth Required** |
|-------------|-----------|-------------|------------------|
| `/api/v1/roles/` | GET/POST | List/Create roles | Yes |
| `/api/v1/roles/{role_id}` | GET/PUT/DELETE | Manage specific role | Yes |
| `/api/v1/roles/assign/` | POST | Assign role to user | Yes |
| `/api/v1/roles/unassign/` | POST | Remove role from user | Yes |
| `/api/v1/roles/add-capability/` | POST | Add capability to role | Yes |
| `/api/v1/capabilities/by-role/{role_id}` | GET | Get role capabilities | Yes |
| `/api/v1/capabilities/by-user/{user_id}` | GET | Get user capabilities | Yes |

### **Advanced Features**
| **Endpoint** | **Method** | **Purpose** | **Auth Required** |
|-------------|-----------|-------------|------------------|
| `/api/v1/otp/send` | POST | Send OTP via email | No |
| `/api/v1/otp/verify-otp` | POST | Verify OTP code | No |
| `/api/v1/backup/export` | GET | Export user data | Admin |
| `/api/v1/backup/database` | GET | Backup database | Admin |
| `/api/v1/backup/restore` | POST | Restore from backup | Admin |

### **Service Health & Monitoring**
| **Endpoint** | **Method** | **Purpose** | **Port** |
|-------------|-----------|-------------|----------|
| `/health` | GET | Service health check | All Services |
| `/api/v1/health` | GET | Node service health | 8001 |

---

## **Authentication Flow**

```mermaid
graph TD
    A[User Registration] --> B[Account Created]
    B --> C[Login Request]
    C --> D[JWT Token Issued]
    D --> E[Access Protected Endpoints]
    E --> F[Upload Media]
    E --> G[Manage Collections]
    E --> H[Analytics Dashboard]
```

1. **Register** → Get user account created
2. **Login** → Get JWT access token  
3. **Use Token** → Access protected endpoints
4. **Upload Media** → Use token for media operations
5. **Analytics** → View device and usage analytics
6. **Collections** → Organize and share media

---

## **Complete User Management Features**

The PPL Meta Node service provides comprehensive user management capabilities beyond basic registration and authentication.

### **User Profile Management**

#### **Update Password**
```bash
# Update your password (requires current password)
curl -X POST http://localhost:8001/api/v1/users/update-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "OldPassword123",
    "new_password": "NewSecurePassword456"
  }'
```

#### **Get User by ID**
```bash
# Get specific user information
curl -X GET http://localhost:8001/api/v1/users/1 \
  -H "Authorization: Bearer $TOKEN"
```

#### **Get User by GUID**
```bash
# Get user by their unique GUID
curl -X GET http://localhost:8001/api/v1/users/guid/your-user-guid \
  -H "Authorization: Bearer $TOKEN"
```

#### **List All Users**
```bash
# List users with pagination
curl -X GET "http://localhost:8001/api/v1/users/?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

#### **View User Actions Log**
```bash
# Get user activity history
curl -X GET "http://localhost:8001/api/v1/users/actions/?skip=0&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

### **Password Recovery System**

#### **Request Password Reset**
```bash
# Request password reset email
curl -X POST http://localhost:8001/api/v1/users/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

**Expected Response:**
```json
{
  "detail": "Password reset email sent"
}
```

#### **Reset Password with Token**
```bash
# Reset password using token from email
curl -X POST http://localhost:8001/api/v1/users/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "password-reset-token-from-email",
    "new_password": "NewPassword123"
  }'
```

### **Two-Factor Authentication (OTP)**

#### **Send OTP Code**
```bash
# Send OTP to user's email
curl -X POST http://localhost:8001/api/v1/otp/send \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1
  }'
```

#### **Verify OTP and Login**
```bash
# Verify OTP and get access token
curl -X POST http://localhost:8001/api/v1/otp/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp_code": "123456"
  }'
```

### **Role-Based Access Control (RBAC)**

#### **Create Role**
```bash
# Create a new role (admin required)
curl -X POST http://localhost:8001/api/v1/roles/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "content_moderator"
  }'
```

#### **List All Roles**
```bash
# Get all available roles
curl -X GET http://localhost:8001/api/v1/roles/ \
  -H "Authorization: Bearer $TOKEN"
```

#### **Assign Role to User**
```bash
# Assign role to a user
curl -X POST http://localhost:8001/api/v1/roles/assign/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "role_id": 2
  }'
```

#### **Remove Role from User**
```bash
# Remove role from user
curl -X POST http://localhost:8001/api/v1/roles/unassign/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "role_id": 2
  }'
```

#### **Get User Capabilities**
```bash
# Get all capabilities for a specific user
curl -X GET http://localhost:8001/api/v1/capabilities/by-user/1 \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "roles": [
    {
      "role_id": 1,
      "role_name": "admin",
      "role_description": "Administrator role"
    }
  ],
  "capabilities": [
    {
      "name": "user_management",
      "description": "Manage users and roles"
    },
    {
      "name": "media_moderation",
      "description": "Moderate media content"
    }
  ]
}
```

### **Administrative Features**

#### **Data Export (Admin Only)**
```bash
# Export all user data (admin required)
curl -X GET http://localhost:8001/api/v1/backup/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  > user_data_backup.json
```

#### **Database Backup (Admin Only)**
```bash
# Create database backup (admin required)
curl -X GET http://localhost:8001/api/v1/backup/database \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  > database_backup.sql
```

#### **Restore from Backup (Admin Only)**
```bash
# Restore from backup file (admin required)
curl -X POST http://localhost:8001/api/v1/backup/restore \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@user_data_backup.json"
```

---

## **Inter-Service Communication**

The PPL Meta Node provides endpoints for other services to validate users and get permissions:

### **Token Validation for Services**
```bash
# Validate JWT token (internal service use)
curl -X POST http://localhost:8001/api/v1/users/validate-token \
  -H "Authorization: Bearer SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "user-jwt-token"
  }'
```

### **Get User Info for Services**
```bash
# Get user information for inter-service communication
curl -X GET http://localhost:8001/api/v1/users/user-info/1 \
  -H "Authorization: Bearer SERVICE_TOKEN"
```

---

## **Complete Workflow Example**

```bash
#!/bin/bash
# Complete PPL Meta Platform User Management Demo
# This script demonstrates the full user lifecycle and management capabilities

echo "🚀 PPL Meta Platform User Management Demo"
echo "=========================================="

# 1. Register a new user
echo "📝 Step 1: Registering new user..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"username": "demo_user", "email": "demo@example.com", "password": "DemoPassword123"}')

echo "Registration Response: $REGISTER_RESPONSE"

# 2. Login and extract token
echo "🔐 Step 2: Logging in to get access token..."
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/users/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo@example.com&password=DemoPassword123" | \
  python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

echo "Token obtained: ${TOKEN:0:50}..."

# 3. Access profile
echo "👤 Step 3: Accessing user profile..."
curl -s -X GET http://localhost:8001/api/v1/users/profile \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 4. List all users
echo "📋 Step 4: Listing all users..."
curl -s -X GET "http://localhost:8001/api/v1/users/?skip=0&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 5. Check user capabilities
echo "🔑 Step 5: Checking user capabilities..."
USER_ID=$(curl -s -X GET http://localhost:8001/api/v1/users/profile \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" 2>/dev/null)

curl -s -X GET "http://localhost:8001/api/v1/capabilities/by-user/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 6. Update password
echo "🔒 Step 6: Updating password..."
curl -s -X POST http://localhost:8001/api/v1/users/update-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password": "DemoPassword123", "new_password": "NewDemoPassword456"}' | python3 -m json.tool

# 7. Test 2FA - Send OTP
echo "📱 Step 7: Testing 2FA - Sending OTP..."
curl -s -X POST http://localhost:8001/api/v1/otp/send \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": $USER_ID}" | python3 -m json.tool

# 8. View user activity log
echo "📊 Step 8: Viewing user activity log..."
curl -s -X GET "http://localhost:8001/api/v1/users/actions/?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 9. Test media service access
echo "📸 Step 9: Testing media service access..."
curl -s -X GET http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -G -d "query=test" | python3 -m json.tool

# 10. Logout
echo "🚪 Step 10: Logging out..."
curl -s -X POST http://localhost:8001/api/v1/users/logout \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "✅ Complete user management demo completed successfully!"
echo ""
echo "🎯 Key Features Demonstrated:"
echo "   • User registration and authentication"
echo "   • Profile management and password updates"
echo "   • Role-based access control (RBAC)"
echo "   • Two-factor authentication (2FA)"
echo "   • User activity monitoring"
echo "   • Inter-service communication"
echo "   • Session management and logout"
```

## **Enterprise User Management Workflows**

### **User Onboarding Workflow**
```bash
#!/bin/bash
# Enterprise user onboarding process

# 1. Admin creates user account
ADMIN_TOKEN="admin-jwt-token"
NEW_USER=$(curl -s -X POST http://localhost:8001/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"username": "new_employee", "email": "employee@company.com", "password": "TempPassword123"}')

# 2. Extract user ID
USER_ID=$(echo $NEW_USER | python3 -c "import json,sys; print(json.load(sys.stdin)['user']['id'])")

# 3. Assign appropriate role
curl -X POST http://localhost:8001/api/v1/roles/assign/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": $USER_ID, \"role_id\": 2}"

# 4. Send welcome email with verification
echo "User $USER_ID onboarded successfully with role assignment"
```

### **User Audit and Compliance**
```bash
#!/bin/bash
# Generate user audit report

echo "📋 User Audit Report - $(date)"
echo "================================"

# 1. List all users
echo "Total Users:"
curl -s -X GET "http://localhost:8001/api/v1/users/?skip=0&limit=1000" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"

# 2. Recent user activities
echo "Recent User Activities:"
curl -s -X GET "http://localhost:8001/api/v1/users/actions/?skip=0&limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool

# 3. Role distribution
echo "Role Distribution:"
curl -s -X GET http://localhost:8001/api/v1/roles/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
```

### **Security Monitoring Workflow**
```bash
#!/bin/bash
# Security monitoring and alerting

# 1. Check for suspicious login patterns
echo "🔒 Security Monitoring Report"
echo "============================"

# 2. Recent failed login attempts (from activity log)
curl -s -X GET "http://localhost:8001/api/v1/users/actions/?skip=0&limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
failed_logins = [action for action in data if 'failed' in action.get('action', '').lower()]
print(f'Failed login attempts: {len(failed_logins)}')
"

# 3. Users with admin privileges
echo "Admin Users:"
curl -s -X GET http://localhost:8001/api/v1/roles/by-name/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
```

---

## **Media Management with Frontend Interface**

Once registered and authenticated, you can access the full media management capabilities through both API and the Flutter frontend interface:

### **Upload Media via Frontend**
1. **Navigate to Upload:** Click "Upload" in the main navigation or visit `http://localhost:3000/upload`
2. **Drag-and-Drop:** Simply drag files onto the upload area
3. **Batch Upload:** Select multiple files for simultaneous upload
4. **Progress Tracking:** Watch real-time upload progress for each file
5. **Device Metadata:** Automatic device information capture and association

```bash
# Alternative: Direct API upload
curl -X POST http://localhost:8000/api/v1/media/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your_image.jpg" \
  -F "user_id=your-user-id" \
  -F "device_name=Your Device" \
  -F "tags=vacation,photos"
```

### **Browse Media via Gallery**
1. **Gallery Interface:** Visit `http://localhost:3000/gallery` for responsive media browsing
2. **Search and Filter:** Use advanced search with device, date, and tag filters
3. **Selection Mode:** Multi-select media for batch operations
4. **Preview Mode:** Click any media for full-screen preview with metadata
5. **Organization:** Drag media into collections directly from gallery

### **Analytics Dashboard**
1. **Analytics View:** Visit `http://localhost:3000/analytics` for comprehensive insights
2. **Device Analytics:** View upload statistics by device type and manufacturer
3. **Storage Insights:** Monitor storage usage and optimization recommendations
4. **Usage Trends:** Track upload patterns and activity over time
5. **Export Data:** Download analytics reports for external analysis

### **Collections Management**
1. **Collections Interface:** Visit `http://localhost:3000/collections` for organization tools
2. **Create Collections:** Custom collections with names, descriptions, and cover images
3. **Drag-and-Drop Organization:** Move media between collections with intuitive interface
4. **Sharing:** Generate share links for entire collections
5. **Collaboration:** Share collections with other platform users

---

## **Security Features Active**

✅ **Password Hashing**: bcrypt with salt  
✅ **JWT Tokens**: HS256 algorithm with configurable expiration  
✅ **Rate Limiting**: 5 requests/minute for registration, 100/minute for API calls  
✅ **Input Validation**: SQL injection and XSS protection  
✅ **CORS**: Configured for local development  
✅ **File Security**: Magic number validation and ClamAV scanning  
✅ **RBAC**: Role-based access control (admin/user/viewer/guest)  

---

## **Performance Features**

✅ **Database Optimization**: 20+ performance indexes  
✅ **Redis Caching**: 70-85% cache hit rates  
✅ **Background Processing**: Celery task queues  
✅ **CDN Integration**: AWS CloudFront support  
✅ **Real-time Monitoring**: Performance metrics and alerting  

---

## **Troubleshooting**

### **Common Issues and Solutions:**

#### **1. "Email already registered"**
- **Solution**: Use a different email address or check if the user already exists
- **Check existing users**: Contact administrator or use forgot password

#### **2. "401 Unauthorized"**
- **Solution**: Ensure JWT token is included in Authorization header
- **Format**: `Authorization: Bearer YOUR_TOKEN_HERE`
- **Check**: Token expiration (default: configurable via settings)

#### **3. "Connection refused"**
- **Solution**: Ensure all services are running
- **Check health**: Run health check endpoints
- **Restart services**: Use VS Code tasks to restart services

#### **4. "Service not responding"**
- **Check logs**: Look at service terminal output
- **Verify ports**: Ensure no port conflicts (8000, 8001, 8080, 8002)
- **Database**: Ensure PostgreSQL is running and accessible

#### **5. Frontend not loading at localhost:3000**
- **Solution**: Check if Flutter frontend service is running
- **Start Frontend**: Use VS Code task "📱 Start Frontend (Web)"
- **Browser Compatibility**: Ensure modern browser with JavaScript enabled
- **Network Issues**: Check firewall settings and port availability

#### **6. Upload interface not responding**
- **Solution**: Check browser developer console for JavaScript errors
- **File Size**: Ensure files are under the 100MB limit
- **Network Connection**: Verify stable internet connection for uploads
- **Browser Permissions**: Allow necessary permissions for file access

#### **7. Gallery images not displaying**
- **Solution**: Check media service connection and file storage
- **Cache Issues**: Clear browser cache and refresh page
- **File Paths**: Verify media files exist in storage directory
- **Authentication**: Ensure valid login session and JWT token

### **Frontend User Experience Features**

#### **Responsive Design**
- **Mobile Optimized**: Full functionality on mobile devices
- **Tablet Support**: Optimized layout for tablet screens
- **Desktop Interface**: Enhanced features for desktop browsers
- **Adaptive UI**: Components adapt to screen size and orientation

#### **Accessibility Features**
- **Screen Reader Support**: Full compatibility with accessibility tools
- **Keyboard Navigation**: Complete keyboard navigation support
- **High Contrast Mode**: Enhanced visibility options
- **Font Scaling**: Adjustable text size for better readability

#### **Performance Optimizations**
- **Lazy Loading**: Images load as needed to improve performance
- **Caching Strategy**: Intelligent caching for faster page loads
- **Progressive Loading**: Gradual content loading for better UX
- **Offline Support**: Basic functionality available offline

### **Health Check Commands:**
```bash
# Individual service health checks
curl http://localhost:8001/api/v1/health  # Node Service (Users)
curl http://localhost:8000/health         # Media Service  
curl http://localhost:8080/health         # Gateway Service
curl http://localhost:8002/health         # Orchestrator Service
```

### **Service Status Check:**
```bash
# Check running processes
ps aux | grep 'python.*main.py\|uvicorn.*main:app' | grep -v grep
```

---

## **Advanced Features**

### **Email Verification System**
- Email verification tokens are automatically generated upon registration
- Check email for verification link after registering
- Verify using: `GET /api/v1/users/verify-email?token=YOUR_TOKEN`

```bash
# Manual email verification
curl -X GET "http://localhost:8001/api/v1/users/verify-email?token=verification-token-from-email"
```

### **Complete Password Management**

#### **Update Password (Authenticated)**
```bash
# Change password while logged in
curl -X POST http://localhost:8001/api/v1/users/update-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "CurrentPassword123",
    "new_password": "NewSecurePassword456"
  }'
```

#### **Forgot Password Flow**
```bash
# Step 1: Request password reset
curl -X POST http://localhost:8001/api/v1/users/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your_email@example.com"
  }'

# Step 2: Use token from email to reset
curl -X POST http://localhost:8001/api/v1/users/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset-token-from-email",
    "new_password": "NewPassword123"
  }'
```

### **Two-Factor Authentication (2FA)**

#### **Enable 2FA for Account**
```bash
# Step 1: Request OTP
curl -X POST http://localhost:8001/api/v1/otp/send \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1
  }'

# Step 2: Verify OTP and login
curl -X POST http://localhost:8001/api/v1/otp/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp_code": "123456"
  }'
```

### **User Session Management**

#### **Logout (Token Invalidation)**
```bash
# Logout and invalidate session
curl -X POST http://localhost:8001/api/v1/users/logout \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "msg": "Logout successful. Please delete your token client-side."
}
```

### **Administrative User Management**

#### **User Activity Monitoring**
```bash
# Get detailed user activity logs
curl -X GET "http://localhost:8001/api/v1/users/actions/?skip=0&limit=50" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### **User Role Management Workflow**
```bash
# 1. Create custom role
curl -X POST http://localhost:8001/api/v1/roles/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "content_editor"}'

# 2. Assign role to user
curl -X POST http://localhost:8001/api/v1/roles/assign/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "role_id": 3}'

# 3. Verify user capabilities
curl -X GET http://localhost:8001/api/v1/capabilities/by-user/1 \
  -H "Authorization: Bearer $TOKEN"
```

#### **System Backup and Recovery**

#### **Complete Data Export**
```bash
# Export all system data (admin only)
curl -X GET http://localhost:8001/api/v1/backup/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o complete_backup_$(date +%Y%m%d).json
```

#### **Database Backup**
```bash
# Create database backup
curl -X GET http://localhost:8001/api/v1/backup/database \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o database_backup_$(date +%Y%m%d).sql
```

#### **System Recovery**
```bash
# Restore from backup
curl -X POST http://localhost:8001/api/v1/backup/restore \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "file=@complete_backup_20250714.json"
```

### **Cloud Storage Integration**
- Supports AWS S3, Azure Blob, Google Cloud Storage
- Configurable via environment variables
- Automatic file migration between providers

### **Performance Monitoring**
```bash
# Get performance metrics
curl -X GET http://localhost:8000/api/v1/performance/status \
  -H "Authorization: Bearer $TOKEN"
```

---

## **Environment Configuration**

Key environment variables for customization:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ppl_meta

# JWT Settings
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# Redis (for caching and rate limiting)
REDIS_URL=redis://localhost:6379

# Email (for verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Cloud Storage (optional)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
```

---

## **Development vs Production**

### **Local Development (Current Setup)**
- **Ports**: Direct service access (8000, 8001, 8080, 8002)
- **Database**: Local PostgreSQL
- **Storage**: Local file system
- **CORS**: Permissive for development

### **Production Deployment**
- **Nginx**: Reverse proxy with SSL termination
- **Docker**: Containerized services
- **Cloud Storage**: S3/Azure/GCP integration
- **Monitoring**: Real-time performance monitoring
- **Security**: Enhanced rate limiting and validation

---

## **Next Steps - Full Platform Experience**

After successful registration and authentication, you have access to both API endpoints and the modern Flutter frontend interface:

### **🎯 Recommended User Journey**

#### **1. Frontend-First Experience (Recommended)**
1. **Web Interface**: Start at `http://localhost:3000` for the full visual experience
2. **Registration**: Use the intuitive registration form with real-time validation
3. **Dashboard**: Explore the modern dashboard with quick actions and overview
4. **Upload Media**: Use drag-and-drop upload with automatic device detection
5. **Browse Gallery**: Enjoy responsive media browsing with advanced search
6. **Organize Collections**: Create and manage collections with visual interface
7. **View Analytics**: Monitor usage patterns through interactive charts

#### **2. API Integration (For Developers)**
1. **Authentication**: Obtain JWT tokens via `/api/v1/users/login`
2. **Media Operations**: Upload via `/api/v1/media/upload` with metadata
3. **Search & Retrieval**: Use comprehensive search and filtering APIs
4. **Analytics**: Access raw analytics data for custom dashboards
5. **Automation**: Build automated workflows with full API coverage

#### **3. Hybrid Approach (Power Users)**
1. **Frontend for Daily Use**: Interactive interface for regular operations
2. **API for Automation**: Scripts and integrations for bulk operations
3. **Custom Dashboards**: Combine frontend insights with API data
4. **Advanced Workflows**: Mix visual tools with programmatic access

### **📱 Platform Features Overview**

#### **Frontend Capabilities**
- **Modern UI/UX**: Responsive Flutter interface across all devices
- **Real-time Updates**: Live upload progress and status notifications
- **Intuitive Navigation**: Easy-to-use interface for all skill levels
- **Visual Analytics**: Interactive charts and usage insights
- **Drag-and-Drop**: Seamless file management and organization
- **Accessibility**: Full support for assistive technologies

#### **Backend API Power**
- **Complete REST API**: Full programmatic access to all features
- **Device Intelligence**: Advanced device-aware metadata capture
- **Scalable Architecture**: Enterprise-ready performance optimization
- **Security Framework**: Comprehensive validation and access control
- **Cloud Integration**: Multi-provider cloud storage support
- **Real-time Processing**: Background task processing and optimization

### **🔗 Integration Examples**

#### **Frontend + API Workflow**
```javascript
// Example: Upload via frontend with API monitoring
const uploadFile = async (file, deviceInfo) => {
  // Frontend handles UI and user experience
  const formData = new FormData();
  formData.append('file', file);
  formData.append('device_metadata', JSON.stringify(deviceInfo));
  
  // API provides robust backend processing
  const response = await fetch('/api/v1/media/upload', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
  
  // Frontend updates UI with results
  return response.json();
};
```

#### **Cross-Platform Consistency**
- **Web Browser**: Full-featured web interface at localhost:3000
- **API Access**: Direct backend integration at localhost:8000/8001
- **Mobile Ready**: Responsive design for mobile devices
- **Desktop Apps**: Flutter desktop builds for native experience

---

## **Support and Documentation**

- **API Documentation**: Available at service endpoints `/docs`
- **Health Monitoring**: Real-time service status via health endpoints
- **Logs**: Service logs available in terminal outputs
- **Performance Metrics**: Available via performance monitoring endpoints

---

*PPL Meta Platform v1.3.0 - Production Ready*  
*Last Updated: July 14, 2025*  
*Documentation: Complete registration and authentication guide*

---

## 4. PPL Meta Media Service - Complete Functionality Guide

The PPL Meta Media Service is a comprehensive media management system that handles file uploads, storage, processing, and serving with device-aware capabilities, cloud storage integration, and advanced analytics.

### 4.1 Core Media Management

#### 4.1.1 Device-Aware Media Upload

Upload media files with automatic device metadata extraction:

```bash
# Basic media upload with device information
curl -X POST "http://localhost:8000/api/v1/media/upload" \
  -F "file=@photo.jpg" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "device_name=iPhone 15 Pro" \
  -F "device_model=iPhone15,2" \
  -F "device_os_version=iOS 17.1" \
  -F "app_version=1.0.0" \
  -F "location_latitude=37.7749" \
  -F "location_longitude=-122.4194" \
  -F "is_public=false"

# Upload with additional metadata
curl -X POST "http://localhost:8000/api/v1/media/upload" \
  -F "file=@video.mp4" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "device_name=Canon EOS R5" \
  -F "tags=vacation,beach,sunset" \
  -F "description=Beautiful sunset at the beach"
```

**Response:**

```json
{
  "id": "media-uuid-here",
  "filename": "photo.jpg",
  "original_filename": "photo.jpg",
  "media_type": "PICTURE",
  "mime_type": "image/jpeg",
  "file_size": 2048576,
  "uploaded_by": "123e4567-e89b-12d3-a456-426614174000",
  "uploaded_at": "2024-01-15T10:30:00Z",
  "device_metadata": {
    "device_name": "iPhone 15 Pro",
    "device_model": "iPhone15,2",
    "device_os_version": "iOS 17.1",
    "app_version": "1.0.0",
    "location": {
      "latitude": 37.7749,
      "longitude": -122.4194
    }
  },
  "processing_status": "completed",
  "public_url": null,
  "thumbnail_urls": {
    "small": "/api/v1/media/thumbnail/media-uuid-here?size=small",
    "medium": "/api/v1/media/thumbnail/media-uuid-here?size=medium",
    "large": "/api/v1/media/thumbnail/media-uuid-here?size=large"
  }
}
```

#### 4.1.2 Advanced Media Search

Search media with comprehensive filtering options:

```bash
# Basic search
curl "http://localhost:8000/api/v1/media/search?user_id=123e4567-e89b-12d3-a456-426614174000&query=vacation"

# Advanced search with filters
curl "http://localhost:8000/api/v1/media/search" \
  -G \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "query=beach sunset" \
  -d "media_type=PICTURE" \
  -d "device_name=iPhone 15 Pro" \
  -d "start_date=2024-01-01" \
  -d "end_date=2024-12-31" \
  -d "has_location=true" \
  -d "is_public=false" \
  -d "limit=50" \
  -d "offset=0"

# Search by tags
curl "http://localhost:8000/api/v1/media/search?user_id=123e4567-e89b-12d3-a456-426614174000&tags=vacation,beach"
```

**Response:**
```json
{
  "results": [
    {
      "id": "media-uuid-1",
      "filename": "beach_sunset.jpg",
      "media_type": "PICTURE",
      "uploaded_at": "2024-01-15T10:30:00Z",
      "device_name": "iPhone 15 Pro",
      "tags": ["vacation", "beach", "sunset"],
      "thumbnail_url": "/api/v1/media/thumbnail/media-uuid-1"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

#### 4.1.3 Media Information and Retrieval

Get detailed media information:

```bash
# Get media details
curl "http://localhost:8000/api/v1/media/media-uuid-here?user_id=123e4567-e89b-12d3-a456-426614174000"

# Delete media
curl -X DELETE "http://localhost:8000/api/v1/media/media-uuid-here" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000"
```

### 4.2 File Serving and Access Control

#### 4.2.1 Direct File Download

Download media files with access control:

```bash
# Download by owner
curl "http://localhost:8000/api/v1/media/download/media-uuid-here?user_id=123e4567-e89b-12d3-a456-426614174000" \
  -o downloaded_file.jpg

# Download with share token (public access)
curl "http://localhost:8000/api/v1/media/download/media-uuid-here?share_token=abc123def456" \
  -o shared_file.jpg
```

#### 4.2.2 Media Streaming

Stream video/audio files with range request support:

```bash
# Stream media file
curl "http://localhost:8000/api/v1/media/stream/media-uuid-here?user_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Range: bytes=0-1023" \
  --output video_chunk.mp4

# Stream without range (full file)
curl "http://localhost:8000/api/v1/media/stream/media-uuid-here?user_id=123e4567-e89b-12d3-a456-426614174000"
```

#### 4.2.3 Thumbnail Generation

Generate and serve thumbnails for images and videos:

```bash
# Get medium thumbnail
curl "http://localhost:8000/api/v1/media/thumbnail/media-uuid-here?size=medium&user_id=123e4567-e89b-12d3-a456-426614174000" \
  -o thumbnail.jpg

# Get video thumbnail from specific timestamp
curl "http://localhost:8000/api/v1/media/thumbnail/video-uuid-here" \
  -G \
  -d "size=large" \
  -d "video_timestamp=00:02:30" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -o video_thumb.jpg

# Get video thumbnail from different positions
curl "http://localhost:8000/api/v1/media/thumbnail/video-uuid-here" \
  -G \
  -d "size=medium" \
  -d "video_position=middle" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000"
```

**Thumbnail Options:**

- **Sizes:** `small` (150px), `medium` (300px), `large` (600px)
- **Video Positions:** `start`, `middle`, `end`
- **Custom Timestamp:** Format `HH:MM:SS` (e.g., `00:02:30`)

### 4.3 EXIF Data Processing

#### 4.3.1 EXIF Data Extraction

Extract and manage EXIF metadata from images:

```bash
# Get existing EXIF data
curl "http://localhost:8000/api/v1/media/exif/media-uuid-here?user_id=123e4567-e89b-12d3-a456-426614174000"

# Extract/re-extract EXIF data
curl -X POST "http://localhost:8000/api/v1/media/exif/extract/media-uuid-here" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "privacy_mode=false"

# Extract EXIF with privacy mode (removes GPS and sensitive data)
curl -X POST "http://localhost:8000/api/v1/media/exif/extract/media-uuid-here" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "privacy_mode=true"
```

**EXIF Response Example:**
```json
{
  "media_id": "media-uuid-here",
  "exif_data": {
    "camera": {
      "make": "Canon",
      "model": "EOS R5",
      "lens_model": "RF24-70mm F2.8 L IS USM"
    },
    "settings": {
      "iso": 100,
      "aperture": "f/2.8",
      "shutter_speed": "1/60",
      "focal_length": "35mm"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "gps": {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "altitude": 15.2
    }
  },
  "privacy_mode": false,
  "extraction_timestamp": "2024-01-15T12:00:00Z"
}
```

#### 4.3.2 Bulk EXIF Processing

Process multiple files at once:

```bash
# Bulk extract EXIF for user's images
curl -X POST "http://localhost:8000/api/v1/media/exif/bulk-extract" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "privacy_mode=false" \
  -d "media_type_filter=picture" \
  -d "limit=100"
```

**Bulk Processing Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "privacy_mode": false,
  "bulk_extraction_summary": {
    "processed": 50,
    "extracted": 42,
    "skipped": 5,
    "errors": 3,
    "details": [
      {
        "media_id": "media-uuid-1",
        "status": "extracted",
        "exif_summary": {
          "camera": "Canon EOS R5",
          "has_gps": true,
          "timestamp": "2024-01-15T10:30:00Z"
        }
      }
    ]
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### 4.4 Collections Management

#### 4.4.1 Create and Manage Collections

Organize media into collections:

```bash
# Create a new collection
curl -X POST "http://localhost:8000/api/v1/media/collections" \
  -F "name=Vacation Photos 2024" \
  -F "description=Photos from our summer vacation" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "is_public=false"

# Add media to collection
curl -X POST "http://localhost:8000/api/v1/media/collections/collection-uuid/add/media-uuid" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000"
```

**Collection Response:**
```json
{
  "id": "collection-uuid-here",
  "name": "Vacation Photos 2024",
  "description": "Photos from our summer vacation",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "is_public": false,
  "created_at": "2024-01-15T10:30:00Z",
  "media_count": 0,
  "cover_image_url": null
}
```

### 4.5 Media Sharing

#### 4.5.1 Create Share Links

Generate secure share links for media:

```bash
# Create basic share link
curl -X POST "http://localhost:8000/api/v1/media/share/media-uuid-here" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "can_download=false"

# Create share link with download permission and expiration
curl -X POST "http://localhost:8000/api/v1/media/share/media-uuid-here" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "can_download=true" \
  -d "expires_hours=72"
```

**Share Response:**
```json
{
  "id": "share-uuid-here",
  "media_id": "media-uuid-here",
  "share_token": "abc123def456ghi789",
  "can_download": true,
  "expires_at": "2024-01-18T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z",
  "public_url": "http://localhost:8000/api/v1/media/download/media-uuid-here?share_token=abc123def456ghi789"
}
```

### 4.6 User Analytics and Statistics

#### 4.6.1 Media Statistics

Get comprehensive user media statistics:

```bash
# Get user media stats
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/stats"

# Get grouped media by device
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/grouped?group_by=device_name"

# Group by media type
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/grouped?group_by=media_type"

# Group by month
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/grouped?group_by=month"
```

**Statistics Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_media": 1250,
  "total_storage_bytes": 5368709120,
  "storage_by_type": {
    "PICTURE": 3221225472,
    "VIDEO": 2147483648
  },
  "device_breakdown": {
    "iPhone 15 Pro": 800,
    "Canon EOS R5": 300,
    "GoPro Hero 12": 150
  },
  "monthly_uploads": {
    "2024-01": 120,
    "2024-02": 95,
    "2024-03": 180
  },
  "top_tags": [
    {"tag": "vacation", "count": 45},
    {"tag": "family", "count": 38},
    {"tag": "work", "count": 22}
  ]
}
```

### 4.7 Cloud Storage Integration

#### 4.7.1 Cloud Storage Operations

The media service integrates with multiple cloud storage providers:

```bash
# Upload to cloud storage
curl -X POST "http://localhost:8000/api/v1/cloud-storage/upload" \
  -F "file=@large_video.mp4" \
  -F "file_key=user123/videos/vacation_2024.mp4" \
  -F "public_read=false" \
  -F "provider=s3"

# Download from cloud storage
curl "http://localhost:8000/api/v1/cloud-storage/download/user123/videos/vacation_2024.mp4?provider=s3" \
  -o downloaded_video.mp4

# Get file metadata
curl "http://localhost:8000/api/v1/cloud-storage/metadata/user123/videos/vacation_2024.mp4?provider=s3"

# List files with prefix
curl "http://localhost:8000/api/v1/cloud-storage/list?prefix=user123/photos/&limit=50&provider=s3"

# Generate presigned URL for direct upload
curl "http://localhost:8000/api/v1/cloud-storage/presigned-url/user123/upload/new_file.jpg" \
  -G \
  -d "expiration=3600" \
  -d "operation=put" \
  -d "provider=s3"

# Delete from cloud storage
curl -X DELETE "http://localhost:8000/api/v1/cloud-storage/delete/user123/videos/old_video.mp4?provider=s3"
```

#### 4.7.2 Cloud Storage Statistics

Monitor cloud storage usage:

```bash
# Get storage statistics for all providers
curl "http://localhost:8000/api/v1/cloud-storage/stats"

# Check cloud storage health
curl "http://localhost:8000/api/v1/cloud-storage/health"
```

**Cloud Storage Stats Response:**
```json
{
  "s3": {
    "provider": "s3",
    "bucket": "ppl-meta-media",
    "file_count": 15000,
    "total_size_bytes": 107374182400,
    "status": "healthy"
  },
  "azure": {
    "provider": "azure",
    "bucket": "ppl-meta-backup",
    "file_count": 12000,
    "total_size_bytes": 85899345920,
    "status": "healthy"
  }
}
```

### 4.8 Security and Validation

#### 4.8.1 Rate Limiting and Security

The media service includes comprehensive security features:

```bash
# Check rate limit status
curl "http://localhost:8000/api/v1/security/rate-limit/client123"

# Validate file before upload
curl -X POST "http://localhost:8000/api/v1/security/validate-file" \
  -F "file=@suspicious_file.jpg"

# Security scan results
curl "http://localhost:8000/api/v1/security/scan-results/media-uuid-here"
```

**Security Features:**

- **File Validation:** MIME type checking, file signature validation
- **Malware Scanning:** Automated security scanning for uploaded files
- **Rate Limiting:** Per-client request rate limiting
- **Access Control:** User-based and token-based access control
- **Content Security:** File size limits, allowed file types

### 4.9 Health Monitoring and Diagnostics

#### 4.9.1 Service Health Checks

Monitor media service health and performance:

```bash
# Basic health check
curl "http://localhost:8000/health"

# Detailed health with system metrics
curl "http://localhost:8000/health/detailed"

# Kubernetes readiness probe
curl "http://localhost:8000/health/ready"

# Kubernetes liveness probe
curl "http://localhost:8000/health/live"
```

**Health Response:**
```json
{
  "status": "healthy",
  "timestamp": 1705320000.123,
  "service": "ppl-meta-media",
  "database": "healthy",
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 68.2,
    "disk_percent": 45.8
  },
  "storage": {
    "local_storage": "healthy",
    "cloud_storage": {
      "s3": true,
      "azure": true,
      "gcp": false
    }
  }
}
```

### 4.10 Integration Examples

#### 4.10.1 Complete Media Workflow

Example workflow for uploading, processing, and sharing media:

```bash
# Step 1: Upload media with device info
MEDIA_ID=$(curl -X POST "http://localhost:8000/api/v1/media/upload" \
  -F "file=@photo.jpg" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "device_name=iPhone 15 Pro" \
  -F "tags=vacation,beach" | jq -r '.id')

# Step 2: Extract EXIF data
curl -X POST "http://localhost:8000/api/v1/media/exif/extract/$MEDIA_ID" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "privacy_mode=false"

# Step 3: Create collection and add media
COLLECTION_ID=$(curl -X POST "http://localhost:8000/api/v1/media/collections" \
  -F "name=Beach Vacation" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" | jq -r '.id')

curl -X POST "http://localhost:8000/api/v1/media/collections/$COLLECTION_ID/add/$MEDIA_ID" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000"

# Step 4: Create share link
SHARE_TOKEN=$(curl -X POST "http://localhost:8000/api/v1/media/share/$MEDIA_ID" \
  -d "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -d "can_download=true" \
  -d "expires_hours=168" | jq -r '.share_token')

# Step 5: Access shared media
curl "http://localhost:8000/api/v1/media/download/$MEDIA_ID?share_token=$SHARE_TOKEN" \
  -o shared_photo.jpg
```

#### 4.10.2 Media Analytics Dashboard Data

Fetch data for building media analytics dashboards:

```bash
# Get comprehensive user statistics
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/stats"

# Get device usage breakdown
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/grouped?group_by=device_name"

# Get monthly upload trends
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/grouped?group_by=month"

# Get storage usage by type
curl "http://localhost:8000/api/v1/media/user/123e4567-e89b-12d3-a456-426614174000/grouped?group_by=media_type"

# Check cloud storage statistics
curl "http://localhost:8000/api/v1/cloud-storage/stats"
```

### 4.11 Advanced Features

#### 4.11.1 Video Processing

Advanced video handling capabilities:

- **Streaming Support:** HTTP range requests for efficient video streaming
- **Video Thumbnails:** Extract thumbnails from any timestamp
- **Multiple Formats:** Support for MP4, MOV, AVI, and other formats
- **Metadata Extraction:** Duration, resolution, codec information

#### 4.11.2 Image Processing

Comprehensive image processing features:

- **Multiple Formats:** JPEG, PNG, TIFF, RAW formats support
- **EXIF Preservation:** Optional EXIF data preservation or removal
- **Thumbnail Generation:** Multiple sizes with caching
- **Color Profile Support:** ICC color profile handling

#### 4.11.3 Device Intelligence

Smart device-aware features:

- **Device Fingerprinting:** Automatic device identification
- **Storage Optimization:** Device-specific compression settings
- **Upload Optimization:** Network-aware upload strategies
- **Sync Intelligence:** Smart synchronization between devices

The PPL Meta Media Service provides a comprehensive solution for modern media management with enterprise-grade security, performance, and scalability features.
