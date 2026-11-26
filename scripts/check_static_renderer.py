"""Exercise the renderer and coverage checks with an original test font and layout."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/adapt-reference-ad/scripts"


def make_font(path):
    font = FontBuilder(1000, isTTF=True)
    font.setupGlyphOrder([".notdef", "A"])
    font.setupCharacterMap({65: "A"})
    empty = TTGlyphPen(None)
    glyph = TTGlyphPen(None)
    glyph.moveTo((0, 0))
    glyph.lineTo((250, 700))
    glyph.lineTo((500, 0))
    glyph.closePath()
    font.setupGlyf({".notdef": empty.glyph(), "A": glyph.glyph()})
    font.setupHorizontalMetrics({".notdef": (600, 0), "A": (600, 0)})
    font.setupHorizontalHeader(ascent=800, descent=-200)
    font.setupNameTable({"familyName": "Test Shape", "styleName": "Regular",
                         "uniqueFontIdentifier": "EvolveTestShape1", "psName": "TestShape-Regular"})
    font.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    font.setupPost()
    font.save(path)


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True)


with TemporaryDirectory() as temp:
    folder = Path(temp)
    make_font(folder / "test.ttf")
    Image.new("RGBA", (20, 20), "#EE3434").save(folder / "art.png")
    font = {"file": "test.ttf", "postscript": "TestShape-Regular"}
    text = {"id": "headline", "type": "text", "x": 50, "y": 43, "font": "test",
            "size": 32, "align": "center", "text": "A", "max_width": 30}
    layout = {"width": 100, "height": 80, "fonts": {"test": font}, "layers": [
        {"id": "art", "type": "image", "file": "art.png", "x": 5, "y": 55, "width": 20, "height": 20},
        text]}
    source, output = folder / "layout.json", folder / "output"
    source.write_text(json.dumps(layout), encoding="utf-8")
    result = run("render_static.py", source, output)
    assert result.returncode == 0, result.stderr
    with Image.open(output / "ad.png") as image:
        assert image.size == (100, 80)
        assert image.getpixel((10, 60)) == (238, 52, 52)
        assert image.getpixel((50, 35)) == (20, 19, 24)
    assert ElementTree.parse(output / "ad.svg").find(".//{http://www.w3.org/2000/svg}text").text == "A"
    report = json.loads((output / "render-report.json").read_text())
    assert report["fonts"][0]["postscript"] == "TestShape-Regular"

    font["postscript"] = "Different-Regular"
    source.write_text(json.dumps(layout))
    result = run("render_static.py", source, output)
    assert result.returncode == 1 and "Expected font" in result.stderr
    font["postscript"] = "TestShape-Regular"
    text["max_width"] = 3
    source.write_text(json.dumps(layout))
    result = run("render_static.py", source, output)
    assert result.returncode == 1 and "mapped slot" in result.stderr

    inventory, reviews = folder / "inventory.jsonl", folder / "reviews.jsonl"
    inventory.write_text('{"id":"A"}\n{"creative_id":"B"}\n')
    reviews.write_text('{"id":"A","status":"eligible","reason":"Format fit"}\n')
    result = run("check_coverage.py", inventory, reviews)
    assert result.returncode == 2 and json.loads(result.stdout)["next_pending_ids"] == ["B"]
    with reviews.open("a") as stream:
        stream.write('{"id":"B","status":"excluded","reason":"Unavailable format"}\n')
    result = run("check_coverage.py", inventory, reviews)
    assert result.returncode == 0 and json.loads(result.stdout)["complete_for_inventory"]
print("Verified PNG, editable SVG, font and text-fit checks, and full template coverage reconciliation.")
