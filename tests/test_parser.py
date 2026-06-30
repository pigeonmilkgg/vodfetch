"""Netzfreie Tests für das URL-/ID-Parsing."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from twitchdl.parser import parse_input, sanitize_filename  # noqa: E402
from twitchdl.models import KIND_VOD, KIND_CLIP, KIND_CHANNEL  # noqa: E402
from twitchdl.errors import InvalidURLError  # noqa: E402


@pytest.mark.parametrize("url,kind,ident", [
    ("https://www.twitch.tv/videos/123456789", KIND_VOD, "123456789"),
    ("twitch.tv/videos/123456789", KIND_VOD, "123456789"),
    ("https://www.twitch.tv/videos/123456789?t=1h2m3s", KIND_VOD, "123456789"),
    ("123456789", KIND_VOD, "123456789"),
    ("v123456789", KIND_VOD, "123456789"),
    ("https://player.twitch.tv/?video=v987654321&parent=x", KIND_VOD, "987654321"),
])
def test_vod(url, kind, ident):
    ref = parse_input(url)
    assert ref.kind == kind
    assert ref.id == ident


@pytest.mark.parametrize("url,slug", [
    ("https://clips.twitch.tv/AwkwardHelpfulFennelKappa", "AwkwardHelpfulFennelKappa"),
    ("https://www.twitch.tv/shroud/clip/AwkwardHelpful-Foo_Bar123", "AwkwardHelpful-Foo_Bar123"),
    ("https://www.twitch.tv/shroud/clips/SomeClipSlug123", "SomeClipSlug123"),
    ("clips.twitch.tv/CoolSlugHere?featured=true", "CoolSlugHere"),
])
def test_clip(url, slug):
    ref = parse_input(url)
    assert ref.kind == KIND_CLIP
    assert ref.id == slug


@pytest.mark.parametrize("url,channel", [
    ("https://www.twitch.tv/shroud", "shroud"),
    ("twitch.tv/Pokimane", "pokimane"),
    ("https://m.twitch.tv/xqc", "xqc"),
    ("ninja", "ninja"),
])
def test_channel(url, channel):
    ref = parse_input(url)
    assert ref.kind == KIND_CHANNEL
    assert ref.id == channel


@pytest.mark.parametrize("bad", ["", "   ", "https://youtube.com/watch?v=x", "https://twitch.tv/videos/abc"])
def test_invalid(bad):
    with pytest.raises(InvalidURLError):
        parse_input(bad)


def test_reserved_not_channel():
    # /downloads, /settings etc. dürfen nicht als Channel durchgehen
    with pytest.raises(InvalidURLError):
        parse_input("https://twitch.tv/settings")


def test_sanitize():
    assert sanitize_filename('a/b:c*?"<>|d') == "a_b_c______d"
    assert sanitize_filename("  spaced   out  ") == "spaced out"
    assert sanitize_filename("") == "twitch_download"
    assert len(sanitize_filename("x" * 500)) <= 150
