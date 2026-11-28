"""Render a reviewed, single-skill image layout using HQ's local renderer."""
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock

from activity import ROOT
from skill_runs import get_run, saved_images

PREVIEW_LOCK = Lock()
LAYOUT_BLOCK = re.compile(r"^```static-layout[ \t]*\r?\n(.*?)^\s*```[ \t]*$", re.M | re.S)
ARTBOARDS = {(1080, 1080), (1080, 1350)}
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
LAYER_ID = re.compile(r"[a-zA-Z][\w-]*")
FONTS = {
    "sans": ("Arial.ttf", "arial.ttf", "ArialMT"),
    "serif": ("Georgia.ttf", "georgia.ttf", "Georgia"),
}


def is_layout_step(step):
    return (step.get("skill") == "build-static-ads-in-figma"
            and step.get("status") == "review"
            and bool(LAYOUT_BLOCK.search(step.get("report") or "")))


def read_layout(text, images):
    blocks = LAYOUT_BLOCK.findall(text)
    try:
        if len(blocks) != 1 or len(blocks[0]) > 24000:
            raise ValueError()
        layout = json.loads(blocks[0])
        width, height = layout["width"], layout["height"]
        layers = layout["layers"]
        if (type(width) is not int or type(height) is not int or (width, height) not in ARTBOARDS
                or not isinstance(layers, list) or not 1 <= len(layers) <= 18):
            raise ValueError()
        background = layout.get("background", "#FFFFFF")
        if not isinstance(background, str) or not COLOR.fullmatch(background):
            raise ValueError("Use a six-digit hex background color.")
        used_images = set()
        ids = set()
        for layer in layers:
            x, y, kind = layer["x"], layer["y"], layer["type"]
            identifier = layer["id"]
            if not isinstance(identifier, str) or not LAYER_ID.fullmatch(identifier) or identifier in ids:
                raise ValueError("Give every layer a unique ID that starts with a letter.")
            ids.add(identifier)
            if kind != "image":
                color = layer.get("fill", "#141318" if kind == "text" else "")
                if not isinstance(color, str) or not COLOR.fullmatch(color):
                    raise ValueError("Use six-digit hex colors in text and shape layers.")
            if type(x) is not int or type(y) is not int or not (0 <= x <= width and 0 <= y <= height):
                raise ValueError()
            if kind == "text":
                if (layer["font"] not in FONTS or type(layer["size"]) is not int
                        or not 18 <= layer["size"] <= 140 or not isinstance(layer["text"], str)
                        or not 1 <= len(layer["text"]) <= 120 or "\n" in layer["text"] or "\r" in layer["text"]):
                    raise ValueError("Use one line per text layer and the sans or serif font.")
                if layer.get("align", "left") not in ("left", "center", "right"):
                    raise ValueError("Use left, center or right alignment.")
                if "max_width" in layer and (type(layer["max_width"]) is not int
                                             or not 1 <= layer["max_width"] <= width):
                    raise ValueError("Keep the text slot width within the artboard.")
                continue
            w, h = layer["width"], layer["height"]
            if (kind not in ("image", "rectangle", "ellipse") or type(w) is not int or type(h) is not int
                    or not (1 <= w <= width - x and 1 <= h <= height - y)):
                raise ValueError()
            if kind == "rectangle" and (type(layer.get("radius", 0)) is not int
                                         or not 0 <= layer.get("radius", 0) <= 500):
                raise ValueError()
            if kind == "image":
                name = layer["file"]
                if name not in images or name in used_images:
                    raise ValueError("Use an attached photo filename once per layout.")
                used_images.add(name)
    except (TypeError, KeyError, ValueError) as error:
        detail = str(error) if type(error) is ValueError and str(error) else ""
        raise ValueError(detail or "This layout needs a repair. Use one square or portrait layout with the required layer fields.") from error
    return layout


def add_fonts(directory, layout):
    mac = Path("/System/Library/Fonts/Supplemental")
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    fonts = {}
    for name in dict.fromkeys(layer["font"] for layer in layout["layers"] if layer["type"] == "text"):
        mac_file, windows_file, postscript = FONTS[name]
        path = next((candidate for candidate in (mac / mac_file, windows / windows_file)
                     if candidate.is_file()), None)
        if path is None:
            raise RuntimeError(f"This preview needs the local {mac_file[:-4]} font. You can still view the layout details.")
        dest = name + ".ttf"
        shutil.copyfile(path, directory / dest)
        fonts[name] = {"file": dest, "postscript": postscript}
    layout["fonts"] = fonts


def add_photos(directory, layout, images):
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("Install the local Static Ads renderer requirements to preview an image.") from error
    for layer in layout["layers"]:
        if layer["type"] != "image":
            continue
        path = images[layer["file"]]
        try:
            with Image.open(path) as photo:
                width, height = photo.size
                if photo.getexif().get(274) in (5, 6, 7, 8):
                    width, height = height, width
                if width * height > 16000000:
                    raise ValueError("Resize the attached photo to 16 megapixels or less for the local preview.")
                if abs(layer["width"] * height / (layer["height"] * width) - 1) > .02:
                    raise ValueError("The layout would stretch your photo. Ask for a layout that preserves its proportions.")
        except (OSError, Image.DecompressionBombError) as error:
            raise ValueError("The attached photo couldn’t be opened. Use a smaller PNG, JPG or WebP.") from error
        shutil.copyfile(path, directory / path.name)


def render_preview(payload):
    identifier = payload.get("run") if isinstance(payload, dict) else None
    key = payload.get("step") if isinstance(payload, dict) else None
    if not isinstance(identifier, str) or not 1 <= len(identifier) <= 350 or not isinstance(key, str):
        raise ValueError("Choose a reviewed image ad layout first.")
    run = get_run(identifier)
    step = next((s for s in run["steps"] if s["id"] == key and is_layout_step(s)), None) if run and not run.get("workflows") else None
    if step is None:
        raise ValueError("This run has no reviewed image layout to preview.")
    relative = Path("adapt-reference-ad/scripts/render_static.py")
    renderer = next((root / relative for root in (ROOT / ".office/portable-skills", ROOT / "skills")
                     if (root / relative).is_file()), None)
    if renderer is None:
        raise RuntimeError("The local Static Ads renderer is missing from this HQ installation.")
    images = {path.name: path for path in saved_images((ROOT / "tasks" / identifier).resolve())}
    layout = read_layout(step["report"], images)
    if not PREVIEW_LOCK.acquire(blocking=False):
        raise RuntimeError("Another image preview is rendering. Try again in a moment.")
    try:
        with TemporaryDirectory(prefix="evolve-image-preview-") as temp:
            directory = Path(temp)
            add_fonts(directory, layout)
            add_photos(directory, layout, images)
            spec = directory / "layout.json"
            spec.write_text(json.dumps(layout), encoding="utf-8")
            command = [sys.executable, str(renderer), str(spec), str(directory), "--no-embed-fonts"]
            try:
                result = subprocess.run(command, timeout=20, capture_output=True, text=True,
                                        encoding="utf-8", errors="replace")
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("The image took too long to render. Try a simpler layout.") from error
            if result.returncode:
                first = result.stderr.partition("\n")[0]
                message = ""
                if first.startswith("Render failed: "):
                    message = first.removeprefix("Render failed: ").replace(str(directory), "preview")
                raise ValueError(message[:220] or "The layout couldn’t render. Ask the skill to check text fit and artwork.")
            return {ext: base64.b64encode((directory / f"ad.{ext}").read_bytes()).decode("ascii")
                    for ext in ("png", "svg")}
    finally:
        PREVIEW_LOCK.release()
