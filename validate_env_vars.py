#!/usr/bin/env python3
"""
PPL Meta Platform - Environment Variable Validation and Documentation
This script validates and documents environment variables across all services.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set


# Standardized environment variables across all services
STANDARD_ENV_VARS = {
    # Application Settings (Required for all services)
    "APP_NAME": {
        "required": True,
        "default": None,
        "description": "Application name",
        "services": ["all"]
    },
    "APP_VERSION": {
        "required": True,
        "default": None,
        "description": "Application version",
        "services": ["all"]
    },
    "ENVIRONMENT": {
        "required": False,
        "default": "development",
        "description": "Deployment environment (development/staging/production)",
        "services": ["all"]
    },
    "DEBUG": {
        "required": False,
        "default": "false",
        "description": "Enable debug mode",
        "services": ["all"]
    },
    "LOG_LEVEL": {
        "required": False,
        "default": "info",
        "description": "Logging level (debug/info/warning/error)",
        "services": ["all"]
    },
    "HOST": {
        "required": False,
        "default": "0.0.0.0",
        "description": "Service bind address",
        "services": ["all"]
    },
    "PORT": {
        "required": False,
        "default": None,
        "description": "Service port (service-specific defaults)",
        "services": ["all"]
    },
    
    # Database Configuration (Required for data services)
    "DATABASE_URL": {
        "required": True,
        "default": None,
        "description": "PostgreSQL connection string",
        "services": ["ppl-meta-node", "ppl-meta-media", "ppl-meta-orchestrator"]
    },
    "DB_HOST": {
        "required": False,
        "default": "localhost",
        "description": "Database host",
        "services": ["ppl-meta-media", "ppl-meta-orchestrator"]
    },
    "DB_PORT": {
        "required": False,
        "default": "5432",
        "description": "Database port",
        "services": ["ppl-meta-media", "ppl-meta-orchestrator"]
    },
    "DB_NAME": {
        "required": False,
        "default": None,
        "description": "Database name (service-specific)",
        "services": ["ppl-meta-media", "ppl-meta-orchestrator"]
    },
    "DB_USER": {
        "required": False,
        "default": "postgres",
        "description": "Database username",
        "services": ["ppl-meta-media", "ppl-meta-orchestrator"]
    },
    "DB_PASSWORD": {
        "required": False,
        "default": "postgres",
        "description": "Database password",
        "services": ["ppl-meta-media", "ppl-meta-orchestrator"]
    },
    
    # Security Configuration (Required for all services)
    "SECRET_KEY": {
        "required": True,
        "default": None,
        "description": "JWT signing key and general encryption secret",
        "services": ["all"]
    },
    "JWT_SECRET": {
        "required": False,
        "default": None,
        "description": "Additional JWT secret",
        "services": ["all"]
    },
    "JWT_ALGORITHM": {
        "required": False,
        "default": "HS256",
        "description": "JWT signing algorithm",
        "services": ["ppl-meta-node", "ppl-meta-orchestrator"]
    },
    "ACCESS_TOKEN_EXPIRE_MINUTES": {
        "required": False,
        "default": "30",
        "description": "JWT token expiration time in minutes",
        "services": ["ppl-meta-node", "ppl-meta-gateway", "ppl-meta-orchestrator"]
    },
    "RESET_PASSWORD_SECRET": {
        "required": False,
        "default": None,
        "description": "Secret for password reset tokens",
        "services": ["ppl-meta-node"]
    },
    
    # Mail Configuration (Optional, standardized across services)
    "MAIL_USERNAME": {
        "required": False,
        "default": "",
        "description": "SMTP username",
        "services": ["all"]
    },
    "MAIL_PASSWORD": {
        "required": False,
        "default": "",
        "description": "SMTP password",
        "services": ["all"]
    },
    "MAIL_FROM": {
        "required": False,
        "default": "",
        "description": "Email sender address",
        "services": ["all"]
    },
    "MAIL_SERVER": {
        "required": False,
        "default": "",
        "description": "SMTP server hostname",
        "services": ["all"]
    },
    "MAIL_PORT": {
        "required": False,
        "default": "587",
        "description": "SMTP server port",
        "services": ["all"]
    },
    "MAIL_FROM_NAME": {
        "required": False,
        "default": None,
        "description": "Email sender display name (service-specific)",
        "services": ["all"]
    },
    "MAIL_STARTTLS": {
        "required": False,
        "default": "true",
        "description": "Enable SMTP STARTTLS",
        "services": ["all"]
    },
    "MAIL_SSL_TLS": {
        "required": False,
        "default": "false",
        "description": "Enable SMTP SSL/TLS",
        "services": ["all"]
    },
    "USE_CREDENTIALS": {
        "required": False,
        "default": "true",
        "description": "Use SMTP credentials",
        "services": ["all"]
    },
    "VALIDATE_CERTS": {
        "required": False,
        "default": "true",
        "description": "Validate SMTP certificates",
        "services": ["all"]
    },
    
    # Service Communication URLs
    "USER_SERVICE_URL": {
        "required": False,
        "default": "http://localhost:8001",
        "description": "User management service URL",
        "services": ["ppl-meta-gateway", "ppl-meta-media", "ppl-meta-orchestrator"]
    },
    "MEDIA_SERVICE_URL": {
        "required": False,
        "default": "http://localhost:8000",
        "description": "Media processing service URL",
        "services": ["ppl-meta-gateway", "ppl-meta-node", "ppl-meta-orchestrator"]
    },
    "GATEWAY_SERVICE_URL": {
        "required": False,
        "default": "http://localhost:8080",
        "description": "Gateway service URL",
        "services": ["ppl-meta-node", "ppl-meta-media", "ppl-meta-orchestrator"]
    },
    
    # Redis Configuration
    "REDIS_URL": {
        "required": False,
        "default": "redis://localhost:6379/0",
        "description": "Redis connection string",
        "services": ["ppl-meta-gateway", "ppl-meta-media", "ppl-meta-node", "ppl-meta-orchestrator"]
    },
}

# Service-specific defaults
SERVICE_DEFAULTS = {
    "ppl-meta-gateway": {
        "PORT": "8080",
        "MAIL_FROM_NAME": "PPL Meta Gateway"
    },
    "ppl-meta-node": {
        "PORT": "8001",
        "MAIL_FROM_NAME": "PPL Meta Node"
    },
    "ppl-meta-media": {
        "PORT": "8000",
        "MAIL_FROM_NAME": "PPL Meta Media"
    },
    "ppl-meta-orchestrator": {
        "PORT": "8002",
        "MAIL_FROM_NAME": "PPL Meta Orchestrator"
    }
}


def get_workspace_root() -> Path:
    """Get the workspace root directory."""
    current = Path(__file__).parent
    while current.parent != current:
        if (current / "docker-compose.ecosystem.yml").exists():
            return current
        current = current.parent
    return Path.cwd()


def get_services() -> List[str]:
    """Get list of all services in the workspace."""
    root = get_workspace_root()
    services = []
    for item in root.iterdir():
        if item.is_dir() and item.name.startswith("ppl-meta-"):
            services.append(item.name)
    return sorted(services)


def validate_service_env_file(service: str, env_file: Path) -> Dict[str, List[str]]:
    """Validate environment file for a service."""
    issues = {
        "missing_required": [],
        "missing_optional": [],
        "deprecated": [],
        "inconsistent": []
    }
    
    if not env_file.exists():
        issues["missing_required"].append(f"No .env.example file found for {service}")
        return issues
    
    # Read existing env vars
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    # Check for required variables
    for var_name, var_config in STANDARD_ENV_VARS.items():
        if "all" in var_config["services"] or service in var_config["services"]:
            if var_config["required"] and var_name not in env_vars:
                issues["missing_required"].append(var_name)
            elif not var_config["required"] and var_name not in env_vars:
                issues["missing_optional"].append(var_name)
    
    return issues


def generate_env_template(service: str) -> str:
    """Generate standardized environment template for a service."""
    template_lines = [
        f"# {service.replace('-', ' ').title()} - Environment Configuration",
        "",
        "# Application Settings"
    ]
    
    # Group variables by category
    categories = {
        "Application Settings": [
            "APP_NAME", "APP_VERSION", "ENVIRONMENT", "DEBUG", "LOG_LEVEL", "HOST", "PORT"
        ],
        "Database Configuration": [
            "DATABASE_URL", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"
        ],
        "Security Settings": [
            "SECRET_KEY", "JWT_SECRET", "JWT_ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES", "RESET_PASSWORD_SECRET"
        ],
        "Mail Configuration": [
            "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM", "MAIL_SERVER", "MAIL_PORT", 
            "MAIL_FROM_NAME", "MAIL_STARTTLS", "MAIL_SSL_TLS", "USE_CREDENTIALS", "VALIDATE_CERTS"
        ],
        "Service URLs": [
            "USER_SERVICE_URL", "MEDIA_SERVICE_URL", "GATEWAY_SERVICE_URL"
        ],
        "Redis Configuration": [
            "REDIS_URL"
        ]
    }
    
    for category, vars_in_category in categories.items():
        applicable_vars = []
        for var_name in vars_in_category:
            if var_name in STANDARD_ENV_VARS:
                var_config = STANDARD_ENV_VARS[var_name]
                if "all" in var_config["services"] or service in var_config["services"]:
                    applicable_vars.append(var_name)
        
        if applicable_vars:
            template_lines.extend(["", f"# {category}"])
            for var_name in applicable_vars:
                var_config = STANDARD_ENV_VARS[var_name]
                default_value = SERVICE_DEFAULTS.get(service, {}).get(var_name, var_config["default"])
                if default_value is None:
                    default_value = f"your-{var_name.lower().replace('_', '-')}-here"
                
                comment = f"# {var_config['description']}"
                if var_config["required"]:
                    comment += " (REQUIRED)"
                
                template_lines.append(comment)
                template_lines.append(f"{var_name}={default_value}")
    
    return "\n".join(template_lines)


def main():
    """Main validation and documentation function."""
    workspace_root = get_workspace_root()
    services = get_services()
    
    print("🔍 PPL Meta Platform - Environment Variable Validation")
    print("=" * 60)
    print(f"Workspace: {workspace_root}")
    print(f"Services found: {', '.join(services)}")
    print()
    
    all_issues = {}
    
    for service in services:
        service_dir = workspace_root / service
        env_file = service_dir / ".env.example"
        
        print(f"📋 Validating {service}...")
        issues = validate_service_env_file(service, env_file)
        all_issues[service] = issues
        
        # Report issues
        if any(issues.values()):
            if issues["missing_required"]:
                print(f"  ❌ Missing required variables: {', '.join(issues['missing_required'])}")
            if issues["missing_optional"]:
                print(f"  ⚠️  Missing optional variables: {', '.join(issues['missing_optional'])}")
        else:
            print(f"  ✅ All environment variables properly configured")
    
    print()
    print("📝 Environment Variable Summary")
    print("-" * 40)
    
    # Show standardized variables
    required_vars = [k for k, v in STANDARD_ENV_VARS.items() if v["required"]]
    optional_vars = [k for k, v in STANDARD_ENV_VARS.items() if not v["required"]]
    
    print(f"Required variables: {len(required_vars)}")
    for var in required_vars:
        print(f"  - {var}: {STANDARD_ENV_VARS[var]['description']}")
    
    print(f"\nOptional variables: {len(optional_vars)}")
    for var in optional_vars[:10]:  # Show first 10 to avoid clutter
        print(f"  - {var}: {STANDARD_ENV_VARS[var]['description']}")
    if len(optional_vars) > 10:
        print(f"  ... and {len(optional_vars) - 10} more")
    
    # Generate templates if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--generate-templates":
        print("\n🔧 Generating updated environment templates...")
        for service in services:
            service_dir = workspace_root / service
            env_file = service_dir / ".env.example"
            template_content = generate_env_template(service)
            
            with open(env_file, 'w') as f:
                f.write(template_content)
            print(f"  ✅ Updated {env_file}")
    
    # Summary
    total_issues = sum(len(issues["missing_required"]) + len(issues["missing_optional"]) 
                      for issues in all_issues.values())
    
    print(f"\n📊 Summary: {total_issues} total issues found across {len(services)} services")
    
    if total_issues > 0:
        print("\n💡 To fix issues:")
        print("  1. Review missing variables listed above")
        print("  2. Add missing variables to .env.example files")
        print("  3. Update service configuration classes to include new variables")
        print("  4. Run this script with --generate-templates to auto-generate templates")
        return 1
    else:
        print("\n🎉 All services have consistent environment variable configuration!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
