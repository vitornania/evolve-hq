"""Make a vertical storyboard preview from local images and captions."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

SIZE = (720, 1280)
ARIAL = Path("/System/Library/Fonts/Supplemental/Arial.ttf")


def font(size):
    return ImageFont.truetype(str(ARIAL), size) if ARIAL.exists() else ImageFont.load_default(size=size)


def card(scene, folder, number):
    image = Image.new("RGB", SIZE, "#142120")
    photo = scene.get("image")
    if photo:
        with Image.open(folder / photo) as source:
            image.paste(ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), SIZE))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 865, 720, 1280), fill="#142120")
    draw.text((50, 920), f"SCENE {number}", fill="#bde4ce", font=font(26))
    caption = scene["caption"].strip()
    lines = wrap(caption, width=23)
    if not lines or len(lines) > 5:
        raise ValueError("Each storyboard caption must fit within five lines of 23 characters.")
    draw.multiline_text((50, 970), "\n".join(lines), fill="white", font=font(46), spacing=8)
    return image


def render(data, folder, out):
    executable = shutil.which("ffmpeg")
    if not executable:
        raise ValueError("FFmpeg is required to render the storyboard.")
    scenes = data["scenes"]
    if not 1 <= len(scenes) <= 20:
        raise ValueError("Provide between one and 20 storyboard scenes.")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        work = Path(temp)
        for number, scene in enumerate(scenes, 1):
            seconds = float(scene.get("seconds", 8))
            if not 0.25 <= seconds <= 30:
                raise ValueError("Scene duration must be between 0.25 seconds and 30 seconds.")
            card(scene, folder, number).save(work / f"{number:02d}.png")
            subprocess.run([executable, "-v", "error", "-loop", "1", "-framerate", "24",
                            "-i", f"{number:02d}.png", "-t", str(seconds), "-an",
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                            f"{number:02d}.mp4"], cwd=work, check=True)
        (work / "concat.txt").write_text("".join(f"file '{number:02d}.mp4'\n"
                                                for number in range(1, len(scenes) + 1)))
        subprocess.run([executable, "-v", "error", "-f", "concat", "-safe", "1",
                        "-i", "concat.txt", "-c", "copy", "-movflags", "+faststart",
                        "preview.mp4"], cwd=work, check=True)
        (work / "preview.mp4").replace(out)
