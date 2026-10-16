"""Decoder-limit checks for signage playback."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.signage_video_compat import signage_stream_needs_transcode


def test_portrait_high_level_5_exceeds_signage_decoder():
    # TB330FU / Helio G88: 1440x2732 High@L5.0 -> NO_EXCEEDS_CAPABILITIES
    stream = {
        "codec_name": "h264",
        "profile": "High",
        "width": 1440,
        "height": 2732,
        "pix_fmt": "yuv420p",
        "level": 50,
        "avg_frame_rate": "25/1",
    }
    assert signage_stream_needs_transcode(stream) is True


def test_1080p_high_level_4_is_playable():
    stream = {
        "codec_name": "h264",
        "profile": "High",
        "width": 1920,
        "height": 1080,
        "pix_fmt": "yuv420p",
        "level": 40,
        "avg_frame_rate": "30/1",
    }
    assert signage_stream_needs_transcode(stream) is False


def test_hevc_and_10bit_need_transcode():
    hevc = {
        "codec_name": "hevc",
        "profile": "Main",
        "width": 1280,
        "height": 720,
        "pix_fmt": "yuv420p",
        "level": 93,
        "avg_frame_rate": "30/1",
    }
    ten_bit = {
        "codec_name": "h264",
        "profile": "High 10",
        "width": 1280,
        "height": 720,
        "pix_fmt": "yuv420p10le",
        "level": 31,
        "avg_frame_rate": "24/1",
    }
    assert signage_stream_needs_transcode(hevc) is True
    assert signage_stream_needs_transcode(ten_bit) is True


def test_missing_probe_keeps_original():
    assert signage_stream_needs_transcode(None) is False
