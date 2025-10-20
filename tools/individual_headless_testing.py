#!/usr/bin/env python3
"""
🧪 Individual Headless Testing Script
PPL Meta Platform - Cross-Video Individual Tracking

This script provides interactive testing for the cross-video individual tracking algorithm.
Features:
- Time frame and collection selection
- Algorithm execution with real-time progress
- Comprehensive results display
- Cache management operations
- Performance metrics and validation

Usage:
    python individual_headless_testing.py

Requirements:
    - Python 3.9+
    - requests
    - rich (for beautiful console output)
    - python-dateutil

Author: PPL Meta Platform Team
Date: October 19, 2025
Version: 1.0.0
"""

import sys
import json
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import argparse

# Rich console imports for beautiful output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.prompt import Prompt, Confirm
    from rich.layout import Layout
    from rich.live import Live
    from rich.tree import Tree
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Rich not available. Install with: pip install rich")
    print("Falling back to basic console output...")

# Date parsing
try:
    from dateutil import parser as date_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    print("⚠️  python-dateutil not available. Install with: pip install python-dateutil")


@dataclass
class TestConfig:
    """Test configuration settings."""
    api_base_url: str = "http://localhost:8008"
    api_version: str = "v1"
    timeout: int = 30
    auth_token: Optional[str] = None
    debug: bool = False
    # Test user credentials
    test_username: str = "fresh.user@example.com"
    test_password: str = "NewPassword234!"
    node_service_url: str = "http://localhost:8001"


