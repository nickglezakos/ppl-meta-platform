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

### Build Tasks

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

---

This enhanced VS Code tasks system resolves ISSUE-014 by providing comprehensive automation for Docker image building, combined start/stop operations, health check verification, and log viewing capabilities. The system is designed to improve developer productivity and streamline the development workflow for the PPL Meta Platform.
