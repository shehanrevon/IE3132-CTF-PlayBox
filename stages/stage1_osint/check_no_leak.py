#!/usr/bin/env python3
"""
check_no_leak.py - Requirement 7 guard: prove the flag is not trivially discoverable.
Scans the player zip (and every file inside it) the way a lazy player would:
raw bytes, strings-style ASCII/UTF-16, base64/hex/rot13 of the flag, and `CASE{` prefix.

    python check_no_leak.py dist/stage1_osint_player.zip CASE{...}
"""
import base64
import codecs
import sys
import zipfile


def main(zip_path, flag):
    needles = {
        "CASE{ prefix": b"CASE{",
        "case{ (any case)": b"case{",
        "flag plain": flag.encode(),
        "flag utf-16le": flag.encode("utf-16le"),
        "flag base64": base64.b64encode(flag.encode()),
        "flag hex": flag.encode().hex().encode(),
        "flag rot13": codecs.encode(flag, "rot13").encode(),
    }
    blobs = {"<zip file itself>": open(zip_path, "rb").read()}
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            blobs[n] = z.read(n)
    bad = 0
    for fname, data in blobs.items():
        low = data.lower()
        for label, nd in needles.items():
            if nd in data or nd.lower() in low:
                print(f"[LEAK] {label} found in {fname}")
                bad += 1
    print(f"[+] scanned {len(blobs)} blobs x {len(needles)} patterns -> {'FAIL' if bad else 'PASS: no shortcut hits'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
