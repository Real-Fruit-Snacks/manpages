#!/usr/bin/env python3
"""Generate docs/favicon.ico (32x32, 32bpp BMP-in-ICO) — terminal chevron + cursor.

Stdlib only; deterministic output so rebuilds don't churn git.
"""
import math
import struct
import sys

SIZE = 32
BG = (0x0d, 0x0c, 0x09, 0xff)      # BGRA: #090c0d opaque
FG = (0xab, 0xf2, 0x63, 0xff)      # BGRA: #63f2ab
TRANSPARENT = (0, 0, 0, 0)
RADIUS = 6                          # rounded corners


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def in_rounded_square(x, y):
    r = RADIUS
    cx = min(max(x, r), SIZE - 1 - r)
    cy = min(max(y, r), SIZE - 1 - r)
    return math.hypot(x - cx, y - cy) <= r + 0.2


def pixel(x, y):
    if not in_rounded_square(x, y):
        return TRANSPARENT
    # chevron ">" : (9,8)->(18,16)->(9,24), stroke ~2.4px
    d = min(seg_dist(x, y, 9, 8, 18, 16), seg_dist(x, y, 18, 16, 9, 24))
    if d <= 2.4:
        return FG
    # cursor block: x 21..26, y 20..24
    if 21 <= x <= 26 and 20 <= y <= 24:
        return FG
    return BG


def main(out_path):
    # BMP rows bottom-up
    xor_data = b''.join(
        struct.pack('<4B', *pixel(x, y))
        for y in range(SIZE - 1, -1, -1) for x in range(SIZE))
    and_row = b'\x00' * (SIZE // 8)
    and_data = and_row * SIZE
    bmp_header = struct.pack('<IiiHHIIiiII', 40, SIZE, SIZE * 2, 1, 32, 0,
                             len(xor_data) + len(and_data), 0, 0, 0, 0)
    image = bmp_header + xor_data + and_data
    ico = struct.pack('<HHH', 0, 1, 1)
    ico += struct.pack('<BBBBHHII', SIZE, SIZE, 0, 0, 1, 32, len(image), 22)
    ico += image
    with open(out_path, 'wb') as f:
        f.write(ico)
    print('wrote %s (%d bytes)' % (out_path, len(ico)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'docs/favicon.ico')
