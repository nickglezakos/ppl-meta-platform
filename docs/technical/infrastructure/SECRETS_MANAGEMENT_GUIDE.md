# PPL Meta Platform - Secrets Management Guide

**Resolves: ISSUE-015 - Hardcoded Secrets in Configuration**

This guide provides comprehensive secrets management for the PPL Meta Platform, ensuring that sensitive information like passwords, API keys, and tokens are properly secured and not hardcoded in configuration files.

## 🔒 Security Overview

### Current Security Issues (RESOLVED)
- ❌ Database passwords in plain text → ✅ Encrypted secrets storage
- ❌ Default SECRET_KEY values → ✅ Generated secure secrets
- ❌ SMTP credentials exposure → ✅ External secrets management
- ❌ Hardcoded secrets in Docker Compose → ✅ Docker secrets integration

### Security Improvements Implemented
- ✅ **Cryptographically secure secret generation**
- ✅ **Docker Swarm secrets integration**
- ✅ **Encrypted secrets storage with master password**
- ✅ **Environment variable templates (no hardcoded values)**
- ✅ **Secret rotation capabilities**
- ✅ **External key management support (Vault)**
- ✅ **Secure file permissions and access control**

---

## 🛠️ Secrets Management System

### Components

1. **Secret Manager** (`secrets/manage_secrets.py`)
   - Generate cryptographically secure secrets
   - Manage Docker secrets
   - Encrypt/decrypt secrets files
   - Environment file generation

2. **Docker Secrets** (`docker-compose.secrets.yml`)
   - Production-ready deployment with secrets
   - Secure secret distribution to containers
   - No hardcoded values in compose files

3. **Environment Templates** (`.env.example` files)
   - Template files with placeholder variables
   - Security documentation and best practices
   - No actual secrets committed to version control

---

## 🚀 Getting Started

### Installation

1. **Install dependencies for secrets management:**
   ```bash
   cd secrets
   pip install -r requirements.txt
   ```

2. **Make the script executable:**
   ```bash
   chmod +x manage_secrets.py
   ```

### Basic Usage

1. **Generate secrets for all services:**
   ```bash
   python secrets/manage_secrets.py generate --encrypted
   ```

2. **Create environment files:**
   ```bash
   python secrets/manage_secrets.py create-env
   ```

3. **List managed secrets:**
   ```bash
   python secrets/manage_secrets.py list
   ```

---

## 🔐 Secret Types

### Common Secrets (Shared across services)
- `DATABASE_PASSWORD` - Master database password
- `REDIS_PASSWORD` - Redis authentication password  
- `MAIL_PASSWORD` - SMTP mail server password
- `VAULT_TOKEN` - HashiCorp Vault access token

### Service-Specific Secrets
**ppl-meta-node:**
- `SECRET_KEY` - General encryption key
- `JWT_SECRET` - JWT token signing key
- `RESET_PASSWORD_SECRET` - Password reset token key
- `SERVICE_SECRET` - Inter-service communication key

**ppl-meta-media:**
- `SECRET_KEY` - General encryption key
- `JWT_SECRET` - JWT token signing key

**ppl-meta-gateway:**
- `SECRET_KEY` - General encryption key
- `JWT_SECRET` - JWT token signing key

**ppl-meta-orchestrator:**
- `SECRET_KEY` - General encryption key
- `JWT_SECRET` - JWT token signing key

---

## 🐳 Docker Secrets Integration

### Production Deployment

1. **Initialize Docker Swarm:**
   ```bash
   docker swarm init
   ```

2. **Generate and create Docker secrets:**
   ```bash
   python secrets/manage_secrets.py generate
   python secrets/manage_secrets.py create-docker
   ```

3. **Deploy with Docker secrets:**
   ```bash
   docker stack deploy -c docker-compose.secrets.yml ppl-platform
   ```

### Development with Docker Secrets

```bash
# Start services with secrets (requires Swarm mode)
docker-compose -f docker-compose.secrets.yml up -d
```

### Reading Secrets in Services

**Python code example:**
```python
import os

def read_secret(secret_name: str, fallback_env: str = None) -> str:
    """Read secret from Docker secrets or environment variable."""
    secret_file = f"/run/secrets/{secret_name}"
    
    if os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            return f.read().strip()
    
    if fallback_env:
        return os.getenv(fallback_env, "")
    
    raise ValueError(f"Secret {secret_name} not found")

# Usage
SECRET_KEY = read_secret("secret_key", "SECRET_KEY")
DATABASE_PASSWORD = read_secret("database_password", "DATABASE_PASSWORD")
```

