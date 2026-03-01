# avif_handler.py
# ────────────────────────────────────────────────
# UPDATED FINAL VERSION - Forensic-aware AVIF compression
# Changes:
# - Added pillow-heif for HEIC/HEIF support
# - Small-file protection now <600 KB with 35% cap
# - Hard minimum size safeguard (~60 KB fallback)
# - Unconditional skip for existing AVIF files
# - Prevent over-downscaling on medium-small originals
# - Higher quality fallback when compression is too aggressive
# - New: warning message when original_size_kb < 100 KB
# ────────────────────────────────────────────────

import io
import os
from typing import Optional, Union

from PIL import Image
import pillow_heif
pillow_heif.register_heif_opener()  # Enables HEIC / HEIF support
pillow_heif.register_avif_opener()  # Extra compatibility for AVIF

# ────────────────────────────────────────────────
# CONSTANTS
# ────────────────────────────────────────────────
MIN_QUALITY_FLOOR = 70
PREFERRED_MIN_QUALITY = 75
MIN_SAFE_FINAL_KB = 60          # Hard floor - don't go below this unless original was tiny

COMPRESSION_THRESHOLDS = {
    "JPEG": {
        "max_dim": 1536,
        "quality": 82,
        "target_reduction_pct": 65,
    },
    "WEBP": {
        "max_dim": 1400,
        "quality": 82,
        "target_reduction_pct": 70,
    },
    "PNG": {
        "max_dim": 1024,
        "quality": 80,
        "target_reduction_pct": 75,
    },
    "AVIF": {
        "max_dim": 2048,
        "quality": 88,
        "target_reduction_pct": 40,
    },
    "BMP": {
        "max_dim": 1024,
        "quality": 78,
        "target_reduction_pct": 70,
    },
    "TIFF": {
        "max_dim": 1024,
        "quality": 78,
        "target_reduction_pct": 70,
    },
    "GIF": {
        "max_dim": 1024,
        "quality": 78,
        "target_reduction_pct": 70,
    },
    "HEIF": {
        "max_dim": 1920,
        "quality": 85,
        "target_reduction_pct": 60,
    },
    "HEIC": {
        "max_dim": 1920,
        "quality": 85,
        "target_reduction_pct": 60,
    },
    "DEFAULT": {
        "max_dim": 1200,
        "quality": 80,
        "target_reduction_pct": 65,
    },
}


def is_avif(data: bytes) -> bool:
    if len(data) < 16:
        return False
    if data[4:8] != b"ftyp":
        return False
    major_brand = data[8:12]
    return major_brand in (b"avif", b"avis")


def is_avif_pillow(data: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(data)) as img:
            return img.format == "AVIF"
    except Exception:
        return False


def get_auto_params(img: Image.Image, original_format: str, original_size_kb: float) -> dict:
    fmt = (original_format or "DEFAULT").upper()
    base = COMPRESSION_THRESHOLDS.get(fmt, COMPRESSION_THRESHOLDS["DEFAULT"]).copy()

    w, h = img.size
    max_side = max(w, h)

    if max_side > 5000:
        base["max_dim"] = min(base["max_dim"], 1024)
    elif max_side > 3000:
        base["max_dim"] = min(base["max_dim"], 1280)
    elif max_side > 2000:
        base["max_dim"] = min(base["max_dim"], 1536)

    # Prevent over-downscaling on medium-small files
    if original_size_kb < 600:
        base["max_dim"] = max(base["max_dim"], 1024)

    if original_size_kb > 10000:
        base["quality"] = max(75, base["quality"] - 5)

    return base


