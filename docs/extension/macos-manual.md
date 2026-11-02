# Quilr Browser Extension — macOS Manual Install

Install on a single Mac without MDM: two profiles, tenant JSON, then the generic pkg.

> **Sister guide:** [macOS Manual Install](/deployment/macos-manual) for the endpoint agent.

---

## Prerequisites

- Admin (sudo) rights, egress to `discover.quilrai.dev` and `quilr-extensions.quilr.ai` — see [Prerequisites](/prerequisites).
- **Tenant ID** from **Quilr support**. Do **not** set `skip_discovery`.
- Generic pkg `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support.
- Tenant `.mobileconfig` from `https://app.quilr.ai/` → **Settings → Browser Extension → Deployment → MDM** (OS = macOS, MDM = Manual / no MDM).

---

## 1. Download the artefacts

```bash
# Generic pkg — copy from Quilr support into ~/Downloads/
# quilrai-browser-extension-vYYYY.MM.DD.pkg

curl -fsSL -o ~/Downloads/quilr_browser_util_Files_Access.mobileconfig \
  "https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig"
```

Also download the tenant `.mobileconfig` from the Quilr console into `~/Downloads/`.

---

## 2. Install

### Step A. Profiles first

```bash
sudo profiles install -path ~/Downloads/<tenant-specific>.mobileconfig
sudo profiles install -path ~/Downloads/quilr_browser_util_Files_Access.mobileconfig
```

Approve each profile in **System Settings → Privacy & Security → Profiles** before continuing.

### Step B. Tenant JSON, then pkg

Write JSON immediately before `installer`. Do not rely on the Installer GUI pane for MDM-style automation.

```bash
sudo mkdir -p /tmp /Users/Shared
sudo tee /tmp/quilr-be-install.json >/dev/null <<'EOF'
{
  "tenant_id": "<TENANT-ID>",
  "browsers": "chrome,edge,firefox,safari"
}
EOF
sudo cp /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json
sudo chmod 644 /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json

sudo installer -pkg ~/Downloads/quilrai-browser-extension-vYYYY.MM.DD.pkg -target /
```

Use `tenant_id`, not `PLASMO_PUBLIC_TENANTID`. Omit `skip_discovery`. For Firefox/Safari-only on an existing Chrome/Edge machine, set `"browsers": "firefox,safari"`.

---

## 3. Validate

[Validate Installation](/extension/validate-installation): extension enabled, native agent running, green popup, Check 2b, then a `claude.ai` prompt in the console.

Without MDM, the extension will not show "Installed by your organization"; that is expected for a manual install.

---

## 4. Uninstall

```bash
sudo quilr-be-uninstall
profiles list | grep -i quilr
sudo profiles remove -identifier <PayloadIdentifier>
```

If you do not know the identifier, `profiles list -output stdout-xml` prints profile metadata.
