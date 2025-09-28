"""
PPL Meta Vision Service - Phase 4: Service Deployment Configuration
Production deployment configuration for PPL Thread (Person Objects) functionality.

This configuration provides production-ready settings for:
- PPL Thread workflow performance optimization
- Database schema migration and maintenance
- Quality analysis and age detection configuration
- API rate limiting and resource management
- Monitoring and logging configuration
- Integration with existing Vision Service infrastructure
"""

import os
from typing import Any, Dict, Optional


class PPLThreadDeploymentConfig:
    """
    Production deployment configuration for PPL Thread functionality.

    Provides centralized configuration management for all Phase 4 components
    with environment-based overrides and production optimization.
    """

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration based on environment."""

        # Base configuration
        self.config = {
            # Core PPL Thread Configuration
            "ppl_thread": {
                "enabled": self._get_env_bool("PPL_THREAD_ENABLED", True),
                "default_tolerance_percent": self._get_env_float(
                    "PPL_DEFAULT_TOLERANCE", 20.0
                ),
                "max_concurrent_workflows": self._get_env_int(
                    "PPL_MAX_CONCURRENT_WORKFLOWS", 5
                ),
                "workflow_timeout_minutes": self._get_env_int(
                    "PPL_WORKFLOW_TIMEOUT_MINUTES", 30
                ),
                "batch_processing_size": self._get_env_int("PPL_BATCH_SIZE", 100),
            },
            # Quality Analysis Configuration
            "quality_analysis": {
                "enabled": self._get_env_bool("PPL_QUALITY_ANALYSIS_ENABLED", True),
                "deepface_enabled": self._get_env_bool("PPL_DEEPFACE_ENABLED", True),
                "quality_calculation_timeout": self._get_env_int(
                    "PPL_QUALITY_TIMEOUT", 10
                ),
                "face_crop_storage_enabled": self._get_env_bool(
                    "PPL_FACE_CROP_STORAGE", True
                ),
                "quality_cache_ttl_hours": self._get_env_int(
                    "PPL_QUALITY_CACHE_TTL", 24
                ),
            },
            # Age Detection Configuration
            "age_detection": {
                "enabled": self._get_env_bool("PPL_AGE_DETECTION_ENABLED", True),
                "fallback_unknown": self._get_env_bool(
                    "PPL_AGE_FALLBACK_UNKNOWN", True
                ),
                "age_detection_timeout": self._get_env_int(
                    "PPL_AGE_DETECTION_TIMEOUT", 5
                ),
                "cache_age_results": self._get_env_bool("PPL_CACHE_AGE_RESULTS", True),
            },
            # Database Configuration
            "database": {
                "schema_auto_migrate": self._get_env_bool("PPL_DB_AUTO_MIGRATE", True),
                "migration_backup_enabled": self._get_env_bool(
                    "PPL_DB_BACKUP_MIGRATIONS", True
                ),
                "cleanup_old_workflows": self._get_env_bool("PPL_DB_CLEANUP_OLD", True),
                "retention_days": self._get_env_int("PPL_DB_RETENTION_DAYS", 30),
                "face_crops_retention_days": self._get_env_int(
                    "PPL_FACE_CROPS_RETENTION", 7
                ),
                "connection_pool_size": self._get_env_int("PPL_DB_POOL_SIZE", 10),
                "query_timeout_seconds": self._get_env_int("PPL_DB_QUERY_TIMEOUT", 30),
            },
            # Performance Configuration
            "performance": {
                "enable_async_processing": self._get_env_bool(
                    "PPL_ASYNC_PROCESSING", True
                ),
                "max_memory_usage_mb": self._get_env_int("PPL_MAX_MEMORY_MB", 2048),
                "face_processing_threads": self._get_env_int(
                    "PPL_PROCESSING_THREADS", 4
                ),
                "quality_analysis_parallel": self._get_env_bool(
                    "PPL_PARALLEL_QUALITY", True
                ),
                "cache_grouping_results": self._get_env_bool(
                    "PPL_CACHE_GROUPING", True
                ),
                "grouping_cache_ttl_minutes": self._get_env_int(
                    "PPL_GROUPING_CACHE_TTL", 60
                ),
            },
            # API Configuration
            "api": {
                "rate_limit_per_minute": self._get_env_int("PPL_API_RATE_LIMIT", 60),
                "max_request_size_mb": self._get_env_int("PPL_API_MAX_REQUEST_MB", 10),
                "enable_request_logging": self._get_env_bool(
                    "PPL_API_LOG_REQUESTS", True
                ),
                "enable_response_caching": self._get_env_bool(
                    "PPL_API_CACHE_RESPONSES", False
                ),
                "workflow_status_cache_ttl": self._get_env_int(
                    "PPL_STATUS_CACHE_TTL", 300
                ),
            },
            # Monitoring and Logging
            "monitoring": {
                "enable_performance_metrics": self._get_env_bool(
                    "PPL_METRICS_ENABLED", True
                ),
                "log_level": self._get_env_str("PPL_LOG_LEVEL", "INFO"),
                "enable_workflow_tracing": self._get_env_bool(
                    "PPL_WORKFLOW_TRACING", True
                ),
                "metrics_collection_interval": self._get_env_int(
                    "PPL_METRICS_INTERVAL", 60
                ),
                "alert_on_workflow_failures": self._get_env_bool(
                    "PPL_ALERT_FAILURES", True
                ),
                "performance_alert_threshold_ms": self._get_env_int(
                    "PPL_PERF_ALERT_MS", 30000
                ),
            },
            # Integration Configuration
            "integration": {
                "register_with_discovery": self._get_env_bool(
                    "PPL_REGISTER_DISCOVERY", True
                ),
                "enable_health_checks": self._get_env_bool("PPL_HEALTH_CHECKS", True),
                "health_check_interval_seconds": self._get_env_int(
                    "PPL_HEALTH_INTERVAL", 30
                ),
                "compatible_with_ppl_mini": self._get_env_bool(
                    "PPL_MINI_COMPATIBLE", True
                ),
                "validate_response_format": self._get_env_bool(
                    "PPL_VALIDATE_RESPONSES", True
                ),
            },
            # Security Configuration
            "security": {
                "require_authentication": self._get_env_bool("PPL_REQUIRE_AUTH", False),
                "api_key_validation": self._get_env_bool(
                    "PPL_API_KEY_VALIDATION", False
                ),
                "rate_limiting_enabled": self._get_env_bool("PPL_RATE_LIMITING", True),
                "input_validation_strict": self._get_env_bool(
                    "PPL_STRICT_VALIDATION", True
                ),
                "log_sensitive_data": self._get_env_bool("PPL_LOG_SENSITIVE", False),
            },
        }

        # Environment-specific overrides
        if self.environment == "development":
            self._apply_development_overrides()
        elif self.environment == "testing":
            self._apply_testing_overrides()
        elif self.environment == "production":
            self._apply_production_overrides()

    def _apply_development_overrides(self):
        """Apply development environment overrides."""
        self.config["ppl_thread"]["max_concurrent_workflows"] = 2
        self.config["database"]["cleanup_old_workflows"] = False
        self.config["database"]["retention_days"] = 7
        self.config["monitoring"]["log_level"] = "DEBUG"
        self.config["security"]["require_authentication"] = False
        self.config["api"]["rate_limit_per_minute"] = 1000  # Higher for development

    def _apply_testing_overrides(self):
        """Apply testing environment overrides."""
        self.config["ppl_thread"]["max_concurrent_workflows"] = 1
        self.config["database"][
            "schema_auto_migrate"
        ] = False  # Manual control in tests
        self.config["quality_analysis"]["deepface_enabled"] = False  # Faster tests
        self.config["age_detection"]["enabled"] = False  # Faster tests
        self.config["monitoring"]["enable_performance_metrics"] = False
        self.config["integration"]["register_with_discovery"] = False

    def _apply_production_overrides(self):
        """Apply production environment overrides."""
        self.config["ppl_thread"]["max_concurrent_workflows"] = 10
        self.config["performance"]["max_memory_usage_mb"] = 4096
        self.config["database"]["connection_pool_size"] = 20
        self.config["monitoring"]["log_level"] = "WARNING"
        self.config["security"]["require_authentication"] = True
        self.config["security"]["rate_limiting_enabled"] = True
        self.config["api"]["enable_response_caching"] = True

    def get_config(self) -> Dict[str, Any]:
        """Get complete configuration dictionary."""
        return self.config.copy()

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get specific configuration section."""
        return self.config.get(section, {}).copy()

    def get_value(self, section: str, key: str, default: Any = None) -> Any:
        """Get specific configuration value."""
        return self.config.get(section, {}).get(key, default)

    def _get_env_str(self, key: str, default: str) -> str:
        """Get string value from environment."""
        return os.getenv(key, default)

    def _get_env_int(self, key: str, default: int) -> int:
        """Get integer value from environment."""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default

    def _get_env_float(self, key: str, default: float) -> float:
        """Get float value from environment."""
        try:
            return float(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default

    def _get_env_bool(self, key: str, default: bool) -> bool:
        """Get boolean value from environment."""
        value = os.getenv(key, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        elif value in ("false", "0", "no", "off"):
            return False
        return default


# Global configuration instance
_deployment_config = None


def get_deployment_config(
    environment: Optional[str] = None,
) -> PPLThreadDeploymentConfig:
    """
    Get deployment configuration instance.

    Args:
        environment: Optional environment override

    Returns:
        PPLThreadDeploymentConfig: Configuration instance
    """
    global _deployment_config

    if _deployment_config is None or environment is not None:
        env = environment or os.getenv("PPL_ENVIRONMENT", "production")
        _deployment_config = PPLThreadDeploymentConfig(env)

    return _deployment_config


def create_deployment_yaml_config() -> str:
    """
    Create YAML configuration for deployment.

    Returns:
        str: YAML configuration content
    """
    config = get_deployment_config()

    yaml_content = """
# PPL Meta Vision Service - Phase 4: Deployment Configuration
# Generated deployment configuration for PPL Thread (Person Objects) functionality

apiVersion: v1
kind: ConfigMap
metadata:
  name: ppl-thread-config
  namespace: ppl-meta-platform
data:
  # PPL Thread Core Configuration
  PPL_THREAD_ENABLED: "{ppl_thread_enabled}"
  PPL_DEFAULT_TOLERANCE: "{default_tolerance}"
  PPL_MAX_CONCURRENT_WORKFLOWS: "{max_workflows}"
  PPL_WORKFLOW_TIMEOUT_MINUTES: "{workflow_timeout}"
  PPL_BATCH_SIZE: "{batch_size}"
  
  # Quality Analysis Configuration
  PPL_QUALITY_ANALYSIS_ENABLED: "{quality_enabled}"
  PPL_DEEPFACE_ENABLED: "{deepface_enabled}"
  PPL_QUALITY_TIMEOUT: "{quality_timeout}"
  PPL_FACE_CROP_STORAGE: "{crop_storage}"
  PPL_QUALITY_CACHE_TTL: "{quality_cache_ttl}"
  
  # Age Detection Configuration
  PPL_AGE_DETECTION_ENABLED: "{age_enabled}"
  PPL_AGE_FALLBACK_UNKNOWN: "{age_fallback}"
  PPL_AGE_DETECTION_TIMEOUT: "{age_timeout}"
  PPL_CACHE_AGE_RESULTS: "{cache_age}"
  
  # Database Configuration
  PPL_DB_AUTO_MIGRATE: "{db_auto_migrate}"
  PPL_DB_BACKUP_MIGRATIONS: "{db_backup}"
  PPL_DB_CLEANUP_OLD: "{db_cleanup}"
  PPL_DB_RETENTION_DAYS: "{retention_days}"
  PPL_FACE_CROPS_RETENTION: "{crops_retention}"
  PPL_DB_POOL_SIZE: "{pool_size}"
  PPL_DB_QUERY_TIMEOUT: "{query_timeout}"
  
  # Performance Configuration
  PPL_ASYNC_PROCESSING: "{async_processing}"
  PPL_MAX_MEMORY_MB: "{max_memory}"
  PPL_PROCESSING_THREADS: "{processing_threads}"
  PPL_PARALLEL_QUALITY: "{parallel_quality}"
  PPL_CACHE_GROUPING: "{cache_grouping}"
  PPL_GROUPING_CACHE_TTL: "{grouping_cache_ttl}"
  
  # API Configuration
  PPL_API_RATE_LIMIT: "{rate_limit}"
  PPL_API_MAX_REQUEST_MB: "{max_request_mb}"
  PPL_API_LOG_REQUESTS: "{log_requests}"
  PPL_API_CACHE_RESPONSES: "{cache_responses}"
  PPL_STATUS_CACHE_TTL: "{status_cache_ttl}"
  
  # Monitoring Configuration
  PPL_METRICS_ENABLED: "{metrics_enabled}"
  PPL_LOG_LEVEL: "{log_level}"
  PPL_WORKFLOW_TRACING: "{workflow_tracing}"
  PPL_METRICS_INTERVAL: "{metrics_interval}"
  PPL_ALERT_FAILURES: "{alert_failures}"
  PPL_PERF_ALERT_MS: "{perf_alert_ms}"
  
  # Integration Configuration
  PPL_REGISTER_DISCOVERY: "{register_discovery}"
  PPL_HEALTH_CHECKS: "{health_checks}"
  PPL_HEALTH_INTERVAL: "{health_interval}"
  PPL_MINI_COMPATIBLE: "{mini_compatible}"
  PPL_VALIDATE_RESPONSES: "{validate_responses}"
  
  # Security Configuration
  PPL_REQUIRE_AUTH: "{require_auth}"
  PPL_API_KEY_VALIDATION: "{api_key_validation}"
  PPL_RATE_LIMITING: "{rate_limiting}"
  PPL_STRICT_VALIDATION: "{strict_validation}"
  PPL_LOG_SENSITIVE: "{log_sensitive}"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ppl-meta-vision-enhanced
  namespace: ppl-meta-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ppl-meta-vision-enhanced
  template:
    metadata:
      labels:
        app: ppl-meta-vision-enhanced
    spec:
      containers:
      - name: ppl-meta-vision
        image: ppl-meta-vision:phase4-latest
        ports:
        - containerPort: 8003
        envFrom:
        - configMapRef:
            name: ppl-thread-config
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8003
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8003
          initialDelaySeconds: 30
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: ppl-meta-vision-service
  namespace: ppl-meta-platform
spec:
  selector:
    app: ppl-meta-vision-enhanced
  ports:
  - port: 8003
    targetPort: 8003
  type: ClusterIP
""".format(
        # PPL Thread Configuration
        ppl_thread_enabled=config.get_value("ppl_thread", "enabled"),
        default_tolerance=config.get_value("ppl_thread", "default_tolerance_percent"),
        max_workflows=config.get_value("ppl_thread", "max_concurrent_workflows"),
        workflow_timeout=config.get_value("ppl_thread", "workflow_timeout_minutes"),
        batch_size=config.get_value("ppl_thread", "batch_processing_size"),
        # Quality Analysis Configuration
        quality_enabled=config.get_value("quality_analysis", "enabled"),
        deepface_enabled=config.get_value("quality_analysis", "deepface_enabled"),
        quality_timeout=config.get_value(
            "quality_analysis", "quality_calculation_timeout"
        ),
        crop_storage=config.get_value("quality_analysis", "face_crop_storage_enabled"),
        quality_cache_ttl=config.get_value(
            "quality_analysis", "quality_cache_ttl_hours"
        ),
        # Age Detection Configuration
        age_enabled=config.get_value("age_detection", "enabled"),
        age_fallback=config.get_value("age_detection", "fallback_unknown"),
        age_timeout=config.get_value("age_detection", "age_detection_timeout"),
        cache_age=config.get_value("age_detection", "cache_age_results"),
        # Database Configuration
        db_auto_migrate=config.get_value("database", "schema_auto_migrate"),
        db_backup=config.get_value("database", "migration_backup_enabled"),
        db_cleanup=config.get_value("database", "cleanup_old_workflows"),
        retention_days=config.get_value("database", "retention_days"),
        crops_retention=config.get_value("database", "face_crops_retention_days"),
        pool_size=config.get_value("database", "connection_pool_size"),
        query_timeout=config.get_value("database", "query_timeout_seconds"),
        # Performance Configuration
        async_processing=config.get_value("performance", "enable_async_processing"),
        max_memory=config.get_value("performance", "max_memory_usage_mb"),
        processing_threads=config.get_value("performance", "face_processing_threads"),
        parallel_quality=config.get_value("performance", "quality_analysis_parallel"),
        cache_grouping=config.get_value("performance", "cache_grouping_results"),
        grouping_cache_ttl=config.get_value(
            "performance", "grouping_cache_ttl_minutes"
        ),
        # API Configuration
        rate_limit=config.get_value("api", "rate_limit_per_minute"),
        max_request_mb=config.get_value("api", "max_request_size_mb"),
        log_requests=config.get_value("api", "enable_request_logging"),
        cache_responses=config.get_value("api", "enable_response_caching"),
        status_cache_ttl=config.get_value("api", "workflow_status_cache_ttl"),
        # Monitoring Configuration
        metrics_enabled=config.get_value("monitoring", "enable_performance_metrics"),
        log_level=config.get_value("monitoring", "log_level"),
        workflow_tracing=config.get_value("monitoring", "enable_workflow_tracing"),
        metrics_interval=config.get_value("monitoring", "metrics_collection_interval"),
        alert_failures=config.get_value("monitoring", "alert_on_workflow_failures"),
        perf_alert_ms=config.get_value("monitoring", "performance_alert_threshold_ms"),
        # Integration Configuration
        register_discovery=config.get_value("integration", "register_with_discovery"),
        health_checks=config.get_value("integration", "enable_health_checks"),
        health_interval=config.get_value(
            "integration", "health_check_interval_seconds"
        ),
        mini_compatible=config.get_value("integration", "compatible_with_ppl_mini"),
        validate_responses=config.get_value("integration", "validate_response_format"),
        # Security Configuration
        require_auth=config.get_value("security", "require_authentication"),
        api_key_validation=config.get_value("security", "api_key_validation"),
        rate_limiting=config.get_value("security", "rate_limiting_enabled"),
        strict_validation=config.get_value("security", "input_validation_strict"),
        log_sensitive=config.get_value("security", "log_sensitive_data"),
    )

    return yaml_content


def create_docker_compose_config() -> str:
    """
    Create Docker Compose configuration for local development.

    Returns:
        str: Docker Compose YAML content
    """
    config = get_deployment_config("development")

    docker_compose = """
version: '3.8'

services:
  ppl-meta-vision-enhanced:
    build:
      context: .
      dockerfile: Dockerfile.phase4
    ports:
      - "8003:8003"
    environment:
      # PPL Thread Configuration
      - PPL_THREAD_ENABLED={ppl_enabled}
      - PPL_DEFAULT_TOLERANCE={tolerance}
      - PPL_MAX_CONCURRENT_WORKFLOWS={max_workflows}
      
      # Quality Analysis Configuration
      - PPL_QUALITY_ANALYSIS_ENABLED={quality_enabled}
      - PPL_DEEPFACE_ENABLED={deepface_enabled}
      
      # Database Configuration
      - PPL_DB_AUTO_MIGRATE={auto_migrate}
      - PPL_DB_RETENTION_DAYS={retention_days}
      
      # Development Configuration
      - PPL_ENVIRONMENT=development
      - PPL_LOG_LEVEL=DEBUG
    depends_on:
      - postgres
    volumes:
      - ./src:/app/src:ro
      - ./logs:/app/logs
    restart: unless-stopped
    
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=ppl_meta_vision
      - POSTGRES_USER=ppl_user
      - POSTGRES_PASSWORD=ppl_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    restart: unless-stopped

volumes:
  postgres_data:
""".format(
        ppl_enabled=config.get_value("ppl_thread", "enabled"),
        tolerance=config.get_value("ppl_thread", "default_tolerance_percent"),
        max_workflows=config.get_value("ppl_thread", "max_concurrent_workflows"),
        quality_enabled=config.get_value("quality_analysis", "enabled"),
        deepface_enabled=config.get_value("quality_analysis", "deepface_enabled"),
        auto_migrate=config.get_value("database", "schema_auto_migrate"),
        retention_days=config.get_value("database", "retention_days"),
    )

    return docker_compose


# Export configuration functions
__all__ = [
    "PPLThreadDeploymentConfig",
    "get_deployment_config",
    "create_deployment_yaml_config",
    "create_docker_compose_config",
]
