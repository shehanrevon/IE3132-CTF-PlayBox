#!/usr/bin/env python3
"""
check_unintended.py - Requirement 7 guard for Stage 3: make sure the IDOR is the ONLY way in.
Standard library only.   python check_unintended.py http://localhost:8082 "CASE{...}"

Checks (all must PASS):
  - nothing unauthenticated returns the flag or any record (everything redirects to /login)
  - Werkzeug debugger / console / common leak paths are not exposed
  - a wrong password and an unknown user are indistinguishable (no user enumeration)
  - SQL-injection style logins fail
  - the flag does not appear in login, dashboard or the user's OWN statement/files
  - Server header does not reveal a debug server
"""
import http.cookiejar
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def req(base, path, data=None, opener=None):
    op = opener or urllib.request.build_opener(NoRedirect)
    try:
        r = op.open(base + path, urllib.parse.urlencode(data).encode() if data else None)
        return r.status, r.read().decode(errors="replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), dict(e.headers)


def main(base, flag):
    bad = 0
    def check(name, ok, detail=""):
        nonlocal bad
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")
        bad += (not ok)

    print("Unauthenticated access")
    for p in ("/dashboard", "/statement/5042", "/api/statements/5042", "/files/9103"):
        s, body, _ = req(base, p)
        check(p, s == 302 and flag not in body, f"-> {s}")

    print("Hidden / debug paths")
    for p in ("/console", "/static/../app.py", "/app.py", "/.env", "/robots.txt", "/admin", "/statement/abc", "/files/-1"):
        s, body, _ = req(base, p)
        check(p, s in (302, 404) and flag not in body and "Traceback" not in body, f"-> {s}")
    s, body, h = req(base, "/login")
    check("Server header not a dev/debug server", "Werkzeug" not in h.get("Server", ""), f"({h.get('Server')})")

    print("Login hardening")
    a = req(base, "/login", {"username": "dwijesekara", "password": "wrong"})
    b = req(base, "/login", {"username": "nobody", "password": "wrong"})
    check("no user enumeration", a[0] == b[0] == 200 and a[1] == b[1])
    for u, pw in (("' OR '1'='1", "x"), ("admin'--", "x"), ("igunawardena", "' OR 1=1--")):
        s, body, _ = req(base, "/login", {"username": u, "password": pw})
        check(f"SQLi-style login {u!r}", s == 200 and "Invalid" in body)

    print("Flag not visible on the player's own pages")
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    page = op.open(base + "/login", urllib.parse.urlencode({"username": "dwijesekara", "password": "Ledger#2291"}).encode()).read().decode()
    own = op.open(base + "/statement/5017").read().decode()
    f1 = op.open(base + "/files/9101").read().decode()
    check("dashboard / own statement / own file", flag not in page + own + f1)

    print(f"\n{'FAIL' if bad else 'PASS: IDOR is the only way in'} ({bad} failed)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/"), sys.argv[2])
