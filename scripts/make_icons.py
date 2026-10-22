"""Writes simple PNG app icons (white page on indigo) using only the stdlib."""
import struct
import zlib
from pathlib import Path

BG = (79, 70, 229)
FG = (255, 255, 255)


def chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def pixel(x: float, y: float):
    """x, y are fractions of the icon size."""
    if 0.25 <= x < 0.75 and 0.18 <= y < 0.82:
        for top in (0.32, 0.46, 0.60):
            if top <= y < top + 0.06 and 0.33 <= x < 0.67:
                return BG
        return FG
    return BG


def png(size: int) -> bytes:
    rows = bytearray()
    for py in range(size):
        rows.append(0)  # filter type: none
        for px in range(size):
            rows.extend(pixel(px / size, py / size))
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "site" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    for size in (180, 192, 512):
        (out / f"icon-{size}.png").write_bytes(png(size))
