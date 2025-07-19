# VS Code Tasks Enhancement Guide

## Overview

This guide documents the comprehensive VS Code tasks implemented to resolve ISSUE-014. The enhanced task system provides developers with powerful automation tools for managing the PPL Meta Platform development environment.

## Table of Contents

1. [Task Categories](#task-categories)
2. [Usage Instructions](#usage-instructions)
3. [Task Details](#task-details)
4. [Troubleshooting](#troubleshooting)
5. [Customization](#customization)

## Task Categories

### 🐍 Python Local Development Tasks

Start, stop, and monitor microservices running locally in Python (non-Docker) mode for development and debugging.

- **🐍 Start Node Service (Local Python)** - Starts ppl-meta-node locally with virtual environment
- **🎨 Start Media Service (Local Python)** - Starts ppl-meta-media locally with virtual environment  
- **🌐 Start Gateway Service (Local Python)** - Starts ppl-meta-gateway locally with uvicorn
- **🎼 Start Orchestrator Service (Local Python)** - Starts ppl-meta-orchestrator locally with uvicorn
- **🚀 Start All Local Python Services** - Starts all services simultaneously in local Python mode
- **🛑 Stop All Local Python Services** - Stops all local Python services
- **🏥 Local Python Health Check - All Services** - Comprehensive health check for local Python services
- **🔍 Show Local Python Services Status** - Shows running local Python service processes
- **🏥 Node Service Health Check (Local)** - Individual health check for Node service
- **🏥 Media Service Health Check (Local)** - Individual health check for Media service
- **🏥 Gateway Service Health Check (Local)** - Individual health check for Gateway service
- **🏥 Orchestrator Service Health Check (Local)** - Individual health check for Orchestrator service

### 🌐 Nginx Proxy Tasks (Local Development)

Use nginx as a reverse proxy for local development, providing a single entry point and load balancing.

- **🌐 Start Nginx Proxy (Local Dev)** - Starts nginx with local development configuration
- **🌐 Stop Nginx Proxy (Local Dev)** - Stops nginx proxy
- **🌐 Reload Nginx Configuration** - Reloads nginx configuration without stopping
- **🌐 Test Nginx Configuration** - Tests nginx configuration for syntax errors
- **🚀 Start All Services + Nginx (Local Python)** - Starts all services and nginx proxy together
- **🛑 Stop All Services + Nginx (Local Python)** - Stops all services and nginx proxy
- **🏥 Health Check via Nginx Proxy** - Tests all services through nginx proxy (http://localhost)

### 📱 Frontend Development Tasks

Manage the Flutter frontend application for cross-platform development.

- **📱 Install Flutter Dependencies** - Install/update Flutter packages
- **📱 Start Frontend (Web)** - Run Flutter app in Chrome (localhost:3000)
- **📱 Start Frontend (Desktop)** - Run Flutter app on macOS desktop
- **📱 Build Frontend (Web)** - Build Flutter web app for production
- **📱 Build Frontend (Desktop)** - Build Flutter desktop app for production
- **📱 Generate Code (Frontend)** - Generate models and serialization code
- **📱 Watch Code Generation (Frontend)** - Auto-generate code on file changes
- **📱 Test Frontend** - Run Flutter unit tests
- **📱 Clean Frontend** - Clean and reinstall Flutter dependencies
- **📱 Check Flutter Doctor** - Check Flutter installation and configuration
- **🚀 Start Full Stack (Backend + Frontend)** - Start all backend services and frontend together

### 🏗️ Docker Build Tasks

Build Docker images for individual services or all services at once.

- **🏗️ Build All Docker Images** - Builds all service images using docker-compose
- **🏗️ Build Gateway Image** - Builds only the ppl-meta-gateway image
- **🏗️ Build Node Image** - Builds only the ppl-meta-node image
- **🏗️ Build Media Image** - Builds only the ppl-meta-media image
- **🏗️ Build Orchestrator Image** - Builds only the ppl-meta-orchestrator image

### 🚀 Service Management Tasks

Start, stop, and restart services with combined operations.

- **🚀 Start All Services** - Starts all services using docker-compose (auto-builds first)
- **🛑 Stop All Services** - Stops all running services
- **🔄 Restart All Services** - Restarts all services
- **Start Infrastructure** - Starts the full ecosystem infrastructure
- **Stop Infrastructure** - Stops the ecosystem infrastructure

### 🏥 Health Check Tasks

Monitor service health and availability.

- **🏥 Health Check - All Services** - Checks health of all services simultaneously
- **🏥 Health Check - Gateway** - Checks gateway service health
- **🏥 Health Check - Node Service** - Checks node service health
- **🏥 Health Check - Media Service** - Checks media service health
- **🏥 Health Check - Orchestrator** - Checks orchestrator service health

### 📋 Log Viewing Tasks

View logs for individual services or all services.

- **📋 View Logs - All Services** - Shows logs from all services in real-time
- **📋 View Logs - Gateway** - Shows only gateway service logs
- **📋 View Logs - Node Service** - Shows only node service logs
- **📋 View Logs - Media Service** - Shows only media service logs
- **📋 View Logs - Database** - Shows database logs

### 📊 Monitoring & Status Tasks

Monitor system status and metrics.

- **📊 Docker Status** - Shows status of all Docker containers
- **📈 Service Metrics - All** - Runs comprehensive metrics validation
- **📦 Show Docker Images** - Lists all PPL Meta Platform Docker images
- **🔍 Service Discovery Status** - Shows Consul cluster status

### 🧪 Testing & Validation Tasks

Run tests and validate system functionality.

- **🧪 Run Tests - All Services** - Executes test suites for all services
- **Setup Development Environment** - Runs the development environment setup script

### 🧹 Maintenance Tasks

Clean up Docker resources and maintain system health.

- **🧹 Clean Docker Resources** - Removes unused Docker resources
- **📦 Show Docker Images** - Lists Docker images for inspection

### Individual Service Tasks

Start services individually for development.

- **Start User Management Service** - Starts ppl-meta-node in development mode
- **Start Media Service** - Starts ppl-meta-media in development mode
- **Start Gateway Service** - Starts ppl-meta-gateway in development mode
- **Start Orchestrator Service** - Starts ppl-meta-orchestrator in development mode

## Usage Instructions

### Method 1: VS Code Command Palette

1. Open VS Code in the PPL Meta Platform workspace
2. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
3. Type "Tasks: Run Task"
4. Select the desired task from the list
5. The task will execute in a VS Code terminal

### Method 2: VS Code Terminal Menu

1. Open the Terminal menu in VS Code
2. Select "Run Task..."
3. Choose from the available tasks
4. The task will execute in the integrated terminal

### Method 3: Keyboard Shortcuts

You can assign keyboard shortcuts to frequently used tasks:

1. Open VS Code Settings (Ctrl+,)
2. Search for "keyboard shortcuts"
3. Click "Open Keyboard Shortcuts (JSON)"
4. Add custom shortcuts:

```json
[
    {
        "key": "ctrl+shift+b",
        "command": "workbench.action.tasks.runTask",
        "args": "🏗️ Build All Docker Images"
    },
    {
        "key": "ctrl+shift+s",
        "command": "workbench.action.tasks.runTask",
        "args": "🚀 Start All Services"
    },
    {
        "key": "ctrl+shift+h",
        "command": "workbench.action.tasks.runTask",
        "args": "🏥 Health Check - All Services"
    }
]
```

## Task Details

### Python Local Development Tasks

#### 🐍 Individual Service Tasks (Local Python)

Start individual services in local Python development mode:

```bash
# Node Service
cd ppl-meta-node && source venv/bin/activate && PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node python src/main.py

# Media Service  
cd ppl-meta-media && source venv/bin/activate && PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media python src/main.py

# Gateway Service
cd ppl-meta-gateway/src && source ../venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Orchestrator Service
cd ppl-meta-orchestrator/src && source ../venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

- Activates the service's virtual environment
- Sets proper PYTHONPATH for imports
- Runs services with hot reload for development
- Connects to local PostgreSQL databases
- Uses localhost URLs for inter-service communication

#### 🚀 Start All Local Python Services

```bash
# Starts all services in background processes
echo 'Starting all PPL Meta services in local Python mode...' && \
(start each service in background) & wait
```

- Starts all four microservices simultaneously
- Runs in background mode with proper process management
- Each service runs in its own virtual environment
- Services auto-restart on code changes (gateway and orchestrator)

#### 🛑 Stop All Local Python Services

```bash
pkill -f 'python.*main.py' && pkill -f 'uvicorn.*main:app'
```

- Gracefully stops all local Python services
- Kills processes matching service patterns
- Cleans up background processes

#### 🏥 Local Python Health Checks

```bash
# All Services Health Check
curl -L -s http://localhost:8001/api/v1/health | python3 -m json.tool
curl -L -s http://localhost:8000/health | python3 -m json.tool  
curl -L -s http://localhost:8080/health | python3 -m json.tool
curl -L -s http://localhost:8002/health | python3 -m json.tool
```

- Tests health endpoints for all services
- Formats JSON responses for readability
- Reports individual service status
- Follows redirects automatically

#### 🔍 Show Local Python Services Status

```bash
ps aux | grep 'python.*main.py\|uvicorn.*main:app' | grep -v grep
```

- Lists all running Python service processes
- Shows process IDs and resource usage
- Helps identify which services are running

### Nginx Proxy for Local Development

#### 🌐 Using Nginx as Reverse Proxy

The nginx configuration (`nginx-local-dev.conf`) provides:

```bash
# Single entry point for all services
http://localhost/          # Routes to Gateway (main entry)
http://localhost/api/      # API Gateway routes
http://localhost/api/v1/users/     # Direct to Node Service
http://localhost/api/v1/auth/      # Direct to Node Service  
http://localhost/api/v1/media/     # Direct to Media Service
http://localhost/api/v1/orchestrate/  # Direct to Orchestrator

# Individual health checks
http://localhost/health/node       # Node service health
http://localhost/health/media      # Media service health
http://localhost/health/gateway    # Gateway service health
http://localhost/health/orchestrator  # Orchestrator health
```

**Benefits of using nginx proxy:**
- Single entry point (`http://localhost` instead of multiple ports)
- Load balancing and rate limiting
- CORS handling for frontend development
- Request routing and path rewriting
- Security headers and SSL termination (if configured)
- Centralized logging and monitoring

#### 🚀 Start All Services + Nginx

```bash
# Starts all Python services + nginx proxy
echo 'Starting all services...' && \
(start each service in background) & \
sleep 5 && sudo nginx -c nginx-local-dev.conf
```

- Starts all four microservices in background
- Waits for services to initialize
- Starts nginx proxy with local development configuration
- Provides single entry point at `http://localhost`

#### 🛑 Stop All Services + Nginx

```bash
sudo nginx -s quit && pkill -f 'python.*main.py' && pkill -f 'uvicorn.*main:app'
```

- Gracefully stops nginx proxy
- Stops all Python services
- Cleans up background processes

#### 🌐 Nginx Management Tasks

```bash
# Test configuration
sudo nginx -t -c nginx-local-dev.conf

# Start nginx  
sudo nginx -c nginx-local-dev.conf

# Reload configuration (zero downtime)
sudo nginx -s reload

# Stop nginx
sudo nginx -s quit
```

- Configuration testing before starting
- Graceful configuration reloading
- Proper shutdown procedures

### Docker Build Tasks

#### 🏗️ Build All Docker Images
```bash
docker-compose -f docker-compose.minimal.yml build
```
- Builds all service images simultaneously
- Uses the minimal compose configuration
- Outputs build progress to a new terminal panel

#### Individual Build Tasks
```bash
docker build -t ppl-meta-[service] .
```
- Builds specific service image
- Runs in the service directory
- Uses the service's Dockerfile

### Service Management Tasks

#### 🚀 Start All Services
```bash
docker-compose -f docker-compose.minimal.yml up -d
```
- Automatically builds images if needed (dependsOn: Build All Docker Images)
- Starts services in detached mode
- Uses minimal compose configuration

#### 🛑 Stop All Services
```bash
docker-compose -f docker-compose.minimal.yml down
```
- Gracefully stops all services
- Removes containers but preserves volumes

#### 🔄 Restart All Services
```bash
docker-compose -f docker-compose.minimal.yml restart
```
- Restarts all services without rebuilding

### Health Check Tasks

#### 🏥 Health Check - All Services
```python
# Python script that checks all service endpoints
services = [
    ('Gateway', 'http://localhost:8080/health'),
    ('Node', 'http://localhost:8001/health'),
    ('Media', 'http://localhost:8000/health'),
    ('Orchestrator', 'http://localhost:8002/health')
]
```
- Checks all service health endpoints
- Reports status for each service
- Uses Python requests library

#### Individual Health Checks
```bash
curl -s http://localhost:[port]/health
```
- Direct HTTP health check using curl
- Returns service health status

### Log Viewing Tasks

#### 📋 View Logs - All Services
```bash
docker-compose -f docker-compose.minimal.yml logs -f
```
- Shows logs from all services in real-time
- Uses follow mode (-f) for live updates
- Opens in a new terminal panel

#### Individual Log Tasks
```bash
docker-compose -f docker-compose.minimal.yml logs -f [service-name]
```
- Shows logs for specific service only
- Real-time log following

## Troubleshooting

### Common Issues

#### Python Local Development Issues

**Problem**: Service fails to start with "No module named 'src'" error.
**Solution**:
1. Ensure the virtual environment is activated
2. Set PYTHONPATH correctly for the service
3. Run from the correct directory (src/ for gateway/orchestrator)
4. Check that all dependencies are installed in the virtual environment

**Problem**: Database connection errors in local Python mode.
**Solution**:
1. Ensure PostgreSQL is running locally (`brew services start postgresql`)
2. Verify databases exist: `createdb ppl_db`, `createdb ppl_media_db`, etc.
3. Check `.env` files have correct local database URLs
4. Verify database credentials match your local PostgreSQL setup

**Problem**: Port already in use errors.
**Solution**:
1. Stop existing services: Use `🛑 Stop All Local Python Services` task
2. Check what's using ports: `lsof -i :8000 -i :8001 -i :8080 -i :8002`
3. Kill specific processes if needed: `kill <PID>`

**Problem**: Services start but health checks fail.
**Solution**:
1. Wait for services to fully start (especially on first run)
2. Check service logs in the terminal output
3. Verify services are binding to correct ports
4. Use individual health check tasks to isolate issues

**Problem**: Virtual environment not found.
**Solution**:
1. Create virtual environments: `python -m venv venv` in each service directory
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure virtual environment path is correct in tasks

**Problem**: Import errors for shared modules.
**Solution**:
1. Ensure shared modules are in the correct location
2. Install shared dependencies in each virtual environment
3. Check PYTHONPATH includes the service root directory

#### Task Not Found
**Problem**: "Task not found" error when trying to run a task.
**Solution**: 
1. Ensure you're in the correct workspace
2. Reload the VS Code window (Ctrl+Shift+P → "Developer: Reload Window")
3. Check that the workspace file is properly configured

#### Docker Commands Fail
**Problem**: Docker commands in tasks fail to execute.
**Solution**:
1. Ensure Docker is installed and running
2. Check Docker permissions (add user to docker group on Linux)
3. Verify Docker Compose is installed

#### Health Check Failures
**Problem**: Health check tasks report services as unhealthy.
**Solution**:
1. Ensure services are running (`🚀 Start All Services`)
2. Check service logs (`📋 View Logs - [Service]`)
3. Verify correct ports are exposed
4. Wait for services to fully start before health checking

#### Python Script Errors
**Problem**: Python-based tasks fail with import errors.
**Solution**:
1. Ensure Python is installed and in PATH
2. Install required packages: `pip install requests`
3. Check that scripts have correct paths

### Debug Mode

To debug task execution:

1. Open a task configuration in the workspace file
2. Add `"options": {"shell": {"args": ["-x"]}}` for verbose output
3. Check the terminal output for detailed execution logs

## Customization

### Adding New Tasks

To add new tasks to the workspace:

1. Open `ppl-meta-platform.code-workspace`
2. Add a new task object to the `tasks.tasks` array:

```json
{
    "label": "🆕 Your New Task",
    "type": "shell",
    "command": "your-command",
    "args": ["arg1", "arg2"],
    "group": "build", // or "test"
    "presentation": {
        "reveal": "always",
        "panel": "new"
    }
}
```

### Task Groups

Tasks are organized into groups:
- **build**: Compilation, building, deployment tasks
- **test**: Testing, validation, monitoring tasks

### Presentation Options

Control how tasks display their output:
- `"reveal": "always"` - Always show terminal output
- `"panel": "new"` - Open in new terminal panel
- `"panel": "shared"` - Reuse existing terminal

### Dependencies

Tasks can depend on other tasks:
```json
{
    "label": "Dependent Task",
    "dependsOn": ["🏗️ Build All Docker Images"]
}
```

### Environment Variables

Set environment variables for tasks:
```json
{
    "label": "Task with Env",
    "options": {
        "env": {
            "CUSTOM_VAR": "value"
        }
    }
}
```

## Best Practices

1. **Use Emojis**: Use emojis in task labels for easy identification
2. **Group Related Tasks**: Organize tasks by functionality
3. **Descriptive Names**: Use clear, descriptive task names
4. **Error Handling**: Include error handling in complex tasks
5. **Documentation**: Document custom tasks and their purpose
6. **Dependencies**: Use task dependencies to ensure proper execution order

## Integration with CI/CD

These tasks can be adapted for CI/CD pipelines:

1. Extract command patterns from tasks
2. Create corresponding pipeline scripts
3. Use similar validation and testing approaches
4. Maintain consistency between local and CI environments

## Performance Tips

1. **Parallel Builds**: Use `docker-compose build --parallel` for faster builds
2. **Layer Caching**: Optimize Dockerfiles for better layer caching
3. **Resource Limits**: Set appropriate resource limits for development
4. **Log Rotation**: Implement log rotation for long-running services

## Security Considerations

1. **Secrets Management**: Never include secrets in task configurations
2. **File Permissions**: Ensure proper file permissions on scripts
3. **Network Security**: Use appropriate network configurations for development
4. **Container Security**: Follow Docker security best practices

## Frontend Development Workflows

### Setup Flutter Development Environment

Before using frontend tasks, ensure Flutter is installed:

```bash
# Check if Flutter is installed
flutter --version

# If not installed, run the setup script
./setup-flutter.sh

# Or install manually via Homebrew
brew install --cask flutter
```

### Frontend Development Workflow

1. **Initial Setup**
   - Task: `📱 Install Flutter Dependencies`
   - Installs all required Flutter packages

2. **Code Generation**
   - Task: `📱 Generate Code (Frontend)` (one-time)
   - Task: `📱 Watch Code Generation (Frontend)` (development)
   - Generates models and serialization code

3. **Development**
   - Task: `📱 Start Frontend (Web)` - Web development (recommended)
   - Task: `📱 Start Frontend (Desktop)` - Desktop development
   - Frontend runs on http://localhost:3000

4. **Testing**
   - Task: `📱 Test Frontend`
   - Runs unit and widget tests

5. **Building**
   - Task: `📱 Build Frontend (Web)` - Production web build
   - Task: `📱 Build Frontend (Desktop)` - Production desktop build

### Full Stack Development

For complete local development with frontend and backend:

1. **Start All Services**
   - Task: `🚀 Start Full Stack (Backend + Frontend)`
   - Starts all backend services + frontend web app

2. **Alternative: Individual Control**
   - Task: `🚀 Start All Local Python Services` (backend only)
   - Task: `📱 Start Frontend (Web)` (frontend only)

3. **With Nginx Proxy**
   - Task: `🚀 Start All Services + Nginx (Local Python)`
   - Frontend available at http://localhost/ (port 80)
   - API available at http://localhost/api/

### Frontend-Specific Troubleshooting

1. **Dependencies Issues**
   - Run: `📱 Clean Frontend`
   - This cleans and reinstalls all dependencies

2. **Code Generation Errors**
   - Stop watch task if running
   - Run: `📱 Generate Code (Frontend)`
   - Restart watch task if needed

3. **Flutter Doctor Issues**
   - Run: `📱 Check Flutter Doctor`
   - Follow the recommendations provided

4. **Hot Reload Not Working**
   - Stop and restart the frontend task
   - Ensure you're running in debug mode

---

This enhanced VS Code tasks system resolves ISSUE-014 by providing comprehensive automation for Docker image building, combined start/stop operations, health check verification, and log viewing capabilities. The system is designed to improve developer productivity and streamline the development workflow for the PPL Meta Platform.
