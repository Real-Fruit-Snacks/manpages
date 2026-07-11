#!/usr/bin/env python3
"""Generate PWA icons (icon-192.png, icon-512.png) from the favicon pixel art.

Pure stdlib PNG writer; deterministic output.
"""
import struct
import sys
import zlib

import make_favicon as fav


def chunk(tag, data):
    c = struct.pack('>I', len(data)) + tag + data
    return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)


def write_png(path, size):
    rows = b''
    for y in range(size):
        row = b'\x00'
        for x in range(size):
            b, g, r, a = fav.pixel(x * fav.SIZE // size, y * fav.SIZE // size)
            row += bytes((r, g, b, a))
        rows += row
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
           + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)
    print('wrote %s (%d bytes)' % (path, len(png)))


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'docs/assets'
    write_png(out + '/icon-192.png', 192)
    write_png(out + '/icon-512.png', 512)
