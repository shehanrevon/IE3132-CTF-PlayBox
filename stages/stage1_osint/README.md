# Stage 1 - OSINT ("The Quiet Poster")  |  Owner: Palugaswewa K I K I B
Difficulty: Easy  |  Delivery: static package via CTFd (optional nginx viewer)  |  Fully offline

## Story
Tip: someone in Finance is hiding something about a "silent ledger". Only trace = internal staff forum.

## Intended solve (3 independent facts -> flag)
1. Forum: the "odd numbers" thread is posted by **@larkspur** (Finance & Audit; real name hidden).
2. `exiftool assets/workspace_larkspur.jpg` -> **GPS** (6.94991 N, 79.85013 E) and **Artist = "Dilani W."**
3. GPS vs Locations page -> **CMB01** (Colombo Harbour Hub). The *other* photo (@duneclimber) points to GLL02 = decoy.
4. Directory: Finance + CMB01 + "Dilani W." -> only **Dilani Wijesekara, MFC2291** (two other Dilan/Dilani Finance staff sit at other hubs / other initials).
5. Flag: `CASE{MFC2291_CMB01_larkspur}`  (CTFd: case-insensitive)

## Why there are no shortcuts (Requirement 7)
- The flag string exists in **no** player file - it is assembled from three facts. `grep`/`strings` find nothing.
- Directory alone leaves 3 Finance candidates; the photo's EXIF is required to pick one.
- `check_no_leak.py` proves it (plain, UTF-16, base64, hex, rot13, `CASE{` prefix).
- No internet: coords are matched to a local page, no reverse-geocode/image search.

## Build / test / run
```powershell
venv\Scripts\Activate.ps1
pip install -r stages\stage1_osint\requirements.txt
cd stages\stage1_osint
python build_stage1.py --print-flag          # builds dist\site + dist\stage1_osint_player.zip
python solve_stage1.py dist\site             # intended-path solver (use in your video)
python check_no_leak.py dist\stage1_osint_player.zip "CASE{MFC2291_CMB01_larkspur}"
docker compose -f docker-compose.stage1.yml up -d     # optional viewer -> http://localhost:8081
```

## Reset / recovery
Stage is static and stateless; the nginx mount is read-only. Reset = `python build_stage1.py` (regenerates identical
site + zip) then `docker compose -f docker-compose.stage1.yml up -d --force-recreate`.

## Files
| File | Purpose |
|---|---|
| `build_stage1.py` | **Self-developed generator** (Requirement 6): site, JPEGs with crafted EXIF/GPS, zip |
| `solve_stage1.py` | Intended-path solver (for video) |
| `check_no_leak.py` | Shortcut/leak scanner |
| `hints.md`, `challenges_block.yml` | CTFd hints + block for `platform/seed/challenges.yml` |
| `docker-compose.stage1.yml` | Optional nginx viewer (port 8081) |
| `dist/` | Generated output (zip is what goes into CTFd) |

## Hand-off notes
- Tell Kosgollage: port **8081** (optional viewer), file to upload = `dist/stage1_osint_player.zip`.
- Design Req. #7: build **Stage 2's pcap so it needs the Stage 1 flag** (e.g. flag as XOR/AES key for a payload) - technical dependency, not just a CTFd prerequisite.
