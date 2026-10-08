#!/usr/bin/env python3
"""
check_no_leak.py - Requirement 7 guard for Stage 2.
Proves neither the Stage 2 flag nor the Stage 1 key (the XOR key) is visible in the pcap
by raw search, strings-style search, or common encodings, and that single-byte XOR
(the lazy attack) does not reveal the flag either.

    python check_no_leak.py dist/silent_ledger_capture.pcap CASE{stage2} CASE{stage1}
"""
import base64
import codecs
import sys


def variants(s):
    b = s.encode()
    return {"plain": b, "utf-16le": s.encode("utf-16le"), "base64": base64.b64encode(b),
            "hex": b.hex().encode(), "rot13": codecs.encode(s, "rot13").encode()}


def main(pcap, flag2, flag1):
    data = open(pcap, "rb").read()
    bad = 0
    for label, s in (("stage2 flag", flag2), ("stage1 flag (key)", flag1)):
        for enc, nd in variants(s).items():
            if nd.lower() in data.lower():
                print(f"[LEAK] {label} visible as {enc}"); bad += 1
    if b"case{" in data.lower():
        print("[LEAK] 'CASE{' prefix present"); bad += 1
    for k in range(1, 256):                       # lazy single-byte XOR attack
        if b"CASE{" in bytes(b ^ k for b in data):
            print(f"[LEAK] single-byte XOR 0x{k:02x} reveals CASE{{"); bad += 1
    print(f"[+] scanned {len(data)} bytes -> {'FAIL' if bad else 'PASS: no shortcut hits'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(*sys.argv[1:4])