def compress_to_avif(
    input_data: bytes,
    max_dimension: int,
    start_quality: int,
    target_reduction_pct: int,
    original_size_kb: float,
) -> bytes:
    img = Image.open(io.BytesIO(input_data))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    current_quality = start_quality
    max_attempts = 10

    target_size_kb = original_size_kb * (1 - target_reduction_pct / 100.0)
    print(f"   Target: \u2265{target_reduction_pct}% reduction (~{target_size_kb:.0f} KB)")

    for attempt in range(max_attempts):
        output.seek(0)
        output.truncate(0)

        img.save(
            output,
            format="AVIF",
            quality=current_quality,
            effort=4,
        )

        result_bytes = output.getvalue()
        size_kb = len(result_bytes) / 1024.0
        reduction_pct = (original_size_kb - size_kb) / original_size_kb * 100

        print(f"   Attempt {attempt+1}: Q={current_quality} | {size_kb:.1f} KB | {reduction_pct:.1f}% reduced")

        if reduction_pct >= target_reduction_pct or current_quality <= MIN_QUALITY_FLOOR:
            print(f"   \u2192 Stopped at Q={current_quality} | {size_kb:.1f} KB | {reduction_pct:.1f}%")
            return result_bytes

        current_quality = max(MIN_QUALITY_FLOOR, current_quality - 5)

    print(f"   \u2192 Reached floor Q={current_quality} | {size_kb:.1f} KB")
    return output.getvalue()


def process_image(data_or_path: Union[bytes, str], output_path: Optional[str] = None) -> bytes:
    """
    Main function - supports both bytes (for web) and path (for CLI)
    """
    if isinstance(data_or_path, str):
        with open(data_or_path, "rb") as f:
            data = f.read()
    else:
        data = data_or_path

    original_size_kb = len(data) / 1024.0
    print(f"Original size: {original_size_kb:.1f} KB")

    # NEW: Warning for very small images
    if original_size_kb < 100:
        print("\u26a0 Very small image - forensic confidence may be lower")

    # Quick + Pillow check
    already_avif = is_avif(data)
    if not already_avif:
        already_avif = is_avif_pillow(data)

    # Skip re-compression for any existing AVIF
    if already_avif:
        print("\u2192 Already AVIF \u2192 skipping re-compression (preserves original forensic quality)")
        result_bytes = data
        if output_path:
            with open(output_path, "wb") as f:
                f.write(result_bytes)
            print(f"Saved original AVIF: {output_path}")
        return result_bytes

    # Compress non-AVIF files
    print("\u2192 Compressing to AVIF (forensic-friendly settings)...")
    img = Image.open(io.BytesIO(data))
    original_format = img.format or "UNKNOWN"
    params = get_auto_params(img, original_format, original_size_kb)

    effective_reduction_pct = params["target_reduction_pct"]

    # Stronger protection for small/medium files
    if original_size_kb < 600:
        effective_reduction_pct = min(effective_reduction_pct, 35)
        print(f"Small/medium file ({original_size_kb:.1f} KB) \u2192 reduction capped at {effective_reduction_pct}%")

    print(f"   Format: {original_format} | "
          f"max_dim={params['max_dim']} | "
          f"start_quality={params['quality']} | "
          f"target_reduction={effective_reduction_pct}%")

    result_bytes = compress_to_avif(
        data,
        max_dimension=params["max_dim"],
        start_quality=params["quality"],
        target_reduction_pct=effective_reduction_pct,
        original_size_kb=original_size_kb,
    )

    final_size_kb = len(result_bytes) / 1024.0

    # Hard safeguard: if went too small \u2192 fallback to milder compression
    if final_size_kb < MIN_SAFE_FINAL_KB and original_size_kb > 150:
        print(f"WARNING: Final size too small ({final_size_kb:.1f} KB) \u2192 fallback to higher quality")
        result_bytes = compress_to_avif(
            data,
            max_dimension=params["max_dim"],
            start_quality=85,
            target_reduction_pct=20,
            original_size_kb=original_size_kb,
        )
        final_size_kb = len(result_bytes) / 1024.0

    reduction = (original_size_kb - final_size_kb) / original_size_kb * 100
    print(f"\u2192 Final: {final_size_kb:.1f} KB ({reduction:.1f}% smaller)")

    if output_path:
        with open(output_path, "wb") as f:
            f.write(result_bytes)
        print(f"Saved: {output_path}")

    return result_bytes


# ────────────────────────────────────────────────
# Command-line testing
# ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python avif_handler.py input.jpg [output.avif]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else None

    try:
        compressed = process_image(input_file, output_file)
        print("Compression completed successfully.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
