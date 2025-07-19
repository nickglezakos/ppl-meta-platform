#!/bin/bash
# PPL Meta Platform - Secrets Setup Script
# Resolves ISSUE-015: Hardcoded Secrets in Configuration

set -e

echo "🔐 Setting up secrets management for PPL Meta Platform..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    print_success "Python found ✓"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_warning "Docker not found. Some features will not be available."
    else
        print_success "Docker found ✓"
    fi
}

# Install secrets management dependencies
install_dependencies() {
    print_status "Installing secrets management dependencies..."
    
    cd secrets
    
    if [ -f "requirements.txt" ]; then
        # Try to install, handling externally managed environment
        if ! python3 -m pip install -r requirements.txt --break-system-packages 2>/dev/null; then
            print_warning "Could not install dependencies globally. Checking if cryptography is available..."
            if ! python3 -c "import cryptography" 2>/dev/null; then
                print_error "cryptography package not available. Please install it:"
                echo "Option 1: pip install cryptography --break-system-packages"
                echo "Option 2: Use a virtual environment:"
                echo "  python3 -m venv venv"
                echo "  source venv/bin/activate"
                echo "  pip install cryptography"
                exit 1
            else
                print_success "cryptography package is available ✓"
            fi
        else
            print_success "Dependencies installed ✓"
        fi
    else
        print_error "requirements.txt not found in secrets directory"
        exit 1
    fi
    
    cd ..
}

# Set up proper permissions
setup_permissions() {
    print_status "Setting up secure file permissions..."
    
    # Make secrets management script executable
    chmod +x secrets/manage_secrets.py
    
    # Secure secrets directory
    chmod 700 secrets/
    
    # Secure environment files (if they exist)
    for service in ppl-meta-node ppl-meta-media ppl-meta-gateway ppl-meta-orchestrator; do
        if [ -f "$service/.env" ]; then
            chmod 600 "$service/.env"
            print_status "Secured $service/.env"
        fi
    done
    
    print_success "Permissions configured ✓"
}

# Generate development secrets
generate_dev_secrets() {
    print_status "Generating development secrets..."
    
    python3 secrets/manage_secrets.py generate
    
    if [ $? -eq 0 ]; then
        print_success "Development secrets generated ✓"
    else
        print_error "Failed to generate secrets"
        exit 1
    fi
}

# Create environment files
create_env_files() {
    print_status "Creating environment files from secrets..."
    
    python3 secrets/manage_secrets.py create-env
    
    if [ $? -eq 0 ]; then
        print_success "Environment files created ✓"
        print_warning "Remember to configure external services (mail, etc.) in .env files"
    else
        print_error "Failed to create environment files"
        exit 1
    fi
}

# Set up Docker secrets (optional)
setup_docker_secrets() {
    if command -v docker &> /dev/null; then
        read -p "Do you want to set up Docker secrets for production deployment? (y/N): " setup_docker
        
        if [[ $setup_docker =~ ^[Yy]$ ]]; then
            print_status "Setting up Docker secrets..."
            
            # Check if Docker daemon is running
            if ! docker info >/dev/null 2>&1; then
                print_error "Docker daemon is not running"
                return 1
            fi
            
            python3 secrets/manage_secrets.py create-docker
            
            if [ $? -eq 0 ]; then
                print_success "Docker secrets created ✓"
                print_status "You can now deploy with: docker-compose -f docker-compose.secrets.yml up -d"
            else
                print_warning "Docker secrets setup failed (this is optional for development)"
            fi
        fi
    fi
}

# Update .gitignore to exclude secrets
update_gitignore() {
    print_status "Updating .gitignore to exclude secrets..."
    
    # Create .gitignore if it doesn't exist
    if [ ! -f ".gitignore" ]; then
        touch .gitignore
    fi
    
    # Add secrets exclusions if not already present
    grep -q "# Secrets and Environment Files" .gitignore || cat >> .gitignore << 'EOF'

# Secrets and Environment Files
.env
.env.local
.env.production
.env.staging
secrets/*.json
secrets/*.key
secrets/*.vault
*.secret

# Service-specific environment files
ppl-meta-*/.env
ppl-meta-*/secrets/
EOF

    print_success ".gitignore updated ✓"
}

# Main setup function
main() {
    echo
    echo "╔══════════════════════════════════════╗"
    echo "║     PPL Meta Secrets Management      ║"
    echo "║                                      ║"
    echo "║  🔐 Secure Configuration Setup       ║"
    echo "╚══════════════════════════════════════╝"
    echo
    
    check_prerequisites
    echo
    
    install_dependencies
    echo
    
    setup_permissions
    echo
    
    generate_dev_secrets
    echo
    
    create_env_files
    echo
    
    setup_docker_secrets
    echo
    
    update_gitignore
    echo
    
    print_success "🎉 Secrets management setup complete!"
    echo
    echo "📋 What was configured:"
    echo "   ✅ Cryptographically secure secrets generated"
    echo "   ✅ Environment files created with proper secrets"
    echo "   ✅ File permissions secured"
    echo "   ✅ .gitignore updated to exclude secrets"
    echo "   ✅ Docker secrets configured (if selected)"
    echo
    echo "📖 Next Steps:"
    echo "   1. Review and update .env files for external services (mail, etc.)"
    echo "   2. For production: Use external key management (Vault, AWS, etc.)"
    echo "   3. Start services: docker-compose -f docker-compose.minimal.yml up -d"
    echo "   4. Or with secrets: docker-compose -f docker-compose.secrets.yml up -d"
    echo
    echo "📚 Documentation:"
    echo "   - SECRETS_MANAGEMENT_GUIDE.md - Complete secrets management guide"
    echo "   - secrets/manage_secrets.py --help - Command-line help"
    echo
    echo "🔒 Security reminders:"
    echo "   - Never commit .env files to version control"
    echo "   - Rotate secrets regularly (monthly for dev, quarterly for prod)"
    echo "   - Use external key management for production"
    echo "   - Monitor secret access and usage"
    echo
}

# Run main function
main "$@"
