# Prepare an image for HQ's local preview

Use this when an individual image ad run requests one buildable image. The person will click **Preview image** after the layout passes review. HQ then renders a PNG and editable SVG from the supplied photos and local fonts. Describe the layout as ready to preview. Report an inspected export only when one actually exists.

Give one finished layout using the format below. Keep the exact proposed ad copy in its layers. Use 1080 × 1080 for square or 1080 × 1350 for portrait. Use integer positions and sizes. Image and shape coordinates start at the upper left. Text uses a baseline for `y`, and each layer holds one line. Use `sans` for Arial and `serif` for Georgia. Add a maximum width for each text line and leave breathing room. Keep all artwork within the page. Preserve the product photo's aspect ratio. Use only attached photo filenames, such as `supplied-image-1.jpg`. Do not invent a file, recolor product art or assume permission to publish. With no product photo, make a usable type-led layout if the brief permits it. Ask for one exact photo when a necessary product visual is missing.

```static-layout
{
  "width": 1080,
  "height": 1350,
  "background": "#FFFFFF",
  "layers": [
    {"id": "heading", "type": "text", "text": "Example headline", "font": "serif", "size": 70, "x": 85, "y": 155, "max_width": 910, "fill": "#181818"},
    {"id": "photo", "type": "image", "file": "supplied-image-1.jpg", "x": 190, "y": 280, "width": 700, "height": 700}
  ]
}
```

The example photo is square. Measure or read the supplied photo's dimensions before setting its layer. The layout supports up to 18 text, image, rectangle or ellipse layers. A rectangle or ellipse uses whole-pixel `x`, `y`, `width`, `height` and a hex `fill`. Use the desktop comments or layout details for notes. Keep internal notes and source IDs off the artwork.
