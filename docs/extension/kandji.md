# Quilr Browser Extension — Kandji (macOS)

Deploy the Quilr browser extension to a macOS fleet via Kandji. Same Library-Item pattern as the agent — **two Custom Profiles + one Custom App**, all assigned to your Blueprint.

> **Sister guide:** [Kandji — macOS](/deployment/kandji) for the agent. Custom Profile + Custom App + Audit-&-Enforce flows are identical; only the artefacts differ.

---

## Prerequisites

Same as the Quilr Endpoint Agent rollout — see [Prerequisites](/prerequisites) for the complete checklist (Kandji tenant, User-Approved MDM, signed packages, network egress, …). Browser-extension-specific extras:

- **Tenant ID** from **Quilr support** (`support@quilr.ai`) — pre-baked into the tenant artefacts you download from the Quilr console.
- Access to the **Quilr platform** at `https://app.quilr.ai/` (Settings → Browser Extension → Deployment).
- Reachability for `quilr-extensions.quilr.ai` (serves the public File-Access mobileconfig).

> **Note on Blueprints vs Assignment Maps.** Classic Blueprints were [deprecated by Kandji on **2025-04-09**](https://support.kandji.io/kb/migrating-from-classic-blueprints-to-assignment-maps); the current model is *Blueprints with Assignment Maps*. The simple "add to Blueprint" wording in this guide maps to the equivalent Assignment Map node in the modern UI.

---

## 1. Download the artefacts

### 1.1 Tenant-specific pkg (direct download)

| Artefact | URL |
|---|---|
| Pkg installer | `https://quilr-extensions.quilr.ai/<TENANT-ID>/browser-util/quilr-installer-mac.pkg` |

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`).

### 1.2 Tenant-specific `.mobileconfig` (Quilr console)

**`https://app.quilr.ai/`** → **Settings → Browser Extension → Deployment → MDM** → **OS** = *macOS*, **MDM solution** = *Kandji* → download the tenant `.mobileconfig`.

### 1.3 Shared File-Access mobileconfig (public)

[`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig)

---

## 2. Deploy in Kandji

### Step A. Add both `.mobileconfig` files as Custom Profiles

For each profile:

1. **Library → Add Library Item → search "Custom Profile" → Add**.
2. Upload the `.mobileconfig`.
3. **Name** as below; **Run on**: *macOS*; **Assignment**: target Blueprint.
   - *Quilr Browser Extension — Tenant Approval*
   - *Quilr Browser Extension — File Access*
4. **Save**.

### Step B. Add the pkg as a Custom App with Audit & Enforce

1. **Library → Add Library Item → search "Custom App" → Add**.
2. **Name**: *Quilr Browser Extension*. Upload `quilr-installer-mac.pkg`.
3. **Run on**: *macOS*.
4. *(Recommended)* Configure **Audit & Enforce** — a small audit script that checks the extension bundle is on disk and the policy registry entries are present, exits `0` when healthy, non-zero when Kandji should reinstall. Ask Quilr support for the canonical audit snippet.
5. **Assignment**: target Blueprint. **Save**.

> **Order of operations:** Custom Profiles install faster than Custom Apps, so even when all three Library Items save together the profiles almost always land before the pkg downloads. To be strict, hold the Custom App unassigned for ~5 minutes after the two profiles report *Installed*.

---

## 3. Validate

```bash
profiles list | grep -i quilr            # both extension profiles present
sudo sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
```

In Kandji: **Library → Quilr Browser Extension → Status** should show *Installed* (green) on the target devices. Audit & Enforce will re-install automatically on drift.

Open the browser's extensions page → Quilr extension present + enabled + *Installed by your organization*. Then send a short test prompt on `https://claude.ai/` — within ~2 seconds the **event should appear in the Quilr console**.

> The browser extension does **not** perform TLS interception — it captures prompts and file uploads at the **DOM level** via the WebExtensions API. The "Issuer = Quilr" cert-chain check from [Validate Installation §4](/reference/validate-installation) applies to the **Endpoint Agent**, not the extension.

---

## 4. Rollback

Remove the Custom App + both Custom Profiles from the Blueprint. Kandji removes the profiles on next check-in. The Custom App stays on disk until you push a one-shot **Custom Script** Library Item that runs the uninstaller (Quilr support supplies the exact command), then remove the script. See [Kandji — macOS](/deployment/kandji) §10 for the full pattern.