@dataclass
class TrackingRequest:
    """Tracking algorithm request parameters."""
    collections: List[str]
    start_time: datetime
    end_time: datetime
    config: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to API request format."""
        return {
            "collections": self.collections,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "algorithm_config": {
                "config_name": "default_headless_testing",
                "description": "Default configuration for headless testing",
                "is_default": False,
                "max_gap_seconds": self.config.get("max_gap_seconds", 3) if self.config else 3,
                "min_sequence_length": 2,
                "iou_threshold": self.config.get("iou_threshold", 0.3) if self.config else 0.3,
                "min_overlap_confidence": self.config.get("min_overlap_confidence", 0.5) if self.config else 0.5,
                "min_appearances": 2,
                "confidence_weight_iou": self.config.get("confidence_weight_iou", 0.4) if self.config else 0.4,
                "confidence_weight_temporal": self.config.get("confidence_weight_temporal", 0.3) if self.config else 0.3,
                "confidence_weight_spatial": self.config.get("confidence_weight_spatial", 0.3) if self.config else 0.3,
                "max_collections": 10,
                "batch_size": 20
            },
            "background_processing": False,
            "force_reprocess": False,
            "description": f"Headless testing session for {len(self.collections)} collections"
        }


class ConsoleOutput:
    """Console output handler with Rich fallback."""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        
    def print(self, *args, **kwargs):
        """Print with Rich or fallback to regular print."""
        if self.console:
            self.console.print(*args, **kwargs)
        else:
            print(*args, **kwargs)
    
    def input(self, prompt: str) -> str:
        """Input with Rich or fallback."""
        if RICH_AVAILABLE:
            return Prompt.ask(prompt)
        else:
            return input(f"{prompt}: ")
    
    def confirm(self, prompt: str) -> bool:
        """Confirmation with Rich or fallback."""
        if RICH_AVAILABLE:
            return Confirm.ask(prompt)
        else:
            response = input(f"{prompt} (y/N): ").lower()
            return response in ['y', 'yes']
    
    def create_table(self, title: str, columns: List[str]) -> 'Table':
        """Create table with Rich or return None."""
        if RICH_AVAILABLE:
            table = Table(title=title, box=box.ROUNDED)
            for col in columns:
                table.add_column(col, style="cyan")
            return table
        return None
    
    def create_panel(self, content: str, title: str) -> 'Panel':
        """Create panel with Rich or return content."""
        if RICH_AVAILABLE:
            return Panel(content, title=title, border_style="blue")
        else:
            return f"\n=== {title} ===\n{content}\n" + "="*50


class APIClient:
    """API client for cross-video tracking endpoints."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.base_url = (f"{config.api_base_url}/api/{config.api_version}/"
                         f"cross-video")
        self.session = requests.Session()
        
        # Auto-authenticate if no token provided
        if not config.auth_token:
            config.auth_token = self._authenticate()
        
        if config.auth_token:
            self.session.headers.update({
                "Authorization": f"Bearer {config.auth_token}"
            })
    
    def _authenticate(self) -> Optional[str]:
        """Authenticate with test user credentials and return token."""
        try:
            auth_url = f"{self.config.node_service_url}/api/v1/users/login"
            auth_data = {
                'username': self.config.test_username,
                'password': self.config.test_password
            }
            
            response = requests.post(
                auth_url,
                data=auth_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            auth_result = response.json()
            token = auth_result.get('access_token')
            
            if self.config.debug:
                print(f"🔐 Authentication successful for {self.config.test_username}")
            
            return token
            
        except Exception as e:
            if self.config.debug:
                print(f"❌ Authentication failed: {e}")
            return None
    
    def create_tracking_session(self, request: TrackingRequest) -> Dict:
        """Create new tracking session."""
        url = f"{self.base_url}/individuals/tracking/sessions"
        response = self.session.post(
            url, 
            json=request.to_dict(),
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_session_status(self, session_uuid: str) -> Dict:
        """Get tracking session status."""
        url = f"{self.base_url}/individuals/tracking/sessions/{session_uuid}"
        response = self.session.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_session_results(self, session_uuid: str, include_details: bool = True) -> Dict:
        """Get tracking session results."""
        url = f"{self.base_url}/individuals/tracking/sessions/{session_uuid}/results"
        params = {"include_details": include_details}
        response = self.session.get(url, params=params, timeout=self.config.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_cache_status(self, collections: Optional[List[str]] = None) -> Dict:
        """Get cache status and statistics."""
        url = f"{self.base_url}/individuals/cache/status"
        params = {"collections": collections} if collections else {}
        response = self.session.get(url, params=params, timeout=self.config.timeout)
        response.raise_for_status()
        return response.json()
    
    def clear_collection_cache(self, collections: List[str], **kwargs) -> Dict:
        """Clear cache for specific collections."""
        url = f"{self.base_url}/individuals/cache/collections"
        data = {"collections": collections, **kwargs}
        response = self.session.delete(url, json=data, timeout=self.config.timeout)
        response.raise_for_status()
        return response.json()
    
    def clear_all_cache(self) -> Dict:
        """Clear all cache (destructive operation)."""
        url = f"{self.base_url}/individuals/cache/all"
        params = {"confirm_operation": "CONFIRM_CLEAR_ALL_CACHE"}
        response = self.session.delete(url, params=params, timeout=self.config.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_available_collections(self) -> List[Dict]:
        """Fetch available collections from the media service."""
        try:
            # Use media service endpoint to get collections
            media_url = "http://localhost:8000/api/v1/media/collections"
            response = self.session.get(media_url, timeout=self.config.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Fallback to empty list if media service unavailable
            return []


class IndividualTrackingTester:
    """Main testing class for cross-video individual tracking."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.console = ConsoleOutput()
        self.api = APIClient(config)
    
    def run(self):
        """Main testing loop."""
        self.console.print("\n🧪 [bold blue]Individual Cross-Video Tracking - Headless Testing[/bold blue]\n")
        self.console.print("PPL Meta Platform v2.19.13+")
        self.console.print("Testing Script v1.0.0 - October 19, 2025")
        
        # Show authentication status
        if self.config.auth_token:
            self.console.print("🔐 [green]Authenticated[/green] (auto-login successful)")
        else:
            self.console.print("❌ [red]Authentication failed[/red] - some features may not work")
        
        self.console.print()
        
        while True:
            try:
                choice = self.show_main_menu()
                
                if choice == "1":
                    self.run_tracking_algorithm()
                elif choice == "2":
                    self.view_cache_status()
                elif choice == "3":
                    self.manage_cache()
                elif choice == "4":
                    self.run_performance_test()
                elif choice == "5":
                    self.configure_settings()
                elif choice == "6":
                    self.console.print("\n👋 [bold green]Goodbye![/bold green]")
                    break
                else:
                    self.console.print("\n❌ [bold red]Invalid option. Please try again.[/bold red]")
                
                self.console.input("\n📝 Press Enter to continue...")
                
            except KeyboardInterrupt:
                self.console.print("\n\n👋 [bold yellow]Interrupted by user. Goodbye![/bold yellow]")
                break
            except Exception as e:
                self.console.print(f"\n💥 [bold red]Error: {str(e)}[/bold red]")
                if self.config.debug:
                    import traceback
                    self.console.print(f"\n[red]{traceback.format_exc()}[/red]")
    
    def show_main_menu(self) -> str:
        """Display main menu and get user choice."""
        self.console.print("\n" + "="*60)
        self.console.print("🎯 [bold]MAIN MENU[/bold]")
        self.console.print("="*60)
        self.console.print("1. 🔍 Run Cross-Video Individual Tracking")
        self.console.print("2. 📊 View Cache Status & Statistics")
        self.console.print("3. 🧹 Manage Cache (Clear/Reset)")
        self.console.print("4. ⚡ Run Performance Testing")
        self.console.print("5. ⚙️  Configure Settings")
        self.console.print("6. 🚪 Exit")
        self.console.print("="*60)
        
        return self.console.input("Select option (1-6)")
    
    def run_tracking_algorithm(self):
        """Run the cross-video individual tracking algorithm."""
        self.console.print("\n🔍 [bold blue]Cross-Video Individual Tracking[/bold blue]")
        
        # Step 1: Get time frame
        start_time, end_time = self.get_time_frame()
        if not start_time or not end_time:
            return
        
        # Step 2: Get collections
        collections = self.get_collections()
        if not collections:
            return
        
        # Step 3: Get algorithm configuration
        config = self.get_algorithm_config()
        
        # Step 4: Create tracking request
        request = TrackingRequest(
            collections=collections,
            start_time=start_time,
            end_time=end_time,
            config=config
        )
        
        # Step 5: Execute tracking
        self.execute_tracking(request)
    
    def get_time_frame(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get time frame from user input."""
        self.console.print("\n⏰ [bold]Time Frame Selection[/bold]")
        
        # Provide quick options
        quick_options = {
            "1": ("Last 1 hour", timedelta(hours=1)),
            "2": ("Last 6 hours", timedelta(hours=6)),
            "3": ("Last 24 hours", timedelta(hours=24)),
            "4": ("Last 3 days", timedelta(days=3)),
            "5": ("Last week", timedelta(weeks=1)),
            "6": ("Custom time range", None)
        }
        
        self.console.print("\nQuick time range options:")
        for key, (desc, delta) in quick_options.items():
            self.console.print(f"{key}. {desc}")
        
        choice = self.console.input("Select time range (1-6)")
        
        if choice in quick_options and choice != "6":
            end_time = datetime.now()
            start_time = end_time - quick_options[choice][1]
            self.console.print(f"📅 Selected: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
            return start_time, end_time
        
        elif choice == "6":
            return self.get_custom_time_range()
        
        else:
            self.console.print("❌ Invalid option")
            return None, None
    
    def get_custom_time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get custom time range from user."""
        self.console.print("\n📅 [bold]Custom Time Range[/bold]")
        self.console.print("Format: YYYY-MM-DD HH:MM or YYYY-MM-DD")
        
        try:
            start_str = self.console.input("Start time")
            end_str = self.console.input("End time")
            
            if DATEUTIL_AVAILABLE:
                start_time = date_parser.parse(start_str)
                end_time = date_parser.parse(end_str)
            else:
                # Basic parsing fallback
                start_time = datetime.fromisoformat(start_str.replace('/', '-').replace(' ', 'T'))
                end_time = datetime.fromisoformat(end_str.replace('/', '-').replace(' ', 'T'))
            
            if start_time >= end_time:
                self.console.print("❌ Start time must be before end time")
                return None, None
            
            self.console.print(f"📅 Time range: {start_time} to {end_time}")
            return start_time, end_time
            
        except Exception as e:
            self.console.print(f"❌ Invalid date format: {e}")
            return None, None
    
    def get_collections(self) -> Optional[List[str]]:
        """Get collections from user input with real collection discovery."""
        self.console.print("\n📂 [bold]Collection Selection[/bold]")
        
        # Fetch real collections from media service
        try:
            collections_data = self.api.get_available_collections()
            if collections_data:
                self.console.print("\n✅ [green]Available Collections:[/green]")
                
                # Group collections by camera type for better UX
                usb_collections = []
                rtsp_collections = []
                mobile_collections = []
                other_collections = []
                
                for col in collections_data:
                    name = col["name"]
                    device_id = col.get("camera_device_id", "")
                    
                    if "usb" in device_id.lower() or "USB Camera" in name:
                        usb_collections.append(name)
                    elif "rtsp" in device_id.lower() or "Nick desk" in name:
                        rtsp_collections.append(name)
                    elif "mobile" in device_id.lower() or "mcam-" in name:
                        mobile_collections.append(name)
                    else:
                        other_collections.append(name)
                
                # Display collections by type
                if usb_collections:
                    self.console.print("📹 [blue]USB Cameras:[/blue]")
                    for col in usb_collections:
                        self.console.print(f"  - {col}")
                
                if rtsp_collections:
                    self.console.print("🌐 [cyan]RTSP Cameras:[/cyan]")
                    for col in rtsp_collections:
                        self.console.print(f"  - {col}")
                
                if mobile_collections:
                    self.console.print("📱 [magenta]Mobile Cameras:[/magenta]")
                    for col in mobile_collections:
                        self.console.print(f"  - {col}")
                        
                if other_collections:
                    self.console.print("📁 [yellow]Other Collections:[/yellow]")
                    for col in other_collections:
                        self.console.print(f"  - {col}")
                
                # Quick selection options
                self.console.print("\n🚀 [bold]Quick Selection Options:[/bold]")
                self.console.print("1️⃣  Type 'usb' for USB camera collections")
                self.console.print("2️⃣  Type 'rtsp' for RTSP camera collections")
                self.console.print("3️⃣  Type 'mobile' for mobile camera collections")
                self.console.print("4️⃣  Type 'all' for all available collections")
                self.console.print("➡️  Or enter specific collection names (comma-separated)")
                
            else:
                self.console.print("⚠️ [yellow]Could not fetch collections from media service[/yellow]")
                self.console.print("💡 [dim]Fallback: Using manual input[/dim]")
                
        except Exception as e:
            self.console.print(f"❌ [red]Error fetching collections: {e}[/red]")
            self.console.print("💡 [dim]Fallback: Using manual input[/dim]")
            collections_data = []
        
        collection_input = self.console.input("\nEnter collection selection")
        if not collection_input.strip():
            self.console.print("❌ No collections specified")
            return None
        
        # Handle quick selections
        if collection_input.lower() == 'usb':
            collections = [col["name"] for col in collections_data if "usb" in col.get("camera_device_id", "").lower() or "USB Camera" in col["name"]]
        elif collection_input.lower() == 'rtsp':
            collections = [col["name"] for col in collections_data if "rtsp" in col.get("camera_device_id", "").lower() or "Nick desk" in col["name"]]
        elif collection_input.lower() == 'mobile':
            collections = [col["name"] for col in collections_data if "mobile" in col.get("camera_device_id", "").lower() or "mcam-" in col["name"]]
        elif collection_input.lower() == 'all':
            collections = [col["name"] for col in collections_data]
        else:
            # Manual collection names
            collections = [c.strip() for c in collection_input.split(",")]
        
        if not collections:
            self.console.print("❌ No valid collections selected")
            return None
            
        self.console.print(f"📂 Selected collections: {collections}")
        return collections
    
    def get_algorithm_config(self) -> Dict:
        """Get algorithm configuration from user."""
        self.console.print("\n⚙️ [bold]Algorithm Configuration[/bold]")
        
        use_default = self.console.confirm("Use default algorithm parameters?")
        if use_default:
            config = {
                "max_gap_seconds": 3,
                "iou_threshold": 0.3,
                "min_overlap_confidence": 0.5,
                "confidence_weight_iou": 0.4,
                "confidence_weight_temporal": 0.3,
                "confidence_weight_spatial": 0.3
            }
            self.console.print("✅ Using default configuration")
            return config
        
        # Custom configuration
        self.console.print("🔧 Custom Configuration:")
        try:
            config = {
                "max_gap_seconds": int(self.console.input("Max gap between videos (seconds) [3]") or "3"),
                "iou_threshold": float(self.console.input("IoU threshold [0.3]") or "0.3"),
                "min_overlap_confidence": float(self.console.input("Min overlap confidence [0.5]") or "0.5"),
                "confidence_weight_iou": float(self.console.input("IoU weight [0.4]") or "0.4"),
                "confidence_weight_temporal": float(self.console.input("Temporal weight [0.3]") or "0.3"),
                "confidence_weight_spatial": float(self.console.input("Spatial weight [0.3]") or "0.3")
            }
            return config
        except ValueError as e:
            self.console.print(f"❌ Invalid configuration: {e}")
            return self.get_algorithm_config()
    
    def execute_tracking(self, request: TrackingRequest):
        """Execute the tracking algorithm with progress monitoring."""
        self.console.print("\n🚀 [bold blue]Executing Cross-Video Individual Tracking[/bold blue]")
        
        try:
            # Create session
            self.console.print("📋 Creating tracking session...")
            session_response = self.api.create_tracking_session(request)
            session_uuid = session_response["session_uuid"]
            
            self.console.print(f"✅ Session created: {session_uuid}")
            
            # Monitor progress
            self.monitor_session_progress(session_uuid)
            
            # Get and display results
            self.display_session_results(session_uuid)
            
        except requests.exceptions.ConnectionError:
            self.console.print("❌ [bold red]Connection failed. Is the API server running?[/bold red]")
        except requests.exceptions.HTTPError as e:
            self.console.print(f"❌ [bold red]API Error: {e.response.status_code} - {e.response.text}[/bold red]")
        except Exception as e:
            self.console.print(f"❌ [bold red]Execution failed: {str(e)}[/bold red]")
    
    def monitor_session_progress(self, session_uuid: str):
        """Monitor session progress with live updates."""
        self.console.print("\n⏳ [bold]Monitoring Progress...[/bold]")
        
        start_time = time.time()
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console.console
            ) as progress:
                
                task = progress.add_task("Processing videos...", total=100)
                
                while True:
                    try:
                        status = self.api.get_session_status(session_uuid)
                        
                        if status["status"] == "completed":
                            progress.update(task, completed=100)
                            self.console.print("✅ [bold green]Processing completed![/bold green]")
                            break
                        elif status["status"] == "failed":
                            self.console.print("❌ [bold red]Processing failed![/bold red]")
                            break
                        
                        # Update progress
                        if status.get("total_videos", 0) > 0:
                            percentage = (status.get("processed_videos", 0) / status["total_videos"]) * 100
                            progress.update(task, completed=percentage)
                            progress.update(task, description=f"Processing videos... {status.get('processed_videos', 0)}/{status.get('total_videos', 0)}")
                        
                        time.sleep(2)
                        
                    except Exception as e:
                        self.console.print(f"⚠️ Status check error: {e}")
                        time.sleep(5)
        else:
            # Fallback without Rich
            while True:
                try:
                    status = self.api.get_session_status(session_uuid)
                    
                    if status["status"] == "completed":
                        print("✅ Processing completed!")
                        break
                    elif status["status"] == "failed":
                        print("❌ Processing failed!")
                        break
                    
                    elapsed = time.time() - start_time
                    print(f"⏳ Processing... {status.get('processed_videos', 0)}/{status.get('total_videos', 0)} videos ({elapsed:.1f}s elapsed)")
                    time.sleep(5)
                    
                except Exception as e:
                    print(f"⚠️ Status check error: {e}")
                    time.sleep(10)
    
    def display_session_results(self, session_uuid: str):
        """Display comprehensive session results."""
        self.console.print("\n📊 [bold blue]Results Analysis[/bold blue]")
        
        try:
            results = self.api.get_session_results(session_uuid)
            
            # Summary statistics
            self.display_summary_statistics(results)
            
            # Individual profiles
            if results.get("individuals"):
                self.display_individual_profiles(results["individuals"])
            
            # Performance metrics
            self.display_performance_metrics(results)
            
        except Exception as e:
            self.console.print(f"❌ Failed to get results: {e}")
    
    def display_summary_statistics(self, results: Dict):
        """Display summary statistics."""
        stats = results.get("session", {})
        
        if RICH_AVAILABLE:
            # Create summary table
            table = self.console.create_table("📊 Summary Statistics", ["Metric", "Value"])
            
            table.add_row("🎯 Individuals Found", str(stats.get("individuals_found", 0)))
            table.add_row("📹 Videos Processed", str(stats.get("processed_videos", 0)))
            table.add_row("👥 Person Objects", str(stats.get("person_objects_processed", 0)))
            table.add_row("⚡ Cache Hits", str(stats.get("cache_hits", 0)))
            table.add_row("⏱️ Processing Time", f"{stats.get('processing_time_seconds', 0):.2f}s")
            
            if stats.get("total_videos", 0) > 0:
                cache_hit_rate = (stats.get("cache_hits", 0) / stats["total_videos"]) * 100
                table.add_row("📈 Cache Hit Rate", f"{cache_hit_rate:.1f}%")
            
            self.console.print(table)
        else:
            # Fallback table
            print("\n📊 Summary Statistics:")
            print(f"🎯 Individuals Found: {stats.get('individuals_found', 0)}")
            print(f"📹 Videos Processed: {stats.get('processed_videos', 0)}")
            print(f"👥 Person Objects: {stats.get('person_objects_processed', 0)}")
            print(f"⚡ Cache Hits: {stats.get('cache_hits', 0)}")
            print(f"⏱️ Processing Time: {stats.get('processing_time_seconds', 0):.2f}s")
    
    def display_individual_profiles(self, individuals: List[Dict]):
        """Display individual profiles."""
        self.console.print(f"\n👥 [bold]Individual Profiles ({len(individuals)} found)[/bold]")
        
        for idx, individual in enumerate(individuals[:10], 1):  # Show first 10
            self.display_individual_profile(individual, idx)
        
        if len(individuals) > 10:
            self.console.print(f"\n... and {len(individuals) - 10} more individuals")
    
    def display_individual_profile(self, individual: Dict, index: int):
        """Display single individual profile."""
        individual_id = individual.get("individual_id", f"individual_{index:03d}")
        confidence = individual.get("confidence_score", 0) * 100
        appearances = individual.get("video_appearances", [])
        
        content = f"""
🆔 ID: {individual_id}
🎯 Confidence: {confidence:.1f}%
📹 Video Appearances: {len(appearances)}
⏰ Time Span: {self.format_time_span(appearances)}
📍 Movement Pattern: {self.format_movement_pattern(appearances)}
        """.strip()
        
        panel = self.console.create_panel(content, f"👤 Individual {index}")
        self.console.print(panel)
    
    def format_time_span(self, appearances: List[Dict]) -> str:
        """Format time span from appearances."""
        if not appearances:
            return "No appearances"
        
        start_times = [app.get("start_timestamp") for app in appearances if app.get("start_timestamp")]
        end_times = [app.get("end_timestamp") for app in appearances if app.get("end_timestamp")]
        
        if start_times and end_times:
            earliest = min(start_times)
            latest = max(end_times)
            return f"{earliest} - {latest}"
        
        return f"{len(appearances)} appearances"
    
    def format_movement_pattern(self, appearances: List[Dict]) -> str:
        """Format movement pattern description."""
        if len(appearances) <= 1:
            return "Single location"
        elif len(appearances) <= 3:
            return f"Simple path ({len(appearances)} locations)"
        else:
            return f"Complex movement ({len(appearances)} locations)"
    
    def display_performance_metrics(self, results: Dict):
        """Display performance metrics."""
        session = results.get("session", {})
        
        self.console.print("\n⚡ [bold]Performance Metrics[/bold]")
        
        total_videos = session.get("total_videos", 0)
        cache_hits = session.get("cache_hits", 0)
        processing_time = session.get("processing_time_seconds", 0)
        
        if total_videos > 0:
            videos_per_second = total_videos / processing_time if processing_time > 0 else 0
            cache_efficiency = (cache_hits / total_videos) * 100
            
            metrics = f"""
📊 Processing Rate: {videos_per_second:.2f} videos/second
💾 Cache Efficiency: {cache_efficiency:.1f}% ({cache_hits}/{total_videos})
⏱️ Average Time per Video: {(processing_time/total_videos)*1000:.1f}ms
🎯 Individuals per Video: {session.get('individuals_found', 0)/total_videos:.2f}
            """.strip()
            
            self.console.print(self.console.create_panel(metrics, "Performance Analysis"))
    
    def view_cache_status(self):
        """View cache status and statistics."""
        self.console.print("\n📊 [bold blue]Cache Status & Statistics[/bold blue]")
        
        try:
            cache_status = self.api.get_cache_status()
            self.display_cache_statistics(cache_status)
            
        except Exception as e:
            self.console.print(f"❌ Failed to get cache status: {e}")
    
    def display_cache_statistics(self, cache_status: Dict):
        """Display cache statistics."""
        if RICH_AVAILABLE:
            table = self.console.create_table("💾 Cache Statistics", ["Metric", "Value"])
            
            table.add_row("📹 Cached Videos", str(cache_status.get("total_cached_videos", 0)))
            table.add_row("👥 Total Individuals", str(cache_status.get("total_individuals", 0)))
            table.add_row("📋 Active Sessions", str(cache_status.get("total_sessions", 0)))
            table.add_row("💽 Cache Size", f"{cache_status.get('cache_size_mb', 0):.2f} MB")
            table.add_row("📈 Hit Rate (30d)", f"{cache_status.get('hit_rate_last_30_days', 0)*100:.1f}%")
            
            # Collections covered
            collections = cache_status.get("collections_covered", [])
            table.add_row("📂 Collections", ", ".join(collections) if collections else "None")
            
            self.console.print(table)
        else:
            print("\n💾 Cache Statistics:")
            print(f"📹 Cached Videos: {cache_status.get('total_cached_videos', 0)}")
            print(f"👥 Total Individuals: {cache_status.get('total_individuals', 0)}")
            print(f"📋 Active Sessions: {cache_status.get('total_sessions', 0)}")
            print(f"💽 Cache Size: {cache_status.get('cache_size_mb', 0):.2f} MB")
            print(f"📈 Hit Rate (30d): {cache_status.get('hit_rate_last_30_days', 0)*100:.1f}%")
    
    def manage_cache(self):
        """Manage cache operations."""
        self.console.print("\n🧹 [bold blue]Cache Management[/bold blue]")
        
        self.console.print("\nCache operations:")
        self.console.print("1. 📊 View cache status")
        self.console.print("2. 🗂️  Clear cache for specific collections")
        self.console.print("3. 🧹 Clear ALL cache (DESTRUCTIVE)")
        self.console.print("4. ↩️  Return to main menu")
        
        choice = self.console.input("Select option (1-4)")
        
        if choice == "1":
            self.view_cache_status()
        elif choice == "2":
            self.clear_collection_cache()
        elif choice == "3":
            self.clear_all_cache()
        elif choice == "4":
            return
        else:
            self.console.print("❌ Invalid option")
    
    def clear_collection_cache(self):
        """Clear cache for specific collections."""
        self.console.print("\n🗂️ [bold]Clear Collection Cache[/bold]")
        
        collections_input = self.console.input("Enter collection names to clear (comma-separated)")
        if not collections_input.strip():
            self.console.print("❌ No collections specified")
            return
        
        collections = [c.strip() for c in collections_input.split(",")]
        
        # Confirmation
        if not self.console.confirm(f"Clear cache for collections: {collections}?"):
            self.console.print("❌ Operation cancelled")
            return
        
        try:
            result = self.api.clear_collection_cache(collections)
            self.console.print("✅ [bold green]Cache cleared successfully![/bold green]")
            self.console.print(f"📊 {result.get('message', 'Cache clearing completed')}")
            
        except Exception as e:
            self.console.print(f"❌ Failed to clear cache: {e}")
    
    def clear_all_cache(self):
        """Clear all cache (destructive operation)."""
        self.console.print("\n🧹 [bold red]Clear ALL Cache (DESTRUCTIVE)[/bold red]")
        self.console.print("⚠️  [bold yellow]WARNING: This will delete ALL cached data and individuals![/bold yellow]")
        self.console.print("This operation cannot be undone.")
        
        # Double confirmation
        if not self.console.confirm("Are you sure you want to clear ALL cache?"):
            self.console.print("❌ Operation cancelled")
            return
        
        confirm_text = self.console.input("Type 'DELETE ALL CACHE' to confirm")
        if confirm_text != "DELETE ALL CACHE":
            self.console.print("❌ Confirmation text incorrect. Operation cancelled.")
            return
        
        try:
            result = self.api.clear_all_cache()
            self.console.print("✅ [bold green]ALL cache cleared successfully![/bold green]")
            self.console.print(f"📊 {result.get('message', 'All cache clearing completed')}")
            
        except Exception as e:
            self.console.print(f"❌ Failed to clear all cache: {e}")
    
    def run_performance_test(self):
        """Run performance testing scenarios."""
        self.console.print("\n⚡ [bold blue]Performance Testing[/bold blue]")
        self.console.print("🚧 Performance testing not implemented yet")
        self.console.print("This would include:")
        self.console.print("- Cache hit rate testing")
        self.console.print("- Processing speed benchmarks")
        self.console.print("- Memory usage monitoring")
        self.console.print("- Accuracy validation")
    
    def configure_settings(self):
        """Configure testing settings."""
        self.console.print("\n⚙️ [bold blue]Configuration Settings[/bold blue]")
        
        self.console.print(f"Current API URL: {self.config.api_base_url}")
        self.console.print(f"API Version: {self.config.api_version}")
        self.console.print(f"Timeout: {self.config.timeout}s")
        self.console.print(f"Debug Mode: {'On' if self.config.debug else 'Off'}")
        
        if self.console.confirm("Update settings?"):
            self.config.api_base_url = self.console.input(f"API URL [{self.config.api_base_url}]") or self.config.api_base_url
            self.config.timeout = int(self.console.input(f"Timeout seconds [{self.config.timeout}]") or str(self.config.timeout))
            self.config.debug = self.console.confirm("Enable debug mode?")
            
            self.console.print("✅ Settings updated")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Individual Cross-Video Tracking Headless Testing")
    parser.add_argument("--api-url", default="http://localhost:8008", help="API base URL")
    parser.add_argument("--auth-token", help="Authentication token (auto-authenticates if not provided)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    config = TestConfig(
        api_base_url=args.api_url,
        auth_token=args.auth_token,
        timeout=args.timeout,
        debug=args.debug
    )
    
    tester = IndividualTrackingTester(config)
    tester.run()


if __name__ == "__main__":
    main()