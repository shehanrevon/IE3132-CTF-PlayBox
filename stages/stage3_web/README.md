# Stage 3 - Web / IDOR ("The Ledger Portal")  |  Owner: Palugaswewa K I K I B
Difficulty: Moderate  |  Delivery: Docker container (Flask + gunicorn)  |  Host port 8082 (CONFIRMED by Kosgollage)

## Story
Stage 2's decrypted payload leaked one working login for Meridian Freight's Ledger Portal. The evidence the insider was hiding
sits in a colleague's record.

## Intended solve (two chained IDORs)
1. Log in: `dwijesekara` / `Ledger#2291` (recovered in Stage 2 - this is the technical Stage 2 -> 3 dependency).
2. Dashboard shows only statement **5017**. Its note says Compliance's follow-up is **statement 5042**.
3. **IDOR #1**: `/statement/5042` (also `/api/statements/5042`) opens although it belongs to Ishara Gunawardena - server checks *login*, not *ownership*.
4. 5042 lists attachment `shadow_batch_Q1.csv` -> `/files/9103`.
5. **IDOR #2**: the download endpoint also has no ownership check. File contains `audit_ref,CASE{sh4dow_batch_idor_9103}`.
Brute-forcing IDs 5000-5099 / 9100-9110 is also valid IDOR technique and finds the same thing.

## Why it is the ONLY way in (Requirement 7)
- No database -> no SQL injection. Passwords for every account except Dilani's are random per start.
- gunicorn (never the Flask dev server) -> no Werkzeug debugger/console. `debug=False` even for local runs.
- Flag + secret key come from environment variables, not from source, templates or any page except the evidence file.
- No user enumeration on login; unauthenticated requests to every data route redirect to /login.
- Container: read-only filesystem, all capabilities dropped, no-new-privileges, non-root user.
- `check_unintended.py` automates these checks.

## Run / test (Windows PowerShell, Docker Desktop running)
```powershell
cd stages\stage3_web
docker compose -f docker-compose.stage3.yml up -d --build
docker ps                                          # status should become (healthy)
python solve_stage3.py http://localhost:8082       # intended-path solver (use in video)
python check_unintended.py http://localhost:8082 "CASE{sh4dow_batch_idor_9103}"
```
Open http://localhost:8082 in a browser to solve it by hand.

## Network note (Kosgollage's isolation setup)
`localhost:8082` only works on the machine running Docker. Players over the Kali/WireGuard tunnel reach live services through
nginx on `10.10.10.1:<port>`. Kosgollage wires that proxy config himself once the Stage 3 PR lands - tell him when it is ready.
Proxy target for him: this container, host port 8082 -> container port 5000.

## Reset / recovery
All state is in memory. Full reset: `docker compose -f docker-compose.stage3.yml up -d --force-recreate`.
Stop: `docker compose -f docker-compose.stage3.yml down`.
Kosgollage's Docker reset mechanism can simply call the recreate command.

## Files
| File | Purpose |
|---|---|
| `app/app.py`, `app/templates/` | The deliberately vulnerable Flask app (in-memory data) |
| `Dockerfile`, `docker-compose.stage3.yml` | Container build + run (port 8082, hardened) |
| `solve_stage3.py` | Intended-path solver (stdlib only) |
| `check_unintended.py` | Unintended-solution scanner (stdlib only) |
| `hints.md`, `challenges_block.yml` | CTFd hints + block |

## Versions
Python 3.11 (container: python:3.11-slim), Flask 3.1.3, gunicorn 23.0.0. Solver/checker: Python stdlib only.
