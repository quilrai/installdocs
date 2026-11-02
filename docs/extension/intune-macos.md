# Quilr Browser Extension — Microsoft Intune (macOS)

Deploy the Quilr browser extension with **one generic pkg + two `.mobileconfig` profiles**.

> **Sister guide:** [Microsoft Intune — macOS (pkg)](/deployment/intune-macos) for the endpoint agent. Patterns match; this page is extension-only.

For offline config and v1/v2→v3 upgrade checklists, see [macOS v3 QA](/extension/qa-macos-v3).

---

## Prerequisites

- Intune admin, enrolled Macs, signed packages, egress to `discover.quilrai.dev` and `quilr-extensions.quilr.ai` — see [Prerequisites](/prerequisites).
- **Tenant ID** from **Quilr support** (`support@quilr.ai`) — written into `/tmp/quilr-be-install.json` in the Pre-install script. Do **not** set `skip_discovery`.
- Quilr console access (`https://app.quilr.ai/`) for the tenant `.mobileconfig`.
- Generic pkg `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support.

---

## 1. Download the artefacts

### 1.1 Generic pkg

Obtain `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support. One pkg serves every tenant; tenant is supplied at install time by the Pre-install script.

### 1.2 Tenant `.mobileconfig` (Quilr console)

1. Sign in at `https://app.quilr.ai/`.
2. **Settings → Browser Extension → Deployment → MDM**.
3. **OS** = *macOS*, **MDM solution** = *Microsoft Intune*.
4. Download the tenant-specific `.mobileconfig`.

### 1.3 File-Access mobileconfig (public)

| Artefact | URL |
|---|---|
| File-Access mobileconfig | [`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig) |

---

## 2. Deploy in Intune

| Object | Intune type | Channel |
|---|---|---|
| Tenant `.mobileconfig` | **Custom configuration profile** | **Device** |
| File-Access `.mobileconfig` | **Custom configuration profile** | **Device** |
| `quilrai-browser-extension-vYYYY.MM.DD.pkg` | **macOS app (PKG)** *(unmanaged PKG)* | — |

### Step A. Upload both `.mobileconfig` files

For each profile:

1. **Devices → Configuration → Create → New Policy**.
2. **Platform**: *macOS*. **Profile type**: *Templates → Custom*.
3. Names: *Quilr Browser Extension — Tenant Approval* and *Quilr Browser Extension — File Access*.
4. **Deployment channel**: **Device**.
5. Upload the `.mobileconfig`. Assign to your Entra ID group. **Review + create**.

### Step B. Add the pkg

1. **Apps → All apps → Add → App type: macOS app (PKG)** *(unmanaged PKG)*.
2. Upload `quilrai-browser-extension-vYYYY.MM.DD.pkg`.
3. **Name**: *Quilr Browser Extension*. **Publisher**: *Quilr AI*.
4. **Pre-install script** (Program tab) — first line must be `#!/bin/bash`. Intune runs as root; do not use `sudo`.
5. Assign **Required** to the same group. **Review + create**.

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

Use `tenant_id`, not `PLASMO_PUBLIC_TENANTID`. Omit `skip_discovery`. If `browsers` is omitted, the pkg installs all four browsers (Discovery must include Firefox and Safari keys). For an existing Chrome/Edge fleet adding only Firefox/Safari, set `"browsers": "firefox,safari"`.

> **Order:** both profiles first, pkg last, so Full Disk Access is already granted when postinstall runs.

---

## 3. Validate

Follow [Validate Installation](/extension/validate-installation): extension enabled, native agent running, green popup, Check 2b (`installer_generation` `3`), then a short `https://claude.ai/` prompt in the Quilr console.

```bash
profiles list | grep -i quilr
pgrep -lf 'quilr-native-messaging-agent'
python3 -m json.tool "/Library/Application Support/QuilrAIBE/installer-stamp.json"
```

---

## 4. Rollback

macOS PKG apps have no Intune **Uninstall** intent.

1. Push a shell script that runs the extension uninstaller (from Quilr support).
2. Unassign the PKG app.
3. Unassign both Custom configuration profiles.
