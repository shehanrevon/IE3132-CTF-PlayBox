# Stage 2 - Networking ("The Drop")  |  Owner: Palugaswewa K I K I B
Difficulty: Easy  |  Delivery: static pcap via CTFd  |  Fully offline  |  Live-container option: NOT built (see below)

## Story
The insider's workstation (10.20.4.17) was captured for ~90 s. Normal intranet browsing, DNS and a timesheet upload hide
one exfiltration: a POST of an encrypted file to an odd host on port 8443.

## Intended solve
1. Wireshark: Statistics -> Conversations / filter `dns` and `http`. Hosts: intranet/updates (internal, normal), `timesheets.partner-hr.test`
   (plain-text decoy) and **`drop.silentledger-mail.test`** (203.0.113.50:8443, odd).
2. `http.request.method == "POST"` -> Follow TCP Stream on the `/u/ledger.dat` upload (body split over 2 TCP segments).
3. Headers: `Content-Type: application/octet-stream`, `X-Key-Hint: case-file-1 answer, exactly as submitted`, `X-Check: <8 hex>`.
4. Body is **XOR with repeating key = Stage 1 flag** (`CASE{MFC2291_CMB01_larkspur}`). Decrypt in CyberChef / Python.
5. `X-Check` = first 8 hex of SHA-256(plaintext) -> lets players verify they have the right key.
6. Plaintext includes `ref: CASE{exfil_stream_confirmed_5547}`  <- Stage 2 flag.
   It also contains portal credentials (`dwijesekara` / `Ledger#2291`) that Stage 3 (IDOR web app) should accept - keep them consistent.

## Why there are no shortcuts (Requirement 7)
- Flag exists only inside XOR ciphertext: `strings` / `grep` / single-byte-XOR brute-force find nothing (`check_no_leak.py`).
- Stage 1 is a **technical** prerequisite: without the exact Stage 1 answer the payload stays gibberish - hiding the CTFd page is not what protects it.
- Decoy streams (plain-text timesheet POST, intranet GETs) make the player actually analyse the traffic.

## Build / test
```powershell
cd stages\stage2_networking
python pcap_generator.py --print-flag
python solve_stage2.py dist\silent_ledger_capture.pcap "CASE{MFC2291_CMB01_larkspur}"
python check_no_leak.py dist\silent_ledger_capture.pcap "CASE{exfil_stream_confirmed_5547}" "CASE{MFC2291_CMB01_larkspur}"
```
No pip installs needed (standard library only). Output is deterministic (fixed RNG seed), so rebuilds are identical.

## Reset / recovery
Static stage: nothing to reset. Re-run `pcap_generator.py` to regenerate the identical file.

## Live two-container option
Not built. Per the master doc, confirm with Kosgollage first: it needs an extra isolated Docker network. Static pcap alone
satisfies the stage (Easy, offline, reset-free). Raise it only if there is spare time.

## Files
| File | Purpose |
|---|---|
| `pcap_generator.py` | **Self-developed script** (Requirement 6): hand-builds Ethernet/IPv4/TCP/UDP/DNS/HTTP packets, valid checksums, XOR payload |
| `solve_stage2.py` | Intended-path solver (use in video) + checksum validation |
| `check_no_leak.py` | Shortcut scanner |
| `hints.md`, `challenges_block.yml` | CTFd hints + block |
| `dist/silent_ledger_capture.pcap` | The file players download |
