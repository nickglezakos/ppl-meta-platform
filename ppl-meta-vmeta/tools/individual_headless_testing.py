#!/usr/bin/env python3
"""
Cross-Video Individual Tracking - Headless Testing Script
PPL Meta Platform v2.19.13+

Command-line testing tool for algorithm validation, cache management,
and comprehensive performance analysis.

Usage:
    python tools/individual_headless_testing.py
    python tools/individual_headless_testing.py --auto-test
    python tools/individual_headless_testing.py --cache-status

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.models.cross_video_tracking import CrossVideoTrackingConfig
    from src.services.integrated_caching import IntegratedCachingService
    from src.database.connection import get_test_db_connection
    from tools.advanced_results_analyzer import AdvancedResultsAnalyzer
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrossVideoTrackingTester:
    """
    Comprehensive testing interface for cross-video individual tracking.
    
    Provides interactive and automated testing capabilities with
    performance analysis and cache management.
    """
    
    def __init__(self):
        """Initialize the testing interface."""
        self.caching_service: Optional[IntegratedCachingService] = None
        self.db_connection = None
        self.results_analyzer = AdvancedResultsAnalyzer()
        self.test_collections = [
            "test_collection_1",
            "test_collection_2",
            "sample_indoor_footage",
            "sample_outdoor_footage"
        ]
    
    async def initialize(self):
        """Initialize database connection and services."""
        try:
            self.db_connection = await get_test_db_connection()
            self.caching_service = IntegratedCachingService(self.db_connection)
            logger.info("✅ Successfully initialized database connection")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    async def run_interactive_mode(self):
        """Run interactive testing mode with user prompts."""
        print("\n" + "="*60)
        print("🎯 Cross-Video Individual Tracking - Testing Interface")
        print("PPL Meta Platform v2.19.13+")
        print("="*60)
        
        while True:
            print("\n📋 Available Operations:")
            print("1. 🚀 Execute Cross-Video Tracking")
            print("2. 📊 View Cache Status")
            print("3. 🧹 Manage Cache")
            print("4. ⚡ Performance Testing")
            print("5. 🔧 Algorithm Configuration")
            print("6. 📈 Generate Test Report")
            print("7. 👤 Analyze Individual Profiles")
            print("8. 🗺️  Analyze Movement Patterns")
            print("9. 📊 Statistical Validation")
            print("10. 🔍 Detailed Results Analysis")
            print("11. ❌ Exit")
            
            try:
                choice = input("\nSelect operation (1-11): ").strip()
                
                if choice == "1":
                    await self._execute_tracking_workflow()
                elif choice == "2":
                    await self._display_cache_status()
                elif choice == "3":
                    await self._manage_cache()
                elif choice == "4":
                    await self._run_performance_tests()
                elif choice == "5":
                    await self._configure_algorithm()
                elif choice == "6":
                    await self._generate_test_report()
                elif choice == "7":
                    await self._analyze_individual_profiles()
                elif choice == "8":
                    await self._analyze_movement_patterns()
                elif choice == "9":
                    await self._perform_statistical_validation()
                elif choice == "10":
                    await self._detailed_results_analysis()
                elif choice == "11":
                    print("\n👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice. Please select 1-7.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                print(f"❌ Error: {e}")
    
    async def _execute_tracking_workflow(self):
        """Execute cross-video tracking with user-specified parameters."""
        print("\n🚀 Cross-Video Individual Tracking Execution")
        print("-" * 50)
        
        try:
            # Get time range
            print("\n📅 Time Range Selection:")
            start_date = self._get_date_input("Start date (YYYY-MM-DD): ")
            end_date = self._get_date_input("End date (YYYY-MM-DD): ")
            
            if start_date >= end_date:
                print("❌ End date must be after start date")
                return
            
            # Get collections
            print(f"\n📂 Available Collections: {', '.join(self.test_collections)}")
            collection_input = input("Enter collections (comma-separated) or 'all': ").strip()
            
            if collection_input.lower() == 'all':
                collections = self.test_collections
            else:
                collections = [c.strip() for c in collection_input.split(',') if c.strip()]
            
            if not collections:
                print("❌ No collections specified")
                return
            
            # Get processing options
            print("\n⚙️ Processing Options:")
            background = input("Background processing? (y/N): ").strip().lower() == 'y'
            force_reprocess = input("Force reprocessing (ignore cache)? (y/N): ").strip().lower() == 'y'
            
            # Create configuration
            config = CrossVideoTrackingConfig()
            
            print("\n🔄 Executing cross-video tracking...")
            print(f"   📂 Collections: {collections}")
            print(f"   📅 Time Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"   ⚙️ Background: {background}, Force Reprocess: {force_reprocess}")
            
            # Execute tracking
            start_time = datetime.now()
            result = await self.caching_service.execute_cache_aware_tracking(
                user_id="test_user",
                collections=collections,
                start_time=start_date,
                end_time=end_date,
                config=config,
                background=background,
                force_reprocess=force_reprocess
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Display results
            self._display_tracking_results(result, execution_time)
            
            if background and result.get('status') == 'started':
                session_uuid = result.get('session_info', {}).get('session_uuid')
                if session_uuid:
                    await self._monitor_background_session(session_uuid)
        
        except Exception as e:
            logger.error(f"Tracking execution failed: {e}")
            print(f"❌ Execution failed: {e}")
    
    async def _display_cache_status(self):
        """Display comprehensive cache status information."""
        print("\n📊 Cache Status & Statistics")
        print("-" * 40)
        
        try:
            # Get cache performance report
            report = await self.caching_service.get_cache_performance_report()
            
            # Display overview
            overview = report.get('cache_overview', {})
            performance = report.get('performance_metrics', {})
            
            print(f"\n📈 Cache Overview:")
            print(f"   Total Entries: {overview.get('total_cached_entries', 0):,}")
            print(f"   Total Size: {overview.get('total_cache_size_mb', 0):.2f} MB")
            print(f"   Unique Configs: {overview.get('unique_configurations', 0)}")
            print(f"   Unique Videos: {overview.get('unique_videos', 0)}")
            
            print(f"\n⚡ Performance Metrics:")
            print(f"   Efficiency Score: {performance.get('cache_efficiency_score', 0):.1f}/100")
            print(f"   Avg Access Count: {performance.get('average_access_count', 0):.2f}")
            print(f"   Storage Efficiency: {performance.get('storage_efficiency', 0):.2f}")
            
            # Display recommendations
            recommendations = report.get('recommendations', [])
            if recommendations:
                print(f"\n💡 Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec}")
            
        except Exception as e:
            logger.error(f"Failed to get cache status: {e}")
            print(f"❌ Failed to get cache status: {e}")
    
    async def _manage_cache(self):
        """Interactive cache management operations."""
        print("\n🧹 Cache Management")
        print("-" * 30)
        
        print("\n📋 Cache Operations:")
        print("1. Clear cache for collections")
        print("2. Optimize cache storage")
        print("3. Validate cache integrity")
        print("4. View cache statistics")
        print("5. Back to main menu")
        
        choice = input("\nSelect operation (1-5): ").strip()
        
        try:
            if choice == "1":
                await self._clear_collection_cache()
            elif choice == "2":
                await self._optimize_cache()
            elif choice == "3":
                await self._validate_cache()
            elif choice == "4":
                await self._display_cache_status()
            elif choice == "5":
                return
            else:
                print("❌ Invalid choice")
                
        except Exception as e:
            logger.error(f"Cache management failed: {e}")
            print(f"❌ Operation failed: {e}")
    
    async def _clear_collection_cache(self):
        """Clear cache for specific collections."""
        print("\n🧹 Clear Collection Cache")
        
        print(f"Available Collections: {', '.join(self.test_collections)}")
        collection_input = input("Enter collections to clear (comma-separated): ").strip()
        
        if not collection_input:
            print("❌ No collections specified")
            return
        
        collections = [c.strip() for c in collection_input.split(',') if c.strip()]
        
        # Confirm operation
        print(f"\n⚠️  WARNING: This will clear cache for: {collections}")
        confirm = input("Type 'CONFIRM' to proceed: ").strip()
        
        if confirm != 'CONFIRM':
            print("❌ Operation cancelled")
            return
        
        # Clear cache
        result = await self.caching_service.cache_clearing.clear_cache_for_collections(
            collections
        )
        
        print(f"✅ Cache cleared successfully:")
        print(f"   Entries removed: {result.get('deleted_count', 0)}")
        print(f"   Space freed: {result.get('freed_space_mb', 0):.2f} MB")
    
    async def _optimize_cache(self):
        """Optimize cache storage."""
        print("\n⚡ Cache Storage Optimization")
        
        max_age = int(input("Maximum age in days (default 30): ") or "30")
        max_size = float(input("Maximum size in GB (default 5.0): ") or "5.0")
        min_access = int(input("Minimum access count (default 1): ") or "1")
        
        print(f"\n🔄 Optimizing cache...")
        result = await self.caching_service.optimize_cache_storage(
            max_age_days=max_age,
            max_size_gb=max_size,
            min_access_count=min_access
        )
        
        space_opt = result.get('space_optimization', {})
        entries_opt = result.get('entries_optimization', {})
        
        print(f"✅ Optimization completed:")
        print(f"   Space freed: {space_opt.get('space_freed_mb', 0):.2f} MB")
        print(f"   Entries removed: {entries_opt.get('entries_removed', 0)}")
        print(f"   Processing time: {result.get('processing_time_seconds', 0):.2f}s")
    
    async def _validate_cache(self):
        """Validate cache integrity."""
        print("\n🔧 Cache Integrity Validation")
        
        result = await self.caching_service.validate_cache_integrity()
        
        print(f"✅ Validation completed:")
        print(f"   Status: {result.get('overall_status', 'unknown')}")
        print(f"   Validation time: {result.get('validation_time_seconds', 0):.2f}s")
        
        issues = result.get('integrity_check', {}).get('issues_found', [])
        if issues:
            print(f"   ⚠️  Issues found: {len(issues)}")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"      - {issue}")
        else:
            print("   ✅ No integrity issues found")
    
    async def _run_performance_tests(self):
        """Run automated performance testing."""
        print("\n⚡ Performance Testing Suite")
        print("-" * 35)
        
        test_scenarios = [
            {
                'name': 'Small Dataset (1 collection, 1 day)',
                'collections': self.test_collections[:1],
                'days': 1
            },
            {
                'name': 'Medium Dataset (2 collections, 7 days)',
                'collections': self.test_collections[:2],
                'days': 7
            },
            {
                'name': 'Large Dataset (All collections, 30 days)',
                'collections': self.test_collections,
                'days': 30
            }
        ]
        
        results = []
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🧪 Test {i}: {scenario['name']}")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=scenario['days'])
            
            try:
                start_time = datetime.now()
                result = await self.caching_service.execute_cache_aware_tracking(
                    user_id="performance_test",
                    collections=scenario['collections'],
                    start_time=start_date,
                    end_time=end_date,
                    config=CrossVideoTrackingConfig(),
                    background=False
                )
                execution_time = (datetime.now() - start_time).total_seconds()
                
                test_result = {
                    'scenario': scenario['name'],
                    'execution_time': execution_time,
                    'cache_hit_rate': result.get('cache_utilization', {}).get('cache_hit_rate', 0),
                    'total_videos': result.get('cache_utilization', {}).get('total_videos', 0),
                    'success': result.get('success', False)
                }
                results.append(test_result)
                
                print(f"   ✅ Completed in {execution_time:.2f}s")
                print(f"   Cache hit rate: {test_result['cache_hit_rate']:.1f}%")
                print(f"   Total videos: {test_result['total_videos']}")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                results.append({
                    'scenario': scenario['name'],
                    'error': str(e),
                    'success': False
                })
        
        # Display summary
        print(f"\n📊 Performance Test Summary:")
        print("-" * 40)
        
        successful_tests = [r for r in results if r.get('success')]
        if successful_tests:
            avg_time = sum(r['execution_time'] for r in successful_tests) / len(successful_tests)
            avg_cache_rate = sum(r['cache_hit_rate'] for r in successful_tests) / len(successful_tests)
            
            print(f"   Successful tests: {len(successful_tests)}/{len(results)}")
            print(f"   Average execution time: {avg_time:.2f}s")
            print(f"   Average cache hit rate: {avg_cache_rate:.1f}%")
        else:
            print("   ❌ No successful tests")
    
    async def _configure_algorithm(self):
        """Interactive algorithm configuration."""
        print("\n🔧 Algorithm Configuration")
        print("-" * 30)
        
        config = CrossVideoTrackingConfig()
        
        print(f"\nCurrent Configuration:")
        print(f"   Max Gap Seconds: {config.max_gap_seconds}")
        print(f"   Min Sequence Length: {config.min_sequence_length}")
        print(f"   IoU Threshold: {config.iou_threshold}")
        print(f"   Min Overlap Confidence: {config.min_overlap_confidence}")
        print(f"   Confidence Weights: IoU={config.confidence_weight_iou}, "
              f"Temporal={config.confidence_weight_temporal}, "
              f"Spatial={config.confidence_weight_spatial}")
        
        modify = input("\nModify configuration? (y/N): ").strip().lower() == 'y'
        
        if modify:
            try:
                config.max_gap_seconds = int(input(f"Max Gap Seconds ({config.max_gap_seconds}): ") or config.max_gap_seconds)
                config.min_sequence_length = int(input(f"Min Sequence Length ({config.min_sequence_length}): ") or config.min_sequence_length)
                config.iou_threshold = float(input(f"IoU Threshold ({config.iou_threshold}): ") or config.iou_threshold)
                config.min_overlap_confidence = float(input(f"Min Overlap Confidence ({config.min_overlap_confidence}): ") or config.min_overlap_confidence)
                
                print("\n✅ Configuration updated successfully")
                return config
                
            except ValueError as e:
                print(f"❌ Invalid input: {e}")
        
        return config
    
    async def _generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n📈 Generating Test Report...")
        
        try:
            # Get cache status
            cache_report = await self.caching_service.get_cache_performance_report()
            
            # Run quick validation
            validation_result = await self.caching_service.validate_cache_integrity()
            
            # Create report
            report = {
                'report_generated_at': datetime.now().isoformat(),
                'system_status': {
                    'database_connected': self.db_connection is not None,
                    'cache_service_initialized': self.caching_service is not None,
                    'overall_health': 'healthy' if validation_result.get('overall_status') == 'healthy' else 'issues'
                },
                'cache_performance': cache_report,
                'integrity_validation': validation_result,
                'test_collections': self.test_collections
            }
            
            # Save report
            report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"✅ Test report saved to: {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")
            print(f"❌ Failed to generate report: {e}")
    
    async def _monitor_background_session(self, session_uuid: str):
        """Monitor background session progress."""
        print(f"\n📊 Monitoring session {session_uuid}...")
        
        monitor = input("Monitor progress? (Y/n): ").strip().lower() != 'n'
        
        if not monitor:
            return
        
        print("🔄 Monitoring (Ctrl+C to stop)...")
        
        try:
            while True:
                status = await self.caching_service.session_manager.get_session_status(
                    session_uuid
                )
                
                if status.get('status') in ['completed', 'failed', 'not_found']:
                    break
                
                progress = status.get('progress_percentage', 0)
                print(f"\r   Progress: {progress:.1f}% - {status.get('status')}", end='', flush=True)
                
                await asyncio.sleep(2)
            
            print(f"\n✅ Session {status.get('status')}")
            
            if status.get('status') == 'completed':
                print(f"   Individuals found: {status.get('individuals_found', 0)}")
                print(f"   Processing time: {status.get('processing_time_seconds', 0):.2f}s")
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Stopped monitoring session {session_uuid}")
    
    def _display_tracking_results(self, result: Dict[str, Any], execution_time: float):
        """Display tracking execution results."""
        print(f"\n✅ Tracking Execution Results")
        print("-" * 35)
        
        if result.get('success', True):
            cache_util = result.get('cache_utilization', {})
            session_info = result.get('session_info', {})
            
            print(f"   Session UUID: {session_info.get('session_uuid', 'N/A')}")
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Execution Time: {execution_time:.2f}s")
            print(f"   Cache Hit Rate: {cache_util.get('cache_hit_rate', 0):.1f}%")
            print(f"   Total Videos: {cache_util.get('total_videos', 0)}")
            print(f"   Cached Videos: {cache_util.get('cached_videos', 0)}")
            print(f"   Force Reprocess: {cache_util.get('force_reprocess', False)}")
            
        else:
            print(f"   ❌ Execution failed: {result.get('error', 'Unknown error')}")
    
    def _get_date_input(self, prompt: str) -> datetime:
        """Get date input from user."""
        while True:
            try:
                date_str = input(prompt).strip()
                if not date_str:
                    # Default to today
                    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print("❌ Invalid date format. Please use YYYY-MM-DD")


async def main():
    """Main entry point for the testing script."""
    parser = argparse.ArgumentParser(
        description="Cross-Video Individual Tracking Testing Interface"
    )
    parser.add_argument(
        '--auto-test',
        action='store_true',
        help='Run automated test suite'
    )
    parser.add_argument(
        '--cache-status',
        action='store_true',
        help='Display cache status and exit'
    )
    parser.add_argument(
        '--performance-test',
        action='store_true',
        help='Run performance testing suite'
    )
    
    args = parser.parse_args()
    
    tester = CrossVideoTrackingTester()
    
    try:
        await tester.initialize()
        
        if args.cache_status:
            await tester._display_cache_status()
        elif args.performance_test:
            await tester._run_performance_tests()
        elif args.auto_test:
            print("🧪 Running automated test suite...")
            await tester._run_performance_tests()
            await tester._display_cache_status()
            await tester._generate_test_report()
        else:
            await tester.run_interactive_mode()
            
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrupted by user")
    except Exception as e:
        logger.error(f"Testing failed: {e}")
        print(f"❌ Testing failed: {e}")
    finally:
        if tester.db_connection:
            await tester.db_connection.close()


if __name__ == "__main__":
    asyncio.run(main())