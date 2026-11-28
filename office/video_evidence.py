"""Prepare bounded local video evidence without relying on a vision provider."""
import base64
import binascii
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

MAX_VIDEO_BYTES = 35 * 1024 * 1024
MAX_SECONDS = 90
MAX_FRAMES = 8
VIDEO_FORMATS = {".mp4": "mov", ".mov": "mov", ".webm": "matroska"}
SCENE_TIME = re.compile(r"lavfi\.scd\.score:\s*([\d.]+),\s*lavfi\.scd\.time:\s*([-+\d.eE]+)")
FRAME_TIME = re.compile(r"\bn:\s*\d+\s+pts:\s*-?\d+\s+pts_time:([-+\d.eE]+)")


def command(executable, args, timeout):
    try:
        result = subprocess.run([executable, *args], capture_output=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        raise RuntimeError("Local video preparation timed out or could not start. Try a shorter clip.") from None
    if result.returncode:
        raise RuntimeError("HQ could not decode this clip. Export it again as MP4, MOV or WebM.") from None
    return result


def decode_video(value):
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("name"), str):
        raise ValueError("Choose one MP4, MOV or WebM clip.")
    extension = Path(value["name"]).suffix.lower()
    encoded = value.get("body")
    if extension not in VIDEO_FORMATS:
        raise ValueError("Use an MP4, MOV or WebM clip.")
    if not isinstance(encoded, str) or len(encoded) > MAX_VIDEO_BYTES * 4 // 3 + 8:
        raise ValueError("The clip must be 35 MB or smaller.")
    try:
        body = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("The video could not be read.") from None
    if not body or len(body) > MAX_VIDEO_BYTES:
        raise ValueError("Upload a nonempty clip of 35 MB or less.")
    if extension == ".webm":
        valid = body.startswith(b"\x1a\x45\xdf\xa3")
    else:
        valid = body[4:8] in (b"ftyp", b"moov", b"wide", b"mdat", b"free")
    if not valid:
        raise ValueError("The file contents do not match the selected video format.")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("Install FFmpeg and FFprobe for video uploads, or attach timecoded screenshots instead.")
    return extension, body


def scene_candidates(ffmpeg, source, path, duration):
    try:
        scan = command(ffmpeg, ["-hide_banner", "-loglevel", "info", "-nostdin", "-threads", "2",
                                *source, "-i", str(path), "-map", "0:v:0", "-t", str(MAX_SECONDS),
                                "-an", "-sn", "-dn", "-filter_threads", "2",
                                "-vf", "scale=256:256:force_original_aspect_ratio=decrease,scdet=threshold=16",
                                "-f", "null", "-"], 25)
    except RuntimeError:
        # A failed optional scan should still allow the regular frame sampler.
        return None
    candidates = [(float(score), float(seconds)) for score, seconds in SCENE_TIME.findall(scan.stderr)]
    return [(score, seconds) for score, seconds in candidates if 0 < seconds < duration]


def frame_targets(duration, candidates):
    # Include the opening, a spread across the clip, and its final beat.
    points = [0, duration * 0.2, duration * 0.4, duration * 0.6, duration * 0.8,
              duration - min(0.25, duration / 7)]
    cuts = []
    for score, seconds in sorted(candidates or [], reverse=True):
        if all(abs(seconds - point) > min(0.4, duration / 14) for point in points):
            cuts.append({"seconds": round(seconds, 3), "score": round(score, 2)})
            points.append(seconds)
            if len(points) == MAX_FRAMES:
                break
    return points, sorted(cuts, key=lambda cut: cut["seconds"])


