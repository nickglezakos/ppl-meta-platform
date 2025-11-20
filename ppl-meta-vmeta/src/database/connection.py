"""
Cross-Video Individual Tracking - Database Configuration
PPL Meta Platform v2.19.13+

PostgreSQL database configuration and connection management
for cross-video individual tracking system.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import asyncpg
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """PostgreSQL database configuration manager."""
    
    def __init__(self):
        """Initialize database configuration."""
        self.config = self._load_database_config()
        self._validate_config()
    
    def _load_database_config(self) -> Dict[str, Any]:
        """Load database configuration from environment and defaults."""
    # Support both POSTGRES_* and DB_* env var naming conventions.
    # Many services use DB_HOST/DB_NAME/DB_USER, older code expects
    # POSTGRES_*. Accept either to avoid misconfiguration.
        return {
            # PostgreSQL connection settings
            'host': os.getenv('POSTGRES_HOST', os.getenv('DB_HOST', 'localhost')),
            'port': int(
                os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', '5432'))
            ),
            'database': os.getenv(
                'POSTGRES_DATABASE', os.getenv('DB_NAME', 'ppl_meta_vmeta')
            ),
            'user': os.getenv(
                'POSTGRES_USER', os.getenv('DB_USER', 'postgres')
            ),
            'password': os.getenv(
                'POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', 'postgres')
            ),
            
            # Connection pool settings
            'min_pool_size': int(os.getenv('DB_MIN_POOL_SIZE', '5')),
            'max_pool_size': int(os.getenv('DB_MAX_POOL_SIZE', '20')),
            'max_inactive_connection_lifetime': float(
                os.getenv('DB_MAX_INACTIVE_TIME', '300')
            ),
            
            # SSL settings
            'ssl': os.getenv('POSTGRES_SSL', 'prefer'),
            'ssl_cert_path': os.getenv('POSTGRES_SSL_CERT'),
            'ssl_key_path': os.getenv('POSTGRES_SSL_KEY'),
            'ssl_ca_path': os.getenv('POSTGRES_SSL_CA'),
            
            # Performance settings
            'command_timeout': float(os.getenv('DB_COMMAND_TIMEOUT', '60')),
            'query_timeout': float(os.getenv('DB_QUERY_TIMEOUT', '30')),
            'connect_timeout': float(os.getenv('DB_CONNECT_TIMEOUT', '10')),
            
            # Cross-video tracking specific
            'enable_vector_extension': bool(
                os.getenv('ENABLE_PGVECTOR', 'true').lower() == 'true'
            ),
            'cache_table_name': os.getenv(
                'CACHE_TABLE_NAME', 'cached_person_objects'
            ),
            'session_table_name': os.getenv(
                'SESSION_TABLE_NAME', 'tracking_sessions'
            ),
            
            # Migration settings
            'auto_migrate': bool(
                os.getenv('AUTO_MIGRATE', 'false').lower() == 'true'
            ),
            'migration_path': os.getenv('MIGRATION_PATH', 'migrations/'),
        }
    
    def _validate_config(self):
        """Validate database configuration."""
        required_fields = ['host', 'port', 'database', 'user', 'password']
        
        for field in required_fields:
            if not self.config.get(field):
                raise ValueError(f"Missing required database config: {field}")
        
        # Validate port range
        if not (1 <= self.config['port'] <= 65535):
            raise ValueError(f"Invalid port: {self.config['port']}")
        
        # Validate pool sizes
        if self.config['min_pool_size'] > self.config['max_pool_size']:
            raise ValueError(
                "min_pool_size cannot be greater than max_pool_size"
            )
    
    def get_connection_url(self, include_password: bool = True) -> str:
        """Get PostgreSQL connection URL."""
        password_part = (
            f":{self.config['password']}" if include_password else ""
        )

        # Build URL in parts to avoid overly long lines
        user_part = f"{self.config['user']}{password_part}"
        host_part = f"{self.config['host']}:{self.config['port']}"
        # Compose without exceeding line length
        return (
            "postgresql://" + user_part + "@" + host_part + "/"
            + self.config['database']
        )
    
    def get_asyncpg_params(self) -> Dict[str, Any]:
        """Get asyncpg connection parameters."""
        params = {
            'host': self.config['host'],
            'port': self.config['port'],
            'database': self.config['database'],
            'user': self.config['user'],
            'password': self.config['password'],
            'command_timeout': self.config['command_timeout'],
            'server_settings': {
                'application_name': 'ppl-meta-vmeta-cross-video-tracking'
            }
        }
        
        # Add SSL configuration if provided
        if self.config['ssl'] and self.config['ssl'] != 'disable':
            ssl_context = self._create_ssl_context()
            if ssl_context:
                params['ssl'] = ssl_context
        
        return params
    
    def _create_ssl_context(self):
        """Create SSL context for database connection."""
        import ssl
        
        try:
            context = ssl.create_default_context()
            
            if self.config['ssl_ca_path']:
                ca_path = self.config['ssl_ca_path']
                context.load_verify_locations(cafile=ca_path)
            
            if self.config['ssl_cert_path'] and self.config['ssl_key_path']:
                context.load_cert_chain(
                    certfile=self.config['ssl_cert_path'],
                    keyfile=self.config['ssl_key_path']
                )
            
            # Configure SSL verification based on setting
            if self.config['ssl'] == 'require':
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
            elif self.config['ssl'] == 'prefer':
                context.check_hostname = False
                context.verify_mode = ssl.CERT_OPTIONAL
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to create SSL context: {e}")
            return None


class DatabaseManager:
    """Database connection and pool management."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize database manager."""
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_cache: Dict[str, asyncpg.Connection] = {}
    
    async def initialize_pool(self) -> asyncpg.Pool:
        """Initialize database connection pool."""
        if self.pool is not None:
            return self.pool
        
        try:
            connection_params = self.config.get_asyncpg_params()
            
            max_inactive = self.config.config['max_inactive_connection_lifetime']
            self.pool = await asyncpg.create_pool(
                min_size=self.config.config['min_pool_size'],
                max_size=self.config.config['max_pool_size'],
                max_inactive_connection_lifetime=max_inactive,
                **connection_params,
            )
            
            # Test connection and verify extensions
            await self._verify_database_setup()
            
            logger.info(
                "✅ Database pool initialized: %s-%s connections",
                self.config.config['min_pool_size'],
                self.config.config['max_pool_size'],
            )
            
            return self.pool
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            raise
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get database connection from pool."""
        if self.pool is None:
            await self.initialize_pool()
        
        try:
            return await self.pool.acquire()
        except Exception as e:
            logger.error(f"Failed to acquire database connection: {e}")
            raise
    
    async def release_connection(self, connection: asyncpg.Connection):
        """Release connection back to pool."""
        if self.pool is not None:
            await self.pool.release(connection)
    
    async def close_pool(self):
        """Close database connection pool."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")
    
    async def _verify_database_setup(self):
        """Verify database setup and required extensions."""
        async with self.pool.acquire() as conn:
            # Check PostgreSQL version
            version_result = await conn.fetchval("SELECT version()")
            logger.info(f"PostgreSQL version: {version_result}")
            
            # Check for pgvector extension if enabled
            if self.config.config['enable_vector_extension']:
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    vector_version = await conn.fetchval(
                        "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                    )
                    if vector_version:
                        logger.info(f"✅ pgvector extension available: v{vector_version}")
                    else:
                        logger.warning("⚠️ pgvector extension not available")
                except Exception as e:
                    logger.warning(f"⚠️ pgvector extension check failed: {e}")
            
            # Verify required tables exist (will be created by migrations)
            required_tables = [
                self.config.config['cache_table_name'],
                self.config.config['session_table_name'],
                'individuals',
                'individual_video_appearances'
            ]
            
            existing_tables = await conn.fetch(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = ANY($1)
                """,
                required_tables
            )
            
            existing_table_names = [row['table_name'] for row in existing_tables]
            missing_tables = set(required_tables) - set(existing_table_names)
            
            if missing_tables:
                logger.warning(f"⚠️ Missing tables: {missing_tables}")
                if self.config.config['auto_migrate']:
                    logger.info("Auto-migration enabled - tables will be created")
                else:
                    logger.warning("Auto-migration disabled - run migrations manually")
            else:
                logger.info("✅ All required tables exist")


# Global database instances
_db_config: Optional[DatabaseConfig] = None
_db_manager: Optional[DatabaseManager] = None


def get_database_config() -> DatabaseConfig:
    """Get global database configuration."""
    global _db_config
    
    if _db_config is None:
        _db_config = DatabaseConfig()
    
    return _db_config


def get_database_manager() -> DatabaseManager:
    """Get global database manager."""
    global _db_manager
    
    if _db_manager is None:
        config = get_database_config()
        _db_manager = DatabaseManager(config)
    
    return _db_manager


async def get_db_connection() -> asyncpg.Connection:
    """Dependency for getting database connection."""
    manager = get_database_manager()
    return await manager.get_connection()


async def get_test_db_connection() -> asyncpg.Connection:
    """Get test database connection with test configuration."""
    test_config = DatabaseConfig()
    
    # Override with test database settings
    test_config.config.update({
        'database': os.getenv('TEST_POSTGRES_DATABASE', 'ppl_meta_vmeta_test'),
        'min_pool_size': 1,
        'max_pool_size': 5
    })
    
    test_manager = DatabaseManager(test_config)
    await test_manager.initialize_pool()
    
    return await test_manager.get_connection()


async def initialize_database() -> bool:
    """Initialize database connection and verify setup."""
    try:
        manager = get_database_manager()
        await manager.initialize_pool()
        logger.info("✅ Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


async def close_database():
    """Close database connections and cleanup."""
    global _db_manager
    
    if _db_manager is not None:
        await _db_manager.close_pool()
        _db_manager = None
        logger.info("Database connections closed")


# Configuration validation function
def validate_database_environment():
    """Validate database environment variables."""
    required_env_vars = [
        'POSTGRES_HOST',
        'POSTGRES_DATABASE', 
        'POSTGRES_USER',
        'POSTGRES_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ Database environment variables validated")
    return True


# Environment-specific configurations
def get_development_config() -> Dict[str, str]:
    """Get development environment database configuration."""
    return {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DATABASE': 'ppl_meta_vmeta_dev',
        'POSTGRES_USER': 'dev_user',
        'POSTGRES_PASSWORD': 'dev_password',
        'DB_MIN_POOL_SIZE': '2',
        'DB_MAX_POOL_SIZE': '10',
        'AUTO_MIGRATE': 'true',
        'ENABLE_PGVECTOR': 'true'
    }


def get_production_config() -> Dict[str, str]:
    """Get production environment database configuration."""
    return {
        'POSTGRES_HOST': 'prod-db.ppl-meta.internal',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DATABASE': 'ppl_meta_vmeta',
        'POSTGRES_USER': 'ppl_meta_user',
        'POSTGRES_PASSWORD': '${VAULT:database/postgres/password}',
        'DB_MIN_POOL_SIZE': '10',
        'DB_MAX_POOL_SIZE': '50',
        'POSTGRES_SSL': 'require',
        'AUTO_MIGRATE': 'false',
        'ENABLE_PGVECTOR': 'true'
    }


def get_test_config() -> Dict[str, str]:
    """Get test environment database configuration."""
    return {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DATABASE': 'ppl_meta_vmeta_test',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_password',
        'DB_MIN_POOL_SIZE': '1',
        'DB_MAX_POOL_SIZE': '5',
        'AUTO_MIGRATE': 'true',
        'ENABLE_PGVECTOR': 'true'
    }