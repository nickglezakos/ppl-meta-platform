"""Unit tests for RTSP URL helpers (main vs substream)."""

from src.services.rtsp_url import (
    build_rtsp_url,
    get_rtsp_substream_path,
    live_connection_string,
    merge_rtsp_substream_settings,
    parse_rtsp_host_path,
    record_connection_string,
)


def test_build_and_parse_main_path():
    url = build_rtsp_url(
        host="192.168.9.19",
        port=554,
        path="/stream1",
        username="user@example.com",
        password="secret",
    )
    assert "@192.168.9.19:554/stream1" in url
    host, path = parse_rtsp_host_path(url)
    assert host == "192.168.9.19"
    assert path == "/stream1"


def test_merge_substream_settings_preserves_other_keys():
    existing = {"recording_enabled": True, "rtsp": {"other": 1}}
    merged = merge_rtsp_substream_settings(existing, "/stream2")
    assert merged["recording_enabled"] is True
    assert merged["rtsp"]["other"] == 1
    assert merged["rtsp"]["substream_path"] == "/stream2"


def test_merge_clears_substream_when_empty():
    existing = {"rtsp": {"substream_path": "/stream2", "other": 1}}
    merged = merge_rtsp_substream_settings(existing, "")
    assert "substream_path" not in merged["rtsp"]
    assert merged["rtsp"]["other"] == 1


def test_live_uses_substream_when_configured():
    main = build_rtsp_url(
        host="192.168.9.19",
        port=554,
        path="/stream1",
        username="cam",
        password="pw",
    )
    settings = merge_rtsp_substream_settings(None, "stream2")
    assert get_rtsp_substream_path(settings) == "/stream2"

    live = live_connection_string(main, "cam", "pw", 554, settings)
    record = record_connection_string(main, "cam", "pw", 554)
    assert live is not None and live.endswith("/stream2")
    assert record is not None and record.endswith("/stream1")
    assert live != record


def test_live_falls_back_to_main_without_substream():
    main = build_rtsp_url(
        host="192.168.9.19",
        port=554,
        path="/stream1",
        username="cam",
        password="pw",
    )
    live = live_connection_string(main, "cam", "pw", 554, None)
    assert live == record_connection_string(main, "cam", "pw", 554)
