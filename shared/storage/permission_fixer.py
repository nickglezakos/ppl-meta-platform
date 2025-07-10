#!/usr/bin/env python3
"""
PPL Meta Platform - Volume Permission Fixer

This utility helps diagnose and fix common Docker volume permission issues
that can occur when containers run with different user IDs.

Author: PPL Meta Platform Team
Version: 1.0.0
Date: 2025-07-10
"""

import argparse
import grp
import logging
import os
import pwd
import stat
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VolumePermissionFixer:
    """Utility to diagnose and fix Docker volume permission issues."""

    def __init__(self):
        """Initialize the permission fixer."""
        self.common_services = {
            "postgres_data": {"uid": 999, "gid": 999},  # postgres user
            "redis_data": {"uid": 999, "gid": 999},  # redis user
            "media-storage": {"uid": 1000, "gid": 1000},  # app user
            "user-data": {"uid": 1000, "gid": 1000},  # app user
            "orchestrator-data": {"uid": 1000, "gid": 1000},  # app user
            "consul_data": {"uid": 100, "gid": 1000},  # consul user
            "prometheus_data": {"uid": 65534, "gid": 65534},  # nobody user
            "grafana_data": {"uid": 472, "gid": 472},  # grafana user
        }

    def get_volume_info(self, volume_name: str) -> Optional[Dict]:
        """Get detailed information about a Docker volume."""
        try:
            result = subprocess.run(
                ["docker", "volume", "inspect", volume_name],
                capture_output=True,
                text=True,
                check=True,
            )
            import json

            volume_info = json.loads(result.stdout)[0]
            return volume_info
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to inspect volume {volume_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing volume info for {volume_name}: {e}")
            return None

    def check_volume_permissions(self, volume_name: str) -> Dict:
        """Check the current permissions of a volume."""
        volume_info = self.get_volume_info(volume_name)
        if not volume_info:
            return {"error": "Failed to get volume information"}

        mount_point = volume_info.get("Mountpoint")
        if not mount_point or not os.path.exists(mount_point):
            return {"error": f"Mount point not found: {mount_point}"}

        try:
            # Get directory stats
            stat_info = os.stat(mount_point)
            uid = stat_info.st_uid
            gid = stat_info.st_gid
            mode = stat.filemode(stat_info.st_mode)

            # Try to get user/group names
            try:
                username = pwd.getpwuid(uid).pw_name
            except KeyError:
                username = f"uid:{uid}"

            try:
                groupname = grp.getgrgid(gid).gr_name
            except KeyError:
                groupname = f"gid:{gid}"

            # Check if this matches expected permissions
            expected = self.common_services.get(volume_name, {})
            expected_uid = expected.get("uid")
            expected_gid = expected.get("gid")

            permission_ok = True
            issues = []

            if expected_uid is not None and uid != expected_uid:
                permission_ok = False
                issues.append(f"UID mismatch: expected {expected_uid}, got {uid}")

            if expected_gid is not None and gid != expected_gid:
                permission_ok = False
                issues.append(f"GID mismatch: expected {expected_gid}, got {gid}")

            # Check if directory is writable by owner
            if not (stat_info.st_mode & stat.S_IWUSR):
                permission_ok = False
                issues.append("Directory not writable by owner")

            return {
                "volume_name": volume_name,
                "mount_point": mount_point,
                "uid": uid,
                "gid": gid,
                "username": username,
                "groupname": groupname,
                "mode": mode,
                "permission_ok": permission_ok,
                "issues": issues,
                "expected_uid": expected_uid,
                "expected_gid": expected_gid,
            }

        except Exception as e:
            return {"error": f"Failed to check permissions: {e}"}

    def fix_volume_permissions(
        self,
        volume_name: str,
        uid: Optional[int] = None,
        gid: Optional[int] = None,
        recursive: bool = True,
    ) -> bool:
        """Fix permissions for a Docker volume."""
        # Get expected permissions if not provided
        if uid is None or gid is None:
            expected = self.common_services.get(volume_name, {})
            if uid is None:
                uid = expected.get("uid", 1000)
            if gid is None:
                gid = expected.get("gid", 1000)

        logger.info(
            f"Fixing permissions for volume '{volume_name}' (uid={uid}, gid={gid}, recursive={recursive})"
        )

        try:
            # Use docker run to fix permissions
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volume_name}:/target",
                "alpine:latest",
                "chown",
            ]

            if recursive:
                cmd.append("-R")

            cmd.extend([f"{uid}:{gid}", "/target"])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Successfully fixed permissions for volume '{volume_name}'")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fix permissions for volume {volume_name}: {e}")
            return False

    def diagnose_permission_issues(self, volume_name: str) -> Dict:
        """Diagnose common permission issues with a volume."""
        check_result = self.check_volume_permissions(volume_name)

        if "error" in check_result:
            return check_result

        diagnosis = {
            "volume_name": volume_name,
            "current_permissions": check_result,
            "recommendations": [],
            "auto_fix_available": False,
        }

        if not check_result["permission_ok"]:
            # Generate recommendations
            issues = check_result["issues"]

            for issue in issues:
                if "UID mismatch" in issue:
                    diagnosis["recommendations"].append(
                        {
                            "issue": issue,
                            "solution": f"Run: fix-permissions {volume_name} --uid {check_result['expected_uid']}",
                            "command": f"fix-permissions {volume_name} --uid {check_result['expected_uid']}",
                        }
                    )

                if "GID mismatch" in issue:
                    diagnosis["recommendations"].append(
                        {
                            "issue": issue,
                            "solution": f"Run: fix-permissions {volume_name} --gid {check_result['expected_gid']}",
                            "command": f"fix-permissions {volume_name} --gid {check_result['expected_gid']}",
                        }
                    )

                if "not writable" in issue:
                    diagnosis["recommendations"].append(
                        {
                            "issue": issue,
                            "solution": "Fix directory permissions to be writable by owner",
                            "command": f"fix-permissions {volume_name}",
                        }
                    )

            # Check if we can auto-fix
            if volume_name in self.common_services:
                diagnosis["auto_fix_available"] = True
                diagnosis["auto_fix_command"] = f"fix-permissions {volume_name} --auto"

        return diagnosis

    def auto_fix_volume(self, volume_name: str) -> bool:
        """Automatically fix permissions for a known volume."""
        if volume_name not in self.common_services:
            logger.error(
                f"No auto-fix configuration available for volume '{volume_name}'"
            )
            return False

        config = self.common_services[volume_name]
        return self.fix_volume_permissions(
            volume_name, uid=config["uid"], gid=config["gid"]
        )

    def check_all_volumes(self) -> Dict:
        """Check permissions for all known volumes."""
        try:
            result = subprocess.run(
                ["docker", "volume", "ls", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                check=True,
            )
            volume_names = result.stdout.strip().split("\n")
            volume_names = [name for name in volume_names if name]  # Filter empty lines
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list volumes: {e}")
            return {"error": "Failed to list volumes"}

        results = {}
        issues_found = 0

        for volume_name in volume_names:
            if volume_name.startswith("buildx_"):
                continue  # Skip buildx volumes

            check_result = self.check_volume_permissions(volume_name)
            results[volume_name] = check_result

            if "error" not in check_result and not check_result.get(
                "permission_ok", True
            ):
                issues_found += 1

        return {
            "volumes": results,
            "total_volumes": len(volume_names),
            "issues_found": issues_found,
            "timestamp": subprocess.run(
                ["date"], capture_output=True, text=True
            ).stdout.strip(),
        }


def main():
    """Main CLI interface for permission fixing."""
    parser = argparse.ArgumentParser(
        description="PPL Meta Platform Volume Permission Fixer"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check volume permissions")
    check_parser.add_argument("volume", help="Volume name to check")

    # Check all command
    check_all_parser = subparsers.add_parser(
        "check-all", help="Check all volume permissions"
    )

    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Fix volume permissions")
    fix_parser.add_argument("volume", help="Volume name to fix")
    fix_parser.add_argument("--uid", type=int, help="User ID to set")
    fix_parser.add_argument("--gid", type=int, help="Group ID to set")
    fix_parser.add_argument(
        "--no-recursive", action="store_true", help="Don't apply recursively"
    )
    fix_parser.add_argument(
        "--auto", action="store_true", help="Use automatic configuration"
    )

    # Diagnose command
    diagnose_parser = subparsers.add_parser(
        "diagnose", help="Diagnose permission issues"
    )
    diagnose_parser.add_argument("volume", help="Volume name to diagnose")

    # List command
    list_parser = subparsers.add_parser("list", help="List known volume configurations")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    fixer = VolumePermissionFixer()

    if args.command == "check":
        result = fixer.check_volume_permissions(args.volume)

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            sys.exit(1)

        print(f"Volume: {result['volume_name']}")
        print(f"Mount Point: {result['mount_point']}")
        print(f"Owner: {result['username']} ({result['uid']})")
        print(f"Group: {result['groupname']} ({result['gid']})")
        print(f"Mode: {result['mode']}")

        if result["permission_ok"]:
            print("✅ Permissions OK")
        else:
            print("❌ Permission Issues:")
            for issue in result["issues"]:
                print(f"  - {issue}")

    elif args.command == "check-all":
        result = fixer.check_all_volumes()

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            sys.exit(1)

        print(f"Checked {result['total_volumes']} volumes")
        print(f"Issues found: {result['issues_found']}")
        print()

        for volume_name, check_result in result["volumes"].items():
            if "error" in check_result:
                print(f"❌ {volume_name}: {check_result['error']}")
            elif not check_result.get("permission_ok", True):
                print(f"⚠️  {volume_name}: {len(check_result['issues'])} issue(s)")
            else:
                print(f"✅ {volume_name}: OK")

    elif args.command == "fix":
        if args.auto:
            success = fixer.auto_fix_volume(args.volume)
        else:
            success = fixer.fix_volume_permissions(
                args.volume, uid=args.uid, gid=args.gid, recursive=not args.no_recursive
            )

        if success:
            print(f"✅ Successfully fixed permissions for volume '{args.volume}'")
        else:
            print(f"❌ Failed to fix permissions for volume '{args.volume}'")
            sys.exit(1)

    elif args.command == "diagnose":
        diagnosis = fixer.diagnose_permission_issues(args.volume)

        if "error" in diagnosis:
            print(f"❌ Error: {diagnosis['error']}")
            sys.exit(1)

        print(f"Diagnosis for volume: {diagnosis['volume_name']}")

        current = diagnosis["current_permissions"]
        if current["permission_ok"]:
            print("✅ No permission issues found")
        else:
            print("❌ Issues found:")
            for rec in diagnosis["recommendations"]:
                print(f"\n  Issue: {rec['issue']}")
                print(f"  Solution: {rec['solution']}")

        if diagnosis["auto_fix_available"]:
            print(f"\n🔧 Auto-fix available: {diagnosis['auto_fix_command']}")

    elif args.command == "list":
        print("Known volume configurations:")
        for volume_name, config in fixer.common_services.items():
            print(f"  {volume_name}: uid={config['uid']}, gid={config['gid']}")


if __name__ == "__main__":
    main()
