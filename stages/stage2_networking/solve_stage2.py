#!/usr/bin/env python3
"""
solve_stage2.py - intended-path solver for Stage 2 (Networking). Pure stdlib.

    python solve_stage2.py dist/silent_ledger_capture.pcap "CASE{...stage1 answer...}"

Mirrors the Wireshark workflow:
  1. List conversations / filter noise  (here: DNS names + HTTP requests)
  2. Spot the odd one: POST of application/octet-stream to an odd host on port 8443
  3. Follow TCP stream -> extract body
  4. Read the X-Key-Hint header -> key = Stage 1 flag
  5. XOR-decrypt -> read payload -> flag
Also verifies every IP/TCP/UDP checksum so the capture is known to be well-formed.
"""
import hashlib
import socket
import struct
import sys
from collections import OrderedDict


def csum(b):
    if len(b) % 2:
        b += b"\0"
    s = sum(struct.unpack("!%dH" % (len(b) // 2), b))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def read_pcap(path):
    d = open(path, "rb").read()
    assert struct.unpack("<I", d[:4])[0] == 0xA1B2C3D4, "not a little-endian pcap"
    off, frames = 24, []
    while off < len(d):
        _, _, cap, _ = struct.unpack("<IIII", d[off:off + 16])
        frames.append(d[off + 16:off + 16 + cap])
        off += 16 + cap
    return frames


def dns_name(payload):
    i, parts = 12, []
    while payload[i]:
        n = payload[i]; parts.append(payload[i + 1:i + 1 + n].decode()); i += n + 1
    return ".".join(parts)


def xor(data, key):
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def main(pcap, key):
    frames = read_pcap(pcap)
    bad, dns_seen, streams = 0, [], OrderedDict()
    for fr in frames:
        ip = fr[14:]
        ihl = (ip[0] & 0xF) * 4
        src, dst = socket.inet_ntoa(ip[12:16]), socket.inet_ntoa(ip[16:20])
        if csum(ip[:ihl]) != 0: bad += 1
        proto = ip[9]
        seg = ip[ihl:struct.unpack("!H", ip[2:4])[0]]
        pseudo = socket.inet_aton(src) + socket.inet_aton(dst) + struct.pack("!BBH", 0, proto, len(seg))
        if csum(pseudo + seg) != 0: bad += 1
        if proto == 17 and struct.unpack("!H", seg[2:4])[0] == 53:
            dns_seen.append(dns_name(seg[8:]))
        elif proto == 6:
            sport, dport = struct.unpack("!HH", seg[:4])
            data = seg[((seg[12] >> 4) * 4):]
            if data and dport in (80, 8443):
                streams.setdefault((src, sport, dst, dport), b"")
                streams[(src, sport, dst, dport)] += data
    print(f"[0] {len(frames)} packets, checksum errors: {bad}")
    print("[1] DNS names seen         :", ", ".join(OrderedDict.fromkeys(dns_seen)))

    hit = None
    for (s, sp, d, dp), data in streams.items():
        head, _, body = data.partition(b"\r\n\r\n")
        line = head.split(b"\r\n")[0].decode()
        print(f"    stream {s}:{sp} -> {d}:{dp}  {line}")
        if line.startswith("POST") and b"application/octet-stream" in head:
            hit = (head.decode(), body)
    assert hit, "no suspicious upload found"
    head, body = hit
    print("[2] suspicious upload      : POST application/octet-stream, port 8443, host drop.silentledger-mail.test")
    hdrs = dict(l.split(": ", 1) for l in head.split("\r\n")[1:])
    print(f"[3] body bytes             : {len(body)}   (declared {hdrs['Content-Length']})")
    print(f"[4] key hint               : {hdrs['X-Key-Hint']}")
    plain = xor(body, key.encode())
    ok = hashlib.sha256(plain).hexdigest()[:8] == hdrs["X-Check"]
    print(f"[5] X-Check matches        : {ok}")
    if not ok:
        print("    -> wrong key (Stage 1 answer must be exact).")
        return None
    print("--- decrypted payload ---\n" + plain.decode().rstrip() + "\n-------------------------")
    flag = [l.split(": ", 1)[1] for l in plain.decode().splitlines() if l.startswith("ref: ")][0]
    print(f"[6] FLAG                   : {flag}")
    return flag


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist/silent_ledger_capture.pcap",
         sys.argv[2] if len(sys.argv) > 2 else "CASE{MFC2291_CMB01_larkspur}")
