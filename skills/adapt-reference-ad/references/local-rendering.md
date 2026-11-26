# Render a static ad locally

The renderer works on macOS and Windows with Python 3.10 or newer. It exports a PNG, an SVG with editable text and separate layers, and a font report. Open the SVG in Inkscape or another local SVG editor. Install the verified fonts locally to reproduce the text in editors that ignore embedded fonts. Canva and Figma are optional.

## Prepare a job

1. Make a folder for the job. Keep the layout JSON, authorized raster assets, exact static font files, and their licenses inside it. The renderer reads only files inside this folder.
2. Measure the original canvas and each source layer's position. For text, measure the baseline, alignment, point size at the output scale, and available line width. In a PDF, inspect the actual font metadata and measure one pixel baseline per line at the selected export size.
3. Write a layout file in bottom-to-top layer order. Give each semantic slot a unique ID. A raster layer should already have its intended crop and transparency. Keep generated clean plates, product photos, logos, and text in separate layers.

```json
{
  "width": 1080,
  "height": 1080,
  "background": "#F8F5F0",
  "fonts": {
    "headline": {"file": "fonts/Poppins-Regular.ttf", "postscript": "Poppins-Regular"}
  },
  "layers": [
    {"id": "background-plate", "type": "image", "file": "plate.png", "x": 0, "y": 0, "width": 1080, "height": 1080},
    {"id": "primary-product", "type": "image", "file": "product.png", "x": 415, "y": 450, "width": 250, "height": 500},
    {"id": "headline-line-1", "type": "text", "text": "Your approved headline", "font": "headline", "x": 540, "y": 210, "size": 64, "align": "center", "max_width": 940, "fill": "#141318"}
  ]
}
```

Text coordinates use pixels. The `y` value is the baseline. Each text layer is one line. Images use whole pixels and are sized to the specified width and height. Shape layers use `rectangle` or `ellipse` with `x`, `y`, `width`, `height` and `fill`. Rectangles can specify a `radius`.

## Export

Open a terminal at Evolve HQ or at the folder containing the installed skill. Change the paths to point at the skill's scripts and your layout.

macOS

```sh
python3 -m pip install -r skills/adapt-reference-ad/scripts/requirements.txt
python3 skills/adapt-reference-ad/scripts/render_static.py path/to/layout.json path/to/exports
```

Windows PowerShell

```powershell
py -3 -m pip install -r skills/adapt-reference-ad/scripts/requirements.txt
py -3 skills/adapt-reference-ad/scripts/render_static.py path/to/layout.json path/to/exports
```

The renderer checks each font's internal PostScript name, available glyphs, and the text width limit in the job. Add a font's verified `sha256` to the JSON to require the exact font file. The report records its version and checksum. Verify the source face and weight separately. A file name or font-name check alone cannot establish a match to the original. Use the correctly weighted static file for a variable font. Associate any substituted font with its own actual PostScript name and disclose the substitution. Keep the original font license with fonts you are allowed to redistribute.

Open the PNG at export size and at phone size. Compare each layer with the source map. The PNG is the verified export, and the SVG is the editable source. Save the layout JSON and its assets when someone else needs to regenerate it locally.
