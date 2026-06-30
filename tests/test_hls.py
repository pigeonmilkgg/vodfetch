"""Netzfreie Tests für das HLS-Parsing."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from twitchdl.hls import parse_master, parse_media, base_of  # noqa: E402
from twitchdl.errors import PlaylistError  # noqa: E402


MASTER = """#EXTM3U
#EXT-X-TWITCH-INFO:NODE="..."
#EXT-X-MEDIA:TYPE=VIDEO,GROUP-ID="chunked",NAME="1080p60 (source)",AUTOSELECT=YES,DEFAULT=YES
#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080,CODECS="avc1.64002A,mp4a.40.2",VIDEO="chunked",FRAME-RATE=60.000
https://cdn.example.net/abc/chunked/index-dvr.m3u8
#EXT-X-MEDIA:TYPE=VIDEO,GROUP-ID="720p60",NAME="720p60",AUTOSELECT=YES,DEFAULT=NO
#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720,CODECS="avc1.4D401F,mp4a.40.2",VIDEO="720p60",FRAME-RATE=60.000
https://cdn.example.net/abc/720p60/index-dvr.m3u8
#EXT-X-MEDIA:TYPE=VIDEO,GROUP-ID="audio_only",NAME="Audio Only",AUTOSELECT=NO,DEFAULT=NO
#EXT-X-STREAM-INF:BANDWIDTH=160000,CODECS="mp4a.40.2",VIDEO="audio_only"
https://cdn.example.net/abc/audio_only/index-dvr.m3u8
"""

MEDIA_VOD = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.000,
0.ts
#EXTINF:10.000,
1.ts
#EXT-X-DISCONTINUITY
#EXTINF:10.000,
2-muted.ts
#EXTINF:4.500,
3.ts
#EXT-X-ENDLIST
"""

MEDIA_LIVE = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:2
#EXT-X-MEDIA-SEQUENCE:100
#EXTINF:2.000,
100.ts
#EXTINF:2.000,
101.ts
"""


def test_master_parses_all_qualities():
    qs = parse_master(MASTER, "https://usher.example/vod/1.m3u8")
    assert len(qs) == 3
    # Source zuerst (sortiert)
    assert qs[0].is_source is True
    assert qs[0].height == 1080
    assert qs[0].fps == 60.0
    assert qs[0].bandwidth == 6000000
    assert qs[0].url.endswith("/chunked/index-dvr.m3u8")
    # audio_only erkannt (height 0)
    audio = [q for q in qs if q.height == 0]
    assert len(audio) == 1


def test_master_rejects_non_m3u8():
    with pytest.raises(PlaylistError):
        parse_master("<html>nope</html>", "https://x/")


def test_media_vod_segments_and_end():
    segs, ended, target = parse_media(MEDIA_VOD, "https://cdn.example.net/abc/chunked/")
    assert ended is True
    assert target == 10.0
    assert len(segs) == 4
    assert segs[0].url == "https://cdn.example.net/abc/chunked/0.ts"
    assert segs[0].index == 0
    assert segs[2].muted is True          # 2-muted.ts
    assert segs[3].duration == 4.5


def test_media_live_not_ended_with_offset():
    segs, ended, target = parse_media(MEDIA_LIVE, "https://cdn/x/", start_index=50)
    assert ended is False
    assert target == 2.0
    assert segs[0].index == 50            # start_index respektiert
    assert len(segs) == 2


def test_base_of():
    assert base_of("https://x/a/b/index.m3u8") == "https://x/a/b/"
