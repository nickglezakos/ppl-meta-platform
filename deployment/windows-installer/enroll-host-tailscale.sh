#!/usr/bin/env bash
# Enroll the WSL host tailscaled into EyeNet Headscale.
# Node runs as appuser and cannot `tailscale up` against the host socket
# (CLI requires root). This script mints an auth key from inside Node, then
# applies it as root on the distro. Never prints the auth key.
set -euo pipefail
if tailscale status >/dev/null 2>&1; then
  if ! tailscale status 2>/dev/null | head -1 | grep -qi 'logged out'; then
    echo "EyeNet Tailscale already enrolled: $(tailscale ip -4 2>/dev/null || true)"
    exit 0
  fi
fi

if ! docker exec pplmeta-ppl-meta-node-1 true 2>/dev/null; then
  echo "WARN: node container not running — skip host Tailscale enroll"
  exit 0
fi

python3 - <<'PY'
import subprocess, sys

def sh(args, **kw):
    return subprocess.check_output(args, text=True, **kw).strip()

mint = r"""
import os, pathlib, httpx
uuid = (os.getenv("EYENET_INSTALLATION_UUID") or os.getenv("INSTALLATION_UUID") or "").strip()
key = (os.getenv("EYENET_APPLICATION_KEY") or os.getenv("APPLICATION_KEY") or "").strip()
url = (os.getenv("AUTHORITY_URL") or "https://authority.eyenet-vision.com").rstrip("/")
if not uuid or not key:
    raise SystemExit("missing uuid/key")
resp = httpx.post(f"{url}/api/v1/vpn/enroll-installation", json={
    "installation_uuid": uuid,
    "application_key": key,
    "node_type": "platform",
}, timeout=20)
resp.raise_for_status()
data = resp.json()
pathlib.Path("/tmp/eyenet-ts.auth").write_text(data["auth_key"])
pathlib.Path("/tmp/eyenet-ts.server").write_text(data.get("headscale_server") or "https://vpn.eyenet-vision.com")
print("mint_ok")
"""
try:
    print(sh(["docker", "exec", "pplmeta-ppl-meta-node-1", "python", "-c", mint]))
except subprocess.CalledProcessError as exc:
    print("WARN: could not mint EyeNet auth key (bootstrap/licence may be incomplete)", file=sys.stderr)
    sys.exit(0)

auth = sh(["docker", "exec", "-u", "0", "pplmeta-ppl-meta-node-1", "cat", "/tmp/eyenet-ts.auth"])
server = sh(["docker", "exec", "-u", "0", "pplmeta-ppl-meta-node-1", "cat", "/tmp/eyenet-ts.server"])
uuid = sh(["docker", "exec", "pplmeta-ppl-meta-node-1", "printenv", "INSTALLATION_UUID"])
host = "".join(c if c.isalnum() or c in "-_" else "-" for c in uuid) or "eyenet-node"
r = subprocess.run(
    [
        "tailscale", "up",
        "--login-server", server,
        "--auth-key", auth,
        "--accept-routes=false",
        "--accept-dns=false",
        "--hostname", host,
    ],
    capture_output=True, text=True, timeout=45,
)
subprocess.run(
    ["docker", "exec", "-u", "0", "pplmeta-ppl-meta-node-1", "rm", "-f", "/tmp/eyenet-ts.auth", "/tmp/eyenet-ts.server"],
    check=False,
)
err = (r.stderr or "").replace(auth, "[redacted]")
if r.returncode != 0:
    print(f"WARN: tailscale up failed (exit={r.returncode}): {err.strip()[:300]}", file=sys.stderr)
    sys.exit(0)
print("EyeNet Tailscale enrolled:", subprocess.check_output(["tailscale", "ip", "-4"], text=True).strip())
PY
