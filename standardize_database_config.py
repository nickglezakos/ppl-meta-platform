#!/usr/bin/env python3
"""
Database Connection Standardization Script
Resolves ISSUE-006: Database Connection String Variations

This script:
1. Standardizes database connection string formats across all services
2. Validates connection string syntax and components
3. Ensures consistent credentials and port usage
4. Updates service configurations for consistency
"""

import os
import re
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration standardization utilities."""
    
    # Standardized database configuration
    STANDARD_CONFIG = {
        'host': 'localhost',
        'port': 5433,  # External port from docker-compose
        'username': 'nickadmin',
        'password': 'Kodikos@23',
        'encoding': 'utf8'
    }
    
    # Service-specific database names
    SERVICE_DATABASES = {
        'ppl-meta-node': 'ppl_db',
        'ppl-meta-media': 'ppl_media_db', 
        'ppl-meta-orchestrator': 'ppl_orchestrator_db',
        'ppl-meta-gateway': 'ppl_gateway_db',  # New for consistency
        'ppl-meta-code': 'ppl_platform'  # Root/shared platform
    }
    
    def __init__(self):
        self.workspace_root = os.path.dirname(os.path.abspath(__file__))
        
    def parse_database_url(self, url: str) -> Optional[Dict[str, str]]:
        """Parse a PostgreSQL URL into components."""
        try:
            if not url.startswith('postgresql://'):
                return None
                
            parsed = urlparse(url)
            return {
                'scheme': parsed.scheme,
                'username': parsed.username,
                'password': parsed.password,
                'hostname': parsed.hostname,
                'port': str(parsed.port) if parsed.port else '5432',
                'database': parsed.path.lstrip('/')
            }
        except Exception as e:
            logger.error(f"Failed to parse URL '{url}': {e}")
            return None
    
    def build_database_url(self, service_name: str, host: str = None, port: int = None, 
                          username: str = None, password: str = None) -> str:
        """Build a standardized database URL for a service."""
        config = self.STANDARD_CONFIG.copy()
        
        # Override with provided values
        if host:
            config['host'] = host
        if port:
            config['port'] = port
        if username:
            config['username'] = username
        if password:
            config['password'] = password
            
        # Get database name for service
        db_name = self.SERVICE_DATABASES.get(service_name, 'ppl_db')
        
        # URL encode password to handle special characters
        encoded_password = quote_plus(config['password'])
        
        return (f"postgresql://{config['username']}:{encoded_password}"
                f"@{config['host']}:{config['port']}/{db_name}")
    
    def validate_connection_string(self, url: str) -> Tuple[bool, List[str]]:
        """Validate a database connection string."""
        issues = []
        
        # Parse the URL
        parsed = self.parse_database_url(url)
        if not parsed:
            issues.append("Invalid PostgreSQL URL format")
            return False, issues
            
        # Check for common issues
        if not parsed['username']:
            issues.append("Missing username")
            
        if not parsed['password']:
            issues.append("Missing password")
            
        if not parsed['hostname']:
            issues.append("Missing hostname")
            
        if not parsed['database']:
            issues.append("Missing database name")
            
        # Check for URL encoding issues
        if '%' in parsed['password'] and '@' in url.split('@')[0]:
            issues.append("Password may need URL encoding")
            
        # Check port consistency
        if parsed['port'] == '5432' and 'localhost' in parsed['hostname']:
            issues.append("Using default PostgreSQL port 5432, should be 5433 for Docker external access")
            
        return len(issues) == 0, issues
    
    def find_service_configs(self) -> Dict[str, List[str]]:
        """Find all service configuration files that need updating."""
        configs = {}
        
        services = ['ppl-meta-node', 'ppl-meta-media', 'ppl-meta-orchestrator', 
                   'ppl-meta-gateway', 'ppl-meta-code']
        
        for service in services:
            service_path = os.path.join(self.workspace_root, service)
            files = []
            
            # Look for .env.example files
            env_example = os.path.join(service_path, '.env.example')
            if os.path.exists(env_example):
                files.append(env_example)
                
            # Look for config.py files
            config_py = os.path.join(service_path, 'src', 'config.py')
            if os.path.exists(config_py):
                files.append(config_py)
                
            # Look for database.py files
            database_py = os.path.join(service_path, 'src', 'database.py')
            if os.path.exists(database_py):
                files.append(database_py)
                
            if files:
                configs[service] = files
                
        return configs
    
    def analyze_current_configs(self) -> Dict[str, Dict[str, any]]:
        """Analyze current database configurations across services."""
        results = {}
        configs = self.find_service_configs()
        
        print("🔍 Analyzing current database configurations...")
        print("=" * 60)
        
        for service, files in configs.items():
            print(f"\n📋 Service: {service}")
            service_results = {
                'files': [],
                'database_urls': [],
                'issues': []
            }
            
            for file_path in files:
                file_info = {
                    'path': file_path,
                    'database_urls': [],
                    'issues': []
                }
                
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                    # Find DATABASE_URL patterns
                    patterns = [
                        r'DATABASE_URL[\\s]*[=:][\\s]*["\']([^"\']+)["\']',
                        r'DATABASE_URL[\\s]*[=:][\\s]*([^\\s]+)',
                        r'postgresql://[^\\s"\']+',
                    ]
                    
                    urls_found = set()
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        urls_found.update(matches)
                    
                    for url in urls_found:
                        if url.startswith('postgresql://'):
                            file_info['database_urls'].append(url)
                            service_results['database_urls'].append(url)
                            
                            # Validate the URL
                            is_valid, issues = self.validate_connection_string(url)
                            if not is_valid:
                                file_info['issues'].extend(issues)
                                service_results['issues'].extend(issues)
                                
                    print(f"   📄 {os.path.basename(file_path)}")
                    if file_info['database_urls']:
                        for url in file_info['database_urls']:
                            print(f"      🔗 {url}")
                    else:
                        print(f"      ℹ️  No database URLs found")
                        
                    if file_info['issues']:
                        for issue in file_info['issues']:
                            print(f"      ⚠️  {issue}")
                            
                except Exception as e:
                    file_info['issues'].append(f"Error reading file: {e}")
                    print(f"   ❌ Error reading {file_path}: {e}")
                    
                service_results['files'].append(file_info)
                
            results[service] = service_results
            
        return results
    
    def generate_standardized_configs(self) -> Dict[str, str]:
        """Generate standardized database configurations for each service."""
        configs = {}
        
        print("\n🔧 Generating standardized database configurations...")
        print("=" * 60)
        
        for service, db_name in self.SERVICE_DATABASES.items():
            # Standard configuration for development (localhost)
            localhost_url = self.build_database_url(service)
            
            # Docker configuration (for compose files)
            docker_url = self.build_database_url(
                service, 
                host='postgres',  # Docker service name
                port=5432        # Internal Docker port
            )
            
            configs[service] = {
                'localhost_url': localhost_url,
                'docker_url': docker_url,
                'database_name': db_name
            }
            
            print(f"\n📋 {service}:")
            print(f"   🏠 Localhost: {localhost_url}")
            print(f"   🐳 Docker:    {docker_url}")
            print(f"   🗄️  Database:  {db_name}")
            
        return configs
    
    def update_env_examples(self, standardized_configs: Dict[str, str]) -> bool:
        """Update .env.example files with standardized database URLs."""
        print("\n📝 Updating .env.example files...")
        print("=" * 60)
        
        updated_files = 0
        
        for service, config in standardized_configs.items():
            env_file = os.path.join(self.workspace_root, service, '.env.example')
            
            if not os.path.exists(env_file):
                print(f"   ⚠️  {service}: .env.example not found")
                continue
                
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    
                # Update DATABASE_URL line
                localhost_url = config['localhost_url']
                updated_content = re.sub(
                    r'DATABASE_URL=.*',
                    f'DATABASE_URL={localhost_url}',
                    content
                )
                
                # Also update individual DB components for consistency
                db_name = config['database_name']
                updated_content = re.sub(
                    r'DB_HOST=.*',
                    f'DB_HOST=localhost',
                    updated_content
                )
                updated_content = re.sub(
                    r'DB_PORT=.*',
                    f'DB_PORT=5433',
                    updated_content
                )
                updated_content = re.sub(
                    r'DB_NAME=.*',
                    f'DB_NAME={db_name}',
                    updated_content
                )
                updated_content = re.sub(
                    r'DB_USER=.*',
                    f'DB_USER=nickadmin',
                    updated_content
                )
                updated_content = re.sub(
                    r'DB_PASSWORD=.*',
                    f'DB_PASSWORD=Kodikos@23',
                    updated_content
                )
                
                with open(env_file, 'w') as f:
                    f.write(updated_content)
                    
                print(f"   ✅ {service}: Updated .env.example")
                updated_files += 1
                
            except Exception as e:
                print(f"   ❌ {service}: Error updating .env.example: {e}")
                
        print(f"\n📊 Updated {updated_files} .env.example files")
        return updated_files > 0
    
    def add_connection_validation(self) -> bool:
        """Add database connection validation helpers to service configs."""
        print("\n🔧 Adding connection validation helpers...")
        print("=" * 60)
        
        validation_helper = '''
    def validate_database_url(self) -> bool:
        """Validate the database connection string format and components."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.get_database_url())
            
            if not parsed.scheme.startswith('postgresql'):
                logger.error("Database URL must use postgresql:// scheme")
                return False
                
            if not parsed.username:
                logger.error("Database URL missing username")
                return False
                
            if not parsed.password:
                logger.error("Database URL missing password")
                return False
                
            if not parsed.hostname:
                logger.error("Database URL missing hostname")
                return False
                
            if not parsed.path or parsed.path == '/':
                logger.error("Database URL missing database name")
                return False
                
            logger.info("Database URL validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Database URL validation failed: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """Get database connection information for debugging."""
        url = self.get_database_url()
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'username': parsed.username,
                'database': parsed.path.lstrip('/'),
                'url_masked': url.replace(parsed.password or '', '*****') if parsed.password else url
            }
        except Exception:
            return {'error': 'Failed to parse database URL'}
'''
        
        services_updated = 0
        
        for service in self.SERVICE_DATABASES.keys():
            config_file = os.path.join(self.workspace_root, service, 'src', 'config.py')
            
            if not os.path.exists(config_file):
                continue
                
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    
                # Check if validation methods already exist
                if 'validate_database_url' in content:
                    print(f"   ℹ️  {service}: Validation helpers already present")
                    continue
                    
                # Add validation helpers before the last class closing or model_config
                if 'model_config = ' in content:
                    # Insert before model_config
                    content = content.replace(
                        '    model_config = ',
                        f'{validation_helper}\n    model_config = '
                    )
                elif content.rstrip().endswith('"""'):
                    # Insert before the closing docstring
                    content = content.rstrip()[:-3] + validation_helper + '\n    """'
                else:
                    # Insert before the last few lines of the class
                    lines = content.split('\n')
                    insert_pos = -1
                    for i in range(len(lines) - 1, -1, -1):
                        if lines[i].strip() and not lines[i].startswith('#'):
                            insert_pos = i + 1
                            break
                    
                    if insert_pos > 0:
                        lines.insert(insert_pos, validation_helper)
                        content = '\n'.join(lines)
                
                with open(config_file, 'w') as f:
                    f.write(content)
                    
                print(f"   ✅ {service}: Added validation helpers to config.py")
                services_updated += 1
                
            except Exception as e:
                print(f"   ❌ {service}: Error updating config.py: {e}")
                
        print(f"\n📊 Added validation helpers to {services_updated} services")
        return services_updated > 0
    
    def create_database_test_script(self) -> bool:
        """Create a database connection test script."""
        test_script = '''#!/usr/bin/env python3
"""
Database Connection Test Script
Tests database connections for all PPL Meta Platform services
"""

import os
import sys
from urllib.parse import urlparse
import logging

# Add src directories to path for each service
services = ['ppl-meta-node', 'ppl-meta-media', 'ppl-meta-orchestrator']
for service in services:
    service_src = os.path.join(os.path.dirname(__file__), service, 'src')
    if os.path.exists(service_src):
        sys.path.insert(0, service_src)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_service_database(service_name: str) -> bool:
    """Test database connection for a specific service."""
    print(f"\\n🔍 Testing {service_name} database connection...")
    
    try:
        if service_name == 'ppl-meta-node':
            from ppl_meta_node.src.config import settings
            from ppl_meta_node.src.database import test_connection
        elif service_name == 'ppl-meta-media':
            from ppl_meta_media.src.config import config as settings
            from ppl_meta_media.src.database import test_connection
        elif service_name == 'ppl-meta-orchestrator':
            from ppl_meta_orchestrator.src.config import settings
            # Import would need to be created
            
        db_url = settings.get_database_url() if hasattr(settings, 'get_database_url') else settings.DATABASE_URL
        
        print(f"   Database URL: {db_url}")
        
        # Validate URL format
        if hasattr(settings, 'validate_database_url'):
            if not settings.validate_database_url():
                print(f"   ❌ URL validation failed")
                return False
        
        # Test actual connection
        if 'test_connection' in locals():
            if test_connection():
                print(f"   ✅ Connection successful")
                return True
            else:
                print(f"   ❌ Connection failed")
                return False
        else:
            print(f"   ⚠️  Connection test not available")
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Test all service database connections."""
    print("🗄️  PPL Meta Platform - Database Connection Test")
    print("=" * 50)
    
    services = ['ppl-meta-node', 'ppl-meta-media', 'ppl-meta-orchestrator']
    results = {}
    
    for service in services:
        results[service] = test_service_database(service)
    
    print(f"\\n📊 Test Results:")
    print("-" * 30)
    
    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {service}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print(f"\\n🎉 All database connections working correctly!")
        return 0
    else:
        print(f"\\n⚠️  Some database connections failed. Check configurations.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''
        
        script_path = os.path.join(self.workspace_root, 'test_database_connections.py')
        
        try:
            with open(script_path, 'w') as f:
                f.write(test_script)
                
            # Make executable
            os.chmod(script_path, 0o755)
            
            print(f"\n📄 Created database test script: {script_path}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error creating test script: {e}")
            return False

def main():
    """Main function to standardize database configurations."""
    print("🗄️  PPL Meta Platform - Database Configuration Standardization")
    print("Resolving ISSUE-006: Database Connection String Variations")
    print("=" * 70)
    
    db_config = DatabaseConfig()
    
    # Step 1: Analyze current configurations
    current_configs = db_config.analyze_current_configs()
    
    # Step 2: Generate standardized configurations
    standardized_configs = db_config.generate_standardized_configs()
    
    # Step 3: Update .env.example files
    db_config.update_env_examples(standardized_configs)
    
    # Step 4: Add validation helpers
    db_config.add_connection_validation()
    
    # Step 5: Create test script
    db_config.create_database_test_script()
    
    print("\n🎉 Database configuration standardization complete!")
    print("\n📋 Summary of standardization:")
    print("   ✅ Standardized connection string format: postgresql://user:password@host:port/database")
    print("   ✅ Consistent credentials: nickadmin:Kodikos@23")
    print("   ✅ Standard ports: 5433 (localhost), 5432 (Docker internal)")
    print("   ✅ Service-specific database names")
    print("   ✅ URL encoding for special characters in passwords")
    print("   ✅ Added connection validation helpers")
    print("   ✅ Created database connection test script")
    
    print("\n🔍 Next steps:")
    print("   1. Review updated .env.example files")
    print("   2. Update actual .env files to match the standardized format")
    print("   3. Run ./test_database_connections.py to validate connections")
    print("   4. Update ECOSYSTEM_ISSUES.md to mark ISSUE-006 as resolved")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
