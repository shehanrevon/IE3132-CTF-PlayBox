#!/usr/bin/env python3
"""
build_stage1.py - Stage 1 (OSINT) generator for Operation Silent Ledger.
Owner: Palugaswewa K I K I B   (self-developed script, Requirement 6)

Builds the fully OFFLINE "Meridian Freight staff forum" mock site and the
player package.  Nothing here touches the internet: no CDNs, no web fonts,
no remote images, no reverse lookups.

    python build_stage1.py            # -> dist/site/ and dist/stage1_osint_player.zip

The flag is NEVER written into any player-facing file.  The player must
assemble it from three separately discovered facts:
    CASE{<STAFF_ID>_<HUB_CODE>_<forum_handle>}
        forum handle : read from the forum (larkspur)
        hub code     : GPS EXIF of larkspur's photo  -> matched to Locations page
        staff ID     : Artist EXIF ("Dilani W.") + hub -> unique Directory row
"""
import argparse
import html
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.TiffImagePlugin import IFDRational

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"

# ----------------------------------------------------------------- ANSWER KEY
# (kept in the generator only - never copied into dist/)
INSIDER = {
    "handle": "larkspur",
    "name": "Dilani Wijesekara",
    "artist_exif": "Dilani W.",
    "staff_id": "MFC2291",
    "hub": "CMB01",
}
FLAG = f"CASE{{{INSIDER['staff_id']}_{INSIDER['hub']}_{INSIDER['handle']}}}"

# ------------------------------------------------------------------- WORLD DATA
HUBS = [
    # code,  name,                       lat,     lon
    ("CMB01", "Colombo Harbour Hub",     6.9497, 79.8503),
    ("GLL02", "Galle Depot",             6.0329, 80.2170),
    ("KDY03", "Kandy Depot",             7.2906, 80.6337),
    ("KGL04", "Kegalle Transfer Depot",  7.2513, 80.3464),
]
HUB_BY_CODE = {h[0]: h for h in HUBS}

STAFF = [
    # name,                    staff id,  dept,                hub,     ext
    ("Dilani Wijesekara",      "MFC2291", "Finance & Audit",   "CMB01", "4417"),
    ("Dilani Weerasinghe",     "MFC1873", "Finance & Audit",   "KDY03", "3302"),
    ("Dilan Wickramasinghe",   "MFC3350", "Finance & Audit",   "CMB01", "4421"),
    ("Nuwan Jayasinghe",       "MFC1042", "Operations",        "CMB01", "4102"),
    ("Tharindu Senanayake",    "MFC1190", "Operations",        "GLL02", "2208"),
    ("Ishara Gunawardena",     "MFC2754", "Customs & Compliance", "CMB01", "4455"),
    ("Kasun Ratnayake",        "MFC3011", "Fleet",             "KGL04", "5120"),
    ("Sachini Abeywickrama",   "MFC2618", "HR",                "KDY03", "3315"),
    ("Mahesh Karunaratne",     "MFC1986", "IT Support",        "CMB01", "4001"),
    ("Chamari Dissanayake",    "MFC3207", "Finance & Audit",   "GLL02", "2230"),
    ("Roshan Pathirana",       "MFC1455", "Warehouse",         "KGL04", "5133"),
    ("Anushka Madushani",      "MFC2890", "Warehouse",         "KDY03", "3340"),
]

# second photo: a different Finance user, different hub (decoy that forces
# the player to pick the right author, not just "any photo")
DECOY = {"handle": "duneclimber", "artist_exif": "C. Dissanayake", "hub": "GLL02"}

CSS = """
*{box-sizing:border-box}body{font-family:Arial,Helvetica,sans-serif;background:#eef1f5;color:#222;margin:0}
header{background:#12355b;color:#fff;padding:14px 28px}header h1{margin:0;font-size:22px}
header small{color:#a9c3e0}nav{background:#0d2a48;padding:8px 28px}
nav a{color:#cfe2f7;margin-right:18px;text-decoration:none;font-size:14px}nav a:hover{text-decoration:underline}
main{max-width:880px;margin:22px auto;padding:0 18px}
.card{background:#fff;border:1px solid #d5dbe3;border-radius:6px;padding:16px 20px;margin-bottom:16px}
.post{border-left:4px solid #12355b}.meta{color:#667;font-size:12px;margin-bottom:8px}
table{border-collapse:collapse;width:100%;background:#fff}th,td{border:1px solid #d5dbe3;padding:7px 10px;font-size:14px;text-align:left}
th{background:#e3eaf3}img.photo{max-width:100%;border:1px solid #ccc;border-radius:4px}
.sig{color:#778;font-size:12px;border-top:1px dashed #ccd;margin-top:10px;padding-top:6px}
footer{text-align:center;color:#889;font-size:12px;padding:24px}a{color:#12508f}
"""