---

## 🔄 Secret Rotation

### Automated Rotation

The secrets management system supports rotating secrets without downtime:

```bash
# Rotate secrets for specific service
python secrets/manage_secrets.py rotate --service ppl-meta-node

# Rotate all secrets
python secrets/manage_secrets.py rotate
```

### Manual Rotation Process

1. **Generate new secrets:**
   ```bash
   python secrets/manage_secrets.py generate
   ```

2. **Update Docker secrets:**
   ```bash
   python secrets/manage_secrets.py create-docker
   ```

3. **Rolling update services:**
   ```bash
   docker service update --force ppl-meta-node
   docker service update --force ppl-meta-media
   docker service update --force ppl-meta-gateway
   docker service update --force ppl-meta-orchestrator
   ```

### Rotation Schedule Recommendations

- **Development**: Monthly
- **Staging**: Weekly  
- **Production**: Quarterly (or immediately if compromised)

---

## 🔧 External Key Management

### HashiCorp Vault Integration

1. **Install Vault:**
   ```bash
   # Using Docker
   docker run -d --name vault --cap-add=IPC_LOCK \
     -p 8200:8200 vault:1.13.3
   ```

2. **Configure Vault policy:**
   ```hcl
   # vault/policies/ppl-platform-policy.hcl
   path "secret/data/ppl-platform/*" {
     capabilities = ["read"]
   }
   
   path "database/creds/ppl-platform-role" {
     capabilities = ["read"]
   }
   ```

3. **Store secrets in Vault:**
   ```bash
   vault kv put secret/ppl-platform/common \
     database_password="$(openssl rand -base64 32)" \
     redis_password="$(openssl rand -base64 32)"
   
   vault kv put secret/ppl-platform/ppl-meta-node \
     secret_key="$(openssl rand -base64 32)" \
     jwt_secret="$(openssl rand -base64 64)"
   ```

### AWS Secrets Manager

```python
import boto3

def get_secret_from_aws(secret_name: str, region: str = "us-east-1") -> dict:
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name=region)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        return {}
```

### Azure Key Vault

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_secret_from_azure(vault_url: str, secret_name: str) -> str:
    """Retrieve secret from Azure Key Vault."""
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    
    try:
        secret = client.get_secret(secret_name)
        return secret.value
    except Exception as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        return ""
