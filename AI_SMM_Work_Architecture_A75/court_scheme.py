# -*- coding: utf-8 -*-
"""Regulation tennis court as canny-style edge map (white on black), pure stdlib PNG."""
import struct, zlib
from pathlib import Path

W = H = 1024
INPUT_DIR = Path(r"C:\ComfyUI_windows_portable\ComfyUI\input")

def _png(path, buf, w, h):
    raw = b"".join(b"\x00" + bytes(buf[y*w*3:(y+1)*w*3]) for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)

def _line(buf, x0, y0, x1, y1, r=1):
    dx = abs(x1-x0); dy = -abs(y1-y0)
    sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for ox in range(-r, r+1):
            for oy in range(-r, r+1):
                px, py = x+ox, y+oy
                if 0 <= px < W and 0 <= py < H:
                    i = (py*W+px)*3
                    buf[i] = buf[i+1] = buf[i+2] = 255
        if x == x1 and y == y1:
            break
        e2 = 2*err
        if e2 >= dy: err += dy; x += sx
        if e2 <= dx: err += dx; y += sy

def _court(buf):
    yh, K, z0, L, cx = 150.0, 830.0, 1.0, 1.964, 512.0
    def geom(t):
        z = z0 + L*t
        return yh + K/z, 460.0/z
    y0, w0 = geom(0.0); y1, w1 = geom(1.0)
    _line(buf, int(cx-w0), int(y0), int(cx+w0), int(y0))          # near baseline
    _line(buf, int(cx-w1), int(y1), int(cx+w1), int(y1))          # far baseline
    _line(buf, int(cx-w0), int(y0), int(cx-w1), int(y1))          # doubles sidelines
    _line(buf, int(cx+w0), int(y0), int(cx+w1), int(y1))
    _line(buf, int(cx-0.75*w0), int(y0), int(cx-0.75*w1), int(y1))  # singles sidelines
    _line(buf, int(cx+0.75*w0), int(y0), int(cx+0.75*w1), int(y1))
    yn, wn = geom(0.5)
    _line(buf, int(cx-wn-12), int(yn), int(cx+wn+12), int(yn), r=2)  # net
    for t in (0.2307, 0.7693):                                     # service lines
        ys, ws = geom(t)
        _line(buf, int(cx-0.75*ws), int(ys), int(cx+0.75*ws), int(ys))
    ya, _ = geom(0.2307); yb, _ = geom(0.7693)
    _line(buf, int(cx), int(ya), int(cx), int(yb))                # center service line
    _line(buf, int(cx), int(y0)-14, int(cx), int(y0))             # center marks
    _line(buf, int(cx), int(y1), int(cx), int(y1)+14)

def ensure_scheme(name="court_scheme.png"):
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    p = INPUT_DIR / name
    buf = bytearray(W*H*3)
    _court(buf)
    _png(p, buf, W, H)
    return p
