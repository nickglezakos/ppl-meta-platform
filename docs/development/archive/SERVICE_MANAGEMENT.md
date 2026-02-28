# PPL Meta Platform - Service Management Guide

## 🚀 Quick Start - Service Management

### VS Code Tasks (Ctrl+Shift+P → "Tasks: Run Task")

| Task | Description | Usage |
|------|-------------|-------|
| 🚀 **Start All Local Python Services** | Starts all 7 PPL Meta services in background | For full platform development |
| 🛑 **Stop All Local Python Services** | Stops all running Python services | Clean shutdown |
| 🔄 **Restart All Local Python Services** | Restart all services (stop + start) | Apply configuration changes |
| 📊 **Check All Services Status** | Health check on ports 8000-8006 | Verify services are running |
| 🌐 **Start Nginx** | Start Nginx reverse proxy | Load balancing/routing |
| 🛑 **Stop Nginx** | Stop Nginx server | Clean shutdown |

### Command Line Usage

```bash
# Start all services
./manage-services.sh start

# Check what's running
./manage-services.sh status

# Stop all services
./manage-services.sh stop

# Restart all services
./manage-services.sh restart

# Nginx management
./manage-services.sh nginx-start
./manage-services.sh nginx-stop
```

### Service Architecture

```text
🏠 PPL Meta Platform Services
├── 👥 User Management     → localhost:8001  (Authentication, users, roles)
├── 🎬 Media Processing    → localhost:8002  (Video/image processing)
├── 🚪 API Gateway         → localhost:8000  (Request routing, load balancing)
├── 🎭 Orchestrator        → localhost:8003  (Service coordination)
├── 📹 Camera Service      → localhost:8004  (Camera management, streaming)
├── 👁️ Vision Service      → localhost:8005  (AI/ML computer vision)
└── 🔍 Discovery Service   → localhost:8006  (Device/service discovery)
```

### Service Features

#### 🚀 **Start All Services**

- Runs all services in background with logging
- Creates PID files for process tracking
- Uses virtual environments automatically
- Logs saved to `logs/[service-name].log`

#### 📊 **Status Monitoring**

- Health checks via `/health` endpoints
- Color-coded status indicators
- Port availability checking
- Service response validation

#### 🛑 **Clean Shutdown**

- Graceful process termination
- PID file cleanup
- Process pattern matching fallback
- No orphaned processes

### Development Workflow

1. **Start Platform**: `🚀 Start All Local Python Services`
2. **Develop**: Make changes to individual services
3. **Test**: `📊 Check All Services Status`
4. **Debug**: Check individual service logs in `logs/` directory
5. **Restart**: `🔄 Restart All Local Python Services` (if needed)
6. **Shutdown**: `🛑 Stop All Local Python Services`

### Nginx Integration

- **Purpose**: Reverse proxy, load balancing, SSL termination
- **Configuration**: Check `nginx/` directory for configs
- **Start**: `🌐 Start Nginx` (requires sudo password)
- **Stop**: `🛑 Stop Nginx`

### Troubleshooting

#### Services Won't Start

- Check if ports are already in use: `lsof -i :8000-8006`
- Verify virtual environments: `ls */venv/`
- Check service logs: `tail -f logs/[service-name].log`

#### Health Checks Fail

- Ensure service has `/health` endpoint
- Check firewall settings
- Verify service is listening on correct port

#### Permission Issues with Nginx

- Ensure user has sudo privileges
- Check nginx installation: `which nginx`
- Install if missing: `brew install nginx`

---

**💡 Tip**: Use VS Code's integrated terminal with these tasks for the best development experience!