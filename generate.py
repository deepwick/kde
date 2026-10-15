"""Write Deepwick.colors from the Deepwick palette.

Run from this directory: PYTHONPATH=../spec python3 generate.py
"""
from pathlib import Path

from deepwick_spec.palette import Palette, load_palette

OUT = Path(__file__).with_name("Deepwick.colors")
BACKGROUNDS = {
    "Colors:Button": ("overlay", "surface"),
    "Colors:Complementary": ("background", "surface"),
    "Colors:Header": ("surface", "overlay"),
    "Colors:Header][Inactive": ("background", "surface"),
    "Colors:Selection": ("selection", "selection"),
    "Colors:Tooltip": ("surface", "overlay"),
    "Colors:View": ("background", "surface"),
    "Colors:Window": ("surface", "overlay"),
}
FOREGROUNDS = {
    "DecorationFocus": "blue", "DecorationHover": "blue",
    "ForegroundActive": "blue", "ForegroundInactive": "comment", "ForegroundLink": "orange",
    "ForegroundNegative": "red", "ForegroundNeutral": "yellow", "ForegroundNormal": "foreground",
    "ForegroundPositive": "green", "ForegroundVisited": "magenta",
}
# Text on Selection: Comment, Blue and Orange fall under 4.5:1 there.
SELECTION_FOREGROUNDS = {
    "ForegroundActive": "white", "ForegroundInactive": "foreground", "ForegroundLink": "lightBlue",
    "ForegroundNormal": "foreground", "ForegroundVisited": "lightBlue",
}
WM = {
    "activeBackground": "surface", "activeBlend": "foreground", "activeForeground": "foreground",
    "inactiveBackground": "background", "inactiveBlend": "comment", "inactiveForeground": "comment",
}
EFFECTS = {
    "ColorEffects:Disabled": {
        "Color": "overlay", "ColorAmount": "0", "ColorEffect": "0", "ContrastAmount": "0.65",
        "ContrastEffect": "1", "IntensityAmount": "0.1", "IntensityEffect": "2",
    },
    "ColorEffects:Inactive": {
        "ChangeSelectionColor": "true", "Color": "overlay", "ColorAmount": "0.025", "ColorEffect": "2",
        "ContrastAmount": "0.1", "ContrastEffect": "2", "Enable": "false", "IntensityAmount": "0",
        "IntensityEffect": "0",
    },
}


def rgb(hex_color: str) -> str:
    return ",".join(str(int(hex_color[i : i + 2], 16)) for i in (1, 3, 5))


def sections(palette: Palette) -> dict[str, dict[str, str]]:
    def c(name: str) -> str:
        return rgb(palette.colors[name])

    out = {name: {k: c(v) if k == "Color" else v for k, v in keys.items()} for name, keys in EFFECTS.items()}
    for group, (normal, alternate) in BACKGROUNDS.items():
        foregrounds = FOREGROUNDS | (SELECTION_FOREGROUNDS if group == "Colors:Selection" else {})
        keys = {"BackgroundAlternate": c(alternate), "BackgroundNormal": c(normal)}
        keys |= {k: c(v) for k, v in foregrounds.items()}
        out[group] = dict(sorted(keys.items()))
    out["General"] = {"ColorScheme": "Deepwick", "Name": "Deepwick", "shadeSortColumn": "true"}
    out["KDE"] = {"contrast": "4"}
    out["WM"] = {k: c(v) for k, v in WM.items()}
    return out


def render(palette: Palette) -> str:
    lines = []
    for section, keys in sections(palette).items():
        lines.append(f"[{section}]")
        lines += [f"{key}={value}" for key, value in keys.items()]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    OUT.write_text(render(load_palette()), encoding="utf-8")
    print(f"wrote {OUT.name}")
