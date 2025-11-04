# Secrets Management for PPL Meta vmeta Service

**Version:** 1.0.0  
**Date:** November 1, 2025

---

## Overview

This document provides guidelines for securely managing secrets and sensitive configuration for the vmeta service in production environments.

## Table of Contents

1. [Secrets Overview](#secrets-overview)
2. [Environment Variables](#environment-variables)
3. [Secrets Manager Integration](#secrets-manager-integration)
4. [Key Rotation](#key-rotation)
5. [Access Control](#access-control)
6. [Best Practices](#best-practices)

---

## Secrets Overview

### What Are Secrets?

Secrets are sensitive configuration values that should never be committed to version control:

- Database credentials (passwords, connection strings)
- API keys and tokens
- JWT secret keys
- SSL/TLS certificates and private keys
- Third-party service credentials
- Encryption keys

### Secrets Hierarchy

```
Production Secrets
├── Database
│   ├── DB_PASSWORD
│   └── DB_CONNECTION_STRING
├── Authentication
│   ├── JWT_SECRET_KEY
│   └── API_KEY
├── External Services
│   ├── ORCHESTRATOR_API_KEY
│   ├── DISCOVERY_API_KEY
│   └── SMTP_PASSWORD
└── Certificates
    ├── SSL_CERTIFICATE
    └── SSL_PRIVATE_KEY
```

---

## Environment Variables

### Using .env Files

**Development:**
```bash
# .env.development (safe to commit with placeholders)
DB_PASSWORD=dev_password_placeholder
JWT_SECRET_KEY=dev_secret_placeholder
```

**Production:**
```bash
# .env.production (NEVER commit to git)
DB_PASSWORD=${VAULT_SECRET_DB_PASSWORD}
JWT_SECRET_KEY=${VAULT_SECRET_JWT_KEY}
```

### Loading Environment Variables

**Option 1: systemd EnvironmentFile**
```ini
[Service]
EnvironmentFile=/etc/ppl-meta/vmeta.env
```

**Option 2: Manual export**
```bash
source /etc/ppl-meta/vmeta.env
```

**Option 3: Docker secrets**
```yaml
services:
  vmeta:
    secrets:
      - db_password
      - jwt_secret
```

---

## Secrets Manager Integration

### AWS Secrets Manager

**Installation:**
```bash
pip install boto3
```

**Usage:**
```python
import boto3
import json

def get_secret(secret_name, region="us-east-1"):
    """Retrieve secret from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name=region)
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        raise Exception(f"Failed to retrieve secret: {e}")

# Usage
secrets = get_secret("vmeta/production")
db_password = secrets['db_password']
jwt_secret = secrets['jwt_secret']
```

**Environment Integration:**
```bash
# Export secrets as environment variables
export DB_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id vmeta/production/db_password \
    --query SecretString \
    --output text)
```

### HashiCorp Vault

**Installation:**
```bash
pip install hvac
```

**Usage:**
```python
import hvac

def get_vault_secret(path, key):
    """Retrieve secret from HashiCorp Vault"""
    client = hvac.Client(url='https://vault.example.com')
    client.auth.approle.login(
        role_id=os.getenv('VAULT_ROLE_ID'),
        secret_id=os.getenv('VAULT_SECRET_ID')
    )
    
    secret = client.secrets.kv.v2.read_secret_version(path=path)
    return secret['data']['data'][key]

# Usage
db_password = get_vault_secret('vmeta/production', 'db_password')
```

### Kubernetes Secrets

**Create secret:**
```bash
kubectl create secret generic vmeta-secrets \
    --from-literal=db-password='<password>' \
    --from-literal=jwt-secret='<secret>'
```

**Mount in deployment:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vmeta
spec:
  containers:
  - name: vmeta
    env:
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: vmeta-secrets
          key: db-password
    - name: JWT_SECRET_KEY
      valueFrom:
        secretKeyRef:
          name: vmeta-secrets
          key: jwt-secret
```

---

## Key Rotation

### JWT Secret Key Rotation

**Step 1: Generate new secret**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Step 2: Update in secrets manager**
```bash
aws secretsmanager update-secret \
    --secret-id vmeta/production/jwt_secret \
    --secret-string "NEW_SECRET_VALUE"
```

**Step 3: Rolling deployment**
```bash
# Deploy with new secret, old tokens still valid
./deploy_vmeta.sh --version latest

# After grace period, old tokens expire naturally
```

### Database Password Rotation

**Step 1: Create new database user**
```sql
CREATE USER vmeta_prod_user_v2 WITH PASSWORD 'new_password';
GRANT ALL PRIVILEGES ON DATABASE ppl_meta_prod TO vmeta_prod_user_v2;
```

**Step 2: Update configuration**
```bash
# Update secrets manager
aws secretsmanager update-secret \
    --secret-id vmeta/production/db_password \
    --secret-string "new_password"

# Update DB_USER if changed
```

**Step 3: Deploy and verify**
```bash
./deploy_vmeta.sh --version latest
```

**Step 4: Remove old user**
```sql
-- After verifying new user works
DROP USER vmeta_prod_user_v1;
```

### Rotation Schedule

| Secret Type | Rotation Frequency | Automation |
|-------------|-------------------|------------|
| JWT Secret | Every 90 days | Manual |
| Database Password | Every 180 days | Manual |
| API Keys | Every 90 days | Automated |
| SSL Certificates | Before expiry | Let's Encrypt |

---

## Access Control

### Principle of Least Privilege

**Service Account:**
```bash
# Create dedicated service account
sudo useradd -r -s /bin/false vmeta

# Grant only necessary permissions
sudo chown vmeta:vmeta /etc/ppl-meta/vmeta.env
sudo chmod 600 /etc/ppl-meta/vmeta.env
```

### File Permissions

```bash
# Configuration files
chmod 600 /etc/ppl-meta/vmeta.env
chown vmeta:vmeta /etc/ppl-meta/vmeta.env

# SSL certificates
chmod 600 /etc/ssl/private/vmeta.key
chown root:root /etc/ssl/private/vmeta.key

# Application directory
chown -R vmeta:vmeta /opt/ppl-meta/vmeta
chmod 750 /opt/ppl-meta/vmeta
```

### IAM Roles (AWS)

**EC2 Instance Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:vmeta/production/*"
      ]
    }
  ]
}
```

---

## Best Practices

### DO ✅

1. **Use a Secrets Manager**
   - AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault
   - Centralized secret management
   - Audit logging

2. **Encrypt at Rest**
   - Encrypt secret files with GPG or similar
   - Use encrypted filesystems for sensitive data

3. **Rotate Regularly**
   - Set up automated rotation where possible
   - Document rotation procedures
   - Test rotation in staging first

4. **Audit Access**
   - Log all secret access
   - Monitor for unauthorized access
   - Regular access reviews

5. **Separate Environments**
   - Different secrets for dev/staging/production
   - Never use production secrets in development

6. **Version Control**
   - Use `.env.template` files with placeholders
   - Document required secrets
   - Never commit actual secrets

### DON'T ❌

1. **Never Hardcode Secrets**
   ```python
   # ❌ BAD
   DB_PASSWORD = "my_password_123"
   
   # ✅ GOOD
   DB_PASSWORD = os.getenv("DB_PASSWORD")
   ```

2. **Never Commit Secrets to Git**
   ```bash
   # Add to .gitignore
   echo ".env.production" >> .gitignore
   echo "secrets/" >> .gitignore
   ```

3. **Never Log Secrets**
   ```python
   # ❌ BAD
   logger.info(f"Connecting with password: {password}")
   
   # ✅ GOOD
   logger.info("Connecting to database...")
   ```

4. **Never Share Secrets via Email/Chat**
   - Use secure secret sharing tools
   - Share access to secrets manager instead

5. **Never Use Default/Weak Secrets**
   - Generate strong random secrets
   - Minimum 32 characters for keys

---

## Secret Generation

### JWT Secret Key

```bash
# Generate 256-bit (32 byte) secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Database Password

```bash
# Generate 20-character password with special chars
python3 -c "import secrets, string; chars = string.ascii_letters + string.digits + '!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(20)))"
```

### API Key

```bash
# Generate UUID-based API key
python3 -c "import uuid; print(str(uuid.uuid4()))"
```

---

## Troubleshooting

### Secret Not Loading

**Check file permissions:**
```bash
ls -la /etc/ppl-meta/vmeta.env
# Should be: -rw------- 1 vmeta vmeta
```

**Verify environment:**
```bash
systemctl show vmeta.service | grep Environment
```

**Test secret access:**
```bash
sudo -u vmeta bash -c 'source /etc/ppl-meta/vmeta.env && echo $DB_PASSWORD'
```

### Secrets Manager Connection Failed

**Test AWS credentials:**
```bash
aws secretsmanager list-secrets --region us-east-1
```

**Check IAM role:**
```bash
aws sts get-caller-identity
```

---

## Emergency Procedures

### Secret Compromised

1. **Immediate Actions:**
   ```bash
   # Rotate compromised secret immediately
   # Revoke access for affected credentials
   # Enable monitoring for unauthorized access
   ```

2. **Investigation:**
   - Check access logs
   - Identify scope of compromise
   - Determine if other secrets affected

3. **Recovery:**
   - Deploy new secrets
   - Update all services
   - Monitor for suspicious activity

### Lost Secret Access

1. **Restore from backup (if available)**
2. **Contact secrets manager administrator**
3. **Generate new secret and redeploy**

---

## Contact

For secrets management issues:
- **Production Incidents:** ops-team@example.com
- **Security Questions:** security@example.com
- **Documentation:** docs@example.com

---

**Last Updated:** November 1, 2025  
**Next Review:** February 1, 2026
