---
title: Kandji — macOS
description: MDM via Kandji. Library Items + Custom Apps.
---

# Quilr Endpoint Agent — Kandji Deployment Guide

**Subtitle:** Mass deployment of the Quilr Endpoint Agent CA trust chain, configuration profiles, and installer package via Kandji on macOS.

**Version:** 2026.05.11

---

## 1. Overview

This guide walks a Kandji administrator through deploying the **Quilr Endpoint Agent** install bundle to a fleet of macOS devices. The bundle ships the Quilr CA trust chain, two `.mobileconfig` profiles (Full Disk Access PPPC and Network Extension approval), and the installer package.

**The deployment order is strict and intentional: CA certificates first, then both configuration profiles, then the installer package.** Following this order means the agent finds a populated trust store and pre-approved system permissions on its very first launch — no failed TLS handshake, no end-user prompt, no blocked network extension dialog.

**Kandji terminology used in this guide** *(map to your Jamf experience if applicable)*:

| Kandji concept | What it is | Jamf analogue |
|---|---|---|
| **Library** | The catalogue of everything that can be assigned to devices | Configuration Profiles + Policies + Packages |
| **Library Item** | A single deployable artefact (profile, app, script) | One profile or one policy |
| **Custom Profile** | A Library Item that delivers a `.mobileconfig` | Uploaded Configuration Profile |
| **Custom App** | A Library Item that installs a pkg/dmg with optional Audit & Enforce | Package + Policy |
| **Audit & Enforce** | Periodic script Kandji runs to verify install state and re-install on drift | Smart-group-driven re-install policy |
| **Blueprint** | The set of Library Items assigned to a group of devices | Scope / Smart Group |
| **Assignment Map** | Per-device-group routing inside a Blueprint | Scope tab on each policy/profile |
| **Self Service** | Built-in catalogue users can install on-demand | Self Service |

