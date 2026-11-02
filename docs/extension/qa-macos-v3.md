---
title: macOS v3 installer QA
sidebar_label: macOS v3 QA
description: Offline config matrix, Intune v1/v2 upgrade, and validation for the generic browser-extension pkg.
---

# macOS v3 installer QA

The v3 macOS pkg is **tenant-agnostic**: `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support. Tenant comes from `/tmp/quilr-be-install.json` (and `/Users/Shared` dual write) at install time. Discovery fills the rest when `skip_discovery` is omitted.

This page is the operator checklist for offline validation and Intune upgrade. Day-to-day install steps live in the MDM guides. Pass/fail for a healthy endpoint is always [Validate Installation](/extension/validate-installation) checks 1–3 plus Check 2b.

The endpoint-agent installer’s Tenant ID / Certificate / Permissions / Summary panes do **not** apply to this pkg. Permissions are the two `.mobileconfig` profiles. There is no Quilr CA or system-extension step.

Architecture diagrams for what v2 kept and what v3 changed live in Project-Vanguard at `docs/architecture/v3-installer-phase2.md`.

---

## 1. Offline config (one variable at a time)

Run the fixture script first (no pkg):

```bash
cd /path/to/BE-PKG-Builder
bash scripts/test-offline-runtime-config.sh
```

That script exercises every required and optional key: missing / `http://` fail, optional omit succeeds, `chrome,edge` without Firefox/Safari keys succeeds, and a good resolve leaves `installer_generation` `3`.

Then, on a Mac that can reach `quilr-extensions.quilr.ai`, do **one** full offline pkg install with the complete JSON from the [BE-PKG-Builder README](https://github.com/quilrbusiness/BE-PKG-Builder) (`skip_discovery` `"1"`, all six `PLASMO_PUBLIC_*`, `BASE_URL`, browser-specific URLs). Watch `/var/log/quilr/quilr.log`. A bad JSON must fail in preinstall before policies are written. A good install leaves:

```bash
python3 -m json.tool "/Library/Application Support/QuilrAIBE/installer-stamp.json"
# installer_generation: "3", pkg_version: YYYY.MM.DD
```

Do not set `skip_discovery` for production MDM or Discovery-backed pilots.

---

## 2. Intune backward compatibility (v1→v3 and v2→v3)

Use **one enrolled Mac per story**. Profiles first, pkg last — same order as [Microsoft Intune — macOS](/extension/intune-macos). Upload the **generic** v3 pkg, not the legacy `…/<TENANT-ID>/browser-util/quilr-installer-mac.pkg`.

### Pre-install script (both stories)

```bash
#!/bin/bash
set -euo pipefail
mkdir -p /tmp /Users/Shared
cat > /tmp/quilr-be-install.json <<'EOF'
{
  "tenant_id": "<EXISTING-TENANT-ID>",
  "browsers": "chrome,edge,firefox,safari"
}
EOF
cp /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json
chmod 644 /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json
```

Omit `skip_discovery`. First line must be `#!/bin/bash`.

### Story A — existing customer, v1 then v3

1. Start from a Mac that only has Chrome and Edge from the old tenant pkg.
2. Assign both Custom configuration profiles (tenant approval + File Access).
3. Assign a **macOS app (PKG)** with the v3 pkg and the pre-install script above.
4. After Company Portal sync, confirm:
   - Same tenant in `be-config.json`
   - Chrome/Edge still force-install from `https://quilr-extensions.quilr.ai/<tenant>/manifest.xml`
   - Firefox and Safari present when Discovery has those keys
   - One `quilr-native-messaging-agent` process
   - `installer_generation` `3` (Check 2b)

### Story B — existing customer, v2 then v3

1. Start from a Mac that already has Chrome, Edge, Firefox, and Safari from the v2 pkg.
2. Same Intune assignment as Story A.
3. After sync, confirm:
   - Tenant unchanged
   - One native agent and one Safari utility (no duplicate leftovers)
   - Firefox/Safari resolve through Discovery nested URLs when configured
   - `installer_generation` `3`

### Pass on both stories

- Extension enabled in the browser
- `pgrep -lf quilr-native-messaging-agent`
- Green popup with Extension and Agent versions
- Short prompt on `https://claude.ai/` appears in the Quilr console

Jamf and Kandji use the same pkg and the same JSON; do not repeat this matrix on every MDM.

---

## 3. New customer, v3 only

Clean Mac, no prior Quilr pkg. Manual or Intune with the same pre-install JSON (`tenant_id`, `browsers`, no `skip_discovery`). Confirm Discovery is used, selected browsers install, and a missing Discovery key fails the install before policies are written.
