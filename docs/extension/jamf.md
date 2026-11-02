# Quilr Browser Extension — Jamf Pro (macOS)

Deploy with **two Configuration Profiles + one Policy** (preinstall script, then the generic pkg).

> **Sister guide:** [Jamf Pro — macOS](/deployment/jamf) for the endpoint agent.

---

## Prerequisites

- Jamf admin, enrolled Macs, signed packages, egress to `discover.quilrai.dev` and `quilr-extensions.quilr.ai` — see [Prerequisites](/prerequisites).
- **Tenant ID** from **Quilr support** — written into `/tmp/quilr-be-install.json` before the pkg. Do **not** set `skip_discovery`.
- Generic pkg `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support.
- Tenant `.mobileconfig` from `https://app.quilr.ai/` → **Settings → Browser Extension → Deployment → MDM** (OS = macOS, MDM = Jamf Pro).

---

## 1. Download the artefacts

| Artefact | Source |
|---|---|
| Generic pkg | `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support |
| Tenant `.mobileconfig` | Quilr console (above) |
| File-Access mobileconfig | [`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig) |

---

## 2. Deploy in Jamf Pro

### Step A. Configuration Profiles

For each `.mobileconfig`: **Computers → Configuration Profiles → Upload**. Level **Computer**. Scope your Mac group. Names: *Quilr Browser Extension — Tenant Approval* and *Quilr Browser Extension — File Access*.

### Step B. Package

**Settings → Computer Management → Packages → New**. Upload `quilrai-browser-extension-vYYYY.MM.DD.pkg`.

### Step C. Preinstall script

Script that runs **before** the package. Use `tenant_id`. Do not set `skip_discovery`.

```bash
#!/bin/bash
set -euo pipefail
mkdir -p /tmp /Users/Shared
cat > /tmp/quilr-be-install.json <<'EOF'
{
  "tenant_id": "<TENANT-ID>",
  "browsers": "chrome,edge,firefox,safari"
}
EOF
cp /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json
chmod 644 /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json
```

### Step D. Policy

1. **Computers → Policies → New**. Trigger *Recurring check-in*, frequency *Once per computer*.
2. **Packages** → the pkg from Step B.
3. **Scripts** → Step C script, **before** the package.
4. **Scope** → same group as the profiles.

Profiles first, pkg last.

---

## 3. Validate

[Validate Installation](/extension/validate-installation): extension enabled, native agent running, green popup, Check 2b, then a `claude.ai` prompt in the console.
