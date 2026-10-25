import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "remote-audio.md"
MICROPHONE_TEMPLATE = ROOT / "src" / "mlsc" / "app" / "templates" / "home" / "settings" / "microphone_adjustment.html"
PAGE_URL = "https://github.com/TobKra96/music_led_strip_control/blob/master/docs/remote-audio.md"


def page_text():
    return PAGE.read_text(encoding="utf-8")


def section_headings():
    return re.findall(r"^## (.+)$", page_text(), flags=re.MULTILINE)


def spotify_section():
    text = page_text()
    start = text.index("## Spotify")
    end = text.find("\n## ", start)
    return text[start:end if end != -1 else None]


def test_microphone_hint_links_to_the_remote_audio_page():
    assert PAGE_URL in MICROPHONE_TEMPLATE.read_text(encoding="utf-8")
    assert PAGE.is_file()


def test_recipes_follow_decision_233_order_with_spotify_last():
    headings = section_headings()
    expected = ["AirPlay (shairport-sync)", "Bluetooth", "PipeWire/PulseAudio network", "Spotify (raspotify)"]

    positions = [headings.index(recipe) for recipe in expected]

    assert positions == sorted(positions)


def test_spotify_recipe_is_marked_your_responsibility_with_its_caveats():
    section = spotify_section()

    assert "your responsibility" in section.lower()
    assert "Premium" in section
    assert "probably forbidden" in section