# ---------------------------------------------------------------------- HELPERS
def page(title, body, depth=0):
    up = "../" * depth
    nav = (f'<a href="{up}index.html">Forum</a>'
           f'<a href="{up}company/locations.html">Locations</a>'
           f'<a href="{up}company/directory.html">Staff Directory</a>')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)} - Meridian Freight Staff Forum</title>
<link rel="stylesheet" href="{up}assets/style.css"></head><body>
<header><h1>Meridian Freight Co. <small>&nbsp;Internal Staff Forum (intranet mirror)</small></h1></header>
<nav>{nav}</nav><main>
{body}
</main><footer>Meridian Freight Co. internal use only. Offline mirror - no external links.</footer></body></html>
"""


def post(user, when, text, extra="", sig=""):
    s = f'<div class="sig">{html.escape(sig)}</div>' if sig else ""
    return (f'<div class="card post"><div class="meta"><a href="__UP__members/{user}.html">@{user}</a>'
            f' &middot; {when}</div><p>{text}</p>{extra}{s}</div>')


def dms(deg):
    d = int(abs(deg))
    m_full = (abs(deg) - d) * 60
    m = int(m_full)
    s = round((m_full - m) * 60, 4)
    return ((IFDRational(d, 1)), IFDRational(m, 1), IFDRational(int(s * 10000), 10000))


def draw_workspace(path, seed_color, label, exif_artist, hub_code, taken):
    """Draw a simple desk-scene JPEG and embed realistic EXIF (incl. GPS)."""
    w, h = 960, 600
    img = Image.new("RGB", (w, h), (214, 224, 236))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 330], fill=(190, 214, 240))              # window / wall
    d.rectangle([60, 40, 420, 290], outline=(255, 255, 255), width=8)
    d.line([240, 40, 240, 290], fill=(255, 255, 255), width=6)
    d.line([60, 165, 420, 165], fill=(255, 255, 255), width=6)
    d.rectangle([0, 330, w, h], fill=seed_color)                   # desk
    d.rectangle([520, 140, 860, 330], fill=(30, 34, 40))           # monitor
    d.rectangle([535, 155, 845, 315], fill=(52, 98, 160))
    d.rectangle([670, 330, 710, 370], fill=(60, 60, 60))
    d.rectangle([300, 420, 700, 470], fill=(70, 70, 76))           # keyboard
    d.rectangle([780, 400, 830, 460], fill=(240, 240, 240))        # mug
    d.rectangle([110, 410, 230, 500], fill=(250, 235, 140))        # sticky pad / notes
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    d.text((120, 430), "TODO: monthly recon", fill=(60, 60, 60), font=font)
    d.text((24, h - 26), label, fill=(255, 255, 255), font=font)

    _, _, lat, lon = HUB_BY_CODE[hub_code]
    # tiny offset so the GPS fix is "near" the hub, not identical to the listed coords
    lat_p, lon_p = lat + 0.00021, lon - 0.00017

    exif = Image.Exif()
    exif[0x010F] = "Samsung"                    # Make
    exif[0x0110] = "SM-A546E"                   # Model
    exif[0x0131] = "A546EXXU6CXB1"              # Software
    exif[0x013B] = exif_artist                  # Artist
    exif[0x0132] = taken                        # DateTime
    exif.get_ifd(0x8769)[0x9003] = taken        # DateTimeOriginal
    exif.get_ifd(0x8769)[0x9286] = b"ASCII\x00\x00\x00" + b"Desk shot for the forum thread"  # UserComment
    gps = exif.get_ifd(0x8825)
    gps[1] = "N" if lat_p >= 0 else "S"
    gps[2] = dms(lat_p)
    gps[3] = "E" if lon_p >= 0 else "W"
    gps[4] = dms(lon_p)
    img.save(path, "JPEG", quality=90, exif=exif)


# ------------------------------------------------------------------------ BUILD
def build_site(site: Path):
    if site.exists():
        shutil.rmtree(site)
    for sub in ("assets", "members", "company"):
        (site / sub).mkdir(parents=True)
    (site / "assets" / "style.css").write_text(CSS.strip(), encoding="utf-8")

    draw_workspace(site / "assets" / "workspace_larkspur.jpg", (150, 112, 78),
                   "larkspur - my corner", INSIDER["artist_exif"], INSIDER["hub"],
                   "2026:03:14 07:52:10")
    draw_workspace(site / "assets" / "workspace_duneclimber.jpg", (110, 130, 96),
                   "duneclimber - new desk", DECOY["artist_exif"], DECOY["hub"],
                   "2026:03:11 16:20:44")

    fix = lambda s, depth: s.replace("__UP__", "../" * depth)

    # ---- forum index
    idx = """
