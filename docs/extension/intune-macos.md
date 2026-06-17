# Quilr Browser Extension — Microsoft Intune (macOS)

Deploy the Quilr browser extension to a macOS fleet via Microsoft Intune. The extension is delivered as **one pkg + two `.mobileconfig` profiles**; this guide reuses the same Intune object types you already use for the Quilr Endpoint Agent on macOS — Custom configuration profiles + Unmanaged macOS PKG app.

> **Sister guide:** if you're rolling out the agent itself, see [Microsoft Intune — macOS (pkg)](/deployment/intune-macos). The patterns are identical; this guide focuses on the extension-specific artefacts.

---

## Prerequisites

Same as the Quilr Endpoint Agent rollout — see [Prerequisites](/prerequisites) for the complete checklist (Intune admin, Apple MDM push certificate, ADE / Company-Portal enrollment, signed packages, network egress, …). Browser-extension-specific extras:

- **Tenant ID** from **Quilr support** (`support@quilr.ai`) — used in the macOS pkg URL and pre-baked into the tenant `.mobileconfig`.
- Access to the **Quilr platform** at `https://app.quilr.ai/` (Settings → Browser Extension → Deployment) to fetch the tenant `.mobileconfig`.
- Reachability for `quilr-extensions.quilr.ai` (serves the pkg + the public File-Access mobileconfig).

---

## 1. Download the artefacts

### 1.1 Tenant-specific pkg (direct download)

| Artefact | URL |
|---|---|
| Pkg installer | `https://quilr-extensions.quilr.ai/<TENANT-ID>/browser-util/quilr-installer-mac.pkg` |

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`).

### 1.2 Tenant-specific `.mobileconfig` (from the Quilr console)

1. Sign in to the **Quilr platform** at `https://app.quilr.ai/`.
2. Navigate **Settings → Browser Extension → Deployment → MDM**.
3. Pick **OS = macOS** and **MDM solution = Microsoft Intune**.
4. Download the tenant-specific `.mobileconfig` (it pre-approves the extension and binds it to your tenant).

### 1.3 Shared File-Access mobileconfig (public URL)

| Artefact | URL |
|---|---|
| File-Access mobileconfig | [`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig) |

This mobileconfig pre-grants Full-Disk-Access so the extension can read screenshots / uploaded files without prompting the user. Deploy it on **every** Mac that receives the extension.

---

## 2. Deploy in Intune

Use the same flow as the *Endpoint Agent — macOS* deployment, with these artefacts:

| Object | Intune type | Channel | Source |
|---|---|---|---|
| Tenant-specific `.mobileconfig` | **Custom configuration profile** | **Device** | §1.1 |
| `quilr_browser_util_Files_Access.mobileconfig` | **Custom configuration profile** | **Device** | §1.2 |
| `quilr-installer-mac.pkg` | **macOS app (PKG)** *(unmanaged PKG)* | — | §1.1 |

### Step A. Upload both `.mobileconfig` files

For each profile:

1. **Intune admin center → Devices → Configuration → Create → New Policy**.
2. **Platform**: *macOS*. **Profile type**: *Templates → Custom*.
3. Name them clearly:
   - *Quilr Browser Extension — Tenant Approval*
   - *Quilr Browser Extension — File Access*
4. **Deployment channel**: **Device** *(cannot be changed after save)*.
5. Upload the `.mobileconfig`.
6. **Assignments**: add to your `MAC-Quilr-Extension` Entra ID group (or reuse the agent group). **Review + create**.

### Step B. Add the pkg

1. **Apps → All apps → Add → App type: macOS app (PKG)** *(unmanaged PKG)*.
2. Upload `quilr-installer-mac.pkg`.
3. **Name**: *Quilr Browser Extension*. **Publisher**: *Quilr AI*.
4. **Assignments → Required → MAC-Quilr-Extension**. **Review + create**.

> **Order of operations:** the two **profiles first**, the **pkg last**. Same rationale as the agent — when the pkg's postinstall runs, every permission is already granted, so no user prompt appears.

---

## 3. Validate

On a pilot Mac:

```bash
# Both extension profiles installed
profiles list | grep -i quilr | wc -l    # expect ≥ 2 new entries

# File-Access mobileconfig granted Full-Disk-Access to the extension binary
sudo sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
```

Open the browser's extension page (`chrome://extensions`, `edge://extensions`, Safari → Settings → Extensions) — the Quilr extension must be **present, enabled, "Installed by your organization"**.

Then send a short test prompt on `https://claude.ai/` (or any monitored AI host). Within ~2 seconds the **prompt event should appear in the Quilr console**.

> The browser extension does **not** perform TLS interception — it captures prompts and file uploads at the **DOM level** via the WebExtensions API. The "Issuer = Quilr" cert-chain check from [Validate Installation §4](/reference/validate-installation) applies to the **Endpoint Agent**, not the extension. For the extension, the source of truth is *"did the event reach the console?"*.

---

## 4. Rollback

> Same Intune-macOS caveat as the agent: the **Uninstall** assignment intent is **not available** for macOS PKG apps.

1. Push a macOS **shell script** that runs the extension uninstaller (Quilr support can supply the exact command).
2. Unassign the PKG app from the group.
3. Unassign both Custom configuration profiles.

See [Microsoft Intune — macOS (pkg)](/deployment/intune-macos) §10 for the same rollback pattern.
