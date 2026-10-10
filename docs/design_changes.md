# Design Changes — Operation Silent Ledger (Assignment 02)

## 1. Stage 6 Ownership Reassignment

**Original Assignment 01 allocation:** Stage 6 (Linux/System Security) was
assigned to Shaheen M F M alongside Stages 4–5 (Digital Forensics, Cryptography).

**Implementation change:** Stage 6 has been reassigned to Aaqib H M
(Integration, Testing & Stage 6), who originally owned only Integration,
Testing and end-to-end validation.

**Justification:** A full VirtualBox VM build (Stage 6) is disproportionately
heavy compared to a disk-image challenge (Stage 4) and a cryptography
challenge (Stage 5). Reassigning Stage 6 balances the workload across the
group: Shaheen retains two static/offline-analysis stages, while Aaqib
combines VM-based capstone work with the integration role he already held,
since both require deep familiarity with how all stages connect end-to-end.

## 2. systemd `NoNewPrivileges` Override (Stage 6)

**Original design:** No systemd-specific security settings were discussed
in the Assignment 01 proposal.

**Implementation finding:** The default systemd hardening setting
`NoNewPrivileges=yes` (applied automatically to services run under
`stage6-webapp.service`) blocked the intended SUID privilege-escalation
exploit path from working through the Flask foothold.

**Change made:** A systemd override (`NoNewPrivileges=false`) was applied
to `stage6-webapp.service` to allow the designed SUID escalation challenge
to function as intended.

**Justification:** This is a deliberate, documented relaxation of a
security control, not an oversight. It is acceptable only because:
- The VM operates on a fully isolated internal network (`ctf-lab`),
  with no route to the public internet or host system.
- The weakened setting applies only to the intentionally vulnerable
  `stage6-webapp.service`, not to the host OS or any other service.
- See `docs/risk_register.md` for the associated risk assessment.