```

---

## 🛡️ Security Best Practices

### Environment Configuration

1. **Never commit secrets to version control:**
   ```gitignore
   # .gitignore
   .env
   .env.local
   .env.production
   secrets/*.json
   secrets/*.key
   ```

2. **Use restrictive file permissions:**
   ```bash
   chmod 600 .env                    # Only owner can read/write
   chmod 700 secrets/               # Only owner can access directory
   chmod 600 secrets/manage_secrets.py
   ```

3. **Separate development and production secrets:**
   - Development: Use placeholder values or generated test secrets
   - Production: Use external key management (Vault, AWS, Azure)

### Secret Generation Best Practices

1. **Use cryptographically secure random generators:**
   - ✅ `secrets.token_urlsafe()` (Python)
   - ✅ `openssl rand -base64` (OpenSSL)
   - ❌ `random.randint()` (Python - not cryptographically secure)

2. **Appropriate secret lengths:**
   - General secrets: 32 bytes (256 bits)
   - JWT secrets: 64 bytes (512 bits)
   - Database passwords: 16-24 characters with mixed character sets

3. **Secret complexity:**
   ```python
   # Good: Mixed character set with sufficient entropy
   alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
   password = ''.join(secrets.choice(alphabet) for _ in range(16))
   
   # Better: Use token_urlsafe for web-safe base64 encoding
   secret = secrets.token_urlsafe(32)
   ```

### Runtime Security

1. **Read secrets at runtime, not startup:**
   ```python
   # Good: Read when needed
   def get_database_connection():
       password = read_secret("database_password")
       return connect(f"postgresql://user:{password}@host/db")
   
   # Avoid: Storing in global variables
   DATABASE_PASSWORD = read_secret("database_password")  # ❌
   ```

2. **Mask secrets in logs:**
   ```python
   def mask_secret(secret: str, show_chars: int = 4) -> str:
       """Mask secret for logging, showing only first few characters."""
       if len(secret) <= show_chars:
           return "*" * len(secret)
       return secret[:show_chars] + "*" * (len(secret) - show_chars)
   
   # Usage
   logger.info(f"Using database password: {mask_secret(password)}")
   # Output: "Using database password: abc1************"
   ```

3. **Validate secret format:**
   ```python
   def validate_secret_key(key: str) -> bool:
       """Validate JWT secret key requirements."""
       if len(key) < 32:
           raise ValueError("Secret key must be at least 32 characters")
       
       if key in ["your-secret-key-change-in-production", "change-me"]:
           raise ValueError("Default secret key detected - change required")
       
       return True
   ```

---

## 📋 Deployment Checklist

### Development Environment
- [ ] Install secrets management dependencies
- [ ] Generate development secrets
- [ ] Create `.env` files from templates
- [ ] Verify services start without hardcoded secrets
- [ ] Test secret rotation functionality

### Staging Environment
- [ ] Set up external key management (Vault/AWS/Azure)
- [ ] Generate staging-specific secrets
- [ ] Configure Docker secrets
- [ ] Test deployment with secrets management
- [ ] Verify secret rotation process

### Production Environment
- [ ] External key management properly configured
- [ ] Production secrets generated and stored securely
- [ ] Docker Swarm secrets created
- [ ] Services deployed with secret management
- [ ] Secret rotation schedule established
- [ ] Monitoring and alerting for secret access
- [ ] Backup and recovery procedures for secrets

---

## 🔍 Troubleshooting

### Common Issues

1. **"Secret not found" errors:**
   ```bash
   # Check if Docker secrets exist
   docker secret ls
   
   # Inspect specific secret
   docker secret inspect ppl-meta-node_secret_key
   
   # Verify secret file exists in container
   docker exec ppl-meta-node ls -la /run/secrets/
   ```

2. **Permission denied errors:**
   ```bash
   # Fix file permissions
   chmod 600 .env
   chmod 700 secrets/
   
   # Check Docker service has access to secrets
   docker service inspect ppl-meta-node | grep -A 10 Secrets
   ```

3. **Vault connection issues:**
   ```bash
   # Test Vault connectivity
   curl -H "X-Vault-Token: $VAULT_TOKEN" \
        $VAULT_ADDR/v1/secret/data/ppl-platform/common
   
   # Check Vault status
   vault status
   ```

### Debugging Commands

```bash
# List all secrets
python secrets/manage_secrets.py list

# Verify Docker secrets
docker secret ls | grep ppl-meta

# Check service logs for secret-related errors
docker service logs ppl-meta-node | grep -i secret

# Test secret reading in container
docker exec ppl-meta-node cat /run/secrets/secret_key
```

---

## 📚 Reference

### Command Reference

```bash
# Secrets Management
python secrets/manage_secrets.py generate [--encrypted]
python secrets/manage_secrets.py create-docker
python secrets/manage_secrets.py create-env [--template-only]
python secrets/manage_secrets.py list

# Docker Secrets
docker secret create <name> <file>
docker secret ls
docker secret inspect <name>
docker secret rm <name>

# Docker Swarm
docker swarm init
docker stack deploy -c docker-compose.secrets.yml <stack-name>
docker service update --secret-add <secret> <service>
```

### Environment Variables Reference

| Variable | Description | Production Source | Required |
|----------|-------------|-------------------|----------|
| `SECRET_KEY` | General encryption key | Docker secret/Vault | Yes |
| `JWT_SECRET` | JWT signing key | Docker secret/Vault | Yes |
| `DATABASE_PASSWORD` | Database password | Docker secret/Vault | Yes |
| `REDIS_PASSWORD` | Redis password | Docker secret/Vault | No |
| `MAIL_PASSWORD` | SMTP password | Docker secret/Vault | No |
| `VAULT_TOKEN` | Vault access token | Environment/IAM | No |

---

## 📄 Files Created/Modified

### New Files
- `secrets/manage_secrets.py` - Comprehensive secrets management system
- `secrets/requirements.txt` - Python dependencies
- `docker-compose.secrets.yml` - Production deployment with Docker secrets
- `SECRETS_MANAGEMENT_GUIDE.md` - This documentation

### Modified Files
- `ppl-meta-node/.env.example` - Removed hardcoded secrets
- `ppl-meta-media/.env.example` - Removed hardcoded secrets  
- `ppl-meta-gateway/.env.example` - Removed hardcoded secrets
- `ppl-meta-orchestrator/.env.example` - Removed hardcoded secrets

---

**Document Version**: 1.0  
**Last Updated**: January 8, 2025  
**Related Issue**: ISSUE-015 - Hardcoded Secrets in Configuration  
**Status**: ✅ Resolved

**Security Notice**: This implementation provides enterprise-grade secrets management suitable for production deployments. Always follow your organization's security policies and regulatory requirements.
