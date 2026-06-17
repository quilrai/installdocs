# Quilr Browser Extension — Jamf Pro (macOS)

Deploy the Quilr browser extension to a macOS fleet via Jamf Pro. The patterns mirror the agent rollout — Configuration Profiles + Policy with a Package payload.

> **Sister guide:** [Jamf Pro — macOS](/deployment/jamf) for the agent. Same MDM, same scoping, same flow — just the artefacts differ.

---

## Prerequisites

Same as the Quilr Endpoint Agent rollout — see [Prerequisites](/prerequisites) for the complete checklist (Jamf admin, User-Approved MDM enrollment, signed packages, network egress, etc.). Browser-extension-specific extras:

- **Tenant ID** from **Quilr support** (`support@quilr.ai`) — pre-baked into the tenant artefacts you download from the Quilr console.
- Access to the **Quilr platform** at `https://app.quilr.ai/` (Settings → Browser Extension → Deployment).
- Reachability for `quilr-extensions.quilr.ai` (serves the public File-Access mobileconfig).

---

## 1. Download the artefacts

### 1.1 Tenant-specific pkg (direct download)

| Artefact | URL |
|---|---|
| Pkg installer | `https://quilr-extensions.quilr.ai/<TENANT-ID>/browser-util/quilr-installer-mac.pkg` |

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`).

### 1.2 Tenant-specific `.mobileconfig` (Quilr console)

1. Sign in to **`https://app.quilr.ai/`**.
2. **Settings → Browser Extension → Deployment → MDM**.
3. **OS** = *macOS*, **MDM solution** = *Jamf Pro*.
4. Download the tenant-specific `.mobileconfig`.

### 1.3 Shared File-Access mobileconfig (public)

| Artefact | URL |
|---|---|
| File-Access mobileconfig | [`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig) |

---

## 2. Deploy in Jamf Pro

### Step A. Upload both `.mobileconfig` files as Configuration Profiles

For each profile:

1. **Computers → Configuration Profiles → Upload**.
2. Select the `.mobileconfig` — Jamf parses the payload and shows the embedded entries.
3. **General**: name as below, category *Endpoint Security*, distribution method **Install Automatically**, level **Computer Level**.
   - *Quilr Browser Extension — Tenant Approval*
   - *Quilr Browser Extension — File Access*
4. **Scope**: target your `MAC-Quilr-Extension` group (or reuse the agent scope).
5. **Save** — Jamf signs and pushes on next MDM check-in.

### Step B. Add the pkg to Jamf

1. **Settings → Computer Management → Packages → New**.
2. Upload `quilr-installer-mac.pkg` to your distribution point.
3. **Display name**: *Quilr Browser Extension*. **Category**: *Endpoint Security*.

### Step C. Build the install Policy

1. **Computers → Policies → New → Display name**: *Install Quilr Browser Extension*.
2. **General → Trigger**: *Recurring check-in*. **Frequency**: *Once per computer*.
3. **Packages → Add** → select the pkg from §B.
4. **Scope**: same group as the Configuration Profiles.
5. **Save**.

> **Order of operations:** Configuration Profiles install via MDM and almost always land before the policy runs. To be strict, scope the policy ~5 minutes after both profiles report *Installed*.

---

## 3. Validate

```bash
profiles list | grep -i quilr                     # both extension profiles present
sudo sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
```

Open the browser's extensions page — Quilr extension must be **present, enabled, "Installed by your organization"**. Then send a short test prompt on `https://claude.ai/` (or any monitored AI host). Within ~2 seconds the **prompt event should appear in the Quilr console**.

> The browser extension does **not** perform TLS interception — it captures prompts and file uploads at the **DOM level** via the WebExtensions API. The "Issuer = Quilr" cert-chain check from [Validate Installation §4](/reference/validate-installation) applies to the **Endpoint Agent**, not the extension. For the extension, the source of truth is *"did the event reach the console?"*.

---

## 4. Rollback

Same pattern as the agent — unscope the Policy + Configuration Profiles from the target group. Jamf removes the profiles on next check-in and stops re-running the install Policy. See [Jamf Pro — macOS](/deployment/jamf) §10 for the full reverse-order procedure.
