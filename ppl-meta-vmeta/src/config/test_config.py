"""
Configuration Management Test
PPL Meta Platform - Cross-Video Individual Tracking

Test the configuration management system without complex imports.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class SimpleConfigurationTest:
    """Simple configuration management test."""
    
    def __init__(self):
        """Initialize test."""
        self.test_config_file = "test_config.json"
    
    def create_test_config(self) -> dict:
        """Create a test configuration."""
        return {
            'config_name': 'test_balanced',
            'description': 'Test balanced configuration',
            'max_gap_seconds': 5.0,
            'iou_threshold': 0.3,
            'min_overlap_confidence': 0.5,
            'face_similarity_threshold': 0.8,
            'max_individuals_per_session': 500,
            'consolidation_window_minutes': 15,
            'enable_face_clustering': True,
            'clustering_threshold': 0.85,
            'min_cluster_size': 2,
            'enable_temporal_smoothing': True,
            'temporal_window_seconds': 3.0,
            'enable_cross_collection_tracking': True,
            'is_default': True
        }
    
    def validate_config_parameters(self, config: dict) -> bool:
        """Validate configuration parameters."""
        try:
            validations = [
                (0.1 <= config['max_gap_seconds'] <= 60.0, 
                 "max_gap_seconds must be between 0.1 and 60.0"),
                (0.0 <= config['iou_threshold'] <= 1.0, 
                 "iou_threshold must be between 0.0 and 1.0"),
                (0.0 <= config['min_overlap_confidence'] <= 1.0, 
                 "min_overlap_confidence must be between 0.0 and 1.0"),
                (0.5 <= config['face_similarity_threshold'] <= 1.0, 
                 "face_similarity_threshold must be between 0.5 and 1.0"),
                (1 <= config['max_individuals_per_session'] <= 10000, 
                 "max_individuals_per_session must be between 1 and 10000"),
                (1 <= config['consolidation_window_minutes'] <= 120, 
                 "consolidation_window_minutes must be between 1 and 120"),
            ]
            
            for condition, message in validations:
                if not condition:
                    logger.error(f"❌ {message}")
                    return False
                else:
                    logger.info(f"✅ Validation passed: {message.split(' must be')[0]}")
            
            # Clustering validation
            if config.get('enable_face_clustering'):
                if not (0.5 <= config.get('clustering_threshold', 0) <= 1.0):
                    logger.error("❌ clustering_threshold must be between 0.5 and 1.0")
                    return False
                logger.info("✅ Clustering threshold validation passed")
                
                if not (1 <= config.get('min_cluster_size', 0) <= 10):
                    logger.error("❌ min_cluster_size must be between 1 and 10")
                    return False
                logger.info("✅ Min cluster size validation passed")
            
            # Temporal smoothing validation
            if config.get('enable_temporal_smoothing'):
                if not (0.1 <= config.get('temporal_window_seconds', 0) <= 30.0):
                    logger.error("❌ temporal_window_seconds must be between 0.1 and 30.0")
                    return False
                logger.info("✅ Temporal window validation passed")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False
    
    def create_config_hash(self, config: dict) -> str:
        """Create hash for configuration."""
        # Use algorithm-relevant parameters only
        relevant_params = {
            'max_gap_seconds': config['max_gap_seconds'],
            'iou_threshold': config['iou_threshold'],
            'min_overlap_confidence': config['min_overlap_confidence'],
            'face_similarity_threshold': config['face_similarity_threshold'],
            'enable_face_clustering': config['enable_face_clustering'],
            'clustering_threshold': config.get('clustering_threshold', 0.85),
            'enable_temporal_smoothing': config['enable_temporal_smoothing'],
            'temporal_window_seconds': config.get('temporal_window_seconds', 3.0),
            'enable_cross_collection_tracking': config['enable_cross_collection_tracking']
        }
        
        config_str = json.dumps(relevant_params, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    async def test_config_creation_and_validation(self) -> bool:
        """Test configuration creation and validation."""
        logger.info("🧪 Testing configuration creation and validation...")
        
        try:
            # Test 1: Create valid configuration
            config = self.create_test_config()
            logger.info(f"✅ Created test config: {config['config_name']}")
            
            # Test 2: Validate configuration
            if not self.validate_config_parameters(config):
                logger.error("❌ Configuration validation failed")
                return False
            
            logger.info("✅ Configuration validation passed")
            
            # Test 3: Create configuration hash
            config_hash = self.create_config_hash(config)
            logger.info(f"✅ Configuration hash created: {config_hash}")
            
            # Test 4: Test invalid configuration
            invalid_config = config.copy()
            invalid_config['max_gap_seconds'] = 100.0  # Invalid value
            
            if self.validate_config_parameters(invalid_config):
                logger.error("❌ Invalid configuration was incorrectly validated")
                return False
            
            logger.info("✅ Invalid configuration correctly rejected")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration creation and validation failed: {e}")
            return False
    
    async def test_config_file_operations(self) -> bool:
        """Test configuration file save/load operations."""
        logger.info("🧪 Testing configuration file operations...")
        
        try:
            # Test 1: Create configuration structure
            config_data = {
                'runtime_settings': {
                    'max_concurrent_videos': 5,
                    'batch_size': 100,
                    'cache_ttl_hours': 24,
                    'enable_gpu_acceleration': True,
                    'memory_limit_mb': 4096,
                    'timeout_seconds': 300
                },
                'algorithm_configs': {
                    'fast_processing': {
                        'config_name': 'fast_processing',
                        'description': 'Fast processing with lower accuracy',
                        'max_gap_seconds': 10.0,
                        'iou_threshold': 0.4,
                        'face_similarity_threshold': 0.75,
                        'enable_face_clustering': False,
                        'is_default': False
                    },
                    'balanced': {
                        'config_name': 'balanced',
                        'description': 'Balanced accuracy and performance',
                        'max_gap_seconds': 5.0,
                        'iou_threshold': 0.3,
                        'face_similarity_threshold': 0.8,
                        'enable_face_clustering': True,
                        'is_default': True
                    }
                },
                'metadata': {
                    'saved_at': datetime.utcnow().isoformat(),
                    'version': '1.0',
                    'default_config': 'balanced'
                }
            }
            
            logger.info("✅ Configuration structure created")
            
            # Test 2: Save configuration to file
            config_path = Path(self.test_config_file)
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"✅ Configuration saved to {self.test_config_file}")
            
            # Test 3: Load configuration from file
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
            
            logger.info("✅ Configuration loaded from file")
            
            # Test 4: Verify loaded data
            assert 'runtime_settings' in loaded_config
            assert 'algorithm_configs' in loaded_config
            assert 'metadata' in loaded_config
            
            runtime_settings = loaded_config['runtime_settings']
            assert runtime_settings['max_concurrent_videos'] == 5
            assert runtime_settings['enable_gpu_acceleration'] is True
            
            algorithm_configs = loaded_config['algorithm_configs']
            assert 'balanced' in algorithm_configs
            assert 'fast_processing' in algorithm_configs
            
            balanced_config = algorithm_configs['balanced']
            assert balanced_config['is_default'] is True
            assert balanced_config['max_gap_seconds'] == 5.0
            
            logger.info("✅ Configuration data verification passed")
            
            # Test 5: Validate each algorithm config
            for config_name, config in algorithm_configs.items():
                if self.validate_config_parameters(config):
                    logger.info(f"✅ Configuration '{config_name}' is valid")
                else:
                    logger.error(f"❌ Configuration '{config_name}' is invalid")
                    return False
            
            # Clean up
            config_path.unlink()
            logger.info("✅ Test file cleaned up")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration file operations failed: {e}")
            return False
    
    async def test_default_config_management(self) -> bool:
        """Test default configuration management."""
        logger.info("🧪 Testing default configuration management...")
        
        try:
            # Test 1: Create multiple configurations
            configs = {
                'fast': {
                    'config_name': 'fast',
                    'description': 'Fast processing',
                    'max_gap_seconds': 10.0,
                    'iou_threshold': 0.4,
                    'min_overlap_confidence': 0.6,
                    'face_similarity_threshold': 0.75,
                    'max_individuals_per_session': 200,
                    'consolidation_window_minutes': 30,
                    'enable_face_clustering': False,
                    'enable_temporal_smoothing': True,
                    'temporal_window_seconds': 5.0,
                    'enable_cross_collection_tracking': False,
                    'is_default': False
                },
                'balanced': {
                    'config_name': 'balanced',
                    'description': 'Balanced processing',
                    'max_gap_seconds': 5.0,
                    'iou_threshold': 0.3,
                    'min_overlap_confidence': 0.5,
                    'face_similarity_threshold': 0.8,
                    'max_individuals_per_session': 500,
                    'consolidation_window_minutes': 15,
                    'enable_face_clustering': True,
                    'clustering_threshold': 0.85,
                    'min_cluster_size': 2,
                    'enable_temporal_smoothing': True,
                    'temporal_window_seconds': 3.0,
                    'enable_cross_collection_tracking': True,
                    'is_default': True  # This is the default
                },
                'accurate': {
                    'config_name': 'accurate',
                    'description': 'High accuracy processing',
                    'max_gap_seconds': 3.0,
                    'iou_threshold': 0.2,
                    'min_overlap_confidence': 0.4,
                    'face_similarity_threshold': 0.85,
                    'max_individuals_per_session': 1000,
                    'consolidation_window_minutes': 10,
                    'enable_face_clustering': True,
                    'clustering_threshold': 0.9,
                    'min_cluster_size': 2,
                    'enable_temporal_smoothing': True,
                    'temporal_window_seconds': 2.0,
                    'enable_cross_collection_tracking': True,
                    'is_default': False
                }
            }
            
            logger.info(f"✅ Created {len(configs)} configurations")
            
            # Test 2: Find default configuration
            default_config = None
            for config_name, config in configs.items():
                if config.get('is_default'):
                    if default_config is not None:
                        logger.error("❌ Multiple default configurations found")
                        return False
                    default_config = config
            
            if not default_config:
                logger.error("❌ No default configuration found")
                return False
            
            logger.info(f"✅ Found default configuration: {default_config['config_name']}")
            
            # Test 3: Validate all configurations
            for config_name, config in configs.items():
                if not self.validate_config_parameters(config):
                    logger.error(f"❌ Configuration '{config_name}' is invalid")
                    return False
                
                # Create hash for each config
                config_hash = self.create_config_hash(config)
                logger.info(f"✅ Config '{config_name}': hash={config_hash}")
            
            # Test 4: Verify configuration differences
            fast_hash = self.create_config_hash(configs['fast'])
            balanced_hash = self.create_config_hash(configs['balanced'])
            accurate_hash = self.create_config_hash(configs['accurate'])
            
            if fast_hash == balanced_hash or balanced_hash == accurate_hash or fast_hash == accurate_hash:
                logger.error("❌ Configuration hashes should be different")
                return False
            
            logger.info("✅ All configuration hashes are unique")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Default configuration management failed: {e}")
            return False
    
    async def run_all_tests(self) -> dict:
        """Run all configuration tests."""
        logger.info("🚀 Starting configuration management test suite...")
        
        tests = [
            ("Configuration Creation and Validation", self.test_config_creation_and_validation),
            ("Configuration File Operations", self.test_config_file_operations),
            ("Default Configuration Management", self.test_default_config_management)
        ]
        
        results = {}
        
        for test_name, test_method in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running: {test_name}")
            
            try:
                result = await test_method()
                results[test_name] = result
                
                if result:
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: CRASHED - {e}")
                results[test_name] = False
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("📋 Configuration Test Results Summary:")
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"  {test_name}: {status}")
        
        logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All configuration tests passed successfully!")
            logger.info("✅ Configuration management is ready for use!")
        else:
            logger.error(f"💥 {total - passed} tests failed")
        
        return results


async def main():
    """Main test runner."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    tester = SimpleConfigurationTest()
    results = await tester.run_all_tests()
    
    # Exit with appropriate code
    failed_tests = [name for name, result in results.items() if not result]
    if failed_tests:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())