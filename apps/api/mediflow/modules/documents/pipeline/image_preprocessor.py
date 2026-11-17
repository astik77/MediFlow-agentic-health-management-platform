"""
Image Preprocessing for Medical Document OCR.
Normalizes EXIF orientation, enhances low-contrast/noisy scans, and prepares
RGB/BGR numpy arrays for RapidOCR / Tesseract without destroying fine decimal dots.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps


@dataclass(slots=True)
class PreprocessResult:
    """Preprocessed image array and telemetry for OCR."""

    image_bgr: np.ndarray
    width: int
    height: int
    applied_steps: list[str]


def preprocess_image_bytes(
    image_bytes: bytes,
    *,
    enhance_degraded: bool = True,
    min_width: int = 1000,
) -> PreprocessResult:
    """
    Load image bytes via Pillow (handling EXIF rotation & TIFF/WebP/PNG/JPEG),
    convert to BGR ndarray, and apply gentle OCR-safe preprocessing.
    """
    applied: list[str] = []
    with Image.open(io.BytesIO(image_bytes)) as pil_img:
        pil_img = ImageOps.exif_transpose(pil_img)
        applied.append("exif_transpose")
        rgb = pil_img.convert("RGB")
        arr_rgb = np.array(rgb)

    bgr = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]

    # Upscale small/low-res scans so decimal points and small lab units stay legible
    if w > 0 and w < min_width:
        scale = min(2.0, min_width / float(w))
        bgr = cv2.resize(
            bgr,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_CUBIC,
        )
        applied.append(f"upscale_{scale:.2f}x")
        h, w = bgr.shape[:2]

    if enhance_degraded:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # Measure actual foreground-vs-background dynamic range (p95 - p5)
        # so crisp white-background scans aren't over-processed
        p5, p95 = np.percentile(gray, [5, 95])
        dynamic_range = float(p95 - p5)
        if dynamic_range < 90.0:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            enhanced = cv2.fastNlMeansDenoising(enhanced, None, h=5, templateWindowSize=7)
            bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            applied.append("clahe_denoise")

    return PreprocessResult(
        image_bgr=bgr,
        width=w,
        height=h,
        applied_steps=applied,
    )
