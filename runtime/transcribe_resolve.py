#!/usr/bin/env python3
"""Create local word-timed transcript JSON for Resolve edit planning."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from faster_whisper import WhisperModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--engine", choices=("faster-whisper", "mlx"), default="faster-whisper")
    parser.add_argument("--model", help="Optional model path or model ID")
    args = parser.parse_args()
    if not args.media.is_file():
        parser.error("The source media file was not found.")
    if args.media.resolve() == args.output.resolve():
        parser.error("Use a new output path for the transcript.")
    pcm = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(args.media), "-map", "0:a:0",
         "-ar", "16000", "-ac", "1", "-f", "f32le", "pipe:1"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    audio = np.frombuffer(pcm, dtype="<f4").copy()
    if not audio.size:
        parser.error("The selected media contains no audio.")
    if args.engine == "mlx":
        import mlx_whisper

        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=args.model or "mlx-community/whisper-large-v3-mlx",
            word_timestamps=True,
            condition_on_previous_text=False,
            hallucination_silence_threshold=1.0,
        )
    else:
        model = WhisperModel(args.model or "base", device="cpu", compute_type="int8",
                             local_files_only=True)
        segments, info = model.transcribe(audio, word_timestamps=True,
                                          condition_on_previous_text=False)
        entries = [{"start": s.start, "end": s.end, "text": s.text,
                    "words": [{"start": w.start, "end": w.end, "word": w.word}
                              for w in (s.words or [])]} for s in segments]
        result = {"language": info.language, "text": "".join(s["text"] for s in entries),
                  "segments": entries}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent, delete=False) as temp:
        json.dump(result, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
    Path(temp.name).replace(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
