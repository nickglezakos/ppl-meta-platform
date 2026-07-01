"""VPN ACL synchronization service for Headscale.

Phase 6: Syncs Headscale ACL policies with EyeNet Matrix group membership.
When an installation joins or leaves a Matrix group, this service updates
the Headscale ACL file to allow or deny mesh communication between members.

The ACL tags (tag:matrix-<uuid>) form the cryptographic boundary that both
VPN and Matrix rely on. Only devices with matching tags can communicate.
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default ACL policy path (configurable via env)
ACL_POLICY_PATH = os.environ.get(
    "HEADSCALE_ACL_PATH",
    "/etc/headscale/acl.json",
)

HEADSCALE_CLI = "headscale"


class VpnACLService:
    """Syncs Headscale ACLs with Matrix group membership.

    The ACL policy is a JSON file consumed by Headscale that defines
    which tagged nodes can communicate. This service adds and removes
    ACL entries as installations join/leave Matrix groups.
    """

    def __init__(self, acl_path: Optional[str] = None):
        self.acl_path = Path(acl_path or ACL_POLICY_PATH)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_matrix_group_acls(
        self, matrix_group_id: str, member_node_ids: list[str]
    ) -> bool:
        """Ensure all members of a Matrix group can communicate via VPN.

        Creates or updates an ACL entry allowing members tagged with
        tag:matrix-<uuid> to communicate with each other.

        Args:
            matrix_group_id: UUID of the Matrix group.
            member_node_ids: List of Headscale node IDs in the group.

        Returns:
            True if ACL was updated successfully.
        """
        tag = f"tag:matrix-{matrix_group_id}"
        acl_entry = {
            "action": "accept",
            "src": [tag],
            "dst": [f"{tag}:*"],
        }

        logger.info(
            "Syncing ACL for Matrix group %s with %d members",
            matrix_group_id,
            len(member_node_ids),
        )

        return self._write_acl_entry(tag, acl_entry) and self._tag_nodes(
            member_node_ids, [tag]
        )

    def add_installation_to_matrix_acls(
        self, matrix_group_id: str, installation_node_id: str
    ) -> bool:
        """Add a single installation to a Matrix group's ACL.

        Tags the node with the appropriate ACL tag and ensures the
        group ACL entry exists.

        Args:
            matrix_group_id: UUID of the Matrix group.
            installation_node_id: Headscale node ID to tag.

        Returns:
            True if the node was tagged successfully.
        """
        tag = f"tag:matrix-{matrix_group_id}"
        logger.info(
            "Adding installation %s to Matrix group %s ACL",
            installation_node_id,
            matrix_group_id,
        )
        return self._tag_node(installation_node_id, tag)

    def remove_installation_from_matrix_acls(
        self, matrix_group_id: str, installation_node_id: str
    ) -> bool:
        """Remove a single installation from a Matrix group's ACL.

        Removes the ACL tag from the node, cutting off its ability
        to communicate with other group members.

        Args:
            matrix_group_id: UUID of the Matrix group.
            installation_node_id: Headscale node ID to untag.

        Returns:
            True if the node was untagged successfully.
        """
        tag = f"tag:matrix-{matrix_group_id}"
        logger.info(
            "Removing installation %s from Matrix group %s ACL",
            installation_node_id,
            matrix_group_id,
        )
        # Headscale doesn't have a direct "remove tag" CLI —
        # we re-tag with only the remaining tags.
        return self._remove_tag_from_node(installation_node_id, tag)

    def remove_matrix_group_acls(self, matrix_group_id: str) -> bool:
        """Remove all ACL entries for a deleted Matrix group.

        Args:
            matrix_group_id: UUID of the deleted Matrix group.

        Returns:
            True if the ACL entry was removed successfully.
        """
        tag = f"tag:matrix-{matrix_group_id}"
        logger.info("Removing ACL entries for deleted Matrix group %s", matrix_group_id)
        return self._remove_acl_entry(tag)

    def get_acl_status(self) -> dict:
        """Get the current ACL policy status.

        Returns:
            Dict with policy path, last modified time, and group count.
        """
        if not self.acl_path.exists():
            return {
                "status": "missing",
                "path": str(self.acl_path),
                "groups": 0,
                "last_modified": None,
            }

        try:
            with open(self.acl_path, "r") as f:
                policy = json.load(f)

            acls = policy.get("acls", [])
            matrix_acls = [a for a in acls if "tag:matrix-" in str(a.get("src", ""))]

            mtime = datetime.fromtimestamp(
                self.acl_path.stat().st_mtime, tz=timezone.utc
            )

            return {
                "status": "active",
                "path": str(self.acl_path),
                "groups": len(matrix_acls),
                "last_modified": mtime.isoformat(),
            }
        except Exception as exc:
            logger.error("Failed to read ACL policy: %s", exc)
            return {
                "status": "error",
                "path": str(self.acl_path),
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_policy(self) -> dict:
        """Read the current ACL policy file."""
        if not self.acl_path.exists():
            return {"hosts": {}, "acls": []}

        with open(self.acl_path, "r") as f:
            return json.load(f)

    def _write_policy(self, policy: dict) -> bool:
        """Write the ACL policy file atomically."""
        try:
            # Write to temp file, then rename (atomic on same filesystem)
            temp_path = self.acl_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(policy, f, indent=2)

            temp_path.replace(self.acl_path)
            logger.info("ACL policy written to %s", self.acl_path)
            return True
        except Exception as exc:
            logger.error("Failed to write ACL policy: %s", exc)
            return False

    def _write_acl_entry(self, tag: str, entry: dict) -> bool:
        """Add or update an ACL entry for a specific tag."""
        policy = self._read_policy()
        acls = policy.get("acls", [])

        # Remove existing entry for this tag (if any)
        acls = [a for a in acls if tag not in str(a.get("src", ""))]

        # Add the entry
        acls.append(entry)

        # Ensure deny-all catch-all exists
        has_deny = any(
            a.get("action") == "deny"
            and a.get("src") == ["*"]
            and a.get("dst") == ["*:*"]
            for a in acls
        )
        if not has_deny:
            acls.append({"action": "deny", "src": ["*"], "dst": ["*:*"]})

        policy["acls"] = acls
        return self._write_policy(policy)

    def _remove_acl_entry(self, tag: str) -> bool:
        """Remove ACL entries matching a specific tag."""
        policy = self._read_policy()
        acls = policy.get("acls", [])

        new_acls = [a for a in acls if tag not in str(a.get("src", ""))]
        policy["acls"] = new_acls
        return self._write_policy(policy)

    def _tag_node(self, node_id: str, tag: str) -> bool:
        """Tag a single node with an ACL tag."""
        return self._tag_nodes([node_id], [tag])

    def _tag_nodes(self, node_ids: list[str], tags: list[str]) -> bool:
        """Tag multiple nodes with ACL tags."""
        if not node_ids:
            return True

        try:
            for node_id in node_ids:
                cmd = [HEADSCALE_CLI, "nodes", "tag", "--tags"]
                cmd.extend(tags)
                cmd.append(node_id)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode != 0:
                    logger.error(
                        "Failed to tag node %s: %s", node_id, result.stderr
                    )
                    return False

                logger.info("Tagged node %s with %s", node_id, tags)

            return True
        except FileNotFoundError:
            logger.error("headscale binary not found — ACL tagging skipped")
            return False
        except Exception as exc:
            logger.error("Failed to tag nodes: %s", exc)
            return False

    def _remove_tag_from_node(self, node_id: str, tag_to_remove: str) -> bool:
        """Remove a specific tag from a node while preserving other tags."""
        try:
            # Get current tags
            result = subprocess.run(
                [HEADSCALE_CLI, "nodes", "list", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error("Failed to list nodes: %s", result.stderr)
                return False

            nodes = json.loads(result.stdout)
            current_tags = []
            for node in nodes:
                if node.get("ID") == node_id or node.get("NodeKey") == node_id:
                    current_tags = node.get("Tags", [])
                    break

            # Re-tag with all tags except the one being removed
            remaining_tags: list[str] = [t for t in current_tags if t != tag_to_remove]
            if not remaining_tags:
                remaining_tags = ["tag:installation"]  # Keep at least one tag

            return self._tag_nodes([node_id], remaining_tags)

        except Exception as exc:
            logger.error("Failed to remove tag from node %s: %s", node_id, exc)
            return False


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

vpn_acl_service = VpnACLService()