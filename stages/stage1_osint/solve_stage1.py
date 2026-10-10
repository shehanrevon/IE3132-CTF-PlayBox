#!/usr/bin/env python3
"""
solve_stage1.py - intended-path solver for Stage 1 (OSINT).  Fully offline.

    python solve_stage1.py dist/site          # or the extracted meridian_forum/ folder

Mirrors what a player does by hand:
  1. Forum -> the suspicious poster is @larkspur
  2. larkspur's workspace photo -> EXIF GPS + Artist  (ExifTool by hand; Pillow here)
  3. GPS -> nearest hub on the Locations page
  4. Artist + hub -> unique row in the Staff Directory
  5. Assemble CASE{STAFFID_HUBCODE_handle}
"""
import math
import re
import sys
from pathlib import Path

from PIL import Image


def dms_to_deg(dms, ref):
    d, m, s = (float(x) for x in dms)
    v = d + m / 60 + s / 3600
    return -v if ref in ("S", "W") else v


def read_exif(path):
    ex = Image.open(path).getexif()
    gps = ex.get_ifd(0x8825)
    lat = dms_to_deg(gps[2], gps[1])
    lon = dms_to_deg(gps[4], gps[3])
    return ex.get(0x013B), lat, lon


def haversine_m(a, b, c, d):
    R = 6371000
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def table_rows(html_text):
    return [re.findall(r"<td>(.*?)</td>", r, re.S) for r in re.findall(r"<tr>(.*?)</tr>", html_text, re.S)
            if "<td>" in r]


def main(site):
    site = Path(site)
    handle = "larkspur"   # the poster of the suspicious ledger thread (step 1, read by a human)
    assert "larkspur" in (site / "thread_ledger.html").read_text(encoding="utf-8")
    print(f"[1] suspicious poster      : @{handle}")

    artist, lat, lon = read_exif(site / "assets" / f"workspace_{handle}.jpg")
    print(f"[2] EXIF Artist            : {artist}")
    print(f"    EXIF GPS               : {lat:.5f}, {lon:.5f}")

    hubs = []
    for r in table_rows((site / "company" / "locations.html").read_text(encoding="utf-8")):
        code = re.sub("<.*?>", "", r[0])
        hubs.append((code, float(re.search(r"[\d.]+", r[2]).group()), float(re.search(r"[\d.]+", r[3]).group())))
    hub = min(hubs, key=lambda h: haversine_m(lat, lon, h[1], h[2]))
    print(f"[3] nearest hub            : {hub[0]} ({haversine_m(lat, lon, hub[1], hub[2]):.0f} m from gate)")

    first, initial = artist.split()[0], artist.split()[1][0]
    cands = []
    for name, sid, dept, h, ext in table_rows((site / "company" / "directory.html").read_text(encoding="utf-8")):
        n = name.split()
        if h == hub[0] and "Finance" in dept and n[0] == first and n[1][0] == initial:
            cands.append((name, sid))
    assert len(cands) == 1, f"ambiguous: {cands}"
    name, sid = cands[0]
    print(f"[4] directory match        : {name} / {sid}")

    flag = f"CASE{{{sid}_{hub[0]}_{handle}}}"
    print(f"[5] FLAG                   : {flag}")
    return flag


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist/site")