> **Note on Blueprints vs Assignment Maps.** Classic Blueprints were [deprecated by Kandji on **2025-04-09**](https://support.kandji.io/kb/migrating-from-classic-blueprints-to-assignment-maps); the current model is **Blueprints with Assignment Maps**. Blueprints still exist as the device-grouping unit — Assignment Maps add conditional logic for routing Library Items to devices within a Blueprint. The simple "add to Blueprint" wording in this guide maps to the equivalent Assignment Map node in the modern UI; no special configuration is needed if every device in the Blueprint should receive the same Library Items.

**Benefits:**

- Silent, zero-prompt rollout to thousands of macOS endpoints.
- Quilr root and intermediate CAs trusted system-wide before the agent runs.
- Full Disk Access and Network Extension pre-approved via MDM.
- Audit & Enforce continuously verifies the agent is installed and current.
- Clean rollback path with no residual TCC entries when removed from the Blueprint.

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| Kandji tenant | Administrator (or Library + Blueprint editor) role |
| MDM enrollment | Target Macs enrolled via Automated Device Enrollment (ADE/DEP) or User Enrollment with **User-Approved MDM** (`profiles status -type enrollment`) |
| Liftoff / Blueprint baseline | A Blueprint exists for the target fleet — e.g. *macOS — Production* or *macOS — Quilr Pilot* |
| Signed installer | `quilr-endpoint-agent-installer.pkg` is signed with a Developer ID Installer certificate and notarized |
| Network egress | Endpoints can reach the Quilr distribution host and the Quilr control plane (see *URL Exception List — AI Apps* / *Non-AI Apps* companion guides for required SSL-bypass entries) |
| Bundle download | Latest bundle obtained from Quilr support (Part 1) |
| Profile signing | Upload each `.mobileconfig` as-is — do **not** re-sign before upload (Kandji re-signs on push) |

---

## 3. Part 1 — Download and Stage the Install Bundle

### Step A. Obtain the bundle

The install bundle zip is distributed by **Quilr support**. Contact your Quilr support representative to request the download URL and any associated checksum for the current production build.

1. **Download the bundle** from [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip).
2. Download the zip on the workstation you use to administer Kandji.
3. Verify the checksum provided by Quilr before extracting.
4. Unzip into a clean staging directory.

### Step B. Bundle contents

```
quilr-endpoint-agent-install-bundle/
├── certs/
│   ├── quilr-ea-intermediate-ca.crt
│   └── quilr-root-ca.crt
├── quilr-endpoint-agent-installer.pkg
├── quilr-endpoint-agent-nw-extension.mobileconfig
└── quilr-endpoint-agent_FullDiskAccess.mobileconfig
```

| File | Purpose | Kandji Library Item | Deploy order |
|---|---|---|---|
| `certs/quilr-root-ca.crt` | Quilr root CA — anchor of trust | **Certificate** Library Item (or Custom Profile with Certificate payload) | 1 |
| `certs/quilr-ea-intermediate-ca.crt` | Quilr intermediate CA — chains to the root | **Certificate** Library Item | 1 |
| `quilr-endpoint-agent_FullDiskAccess.mobileconfig` | Pre-grants Full Disk Access + App Management (PPPC) | **Custom Profile** | 2 |
| `quilr-endpoint-agent-nw-extension.mobileconfig` | Pre-approves the Network Extension / content filter | **Custom Profile** | 2 |
| `quilr-endpoint-agent-installer.pkg` | Installs the Quilr Endpoint Agent to `/Applications` | **Custom App** (with Audit & Enforce) | 3 |

> **Order of operations:** Always deploy in this sequence — **(1) Certificate Library Items (Part 2), (2) both Custom Profiles (Part 3), (3) Custom App (Part 4).** When the .pkg lands last, the agent inherits a populated trust store and every required system approval on its very first launch — no failed TLS handshakes, no user prompts, no blocked extensions.

---

## 4. Part 2 — Deploy CA Certificates to the System Trust Store

This is the **first** thing to add to the Blueprint. The Quilr Endpoint Agent validates TLS against Quilr's internal CA, so the trust store must be populated before the agent runs. Push the root and intermediate CAs to the **System keychain** via Kandji so every managed Mac trusts them automatically. **MDM-delivered roots are trusted system-wide without user prompts** — this is the key advantage over a manual `security add-trusted-cert`.

### Step A. Add each certificate as a Library Item

1. **Library → Add Library Item → search "Certificate" → Add**.
2. **Name**: *Quilr Root CA* (one Library Item per cert keeps assignments clean).
3. **Certificate file**: upload `quilr-root-ca.crt`.
4. **Allow export from keychain**: *off* for the root.
5. **Assignment**: add to the *macOS — Quilr Pilot* Blueprint (and any other Blueprints in scope).
6. **Save**.
7. Repeat Steps 1–6 for `quilr-ea-intermediate-ca.crt` — Library Item name *Quilr Intermediate CA*.

> Both certificates **must** land before any other Quilr Library Item is enabled — if the intermediate is missing, the agent's first TLS handshake against the Quilr control plane fails with *unknown authority*.

### Step B. Verify the certs landed and are trusted

```bash
# List managed certs in the System keychain
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr

# Validate the agent intercepts a monitored AI host (Claude)
openssl s_client -connect claude.ai:443 -servername claude.ai </dev/null
```

In the Kandji console, you can also confirm at **Devices → *device* → Library** that both Certificate Library Items show *Status: Installed* (green check).

> Wait until both certs show as installed on a pilot device before enabling Part 3. If the agent runs before the trust store is populated, its first TLS handshake fails, and depending on retry logic the user may see a transient error.

---

## 5. Part 3 — Deploy the Configuration Profiles

Add each `.mobileconfig` from the bundle root as a **Custom Profile** Library Item **after** the certs have landed and **before** the installer Custom App. Upload them as **two separate** Custom Profiles — do not merge their payloads, since each one is signed by Quilr and corresponds to a distinct system control surface.

### Step A. General workflow for every `.mobileconfig`

For each `.mobileconfig`, repeat the following:

1. **Library → Add Library Item → search "Custom Profile" → Add**.
2. **Profile**: drag in the `.mobileconfig` and upload. Kandji parses the payload and shows the embedded entries.
3. **Name**: as listed in the table in Step B.
4. **Run on**: *macOS*.
5. **Assignment**: add to the *macOS — Quilr Pilot* Blueprint.
6. **Save**. Kandji signs and pushes the profile on the next device check-in.

### Step B. Profile-by-profile reference

| Bundle file | Kandji Custom Profile name | Purpose |
|---|---|---|
| `quilr-endpoint-agent_FullDiskAccess.mobileconfig` | *Quilr Endpoint Agent — Full Disk Access (PPPC)* | Pre-grants Full Disk Access and App Management for the agent's binaries |
| `quilr-endpoint-agent-nw-extension.mobileconfig` | *Quilr Endpoint Agent — Network Extension* | Approves the System Extension and activates its content-filter payload |

### Step C. What the PPPC profile grants

The Full Disk Access mobileconfig contains a `com.apple.TCC.configuration-profile-policy` payload pre-authorizing the agent for:

| TCC service | Why the agent needs it |
|---|---|
| `kTCCServiceSystemPolicyAllFiles` (Full Disk Access) | Read the TCC database, read protected directories during file-upload extraction |
| `kTCCServiceAppManagement` | Manage the installed agent binaries on macOS 14+ where App Management is gated |

Both entries are matched against the agent's CodeRequirement (Team ID + bundle ID + designated requirement). If Quilr re-signs with a new Team ID, the profile must be re-issued.

### Step D. Confirm both profiles are scoped on a pilot device

```bash
# Both Quilr profiles should be listed
profiles list | grep -i quilr

# Inspect payload contents
profiles show -type configuration | grep -i quilr -A 4

# FDA entry should appear (allowed=1) within ~1 minute of profile install
sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed, auth_reason from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
```

In the Kandji console: **Devices → *device* → Library → filter for "Quilr"** — both Custom Profiles must show *Installed*.

---

## 6. Part 4 — Upload and Deploy `quilr-endpoint-agent-installer.pkg`

Add the package **last** as a Custom App Library Item with Audit & Enforce enabled. Audit & Enforce makes Kandji periodically verify the agent is installed at the expected version and re-install it if a user (or another tool) removes it — a key advantage over Jamf's policy model.

### Step A. Pre-install — write the tenant config

Before the `.pkg` runs, the agent's postinstall reads `/tmp/quilr-endpoint-agent.json` to enroll into the correct Quilr tenant. In Kandji, paste this into the Custom App's **Pre-install script** field (Step C below documents the same field for environment cleanup — you can combine both scripts).

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`).

```bash
#!/bin/bash
TENANT="<TENANT-ID>"   # obtained from Quilr support (support@quilr.ai)
printf '{"tenant_id":"%s","discover_skip":false}\n' "$TENANT" \
  > /tmp/quilr-endpoint-agent.json
exit 0
```

### Step B. Add the Custom App

1. **Library → Add Library Item → search "Custom App" → Add**.
2. **Name**: *Quilr Endpoint Agent*.
3. **Installer**: upload `quilr-endpoint-agent-installer.pkg`. Kandji uploads it to its hosted CDN.
4. **Restart**: *None required*.
5. **Run on**: *macOS*.

### Step B. Configure Audit & Enforce

Audit & Enforce gives Kandji a way to detect that the agent is healthy and re-install if not. Use the following helpers:

**Audit script** (Kandji runs on each device check-in; exit `0` = installed and healthy, non-zero = re-install)

```bash
#!/bin/bash
APP="/Applications/QuilrAIProxy.app"
PLIST="/Library/LaunchDaemons/ai.quilr.sentinel.plist"
EXPECTED_VERSION="2026.05.08"

# 1. Binary present?
[ -d "$APP" ] || { echo "missing: $APP"; exit 1; }

# 2. LaunchDaemon present?
[ -f "$PLIST" ] || { echo "missing: $PLIST"; exit 1; }

# 3. Version matches?
INSTALLED=$(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null)
[ "$INSTALLED" = "$EXPECTED_VERSION" ] || { echo "version drift: $INSTALLED != $EXPECTED_VERSION"; exit 1; }

# 4. Daemon is loaded?
launchctl print system/ai.quilr.sentinel >/dev/null 2>&1 || { echo "daemon not loaded"; exit 1; }

exit 0
```

**Pre-install script** *(optional)* — clean up any stale state from a prior version:

```bash
#!/bin/bash
sudo launchctl bootout system/ai.quilr.sentinel 2>/dev/null
sudo launchctl bootout system/ai.quilr.quilrai-proxy 2>/dev/null
exit 0
```

**Post-install script** *(optional)* — confirm the daemon is running after install:

```bash
#!/bin/bash
sleep 2
launchctl print system/ai.quilr.sentinel >/dev/null 2>&1 || {
  echo "post-install: daemon not loaded — kickstarting"
  sudo launchctl kickstart -k system/ai.quilr.sentinel
}
exit 0
```

### Step C. Assign and release

1. **Assignment**: add the Custom App to the *macOS — Quilr Pilot* Blueprint.
2. **Save**. Kandji queues the install on the next check-in for every device in the Blueprint.
3. **Library Item → Status** tab shows install progress per device (Installed / Failed / Pending / Re-installing).

> **Sequencing safety:** Custom Profiles install much faster than Custom Apps, so even if you add all five Library Items in the same Save, the certs and PPPC/NetExt profiles almost always land before the pkg downloads. If you want to be strict, hold the Custom App in an *unassigned* state for ~5 minutes after the profiles, then assign it to the Blueprint.

---

## 7. Key Fields and Identifiers

| Field | Value |
|---|---|
| Installer package name | `quilr-endpoint-agent-installer.pkg` |
| PPPC mobileconfig | `quilr-endpoint-agent_FullDiskAccess.mobileconfig` |
| Network Extension mobileconfig | `quilr-endpoint-agent-nw-extension.mobileconfig` |
| Root CA file | `certs/quilr-root-ca.crt` |
| Intermediate CA file | `certs/quilr-ea-intermediate-ca.crt` |
| Bundle download URL | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip) |
| Kandji Blueprint (suggested) | *macOS — Quilr Pilot* (promote to *macOS — Production* after validation) |
| Sample tenant ID | `t-7f2c9a18-b3e4` |
| Sample subscriber ID | `sub-19adf6e1` |

---

## 8. Validation and Testing

**Cert profiles installed (run this first):**

```bash
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr | wc -l   # expect: 2
```

**Both Custom Profiles installed:**

```bash
profiles list | grep -i quilr | wc -l    # expect: 3 (1 cert payload bundle + 2 mobileconfigs OR 2 cert items + 2 profiles)
```

> Note: Kandji delivers each Certificate Library Item as its own profile, and each Custom Profile as another. Total visible profiles in `profiles list` is **4** if you used two separate Certificate Library Items, or **3** if you bundled both certs into one Custom Profile. Both are valid.

**Network Extension active:**

```bash
systemextensionsctl list | grep -i quilr   # expect: [activated enabled]
```

**Full Disk Access granted via MDM (no user prompt):**

```bash
sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
# expect: 1 (allowed)
```

**Agent process running:**

```bash
pgrep -lf "quilrai|quilrai-proxy"   # expect: 2+ PIDs (quilrai + quilrai-proxy)
```

**Live intercept stream (functional test):**

```bash
sudo log stream --predicate 'subsystem == "ai.quilr.endpoint"' --info
# In Safari/Chrome, visit chatgpt.com and send a short prompt; a 'matched' event must appear within ~2s
```

**Audit & Enforce status in Kandji:**

In the console, open *Library → Quilr Endpoint Agent → Status* and confirm every device shows *Installed* (green). Devices that fail audit appear as *Remediation Pending* and Kandji will re-run the install automatically.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `tls: x509: certificate signed by unknown authority` in the agent log | Only one of the two CA Library Items was installed (root or intermediate missing) | Confirm both Certificate Library Items are in the Blueprint and show *Installed* on the device. Re-issue if missing. |
| Network Extension stuck at `[activated waiting for user]` | SystemExtensions payload missing or wrong Team / bundle ID in the mobileconfig | Re-validate the Network Extension Custom Profile (Step 5.B). The bundle ID must match the binary inside `QuilrEndpointAgent.app/Contents/PlugIns/`. |
| FDA prompt is shown to the user on first launch | PPPC profile not installed, or CodeRequirement does not match a re-signed binary | Confirm the FDA Custom Profile is *Installed*; re-sync. If the binary was re-signed by Quilr, request a refreshed PPPC bundle. |
| Browser shows "Cannot verify identity" for a monitored host (e.g. `chatgpt.com`) | Upstream SWG (Netskope / Zscaler / etc.) is decrypting the same host | Add the host to the SWG's SSL-bypass list — see the *URL Exception List — AI Apps* (or *Non-AI Apps*) companion guide. |
| Custom App stuck at "Pending" in Kandji | Device hasn't checked in since the Library Item was added | Open the **Kandji menu-bar app** on the device → *Check In Now*, or wait for the next 15-minute scheduled check-in. |
| Audit & Enforce repeatedly re-installing the agent | Audit script returning non-zero — version drift or daemon not loaded | Inspect Kandji's audit output (per-device run history in the console). Fix the underlying cause (e.g. a user manually killed the daemon). |
| Daemon not running on a device that reports *Installed* | Postinstall script didn't kickstart the LaunchDaemon | Run `sudo launchctl kickstart -k system/ai.quilr.sentinel` manually; add the post-install script in §6.B if not already present. |

For deeper diagnostics, see the *Quilr Endpoint Agent Troubleshooting Guide* and the `logsamples/` folder.

---

## 10. Rollback

Kandji rollback is cleaner than Jamf's because Library Items are removed from the device the moment they leave the Blueprint — no separate uninstall policy required.

1. **Remove the Custom App from the Blueprint first.** Library → *Quilr Endpoint Agent* → Assignment → remove the Blueprint → **Save**. Kandji will not run the postinstall on next check-in, but the existing install remains.
2. *(Optional)* Push a one-shot **Custom Script** Library Item that runs the uninstall — paste the contents of §9 of the *Troubleshooting Guide*'s **Clean Uninstall** block. Assign to the Blueprint, wait for execution, then remove the script.
3. **Unscope both Custom Profiles** (FDA + Network Extension). Kandji removes them on next check-in, which also drops the PPPC entries from `TCC.db` and deactivates the system extension.
4. **Unscope both Certificate Library Items.** Kandji removes the CAs from the System keychain.
5. *Confirm clean state:*
   - `profiles list | grep -i quilr` returns nothing
   - `systemextensionsctl list | grep -i quilr` returns nothing
   - `security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr` returns nothing

---

## 11. Summary

| Step | Action | Where in Kandji |
|---|---|---|
| 1 | Obtain install bundle zip | Request URL from Quilr support |
| 2 | Add both Certificate Library Items (deploy **first**) | Library → Add → *Certificate* (×2) |
| 3 | Add both Custom Profiles — FDA PPPC + Network Extension (deploy **second**) | Library → Add → *Custom Profile* (×2) |
| 4 | Add the installer .pkg as a Custom App with Audit & Enforce (deploy **last**) | Library → Add → *Custom App* |
| 5 | Assign all five Library Items to the *macOS — Quilr Pilot* Blueprint | Each Library Item → Assignment tab |
| 6 | Validate certs → profiles → agent on a target Mac | `profiles list`, `tccutil`, `systemextensionsctl`, `openssl s_client` |
| 7 | Promote the Blueprint to production rings | Devices → reassign target devices to *macOS — Production* |

---

## 12. References — Kandji Documentation

Every step above is grounded in the official Kandji support documentation. The URLs below are the authoritative source — open them whenever the Kandji UI changes or a step in this guide is unclear.

| Section | Kandji documentation |
|---|---|
| §1 Overview — Blueprints + Assignment Maps model | [Migrating from Classic Blueprints to Assignment Maps](https://support.kandji.io/kb/migrating-from-classic-blueprints-to-assignment-maps) · [Modifying a Blueprint](https://support.kandji.io/modifying-a-blueprint) · [Using Assignment Rules](https://support.kandji.io/kb/using-assignment-rules) |
| §1 Library Items overview | [Library Items & Profiles](https://support.kandji.io/kb/library-items-profiles) |
| §2 Prerequisites — Enrollment | [Configuring Device Enrollment](https://support.kandji.io/kb/configuring-device-enrollment) · [Getting Started — Enrolling Devices](https://support.kandji.io/support/solutions/articles/72000559773-getting-started-enrolling-devices) · [Liftoff](https://support.kandji.io/kb/liftoff) |
| §4 Part 2 — Certificate Library Item (root + intermediate) | [Configure the Certificate Library Item](https://support.kandji.io/kb/certificate-library-item) · [Certificate Services](https://support.kandji.io/kb/certificate-services) |
| §5 Part 3 — Custom Profile Library Item (mobileconfig upload) | [Custom Profiles Overview](https://support.kandji.io/kb/custom-profiles-overview) |
| §5C Full Disk Access PPPC | [Create a Privacy Preferences Policy Control (PPPC) Library Item](https://support.kandji.io/kb/create-a-privacy-preferences-policy-control-pppc-library-item) · [Create a Privacy Preferences Policy Control (PPPC) Profile](https://support.kandji.io/kb/create-a-privacy-preferences-policy-control-pppc-profile) |
| §6 Part 4 — Custom App + Audit & Enforce | [Custom Apps Overview](https://support.kandji.io/kb/custom-apps-overview) · [Deploying Custom Apps](https://support.kandji.io/kb/deploying-custom-apps) · [Adding Custom Apps to Your Library](https://support.kandji.io/support/solutions/articles/72000559807-adding-custom-apps-to-your-library) |
| §6B Pre/Post-install + audit scripts | [Custom Scripts Overview](https://support.kandji.io/kb/custom-scripts-overview) |
| §8 Validation — device check-in mechanics | [macOS Check-In](https://support.kandji.io/kb/macos-check-in) |
| §9 Troubleshooting — agent check-in not happening | [Troubleshooting Kandji Agent Check-In](https://support.kandji.io/support/solutions/articles/72000559774-why-isn-t-a-device-checking-in-as-expected-) |
| §10 Rollback — moving devices between Blueprints | [Move a Device to a Different Blueprint](https://support.kandji.io/kb/move-a-device-to-a-different-blueprint) |
| Real-world reference deployments (third-party agents — same pattern as this guide) | [Deploy CrowdStrike as a Custom App](https://support.kandji.io/kb/deploying-crowdstrike-as-a-custom-app) · [Deploy Bitdefender Endpoint Security Tool as a Custom App](https://support.kandji.io/kb/deploying-bitdefender-endpoint-security-tool-as-a-custom-app) |

> **Pattern reuse.** The CrowdStrike and Bitdefender deployment guides above are the closest published parallels to this Quilr Endpoint Agent deployment — both ship a CA chain + PPPC + System Extension + pkg with an audit script. If anything in this guide is ambiguous, those two Kandji-authored guides describe the same operational pattern with a different vendor's payload.

---

*End of document — Quilr AI | Adapt AI Securely*