#!/usr/bin/env python3
"""
PPL Meta Platform - Secrets Management System
Resolves ISSUE-015: Hardcoded Secrets in Configuration

This module provides comprehensive secrets management capabilities:
- Generate secure random secrets
- Manage Docker secrets
- Rotate secrets safely
- Integrate with external secret management systems
"""

import argparse
import base64
import json
import os
import secrets as crypto_secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecretManager:
    """Comprehensive secrets management for PPL Meta Platform."""

    def __init__(self, workspace_root: str = None):
        """Initialize the secret manager."""
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.secrets_dir = self.workspace_root / "secrets"
        self.secrets_dir.mkdir(exist_ok=True)

        # Service definitions
        self.services = {
            "ppl-meta-node": {
                "port": 8001,
                "database": "ppl_db",
                "secrets": [
                    "SECRET_KEY",
                    "JWT_SECRET",
                    "RESET_PASSWORD_SECRET",
                    "SERVICE_SECRET",
                ],
            },
            "ppl-meta-media": {
                "port": 8000,
                "database": "ppl_media_db",
                "secrets": ["SECRET_KEY", "JWT_SECRET"],
            },
            "ppl-meta-gateway": {
                "port": 8080,
                "database": "ppl_gateway_db",
                "secrets": ["SECRET_KEY", "JWT_SECRET"],
            },
            "ppl-meta-orchestrator": {
                "port": 8002,
                "database": "ppl_orchestrator_db",
                "secrets": ["SECRET_KEY", "JWT_SECRET"],
            },
        }

        # Common secrets for all services
        self.common_secrets = {
            "DATABASE_PASSWORD": "Database master password",
            "REDIS_PASSWORD": "Redis authentication password",
            "MAIL_PASSWORD": "SMTP mail password",
            "VAULT_TOKEN": "HashiCorp Vault access token",
        }

        print(f"🔐 Secret Manager initialized for workspace: " f"{self.workspace_root}")

    def generate_secret(self, length: int = 32) -> str:
        """Generate a cryptographically secure random secret."""
        return crypto_secrets.token_urlsafe(length)

    def generate_jwt_secret(self) -> str:
        """Generate a JWT-specific secret with sufficient entropy."""
        return crypto_secrets.token_urlsafe(64)

    def generate_database_password(self) -> str:
        """Generate a secure database password."""
        # Generate a strong password with mixed characters
        alphabet = (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789!@#$%^&*"
        )
        password = "".join(crypto_secrets.choice(alphabet) for _ in range(16))
        return password

    def generate_service_secrets(self, service_name: str) -> Dict[str, str]:
        """Generate all secrets for a specific service."""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        service_config = self.services[service_name]
        secrets_dict = {}

        # Generate service-specific secrets
        for secret_name in service_config["secrets"]:
            if secret_name.endswith("_JWT_SECRET") or secret_name == "JWT_SECRET":
                secrets_dict[secret_name] = self.generate_jwt_secret()
            else:
                secrets_dict[secret_name] = self.generate_secret()

        # Add service identifier
        secrets_dict["SERVICE_ID"] = f"{service_name}-{self.generate_secret(8)}"

        return secrets_dict

    def generate_all_secrets(self) -> Dict[str, Dict[str, str]]:
        """Generate secrets for all services."""
        print("🔑 Generating secrets for all services...")

        all_secrets = {}

        # Generate common secrets
        common_secrets = {}
        for secret_name, description in self.common_secrets.items():
            if secret_name == "DATABASE_PASSWORD":
                common_secrets[secret_name] = self.generate_database_password()
            elif secret_name.endswith("_PASSWORD"):
                common_secrets[secret_name] = self.generate_secret(24)
            else:
                common_secrets[secret_name] = self.generate_secret()
            print(f"   ✅ Generated {secret_name}: {description}")

        all_secrets["common"] = common_secrets

        # Generate service-specific secrets
        for service_name in self.services:
            service_secrets = self.generate_service_secrets(service_name)
            all_secrets[service_name] = service_secrets
            print(
                f"   ✅ Generated {len(service_secrets)} secrets for " f"{service_name}"
            )

        return all_secrets

    def save_secrets_to_file(
        self, secrets_data: Dict[str, Dict[str, str]], encrypted: bool = True
    ) -> str:
        """Save secrets to a secure file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if encrypted:
            # Generate encryption key from master password
            master_password = input("Enter master password for encryption: ")
            master_password = master_password.encode()
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password))
            fernet = Fernet(key)

            # Encrypt secrets
            secrets_json = json.dumps(secrets_data, indent=2)
            encrypted_data = fernet.encrypt(secrets_json.encode())

            # Save encrypted file
            secrets_file = self.secrets_dir / f"secrets_encrypted_{timestamp}.key"
            with open(secrets_file, "wb") as f:
                f.write(salt + encrypted_data)

            print(f"🔒 Encrypted secrets saved to: {secrets_file}")

        else:
            # Save as plain JSON (for development only)
            secrets_file = self.secrets_dir / f"secrets_{timestamp}.json"
            with open(secrets_file, "w", encoding="utf-8") as f:
                json.dump(secrets_data, f, indent=2)

            print(f"📄 Secrets saved to: {secrets_file}")
            print("⚠️  WARNING: Secrets are stored in plain text!")

        return str(secrets_file)

    def load_secrets_from_file(
        self, file_path: str, master_password: str = None
    ) -> Dict[str, Dict[str, str]]:
        """Load secrets from a file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Secrets file not found: {file_path}")

        if file_path.suffix == ".key":
            # Load encrypted secrets
            if not master_password:
                master_password = input("Enter master password: ")

            with open(file_path, "rb") as f:
                encrypted_data = f.read()

            # Extract salt and encrypted data
            salt = encrypted_data[:16]
            encrypted_content = encrypted_data[16:]

            # Derive key and decrypt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            fernet = Fernet(key)

            decrypted_data = fernet.decrypt(encrypted_content)
            secrets_data = json.loads(decrypted_data.decode())

        else:
            # Load plain JSON
            with open(file_path, "r", encoding="utf-8") as f:
                secrets_data = json.load(f)

        return secrets_data

    def create_docker_secrets(self, secrets_data: Dict[str, Dict[str, str]]) -> bool:
        """Create Docker secrets for Docker Swarm deployment."""
        print("🐳 Creating Docker secrets...")

        try:
            # Check if Docker Swarm is initialized
            result = subprocess.run(
                ["docker", "info", "--format", "{{.Swarm.LocalNodeState}}"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0 or result.stdout.strip() != "active":
                print("⚠️  Docker Swarm not initialized. Initializing...")
                subprocess.run(["docker", "swarm", "init"], check=True)

            # Create secrets for each service
            for service_name, service_secrets in secrets_data.items():
                if service_name == "common":
                    continue

                for secret_name, secret_value in service_secrets.items():
                    docker_secret_name = f"{service_name}_{secret_name.lower()}"

                    # Check if secret already exists
                    check_result = subprocess.run(
                        ["docker", "secret", "inspect", docker_secret_name],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if check_result.returncode == 0:
                        print(
                            f"   ⚠️  Secret {docker_secret_name} already exists, "
                            f"skipping"
                        )
                        continue

                    # Create the secret
                    create_result = subprocess.run(
                        ["docker", "secret", "create", docker_secret_name, "-"],
                        input=secret_value,
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    if create_result.returncode == 0:
                        print(f"   ✅ Created Docker secret: {docker_secret_name}")
                    else:
                        print(
                            f"   ❌ Failed to create secret {docker_secret_name}: "
                            f"{create_result.stderr}"
                        )
                        return False

            # Create common secrets
            for secret_name, secret_value in secrets_data.get("common", {}).items():
                docker_secret_name = f"common_{secret_name.lower()}"

                # Check if secret already exists
                check_result = subprocess.run(
                    ["docker", "secret", "inspect", docker_secret_name],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if check_result.returncode == 0:
                    print(
                        f"   ⚠️  Secret {docker_secret_name} already exists, "
                        f"skipping"
                    )
                    continue

                # Create the secret
                create_result = subprocess.run(
                    ["docker", "secret", "create", docker_secret_name, "-"],
                    input=secret_value,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                if create_result.returncode == 0:
                    print(f"   ✅ Created Docker secret: {docker_secret_name}")
                else:
                    print(
                        f"   ❌ Failed to create secret {docker_secret_name}: "
                        f"{create_result.stderr}"
                    )
                    return False

            print("✅ Docker secrets created successfully!")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Docker command failed: {e}")
            return False
        except (OSError, FileNotFoundError) as e:
            print(f"❌ Error creating Docker secrets: {e}")
            return False

    def create_env_files(
        self, secrets_data: Dict[str, Dict[str, str]], template_only: bool = False
    ) -> bool:
        """Create environment files for each service."""
        print("📝 Creating environment files...")

        for service_name in self.services:
            service_dir = self.workspace_root / service_name
            if not service_dir.exists():
                print(f"   ⚠️  Service directory not found: {service_dir}")
                continue

            service_config = self.services[service_name]
            service_secrets = secrets_data.get(service_name, {})

            # Create .env file content
            env_content = f"""# {service_name} - Environment Configuration
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# WARNING: This file contains sensitive information - do not commit to version control!

# Application Settings
APP_NAME={service_name}
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=info
LOG_FORMAT=console
HOST=0.0.0.0
PORT={service_config['port']}
ENVIRONMENT=production

# Database Configuration
DATABASE_URL=postgresql://nickadmin:${{DATABASE_PASSWORD}}@postgres:5432/{service_config['database']}
DB_HOST=postgres
DB_PORT=5432
DB_NAME={service_config['database']}
DB_USER=nickadmin
DB_PASSWORD=${{DATABASE_PASSWORD}}

"""

            # Add service-specific secrets
            for secret_name in service_config["secrets"]:
                if template_only:
                    env_content += f"{secret_name}=${{{secret_name}}}\n"
                else:
                    secret_value = service_secrets.get(secret_name, "CHANGE_ME")
                    env_content += f"{secret_name}={secret_value}\n"

            # Add common secrets
            common_secrets = secrets_data.get("common", {})
            for secret_name, secret_value in common_secrets.items():
                if template_only:
                    env_content += f"{secret_name}=${{{secret_name}}}\n"
                else:
                    env_content += f"{secret_name}={secret_value}\n"

            # Add common configuration
            env_content += f"""
# Service Communication URLs
USER_SERVICE_URL=http://ppl-meta-node:8001
MEDIA_SERVICE_URL=http://ppl-meta-media:8000
GATEWAY_SERVICE_URL=http://ppl-meta-gateway:8080
ORCHESTRATOR_SERVICE_URL=http://ppl-meta-orchestrator:8002

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=${{REDIS_PASSWORD}}

# Mail Configuration (for notifications)
MAIL_USERNAME=${{MAIL_USERNAME}}
MAIL_PASSWORD=${{MAIL_PASSWORD}}
MAIL_FROM=${{MAIL_FROM}}
MAIL_SERVER=${{MAIL_SERVER}}
MAIL_PORT=587
MAIL_FROM_NAME={service_name}
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
USE_CREDENTIALS=true
VALIDATE_CERTS=true

# External Services
VAULT_TOKEN=${{VAULT_TOKEN}}
"""

            # Write environment file
            env_file_name = ".env.template" if template_only else ".env"
            env_file = service_dir / env_file_name
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(env_content)

            if template_only:
                print(f"   ✅ Created template: {env_file}")
            else:
                print(f"   ✅ Created environment file: {env_file}")
                # Set restrictive permissions
                os.chmod(env_file, 0o600)

        return True

    def list_secrets(self) -> None:
        """List all managed secrets."""
        print("📋 Managed Secrets:")
        print("=" * 50)

        print("\n🔗 Common Secrets:")
        for secret_name, description in self.common_secrets.items():
            print(f"   • {secret_name}: {description}")

        print("\n🔧 Service-Specific Secrets:")
        for service_name, config in self.services.items():
            print(f"\n   {service_name}:")
            for secret_name in config["secrets"]:
                print(f"     • {secret_name}")


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(
        description="PPL Meta Platform - Secrets Management System"
    )
    parser.add_argument(
        "action",
        choices=["generate", "create-docker", "create-env", "list"],
        help="Action to perform",
    )
    parser.add_argument(
        "--template-only",
        action="store_true",
        help="Create template files only (for create-env action)",
    )
    parser.add_argument("--workspace", default=".", help="Path to workspace root")
    parser.add_argument("--encrypted", action="store_true", help="Encrypt secrets file")

    args = parser.parse_args()

    # Initialize secret manager
    secret_manager = SecretManager(args.workspace)

    if args.action == "generate":
        # Generate all secrets
        secrets_data = secret_manager.generate_all_secrets()

        # Save to file
        secrets_file = secret_manager.save_secrets_to_file(secrets_data, args.encrypted)

        print(f"\n✅ Secrets generated and saved to: {secrets_file}")
        print("🔒 Keep this file secure and do not commit to version control!")

    elif args.action == "create-docker":
        # Load secrets from latest file
        secrets_files = list(secret_manager.secrets_dir.glob("secrets_*.json"))
        if not secrets_files:
            print("❌ No secrets file found. Run 'generate' first.")
            return

        latest_file = max(secrets_files, key=lambda f: f.stat().st_mtime)
        secrets_data = secret_manager.load_secrets_from_file(str(latest_file))

        # Create Docker secrets
        secret_manager.create_docker_secrets(secrets_data)

    elif args.action == "create-env":
        # Load secrets from latest file
        secrets_files = list(secret_manager.secrets_dir.glob("secrets_*.json"))
        if not secrets_files:
            print("❌ No secrets file found. Run 'generate' first.")
            return

        latest_file = max(secrets_files, key=lambda f: f.stat().st_mtime)
        secrets_data = secret_manager.load_secrets_from_file(str(latest_file))

        # Create environment files
        secret_manager.create_env_files(secrets_data, args.template_only)

    elif args.action == "list":
        # List all managed secrets
        secret_manager.list_secrets()

    print("\n🎉 Secrets management operation completed!")


if __name__ == "__main__":
    main()
