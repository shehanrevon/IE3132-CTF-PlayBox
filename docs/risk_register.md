# Risk Register — Operation Silent Ledger (Assignment 02)

## Stage 6 — Linux Privilege Escalation Capstone

| # | Risk | Category | Likelihood | Impact | Mitigation |
|---|------|----------|------------|--------|------------|
| 1 | `NoNewPrivileges=false` override on `stage6-webapp.service` weakens systemd hardening | Security | Low (isolated network only) | Medium — if network isolation ever fails, this increases exploitability of the host | VM confined to internal network `ctf-lab` with no route to public internet/host; override applies only to this one service, not system-wide |
| 2 | SUID `logchecker` binary grants root via `setuid(0)` + unsanitized input | Security (by design) | N/A — intentional vulnerability | High (intended) | This is the designed challenge objective; access is restricted to the isolated VM, and the binary has no legitimate purpose outside the CTF |
| 3 | Flask foothold runs as dedicated low-privilege user `webappuser`, not `ctfadmin` | Security | Low | N/A (control, not risk) | Confirms exploitation chain requires privilege escalation rather than trivially landing on a privileged account |
| 4 | VM network settings (static IPs) are manually configured and could be lost if VM is re-imported incorrectly | Dependency | Medium | Medium — breaks Kali-to-Ubuntu connectivity | Settings persisted via netplan (survive reboot); documented in README.md setup steps |
| 5 | Resource contention if Stage 6 VM runs concurrently with other heavy VMs on the host | Technical | Medium (multi-team use) | Medium — slow boot, soft-lockup warnings observed during testing | Documented in README; recommend running only Stage6-VM when testing/grading this stage |
| 6 | Flag embedded in a root-only file; accessible only via the intended SUID exploit path, not via `grep`/`strings` on any static artifact | Security (anti-shortcut) | N/A — intentional control | N/A | Satisfies Assignment requirement 7 (no trivial unintended shortcuts) |
| 7 | Clean snapshot (`clean-state`) must be restored before each grading/demo run, or leftover test artifacts may remain | Operational | Medium | Low — cosmetic/confusing during demo | Snapshot restore documented as the official reset step in README.md |

## Open Items for Integration Phase
- Coordinate with Kosgollage on `platform/seed/challenges.yml` structure once created, to add the Stage 6 flag/description/prerequisite block.
- Confirm Stage 5 → Stage 6 unlock trigger (webhook-based VM boot) once Kosgollage's orchestration script is ready; Stage 6 currently only tested in a standalone, manually-started configuration.

