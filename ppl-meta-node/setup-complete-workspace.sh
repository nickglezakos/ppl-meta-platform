#!/bin/bash
# PPL Meta Platform - Complete Setup
# One command to set up the entire unified workspace

set -e

echo "🚀 PPL Meta Platform - Complete Unified Workspace Setup"
echo "======================================================"
echo ""
echo "This will create a unified workspace for your entire PPL Meta Platform"
echo "with all microservices, infrastructure, and shared components."
echo ""

# Confirm with user
read -p "Do you want to proceed? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

echo ""
echo "🏗️  Creating unified workspace structure..."

# Run the migration
./migrate-to-unified-workspace.sh

# Move to the new workspace
cd ../ppl-meta-code

echo ""
echo "🔧 Setting up development environment..."

# Make setup script executable and run it
chmod +x tools/dev/setup-workspace.sh
./tools/dev/setup-workspace.sh

echo ""
echo "🎉 PPL Meta Platform Unified Workspace Complete!"
echo ""
echo "📁 Workspace Structure:"
echo "   ppl-meta-code/                 # Your unified workspace"
echo "   ├── services/                  # All microservices"
echo "   │   ├── gateway/               # API Gateway"
echo "   │   ├── user-management/       # User Management (migrated)"
echo "   │   ├── media/                 # Media Service"
echo "   │   ├── orchestrator/          # Orchestrator Service"
echo "   │   └── vision/                # Vision Service"
echo "   ├── infrastructure/            # All infrastructure"
echo "   ├── shared/                    # Shared libraries"
echo "   ├── docs/                      # Documentation"
echo "   ├── tools/                     # Development tools"
echo "   └── docker-compose.yml         # Main orchestration"
echo ""
echo "🚀 Quick Start Commands:"
echo "   cd ppl-meta-code"
echo "   docker-compose up -d           # Start entire platform"
echo "   docker-compose logs -f         # View logs"
echo "   docker-compose down            # Stop platform"
echo ""
echo "🌐 Service URLs:"
echo "   Main Platform:     https://localhost"
echo "   API Gateway:       http://localhost:8080"
echo "   User Management:   http://localhost:8001"
echo "   Media Service:     http://localhost:8000"
echo "   Orchestrator:      http://localhost:8002"
echo "   Monitoring:        http://localhost:3000"
echo "   Service Discovery: http://localhost:8500"
echo ""
echo "✅ Benefits of this unified workspace:"
echo "   • Single repository for entire platform"
echo "   • Shared code and configurations"
echo "   • Consistent development environment"
echo "   • Simplified CI/CD and deployment"
echo "   • Better dependency management"
echo "   • Easier team collaboration"
echo ""
echo "📚 Next Steps:"
echo "   1. Move your other microservices to services/ directory"
echo "   2. Update shared configurations in shared/ directory"
echo "   3. Add new services by copying the template structure"
echo "   4. Customize environments/ for your deployment needs"
echo ""
echo "🆘 Need Help?"
echo "   • Check docs/ directory for detailed documentation"
echo "   • Read UNIFIED_WORKSPACE_STRATEGY.md for architecture details"
echo "   • Use tools/dev/ scripts for common development tasks"
echo ""
