# Quilr Browser Extension — macOS Manual Install

Install the Quilr browser extension on a single Mac without MDM — useful for pilots, technician workstations, and one-off rollouts. Same three artefacts as every macOS guide; install them in Terminal as the admin user.

> **Sister guide:** [macOS Manual Install](/deployment/macos-manual) for the agent. The `installer -pkg` + `profiles install` Terminal patterns are identical.

---

## Prerequisites

Same as the Quilr Endpoint Agent rollout — see [Prerequisites](/prerequisites) for the complete checklist. Browser-extension-specific extras:

- **Tenant ID** from **Quilr support** (`support@quilr.ai`) — written into `/tmp/quilr-be-install.json` immediately before `installer`. Do **not** set `skip_discovery`.
- Access to the **Quilr platform** at `https://app.quilr.ai/` (Settings → Browser Extension → Deployment) to fetch the tenant `.mobileconfig`.
- Egress to `discover.quilrai.dev` and `quilr-extensions.quilr.ai`.
- Admin (sudo) rights on the target Mac.

---

## 1. Download the artefacts

### 1.1 Tenant-specific pkg (direct download)

```bash
TENANT_ID="<TENANT-ID>"   # obtained from Quilr support (support@quilr.ai)

curl -fsSL -o ~/Downloads/quilr-installer-mac.pkg \
  "https://quilr-extensions.quilr.ai/${TENANT_ID}/browser-util/quilr-installer-mac.pkg"
```

### 1.2 Tenant-specific `.mobileconfig` (Quilr console)

Sign in to `https://app.quilr.ai/` → **Settings → Browser Extension → Deployment → MDM** → **OS** = *macOS*, **MDM solution** = *Manual / no MDM* → download the tenant-specific `.mobileconfig` into `~/Downloads/`.

### 1.3 Shared File-Access mobileconfig (public)

```bash
curl -fsSL -o ~/Downloads/quilr_browser_util_Files_Access.mobileconfig \
  "https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig"
```

---

## 2. Install

### Step A. Install both `.mobileconfig` profiles (first)

```bash
sudo profiles install \
  -path ~/Downloads/<tenant-specific>.mobileconfig

sudo profiles install \
  -path ~/Downloads/quilr_browser_util_Files_Access.mobileconfig
```

You will be prompted to **approve** each profile in **System Settings → Privacy & Security → Profiles** (or *General → Device Management* on macOS 12 and earlier). Approve both before continuing.

### Step B. Write tenant JSON, then install the pkg

CLI/MDM must not rely on the installer GUI pane. Write tenant JSON to `/tmp` and `/Users/Shared` immediately before `installer`. Double-click still uses the installer pane.

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

sudo installer -pkg ~/Downloads/quilr-installer-mac.pkg -target /
```

Use `tenant_id` (not `PLASMO_PUBLIC_TENANTID`). Do not set `skip_discovery`. For Firefox/Safari-only on an existing Chrome/Edge machine, set `"browsers": "firefox,safari"`.

> **Why this order:** with the two profiles already approved, the pkg's postinstall finds Full Disk Access pre-granted, so no user prompt appears.

---

## 3. Validate

```bash
# Both extension profiles installed
profiles list | grep -i quilr | wc -l

# Full Disk Access granted to the extension binary
sudo sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
```

Open the browser's extensions page (`chrome://extensions`, `edge://extensions`, Safari → Settings → Extensions) — Quilr extension must be **present and enabled**. *Note: without an MDM, the extension won't show "Installed by your organization"; that's expected for a manual install.*

Then send a short test prompt on `https://claude.ai/` — within ~2 seconds the **event should appear in the Quilr console**.

> The browser extension does **not** perform TLS interception — it captures prompts and file uploads at the **DOM level** via the WebExtensions API. The "Issuer = Quilr" cert-chain check from [Validate Installation §4](/reference/validate-installation) applies to the **Endpoint Agent**, not the extension.

---

## 4. Uninstall

```bash
# Remove the extension pkg (Quilr support can supply the canonical uninstaller path)
sudo /Library/Application\ Support/QuilrAI/uninstall-browser-extension.sh

# Remove both mobileconfig profiles (look up the PayloadIdentifier first)
profiles list | grep -i quilr
sudo profiles remove -identifier <PayloadIdentifier>
```

If you don't know the `PayloadIdentifier`, `profiles list -output stdout-xml` prints all profile metadata.
