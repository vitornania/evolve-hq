#!/usr/bin/env python3
"""Render a local static-ad layout to PNG and a layered SVG with editable text."""

import argparse
import base64
from dataclasses import dataclass
from hashlib import sha256
from html import escape
from io import BytesIO
import json
from math import isfinite
from pathlib import Path
import re
import sys


def number(value, label, *, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return value


def positive_integer(value, label):
    if not isinstance(value, int) or value > 8192:
        raise ValueError(f"{label} must be an integer from 1 to 8192")
    return number(value, label, minimum=1)


def color(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError("Use six-digit hexadecimal colors, such as #141318")
    return value


def local_asset(root, value):
    if not isinstance(value, str) or Path(value).is_absolute():
        raise ValueError("Asset paths must be relative to the layout file")
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Missing or out-of-folder asset: {value}")
    return path


def embedded(data, media_type):
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"


@dataclass
class RegisteredFont:
    path: Path
    family: str
    version: str
    digest: str
    postscript: str
    weight: int
    glyphs: set
    embeds: bool


def verify_font(path, recipe, TTFont):
    if path.suffix.lower() not in {".ttf", ".otf"}:
        raise ValueError(f"Use a static TTF or OTF font: {path.name}")
    expected = recipe["postscript"]
    digest = sha256(path.read_bytes()).hexdigest()
    if "sha256" in recipe and recipe["sha256"] != digest:
        raise ValueError(f"Font file checksum does not match: {path.name}")
    with TTFont(path) as face:
        if "fvar" in face:
            raise ValueError(f"{path.name} is variable. Export the required static weight first.")
        name = face["name"]
        actual = name.getDebugName(6)
        if actual != expected:
            raise ValueError(f"Expected font {expected}; {path.name} identifies as {actual}")
        os2 = face["OS/2"]
        embedding_restricted = os2.fsType & (0x0002 | 0x0200)
        return RegisteredFont(
            path, name.getBestFamilyName(), name.getDebugName(5), digest, actual,
            os2.usWeightClass, set(face.getBestCmap()), not embedding_restricted,
        )


def read_fonts(root, choices, TTFont):
    if not isinstance(choices, dict):
        raise ValueError("fonts must map font IDs to font files and PostScript names")
    return {
        key: verify_font(local_asset(root, row["file"]), row, TTFont)
        for key, row in choices.items()
    }


def paint_image(root, item, canvas, image_module, image_ops, x, y):
    width = positive_integer(item["width"], "Image width")
    height = positive_integer(item["height"], "Image height")
    if int(x) != x or int(y) != y:
        raise ValueError("Image positions must be whole pixels")
    with image_module.open(local_asset(root, item["file"])) as source:
        layer = image_ops.exif_transpose(source).convert("RGBA")
    if layer.size != (width, height):
        layer = layer.resize((width, height), image_module.Resampling.LANCZOS)
    canvas.alpha_composite(layer, (int(x), int(y)))
    data = BytesIO()
    layer.save(data, format="PNG")
    href = embedded(data.getvalue(), "image/png")
    return f'<image x="{x}" y="{y}" width="{width}" height="{height}" href="{href}"/>'


def paint_text(item, fonts, draw, image_font, x, y, width, height):
    value = item["text"]
    if not isinstance(value, str) or not value or "\n" in value or "\r" in value:
        raise ValueError("Each text layer needs exactly one nonempty line")
    font = fonts[item["font"]]
    if absent := sorted({char for char in value if ord(char) not in font.glyphs}):
        raise ValueError(f"{font.postscript} is missing characters {absent!r}")
    size = number(item["size"], "Font size", minimum=1)
    align = item.get("align", "left")
    anchors = {"left": ("ls", "start"), "center": ("ms", "middle"), "right": ("rs", "end")}
    if align not in anchors:
        raise ValueError("Text alignment must be left, center, or right")
    pix_anchor, svg_anchor = anchors[align]
    ink = color(item.get("fill", "#141318"))
    face = image_font.truetype(str(font.path), size)
    left, top, right, bottom = draw.textbbox((x, y), value, font=face, anchor=pix_anchor)
    if left < 0 or top < 0 or right > width or bottom > height:
        raise ValueError(f"Text exceeds the canvas: {value!r}")
    if "max_width" in item and right - left > number(item["max_width"], "Maximum text width", minimum=1):
        raise ValueError(f"Text exceeds its mapped slot: {value!r}")
    draw.text((x, y), value, font=face, anchor=pix_anchor, fill=ink)
    family = escape(font.family, quote=True)
    return (f'<text x="{x}" y="{y}" text-anchor="{svg_anchor}" fill="{ink}" '
            f'font-family="{family}" font-weight="{font.weight}" font-size="{size}">'
            f'{escape(value)}</text>')


def paint_shape(item, draw, kind, x, y):
    w = number(item["width"], "Shape width", minimum=1)
    h = number(item["height"], "Shape height", minimum=1)
    ink = color(item["fill"])
    box = (x, y, x + w - 1, y + h - 1)
    if kind == "ellipse":
        draw.ellipse(box, fill=ink)
        return f'<ellipse cx="{x + w / 2}" cy="{y + h / 2}" rx="{w / 2}" ry="{h / 2}" fill="{ink}"/>'
    radius = number(item.get("radius", 0), "Corner radius", minimum=0)
    draw.rounded_rectangle(box, radius=radius, fill=ink)
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{ink}"/>'


def font_css(fonts):
    rules = []
    for font in fonts.values():
        if font.embeds:
            kind = font.path.suffix.lower()[1:]
            uri = embedded(font.path.read_bytes(), f"font/{kind}")
            family = font.family.replace("\\", "\\\\").replace('"', '\\"')
            rules.append(f'@font-face{{font-family:"{family}";font-weight:{font.weight};src:url("{uri}")}}')
    return escape("\n".join(rules), quote=False)


def render(spec_path, output):
    try:
        from fontTools.ttLib import TTFont
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError as exc:
        raise ValueError("Install the packages listed in scripts/requirements.txt first") from exc

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    width = positive_integer(spec["width"], "Canvas width")
    height = positive_integer(spec["height"], "Canvas height")
    root = spec_path.resolve().parent
    fonts = read_fonts(root, spec.get("fonts", {}), TTFont)
    bg = color(spec.get("background", "#FFFFFF"))
    canvas = Image.new("RGBA", (width, height), bg)
    draw = ImageDraw.Draw(canvas)
    parts = [f'<rect width="{width}" height="{height}" fill="{bg}"/>']
    ids = set()
    for item in spec["layers"]:
        slot = item["id"]
        if not isinstance(slot, str) or not re.fullmatch(r"[a-zA-Z][\w-]*", slot) or slot in ids:
            raise ValueError(f"Layer IDs must be unique names: {slot!r}")
        ids.add(slot)
        x, y = number(item["x"], "Layer x"), number(item["y"], "Layer y")
        kind = item["type"]
        if kind == "image":
            art = paint_image(root, item, canvas, Image, ImageOps, x, y)
        elif kind == "text":
            art = paint_text(item, fonts, draw, ImageFont, x, y, width, height)
        elif kind in {"rectangle", "ellipse"}:
            art = paint_shape(item, draw, kind, x, y)
        else:
            raise ValueError(f"Unsupported layer type: {kind}")
        parts.append(f'<g id="{escape(slot, quote=True)}">{art}</g>')
    output.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output / "ad.png")
    (output / "ad.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><defs><style>{font_css(fonts)}</style></defs>\n'
        + "\n".join(parts) + "\n</svg>\n", encoding="utf-8",
    )
    summary = {
        "canvas": [width, height],
        "layers": sorted(ids),
        "fonts": [{"file": f.path.name, "family": f.family, "postscript": f.postscript,
                   "version": f.version, "sha256": f.digest,
                   "weight": f.weight, "embedded_in_svg": f.embeds} for f in fonts.values()],
    }
    (output / "render-report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path, help="Local JSON layout and adjacent assets")
    parser.add_argument("output", type=Path, help="Directory for ad.png, ad.svg and render-report.json")
    args = parser.parse_args()
    try:
        render(args.layout, args.output)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Render failed: {exc}", file=sys.stderr)
        return 1
    print(f"Exported static ad to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
