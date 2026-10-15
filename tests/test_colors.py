import configparser
import importlib.util
import os
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors
GROUPS = [
    "Colors:Button", "Colors:Complementary", "Colors:Header", "Colors:Header][Inactive",
    "Colors:Selection", "Colors:Tooltip", "Colors:View", "Colors:Window",
]
KEYS = {
    "BackgroundNormal", "BackgroundAlternate", "ForegroundNormal", "ForegroundInactive",
    "ForegroundActive", "ForegroundLink", "ForegroundVisited", "ForegroundNegative",
    "ForegroundNeutral", "ForegroundPositive", "DecorationFocus", "DecorationHover",
}
BACKGROUNDS = {
    "Colors:Window": ("surface", "overlay"),
    "Colors:View": ("background", "surface"),
    "Colors:Button": ("overlay", "surface"),
    "Colors:Selection": ("selection", "selection"),
    "Colors:Tooltip": ("surface", "overlay"),
    "Colors:Complementary": ("background", "surface"),
    "Colors:Header": ("surface", "overlay"),
    "Colors:Header][Inactive": ("background", "surface"),
}
FOREGROUNDS = {
    "ForegroundNormal": "foreground", "ForegroundInactive": "comment", "ForegroundActive": "blue",
    "ForegroundLink": "orange", "ForegroundVisited": "magenta", "ForegroundNegative": "red",
    "ForegroundNeutral": "yellow", "ForegroundPositive": "green",
    "DecorationFocus": "blue", "DecorationHover": "blue",
}
SELECTION_FOREGROUNDS = {
    "ForegroundNormal": "foreground", "ForegroundInactive": "foreground", "ForegroundActive": "white",
    "ForegroundLink": "lightBlue", "ForegroundVisited": "lightBlue",
}


def rgb(name):
    return ",".join(str(int(C[name][i : i + 2], 16)) for i in (1, 3, 5))


def scheme():
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(REPO / "Deepwick.colors", encoding="utf-8")
    assert parser.sections(), "Deepwick.colors missing or empty"
    return parser


def test_sections():
    expected = {"ColorEffects:Disabled", "ColorEffects:Inactive", *GROUPS, "General", "KDE", "WM"}
    assert set(scheme().sections()) == expected


@pytest.mark.parametrize("group", GROUPS)
def test_group_sets_every_key(group):
    assert set(scheme()[group]) == KEYS


def test_general_names_the_file():
    general = scheme()["General"]
    assert general["ColorScheme"] == "Deepwick"
    assert general["Name"] == "Deepwick"


@pytest.mark.parametrize("group", GROUPS)
def test_backgrounds(group):
    normal, alternate = BACKGROUNDS[group]
    assert scheme()[group]["BackgroundNormal"] == rgb(normal)
    assert scheme()[group]["BackgroundAlternate"] == rgb(alternate)


@pytest.mark.parametrize("group", GROUPS)
def test_foregrounds(group):
    expected = FOREGROUNDS | (SELECTION_FOREGROUNDS if group == "Colors:Selection" else {})
    for key, name in expected.items():
        assert scheme()[group][key] == rgb(name), f"{group} {key}"


def test_window_manager():
    wm = scheme()["WM"]
    assert wm["activeBackground"] == rgb("surface")
    assert wm["activeForeground"] == rgb("foreground")
    assert wm["activeBlend"] == rgb("foreground")
    assert wm["inactiveBackground"] == rgb("background")
    assert wm["inactiveForeground"] == rgb("comment")
    assert wm["inactiveBlend"] == rgb("comment")


def test_effects_use_overlay():
    for section in ("ColorEffects:Disabled", "ColorEffects:Inactive"):
        assert scheme()[section]["Color"] == rgb("overlay")


def test_every_triple_is_a_palette_color():
    allowed = {rgb(name) for name in C}
    for section in scheme().sections():
        for key, value in scheme()[section].items():
            if re.fullmatch(r"\d+,\d+,\d+", value):
                assert value in allowed, f"{section} {key}={value}"


def test_committed_file_matches_generator():
    spec = importlib.util.spec_from_file_location("generate", REPO / "generate.py")
    generate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate)
    assert (REPO / "Deepwick.colors").read_text(encoding="utf-8") == generate.render(PALETTE)


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []


VSHOT = REPO.parent / "tools" / "vshot"
needs_vshot = pytest.mark.skipif(
    not (VSHOT.is_file() and shutil.which("kwin_wayland") and shutil.which("spectacle") and shutil.which("magick")),
    reason="needs tools/vshot, kwin_wayland, spectacle and ImageMagick",
)


def vshot(base, *cmd, **env):
    """Run cmd off-screen with SHOT_XDG=base; return the screenshot's color histogram."""
    out = base / "shot.png"
    subprocess.run(
        [str(VSHOT), str(out), "--", *cmd],
        env={**os.environ, "SHOT_XDG": str(base), **env},
        check=True,
        timeout=120,
    )
    hist = subprocess.run(
        ["magick", str(out), "-alpha", "off", "-format", "%c", "histogram:info:-"],
        capture_output=True, text=True, check=True,
    ).stdout
    counts = Counter()
    for m in re.finditer(r"^\s*(\d+):.*?#([0-9A-Fa-f]{6})", hist, re.M):
        counts["#" + m.group(2).lower()] += int(m.group(1))
    return counts


def px(counts, name):
    return counts[PALETTE.colors[name].lower()]


def dolphin(base, select_scheme):
    (base / "data" / "color-schemes").mkdir(parents=True)
    shutil.copy(REPO / "Deepwick.colors", base / "data" / "color-schemes")
    (base / "config").mkdir(exist_ok=True)
    if select_scheme:
        (base / "config" / "dolphinrc").write_text("[UiSettings]\nColorScheme=Deepwick\n")
    tree = base / "tree"
    (tree / "src").mkdir(parents=True)
    (tree / "app.py").write_text("print('hi')\n")
    return vshot(base, "dolphin", "--new-window", str(tree))


@needs_vshot
def test_dolphin_renders_scheme(tmp_path):
    counts = dolphin(tmp_path, select_scheme=True)
    assert px(counts, "background") > 20000, "view background is not Deepwick Background"
    assert px(counts, "surface") > 5000, "window/title bar is not Deepwick Surface"


@needs_vshot
def test_dolphin_without_scheme_is_not_deepwick(tmp_path):
    counts = dolphin(tmp_path, select_scheme=False)
    assert px(counts, "background") < 500
