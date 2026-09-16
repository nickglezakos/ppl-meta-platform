"""Tests for LAN/VPN advertise-host rewriting (Docker/WSL/Lima)."""

from datetime import datetime

import main as discovery_main
from models.service_models import ServiceInfo, ServiceList, ServiceStatus, ServiceType


def _svc(name: str, host: str, port: int = 8001) -> ServiceInfo:
    now = datetime.utcnow()
    return ServiceInfo(
        service_id=f"id-{name}",
        name=name,
        service_type=ServiceType.BACKEND,
        version="1.0.0",
        host=host,
        port=port,
        health_endpoint="/health",
        status=ServiceStatus.HEALTHY,
        capabilities=[],
        metadata={},
        registered_at=now,
        last_seen=now,
        heartbeat_count=0,
    )


def test_docker_bridge_and_compose_hosts_need_rewrite():
    assert discovery_main._needs_host_rewrite("172.18.0.12")
    assert discovery_main._needs_host_rewrite("ppl-meta-node")
    assert discovery_main._needs_host_rewrite("0.0.0.0")
    assert discovery_main._needs_host_rewrite("127.0.0.1")
    assert discovery_main._needs_host_rewrite("localhost")
    assert not discovery_main._needs_host_rewrite("192.168.11.14")
    assert not discovery_main._needs_host_rewrite("100.64.0.1")


def test_resolve_rewrites_to_advertise_host(monkeypatch):
    monkeypatch.setattr(
        discovery_main,
        "get_settings",
        lambda: type("S", (), {"ADVERTISE_HOST": "192.168.11.14"})(),
    )
    monkeypatch.setattr(discovery_main, "get_tailscale_ip", lambda: None)

    services = ServiceList(
        services=[
            _svc("ppl-meta-gateway", "172.18.0.12", 8080),
            _svc("ppl-meta-node", "ppl-meta-node", 8001),
            _svc("already-lan", "192.168.11.50", 9000),
        ],
        total_count=3,
        healthy_count=3,
    )
    resolved = discovery_main.resolve_service_hosts(services)
    by_name = {s.name: s for s in resolved.services}
    assert by_name["ppl-meta-gateway"].host == "192.168.11.14"
    assert by_name["ppl-meta-gateway"].port == 8080
    assert by_name["ppl-meta-node"].host == "192.168.11.14"
    assert by_name["already-lan"].host == "192.168.11.50"


def test_get_advertise_host_prefers_env(monkeypatch):
    monkeypatch.setattr(
        discovery_main,
        "get_settings",
        lambda: type("S", (), {"ADVERTISE_HOST": "10.0.0.5"})(),
    )
    monkeypatch.setattr(discovery_main, "get_tailscale_ip", lambda: "100.64.0.2")
    assert discovery_main.get_advertise_host() == "10.0.0.5"
