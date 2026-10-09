# Stage 6 — Linux Privilege Escalation Capstone

## Overview
Final capstone stage of Operation Silent Ledger. Players gain an initial
low-privilege foothold through a vulnerable web service, then escalate to
root via a misconfigured SUID binary to retrieve the final evidence flag.

## Architecture
- **Target VM:** `Stage6-VM` (Ubuntu Server 22.04.5 LTS)
- **Network:** Isolated internal network `ctf-lab` (192.168.56.0/24)
  - Ubuntu: `192.168.56.10`
  - Attacker (Kali): `192.168.56.20`
- **Foothold service:** Flask app (`webapp/app.py`), port 8080, runs as
  systemd service `stage6-webapp.service` under the restricted user
  `webappuser`
- **Privilege escalation target:** SUID binary `privesc/logchecker`
  (owned by root, mode 4755)
- **Protected evidence:** `/var/log/app/evidence.log` (root-only, 600)

## Vulnerabilities
1. **Command injection (foothold):** The `/convert` endpoint saves an
   uploaded file using its unsanitized filename, which is then passed
   directly into a shell command via `subprocess.run(..., shell=True)`.
2. **SUID privilege escalation:** `logchecker.c` calls `setuid(0)` before
   invoking `system()` with unsanitized user input, allowing arbitrary
   root command execution.

## Setup (from clean VM)
1. Import/start `Stage6-VM` in VirtualBox.
2. Confirm network adapters: Adapter 1 = NAT, Adapter 2 = Internal Network
   `ctf-lab`.
3. Confirm static IP `192.168.56.10/24` on `enp0s8` (persists via netplan).
4. Confirm Flask service is running:
```bash
   systemctl status stage6-webapp.service
```

## Solving the Stage
Run the automated solver from an attacker machine on the `ctf-lab` network:
```bash
python3 exploit_full_chain.py
```
This performs:
- **Phase 1:** Exploits the file-upload command injection to confirm
  foothold access as `webappuser`.
- **Phase 2:** Uses the same injection channel to invoke the SUID
  `logchecker` binary and retrieve the evidence log, which contains the
  final flag.

**Flag format:** `CASE{blacktide_motive_confirmed}`

## Reset / Recovery
Restore the VM to its pre-exploit clean state:
```powershell
VBoxManage snapshot "Stage6-VM" restore "clean-state"
```

## Known Design Notes
- `NoNewPrivileges=false` is intentionally set in the systemd service
  override to allow the designed SUID escalation path. This is safe only
  because the VM is network-isolated (see `docs/risk_register.md`).
