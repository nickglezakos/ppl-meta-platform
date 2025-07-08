"""
Shared secrets management module for PPL Meta Platform

This module provides secure secrets management with support for:
- Environment variables
- Docker secrets
- HashiCorp Vault (future)
- AWS Secrets Manager (future)
- Secret rotation capabilities
"""

import os
import logging
from typing import Optional, Dict
from pathlib import Path
from datetime import datetime, timedelta
import secrets as crypto_secrets
import base64

logger = logging.getLogger(__name__)


class SecretsManager:
    """Secure secrets management with multiple backends"""
    
    def __init__(self, backend: str = "auto"):
        """
        Initialize secrets manager
        
        Args:
            backend: Backend type ('env', 'docker', 'vault', 'aws', 'auto')
        """
        self.backend = backend
        self._secrets_cache = {}
        self._last_rotation_check = {}
        self._rotation_intervals = {
            'SECRET_KEY': timedelta(days=90),
            'JWT_SECRET': timedelta(days=30),
            'DB_PASSWORD': timedelta(days=180),
            'SMTP_PASSWORD': timedelta(days=90),
            'RESET_PASSWORD_SECRET': timedelta(days=30)
        }
        
        # Auto-detect backend if not specified
        if backend == "auto":
            self.backend = self._detect_backend()
        
        logger.info("Initialized SecretsManager with backend: %s",
                    self.backend)
    
    def _detect_backend(self) -> str:
        """Auto-detect the best available secrets backend"""
        # Check for Docker secrets
        if Path("/run/secrets").exists():
            return "docker"
        
        # Check for Vault
        if os.getenv("VAULT_ADDR"):
            return "vault"
        
        # Check for AWS
        if os.getenv("AWS_REGION") and os.getenv("AWS_ACCESS_KEY_ID"):
            return "aws"
        
        # Default to environment variables
        return "env"
    
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value from the configured backend
        
        Args:
            secret_name: Name of the secret
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        try:
            if self.backend == "docker":
                return self._get_docker_secret(secret_name, default)
            elif self.backend == "vault":
                return self._get_vault_secret(secret_name, default)
            elif self.backend == "aws":
                return self._get_aws_secret(secret_name, default)
            else:
                return self._get_env_secret(secret_name, default)
        except (OSError, IOError) as e:
            logger.error("Error getting secret %s: %s", secret_name, e)
            return default
    
    def _get_env_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from environment variables"""
        value = os.getenv(secret_name, default)
        if value and value != default:
            # Check if it's a placeholder that should be replaced
            if value in ["", "your-secret-key-change-in-production", 
                         "default-secret-key-change-in-production"]:
                logger.warning("Secret %s has placeholder value, generating new one", secret_name)
                value = self._generate_secret(secret_name)
        return value
    
    def _get_docker_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from Docker secrets"""
        secret_path = Path(f"/run/secrets/{secret_name.lower()}")
        if secret_path.exists():
            try:
                return secret_path.read_text().strip()
            except Exception as e:
                logger.error(f"Error reading Docker secret {secret_name}: {e}")
        
        # Fallback to environment variable
        return self._get_env_secret(secret_name, default)
    
    def _get_vault_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from HashiCorp Vault (placeholder for future implementation)"""
        logger.warning("Vault backend not implemented yet, falling back to environment")
        return self._get_env_secret(secret_name, default)
    
    def _get_aws_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret from AWS Secrets Manager (placeholder for future implementation)"""
        logger.warning("AWS Secrets Manager backend not implemented yet, falling back to environment")
        return self._get_env_secret(secret_name, default)
    
    def _generate_secret(self, secret_name: str) -> str:
        """Generate a new secret value"""
        if secret_name in ["SECRET_KEY", "JWT_SECRET", "RESET_PASSWORD_SECRET"]:
            # Generate a secure random string
            return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        elif "PASSWORD" in secret_name:
            # Generate a secure password
            return self._generate_password()
        else:
            # Generate a secure random string
            return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    def _generate_password(self, length: int = 16) -> str:
        """Generate a secure password"""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for i in range(length))
    
    def check_rotation_needed(self, secret_name: str) -> bool:
        """Check if a secret needs rotation"""
        if secret_name not in self._rotation_intervals:
            return False
        
        last_rotation = self._last_rotation_check.get(secret_name)
        if not last_rotation:
            return True
        
        interval = self._rotation_intervals[secret_name]
        return datetime.now() - last_rotation > interval
    
    def rotate_secret(self, secret_name: str) -> str:
        """Rotate a secret and return the new value"""
        new_value = self._generate_secret(secret_name)
        self._last_rotation_check[secret_name] = datetime.now()
        
        # In a production environment, you would store the new secret
        # in your secrets backend and update any dependent services
        logger.info(f"Secret {secret_name} rotated successfully")
        
        return new_value
    
    def get_all_secrets(self) -> Dict[str, str]:
        """Get all required secrets for the platform"""
        secrets_config = {
            'SECRET_KEY': self.get_secret('SECRET_KEY'),
            'JWT_SECRET': self.get_secret('JWT_SECRET'),
            'RESET_PASSWORD_SECRET': self.get_secret('RESET_PASSWORD_SECRET'),
            'DB_PASSWORD': self.get_secret('DB_PASSWORD', 'postgres'),
            'SMTP_PASSWORD': self.get_secret('SMTP_PASSWORD', ''),
            'MAIL_PASSWORD': self.get_secret('MAIL_PASSWORD', ''),
        }
        
        # Generate any missing secrets
        for key, value in secrets_config.items():
            if not value or value in ["", "your-secret-key-change-in-production", "default-secret-key-change-in-production"]:
                secrets_config[key] = self._generate_secret(key)
                logger.info(f"Generated new secret for {key}")
        
        return secrets_config
    
    def validate_secrets(self) -> Dict[str, bool]:
        """Validate that all secrets are properly configured"""
        validation_results = {}
        secrets_config = self.get_all_secrets()
        
        for key, value in secrets_config.items():
            if not value:
                validation_results[key] = False
                logger.error(f"Secret {key} is empty or not configured")
            elif value in ["", "your-secret-key-change-in-production", "default-secret-key-change-in-production"]:
                validation_results[key] = False
                logger.error(f"Secret {key} has placeholder value")
            elif len(value) < 8:
                validation_results[key] = False
                logger.error(f"Secret {key} is too short")
            else:
                validation_results[key] = True
        
        return validation_results


# Global instance
secrets_manager = SecretsManager()


def get_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret"""
    return secrets_manager.get_secret(secret_name, default)


def validate_all_secrets() -> bool:
    """Validate all secrets are properly configured"""
    results = secrets_manager.validate_secrets()
    return all(results.values())