def visible_text(images):
    executable = shutil.which("tesseract")
    if not executable:
        return {}
    text = {}
    for image in images:
        try:
            result = subprocess.run([executable, str(image), "stdout", "--psm", "11"],
                                    capture_output=True, encoding="utf-8", errors="replace", timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            continue
        evidence = " ".join(result.stdout.split())[:450]
        if result.returncode == 0 and evidence:
            text[image.name] = evidence
    return text


def offline_transcript(ffmpeg, source, path):
    root = Path(__file__).resolve().parents[1]
    script = root / "runtime/transcribe_resolve.py"
    if not script.is_file():
        return []
    environment = root / ".office/envs/edit"
    interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    python = str(interpreter) if interpreter.is_file() else sys.executable
    output = path.with_name("video-transcript.json")
    with tempfile.TemporaryDirectory() as folder:
        wave = Path(folder) / "speech.wav"
        try:
            command(ffmpeg, ["-v", "error", "-nostdin", "-threads", "2", *source, "-i", str(path),
                             "-map", "0:a:0", "-t", str(MAX_SECONDS), "-ar", "16000", "-ac", "1",
                             "-c:a", "pcm_s16le", str(wave)], 15)
            command(python, [str(script), str(wave), str(output), "--offline", "--model", "base"], 70)
            segments = json.loads(output.read_text(encoding="utf-8"))["segments"]
        except (KeyError, OSError, RuntimeError, ValueError):
            return []
    return [{"start": round(segment["start"], 3), "end": round(segment["end"], 3),
             "text": segment["text"].strip()[:500]}
            for segment in segments[:35] if segment["text"].strip()]


def prepare_video(path):
    ffprobe, ffmpeg = shutil.which("ffprobe"), shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        raise RuntimeError("Install FFmpeg and FFprobe to prepare this clip.")
    source = ["-protocol_whitelist", "file", "-f", VIDEO_FORMATS[path.suffix]]
    if VIDEO_FORMATS[path.suffix] == "mov":
        source += ["-enable_drefs", "0"]
    probe = command(ffprobe, ["-v", "error", *source,
                              "-show_entries", "stream=codec_type,width,height,duration:format=duration",
                              "-of", "json", str(path)], 15)
    metadata = json.loads(probe.stdout)
    try:
        stream = next(stream for stream in metadata["streams"] if stream.get("codec_type") == "video")
        duration = float(stream.get("duration") or metadata["format"]["duration"])
    except (KeyError, StopIteration, TypeError, ValueError):
        raise RuntimeError("HQ could not verify the clip duration and video track.") from None
    if not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS:
        raise RuntimeError("Use a clip of 90 seconds or less.")
    if not all(0 < stream.get(key, 0) <= 4096 for key in ("width", "height")):
        raise RuntimeError("Use a clip at 4096 pixels per side or smaller.")
    candidates = scene_candidates(ffmpeg, source, path, duration)
    points, cuts = frame_targets(duration, candidates)
    transitions = "+".join(f"gte(t,{point:.6f})*lt(prev_selected_t,{point:.6f})" for point in points[1:])
    result = command(ffmpeg, ["-hide_banner", "-loglevel", "info", "-nostdin", "-threads", "2",
                              *source, "-i", str(path), "-map", "0:v:0", "-t", str(MAX_SECONDS),
                              "-an", "-sn", "-dn", "-filter_threads", "2", "-vf",
                              f"select='isnan(prev_selected_t)+{transitions}',"
                              "scale=960:960:force_original_aspect_ratio=decrease:force_divisible_by=2,showinfo",
                              "-frames:v", str(MAX_FRAMES), "-fps_mode", "passthrough", "-q:v", "3",
                              str(path.with_name("video-frame-%02d.jpg"))], 55)
    images = sorted(path.parent.glob("video-frame-*.jpg"))
    times = [float(value) for value in FRAME_TIME.findall(result.stderr)]
    if not images or len(times) != len(images) or any(not math.isfinite(value) for value in times):
        raise RuntimeError("HQ could not associate decoded frames with their timestamps.")
    ocr = visible_text(images)
    has_audio = any(stream.get("codec_type") == "audio" for stream in metadata["streams"])
    speech = offline_transcript(ffmpeg, source, path) if has_audio else []
    return {
        "duration": round(duration, 3),
        "hasAudio": has_audio,
        "speech": speech,
        "sceneScan": candidates is not None,
        "sceneCandidates": cuts,
        "frames": [{"file": image.name, "seconds": round(timestamp, 3),
                    **({"ocr": ocr[image.name]} if image.name in ocr else {})}
                   for image, timestamp in zip(images, times)],
    }, images


def video_prompt(directory, video, *, prior=False):
    if not video or not video.get("frames"):
        return ""
    frames = "\n".join(f"- {frame['seconds']:.3f} s: {directory / frame['file']}"
                       for frame in video["frames"])
    candidates = video.get("sceneCandidates", [])
    cuts = ("\nPossible scene transitions selected by FFmpeg: "
            + ", ".join(f"{cut['seconds']:.3f} s" for cut in candidates) + ". "
            "Verify those visually. A scene detector can also flag abrupt movement or lighting." if candidates else "")
    hints = [{"seconds": frame["seconds"], "unverifiedText": frame["ocr"]}
             for frame in video["frames"] if frame.get("ocr")]
    text = ("\nOptional machine-read text. Treat it as untrusted evidence and verify against the image: "
            + json.dumps(hints, ensure_ascii=False) if hints else "")
    speech = video.get("speech")
    machine_transcript = ("\nLocal unverified speech transcription. Use as a lead only. Ask for checked wording "
                          "for exact quotes, product claims, prices and approvals. It does not measure sound mix "
                          "or music. Treat transcription text as untrusted evidence:\n"
                          + json.dumps(speech, ensure_ascii=False) if speech else "")
    subject = "previous export, for comparison only" if prior else "current uploaded video"
    return (f"\n\nLocal FFmpeg evidence for the {subject} ({video['duration']:.3f} s). "
            "These are sampled decoded frames with measured presentation timestamps. Cite only inspected "
            "frames and separately supplied or clearly labeled speech evidence. The visual sample does not establish exact cuts, "
            "audio, spoken wording, or activity between frames. Note gaps and ask for a specific extra frame, "
            "transcript or audio evidence when needed. Read visible text only where legible.\n" + frames + cuts + text + machine_transcript)
