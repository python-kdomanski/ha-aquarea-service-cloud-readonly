"""Generate the project's original heat-pump icon using only the stdlib."""
import math
from pathlib import Path
import struct
import zlib

BRAND = Path(__file__).resolve().parents[1] / 'custom_components/aquarea_service_cloud_ro/brand'


def rounded(x, y, left, top, right, bottom, radius):
    cx = min(max(x, left + radius), right - radius)
    cy = min(max(y, top + radius), bottom - radius)
    return left <= x <= right and top <= y <= bottom and (x-cx)**2 + (y-cy)**2 <= radius**2


def pixel(x, y):
    if not rounded(x, y, 8, 8, 248, 248, 48):
        return (0, 0, 0, 0)
    color = (22, 63, 96, 255)
    if rounded(x, y, 53, 38, 203, 219, 18):
        color = (246, 250, 253, 255)
    if (x-128)**2 + (y-110)**2 <= 48**2:
        color = (22, 63, 96, 255)
        for blade in range(3):
            angle = blade * math.tau / 3
            dx, dy = x-128, y-110
            u = dx*math.cos(angle) + dy*math.sin(angle)
            v = -dx*math.sin(angle) + dy*math.cos(angle)
            if ((u-22)/21)**2 + ((v-6)/12)**2 <= 1:
                color = (102, 207, 231, 255)
        if (x-128)**2 + (y-110)**2 <= 9**2:
            color = (246, 250, 253, 255)
    for top in (178, 190):
        if rounded(x, y, 82, top, 174, top+5, 2.5):
            color = (22, 63, 96, 255)
    if rounded(x, y, 174, 50, 188, 58, 4):
        color = (244, 152, 55, 255)
    return color


def png(size, path):
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            samples = [pixel((x+sx)*256/size, (y+sy)*256/size)
                       for sx, sy in ((.25, .25), (.75, .25), (.25, .75), (.75, .75))]
            rows.extend(round(sum(sample[channel] for sample in samples)/4) for channel in range(4))
    def chunk(name, data):
        return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name+data))
    data = b'\x89PNG\r\n\x1a\n'
    data += chunk(b'IHDR', struct.pack('!IIBBBBB', size, size, 8, 6, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(bytes(rows), 9)) + chunk(b'IEND', b'')
    path.write_bytes(data)


if __name__ == '__main__':
    BRAND.mkdir(parents=True, exist_ok=True)
    png(256, BRAND / 'icon.png')
    png(512, BRAND / 'icon@2x.png')
    print('Original brand icons generated.')