<div class="card"><h2>Boards</h2>
<table><tr><th>Thread</th><th>Started by</th><th>Replies</th></tr>
<tr><td><a href="thread_welcome.html">Welcome to the new intranet forum</a></td><td>@mahesh_it</td><td>3</td></tr>
<tr><td><a href="thread_ledger.html">Anyone else seeing odd numbers in the Q1 ledger?</a></td><td>@larkspur</td><td>4</td></tr>
<tr><td><a href="thread_workspace.html">Show off your workspace!</a></td><td>@duneclimber</td><td>5</td></tr>
<tr><td><a href="thread_canteen.html">Canteen: rice and curry rota</a></td><td>@roshan_wh</td><td>9</td></tr>
</table></div>"""
    (site / "index.html").write_text(page("Home", idx), encoding="utf-8")

    # ---- welcome thread
    t = post("mahesh_it", "02 Jan 2026, 09:10",
             "Welcome all! This forum is for staff only. Please remember: <b>do not post customer data</b>. "
             "Profile photos and attachments are fine, but you are responsible for what you upload.") + \
        post("roshan_wh", "02 Jan 2026, 11:45", "Finally, somewhere to complain about the forklift queue. Thanks IT!") + \
        post("duneclimber", "03 Jan 2026, 08:02", "Is there a dark mode? Asking for my eyes.") + \
        post("mahesh_it", "03 Jan 2026, 08:30", "Not yet. Ticket opened.")
    (site / "thread_welcome.html").write_text(fix(page("Welcome", t), 0), encoding="utf-8")

    # ---- ledger thread (the suspicious one)
    t = '<h2>Anyone else seeing odd numbers in the Q1 ledger?</h2>' + \
        post("larkspur", "09 Mar 2026, 22:14",
             "Probably just me, but three of the Q1 freight invoices reference a consignee that I cannot find in any "
             "customs record. Amounts are all just under the review threshold. Not going to name the account here. "
             "Leaving this as a quiet note in case somebody on the audit side recognises the pattern.") + \
        post("nuwan_ops", "10 Mar 2026, 07:31", "Could be a data-entry thing. Which hub batch?") + \
        post("larkspur", "10 Mar 2026, 21:50", "Not saying yet. If this is what I think it is, the less I type the better. "
             "Something like a silent ledger, running beside the real one.") + \
        post("ishara_cc", "11 Mar 2026, 08:05", "Please take this to compliance directly rather than the forum.")
    (site / "thread_ledger.html").write_text(fix(page("Odd numbers in Q1 ledger", t), 0), encoding="utf-8")

    # ---- workspace thread (the photos live here)
    def img_block(fn, alt):
        return (f'<p><img class="photo" src="assets/{fn}" alt="{alt}" width="480"></p>'
                f'<p><a href="assets/{fn}" download>Download original ({fn})</a></p>')
    t = '<h2>Show off your workspace!</h2>' + \
        post("duneclimber", "10 Mar 2026, 17:00",
             "New desk, new me. Window seat at last! Let's see yours.",
             img_block("workspace_duneclimber.jpg", "duneclimber workspace")) + \
        post("larkspur", "14 Mar 2026, 08:15",
             "Early shift, coffee, and the usual pile of paper. Here is my corner.",
             img_block("workspace_larkspur.jpg", "larkspur workspace"),
             sig="-- larkspur") + \
        post("roshan_wh", "14 Mar 2026, 09:40", "Ha, my desk is a pallet. No photo.") + \
        post("nuwan_ops", "14 Mar 2026, 10:02", "Nice monitor. Mine is from 2014.") + \
        post("mahesh_it", "14 Mar 2026, 10:30",
             "Reminder: forum compresses nothing. Uploads are stored exactly as sent.")
    (site / "thread_workspace.html").write_text(fix(page("Show off your workspace", t), 0), encoding="utf-8")

    # ---- canteen thread (noise)
    t = '<h2>Canteen: rice and curry rota</h2>' + \
        post("roshan_wh", "05 Feb 2026, 12:20", "Dhal on Monday again? Petition to swap with Thursday.") + \
        post("anushka_wh", "05 Feb 2026, 12:41", "Signed. Also: more pol sambol please.")
    (site / "thread_canteen.html").write_text(fix(page("Canteen", t), 0), encoding="utf-8")

    # ---- members
    def profile(handle, dept, joined, bio, sigline):
        body = (f'<div class="card"><h2>@{handle}</h2><table>'
                f'<tr><th>Department</th><td>{dept}</td></tr>'
                f'<tr><th>Member since</th><td>{joined}</td></tr>'
                f'<tr><th>Bio</th><td>{bio}</td></tr>'
                f'<tr><th>Signature</th><td>{sigline}</td></tr></table>'
                f'<p class="meta">Real name and location are hidden by the default forum privacy settings.</p></div>')
        (site / "members" / f"{handle}.html").write_text(page(f"@{handle}", body, depth=1), encoding="utf-8")

    profile("larkspur", "Finance &amp; Audit", "14 Jan 2024", "Numbers person. Tea over coffee, usually.", "-- larkspur")
    profile("duneclimber", "Finance &amp; Audit", "09 Jan 2024", "Weekend hiker. Will fix your spreadsheet for biscuits.", "-- dc")
    profile("mahesh_it", "IT Support", "01 Jan 2024", "Forum admin. Reboot first.", "-- IT")
    profile("roshan_wh", "Warehouse", "12 Feb 2024", "Forklift certified.", "-- pallet life")
    profile("nuwan_ops", "Operations", "20 Jan 2024", "Schedules, dispatch, repeat.", "-- ops")
    profile("ishara_cc", "Customs &amp; Compliance", "03 Feb 2024", "Paperwork enthusiast.", "-- cc")
    profile("anushka_wh", "Warehouse", "17 Feb 2024", "Sorting things.", "-- aw")

    # ---- locations
    rows = "".join(f"<tr><td><b>{c}</b></td><td>{n}</td><td>{lat:.4f}&deg; N</td><td>{lon:.4f}&deg; E</td></tr>"
                   for c, n, lat, lon in HUBS)
    body = ('<div class="card"><h2>Company locations</h2>'
            '<p>Hub codes are used on badges, shipping manifests and the staff directory. '
            'Coordinates are the main gate of each site (WGS84, decimal degrees).</p>'
            f'<table><tr><th>Hub code</th><th>Site</th><th>Latitude</th><th>Longitude</th></tr>{rows}</table></div>')
    (site / "company" / "locations.html").write_text(page("Locations", body, depth=1), encoding="utf-8")

    # ---- directory
    rows = "".join(f"<tr><td>{n}</td><td>{sid}</td><td>{dept}</td><td>{hub}</td><td>{ext}</td></tr>"
                   for n, sid, dept, hub, ext in STAFF)
    body = ('<div class="card"><h2>Staff directory</h2>'
            '<table><tr><th>Name</th><th>Staff ID</th><th>Department</th><th>Hub</th><th>Ext.</th></tr>'
            f'{rows}</table></div>')
    (site / "company" / "directory.html").write_text(page("Staff Directory", body, depth=1), encoding="utf-8")


def package(site: Path, zip_path: Path):
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(site.rglob("*")):
            if p.is_file():
                z.write(p, Path("meridian_forum") / p.relative_to(site))


def main():
    ap = argparse.ArgumentParser(description="Build Stage 1 (OSINT) offline site + player zip")
    ap.add_argument("--print-flag", action="store_true", help="print the flag (for challenges.yml)")
    a = ap.parse_args()
    DIST.mkdir(exist_ok=True)
    site = DIST / "site"
    build_site(site)
    package(site, DIST / "stage1_osint_player.zip")
    print(f"[+] site  -> {site}")
    print(f"[+] zip   -> {DIST / 'stage1_osint_player.zip'}")
    if a.print_flag:
        print(f"[+] flag  -> {FLAG}")


if __name__ == "__main__":
    main()
