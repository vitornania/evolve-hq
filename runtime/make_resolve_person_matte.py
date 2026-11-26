#!/usr/bin/env python3
"""Create a video-only ProRes 4444 clip with a local foreground matte."""
import argparse
from pathlib import Path
import platform
import tempfile

import av
import numpy as np
from PIL import Image


def mask_for_frame(Quartz, handler, request, rgba):
    height, width = rgba.shape[:2]
    provider = Quartz.CGDataProviderCreateWithCFData(rgba.tobytes())
    image = Quartz.CGImageCreate(width, height, 8, 32, width * 4,
                                 Quartz.CGColorSpaceCreateDeviceRGB(),
                                 Quartz.kCGImageAlphaLast, provider, None, False,
                                 Quartz.kCGRenderingIntentDefault)
    ok, error = handler.performRequests_onCGImage_error_([request], image, None)
    if not ok:
        raise RuntimeError(f"Apple Vision failed: {error}")
    observations = request.results()
    if not observations:
        return np.zeros((height, width), dtype=np.uint8)
    pixel_buffer = observations[0].pixelBuffer()
    lock = Quartz.kCVPixelBufferLock_ReadOnly
    if Quartz.CVPixelBufferLockBaseAddress(pixel_buffer, lock) != 0:
        raise RuntimeError("Apple Vision mask could not be read.")
    try:
        h = Quartz.CVPixelBufferGetHeight(pixel_buffer)
        w = Quartz.CVPixelBufferGetWidth(pixel_buffer)
        stride = Quartz.CVPixelBufferGetBytesPerRow(pixel_buffer)
        address = Quartz.CVPixelBufferGetBaseAddress(pixel_buffer)
        raw = address.as_buffer(h * stride) if hasattr(address, "as_buffer") else memoryview(address)
        mask = np.frombuffer(raw, dtype=np.uint8, count=h * stride).reshape(h, stride)[:, :w].copy()
    finally:
        Quartz.CVPixelBufferUnlockBaseAddress(pixel_buffer, lock)
    return np.array(Image.fromarray(mask).resize((width, height), Image.Resampling.BILINEAR))


def vision_segmenter():
    import Quartz
    import Vision

    handler = Vision.VNSequenceRequestHandler.alloc().init()
    request = Vision.VNGeneratePersonSegmentationRequest.alloc().initWithCompletionHandler_(None)
    request.setQualityLevel_(Vision.VNGeneratePersonSegmentationRequestQualityLevelAccurate)
    request.setOutputPixelFormat_(Quartz.kCVPixelFormatType_OneComponent8)
    return lambda rgba: mask_for_frame(Quartz, handler, request, rgba)


def foreground_segmenter():
    from rembg import new_session, remove

    session = new_session("u2netp")

    def segment(rgba):
        image = Image.fromarray(rgba).convert("RGB")
        mask = remove(image, session=session, only_mask=True)
        return np.asarray(mask.convert("L"), dtype=np.uint8)

    return segment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--engine", choices=("auto", "vision", "rembg"), default="auto")
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error("The input video does not exist.")
    if args.output.suffix.lower() != ".mov" or args.output.exists():
        parser.error("Choose a new .mov output path.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    use_vision = args.engine == "vision" or (args.engine == "auto" and platform.system() == "Darwin")
    try:
        segment = vision_segmenter() if use_vision else foreground_segmenter()
    except ImportError as error:
        parser.error(f"Install the optional matte dependencies in docs/SETUP.md: {error}")
    with tempfile.TemporaryDirectory(dir=args.output.parent) as folder:
        partial = Path(folder) / "matte.mov"
        with av.open(str(args.input)) as source, av.open(str(partial), "w") as target:
            incoming = source.streams.video[0]
            if incoming.average_rate is None:
                parser.error("The source video has no detectable frame rate.")
            stream = target.add_stream("prores_ks", rate=incoming.average_rate, options={"profile": "4"})
            stream.width, stream.height = incoming.width, incoming.height
            stream.pix_fmt = "yuva444p10le"
            for frame in source.decode(incoming):
                rgba = frame.to_ndarray(format="rgba")
                rgba[:, :, 3] = segment(rgba)
                matte = av.VideoFrame.from_ndarray(rgba, format="rgba")
                matte.pts, matte.time_base = frame.pts, frame.time_base
                for packet in stream.encode(matte):
                    target.mux(packet)
            for packet in stream.encode():
                target.mux(packet)
        partial.rename(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
