---
title: Jamf Pro — macOS
description: MDM via Jamf Pro. Configuration Profiles + Policy.
---

# Quilr Endpoint Agent — Jamf Pro Deployment Guide

**Subtitle:** Mass deployment of the Quilr Endpoint Agent CA trust chain, configuration profiles, and installer package via Jamf Pro on macOS.

**Version:** 2026.05.08

---

## 1. Overview

This guide walks a Jamf Pro administrator through deploying the **Quilr Endpoint Agent** install bundle to a fleet of macOS devices. The bundle includes the Quilr CA trust chain, two `.mobileconfig` profiles (Full Disk Access PPPC and Network Extension approval), and the installer package.

**The deployment order is strict and intentional: CA certificates first, then both configuration profiles, then the installer package.** Following this order means the agent finds a populated trust store and pre-approved system permissions on its very first launch — no failed TLS handshake, no end-user prompt, no blocked network extension dialog.

**Benefits:**

- Silent, zero-prompt rollout to thousands of macOS endpoints
- Quilr root and intermediate CAs trusted system-wide before the agent runs
- Full Disk Access and Network Extension pre-approved via MDM
- Reproducible policy/profile/scope pattern that survives re-enrollment
- Clean rollback path with no residual TCC entries when unscoped

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| Jamf Pro tenant | Administrator privileges and a configured distribution point |
| MDM enrollment | Target Macs enrolled and showing **User-Approved MDM** (`profiles status -type enrollment`) |
| Signed installer | `quilr-endpoint-agent-installer.pkg` is signed with a Developer ID Installer certificate and notarized |
| Network egress | Endpoints can reach the Quilr distribution host and the Quilr control plane |
| Bundle download | Latest bundle obtained from Quilr support (Part 1) |
| Profile signing | Upload each `.mobileconfig` as-is — do **not** re-sign before upload (Jamf signs on push) |

---

## 3. Part 1 — Download and Stage the Install Bundle

### Step A. Obtain the bundle

The install bundle zip is distributed by **Quilr support**. Contact your Quilr support representative to request the download URL and any associated checksum for the current production build.

1. **Download the bundle** from [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip).
2. Download the zip on the workstation you use to administer Jamf Pro.
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

| File | Purpose | Jamf object | Deploy order |
|---|---|---|---|
| `certs/quilr-root-ca.crt` | Quilr root CA — anchor of trust | Configuration Profile (Certificate payload) | 1 |
| `certs/quilr-ea-intermediate-ca.crt` | Quilr intermediate CA — chains to the root | Configuration Profile (Certificate payload) | 1 |
| `quilr-endpoint-agent_FullDiskAccess.mobileconfig` | Pre-grants Full Disk Access and App Management (PPPC) | Configuration Profile | 2 |
| `quilr-endpoint-agent-nw-extension.mobileconfig` | Pre-approves the agent's Network Extension / content filter | Configuration Profile | 2 |
| `quilr-endpoint-agent-installer.pkg` | Installs the Quilr Endpoint Agent to `/Applications` | Package + Policy | 3 |

> **Order of operations:** Always deploy in this sequence — **(1) CA cert profile (Part 2), (2) both configuration profiles (Part 3), (3) install policy (Part 4).** When the .pkg lands last, the agent inherits a populated trust store and every required system approval on its very first launch — no failed TLS handshakes, no user prompts, no blocked extensions.

---

## 4. Part 2 — Deploy CA Certificates to the System Trust Store

This is the **first** thing to scope. The Quilr Endpoint Agent validates TLS against Quilr's internal CA, so the trust store must be populated before the agent runs. Push the root and intermediate CAs to the System keychain via Jamf so every managed Mac trusts them automatically. **MDM-delivered roots are trusted system-wide without user prompts** — this is the key advantage over a manual `security add-trusted-cert`.

### Step A. Upload each certificate as a Configuration Profile

1. **Computers → Configuration Profiles → New**.
2. **General**: name *Quilr CA — Trust Chain*, category *Certificates*, level **Computer Level**, distribution method **Install Automatically**.
3. Add a **Certificate** payload → **Upload** and select `quilr-root-ca.crt`.
4. Set **Allow export from keychain** = *off* for the root.
5. Add a second **Certificate** payload → **Upload** and select `quilr-ea-intermediate-ca.crt`.
6. **Scope**: same group you will scope the configuration profiles and install policy to. **Save**.

### Step B. Verify the certs landed and are trusted

```bash
# List managed certs in the System keychain
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr

# Validate trust on a server using the cert
openssl s_client -connect claude.ai:443 -servername claude.ai </dev/null
```

> Wait until the cert profile shows as installed on a pilot device before scoping Part 3. If the agent runs before the trust store is populated, its first TLS handshake fails, and depending on retry logic the user may see a transient error.

---

## 5. Part 3 — Deploy the Configuration Profiles

Scope each `.mobileconfig` from the bundle root **after** the certs have landed and **before** the installer policy. Upload them as **two separate** Configuration Profiles in Jamf — do not merge their payloads, since each one is signed by Quilr and corresponds to a distinct system control surface.

### Step A. General workflow for every `.mobileconfig`

For each `.mobileconfig`, repeat the following:

1. **Computers → Configuration Profiles → Upload**.
2. Select the `.mobileconfig` and upload. Jamf parses the payload and shows the embedded entries.
3. **General**: name as listed in the table below, category *Endpoint Security*, distribution method **Install Automatically**, level **Computer Level**.
4. **Scope**: same group as the cert profile.
5. **Save**. Jamf signs and pushes the profile on the next MDM check-in.

### Step B. Profile-by-profile reference

| Mobileconfig file | Suggested Jamf name | What it configures |
|---|---|---|
| `quilr-endpoint-agent_FullDiskAccess.mobileconfig` | *Quilr Endpoint Agent — PPPC* | TCC Full Disk Access + App Management (`SystemPolicyAllFiles`, `SystemPolicyAppBundles`) |
| `quilr-endpoint-agent-nw-extension.mobileconfig` | *Quilr Endpoint Agent — Network Extension* | Pre-approves the agent's Network Extension (content filter / DNS proxy / packet filter) by Team ID + bundle ID |

### Step C. What the PPPC profile grants

| TCC service | UI label | Identifier | Auth |
|---|---|---|---|
| `SystemPolicyAllFiles` | Full Disk Access | `/Applications/QuilrAIProxy.app` | Allow |
| `SystemPolicyAppBundles` | App Management | `/Applications/QuilrAIProxy.app` | Allow |

> **Verify CodeRequirement before pushing:** On a reference Mac with the .app installed, run `codesign -dr - /Applications/QuilrAIProxy.app`. The *designated =>* line must match the `CodeRequirement` strings in each `.mobileconfig` byte-for-byte. If signing identifier or Team ID differ, edit the .mobileconfig before uploading — TCC and Network Extension policy silently ignore entries whose requirement does not match the running binary.

### Step D. Confirm both profiles are scoped on a pilot device

```bash
profiles list | grep -i quilr
sudo profiles show -type configuration | grep -E 'AllFiles|AppBundles|NetworkExtension|webcontent-filter|content-filter'
```

You should see the cert profile + both configuration profiles in the list before moving on to Part 4.

---

## 6. Part 4 — Upload and Deploy `quilr-endpoint-agent-installer.pkg`

Only run this step after Parts 2 and 3 are confirmed installed on a pilot device.

### Step A. Pre-install — write the tenant config

Before the `.pkg` runs, the agent's postinstall reads `/tmp/quilr-endpoint-agent.json` to enroll into the correct Quilr tenant. In Jamf Pro, deliver this as a **Script** attached to the install Policy with **Priority = Before**.

1. **Settings → Computer Management → Scripts → New**.
2. **Display name**: *Quilr — Write tenant config (pre-install)*.
3. **Script** tab — paste the snippet below. Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`).

```bash
#!/bin/bash
TENANT="<TENANT-ID>"   # obtained from Quilr support (support@quilr.ai)
printf '{"tenant_id":"%s","discover_skip":false}\n' "$TENANT" \
  > /tmp/quilr-endpoint-agent.json
exit 0
```

4. **Save**. Attach this Script to the install Policy in the next step with **Priority = Before**.

### Step B. Add the package

1. In Jamf Pro: **Settings → Computer Management → Packages → New**.
2. Upload `quilr-endpoint-agent-installer.pkg`.
3. Set **Category** (e.g. *Endpoint Security*) and **Priority** = 10.
4. Set **Fill user template** = off, **Fill existing user homes** = off.
5. Click **Save**. Wait for replication to all distribution points.

### Step B. Build the install policy

1. **Computers → Policies → New**.
2. **General** tab: name *Install Quilr Endpoint Agent*; triggers **Recurring Check-in** and **Enrollment Complete**; execution frequency **Once per computer**.
3. **Packages** tab: add `quilr-endpoint-agent-installer.pkg`, action = **Install**.
4. **Scope** tab: target the same smart/static group used in Parts 2 and 3.
5. **Self Service** (optional): expose for on-demand reinstall.
6. **Save**. New devices receive the package on their next check-in.

> **Note:** When you scope this policy to a brand-new Mac, ensure that the cert and configuration profiles are scoped via *Enrollment Complete* triggers or a smart group that the device joins immediately, so all profiles arrive in the same MDM check-in window — never after the .pkg.

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
| Sample tenant ID | `t-7f2c9a18-b3e4` |
| Sample subscriber ID | `sub-19adf6e1` |

---

## 8. Validation and Testing

**Cert profile is installed (run this first):**

```bash
profiles list | grep -i quilr
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr
```

**Both configuration profiles are installed:**

```bash
profiles list | grep -i quilr | wc -l            # expect: 3 (1 cert chain + 2 mobileconfigs)
sudo profiles show -type configuration | grep -E 'AllFiles|AppBundles|NetworkExtension|content-filter'
```

**System UI shows the agent as managed (after .pkg installs):**

- System Settings → Privacy & Security → **Full Disk Access** → Quilr Endpoint Agent is on, with a managed-by-MDM badge.
- System Settings → Network → **Filters** lists Quilr's filter as *Active*.

**Live TCC log:**

```bash
log show --predicate 'subsystem == "com.apple.TCC"' --last 5m --info | grep -i quilr
```

**Agent reports check-in:** Confirm the device appears in the Quilr console with the expected hostname and recent heartbeat.

---

## 9. Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| Agent logs TLS errors — "unable to get local issuer certificate" | CA profile not yet delivered, or intermediate missing from chain | Confirm both root + intermediate land via `security find-certificate` and re-scope the cert profile |
| Cert installed but not trusted | Cert delivered into wrong keychain or non-root with no trust override | Re-upload via the Certificate payload at **Computer Level** so it lands in the System keychain |
| FDA prompt still appears after PPPC profile | `CodeRequirement` does not match the signed binary | Run `codesign -dr -` on the .app, copy the designated requirement into the .mobileconfig, re-upload |
| Network Extension blocked / "Allow in Privacy & Security" banner | NW Extension profile not delivered, or Team ID/bundle ID mismatch | Confirm `quilr-endpoint-agent-nw-extension.mobileconfig` is installed; ensure Team ID matches `codesign -dv` |
| Network filter installs but stays inactive | NetworkExtension payload identifier does not match agent | Edit the NW Extension `.mobileconfig` to match `codesign -dv` output, re-upload |
| Profile fails to install / disappears silently | Mac is not user-approved MDM | `profiles status -type enrollment` must show "User Approved" — re-enroll if not |
| TCC keeps showing a stale Deny | Cached decision from before the profile | `tccutil reset SystemPolicyAllFiles`; relaunch the agent |
| .pkg installed but agent fails on first run | Installer reached the device before some profile (out-of-order delivery) | Unscope the install policy, confirm cert + both profiles installed via `profiles list`, then re-scope |
| Bundle ID in TCC.db differs from profile | `Info.plist` `CFBundleIdentifier` does not match the PPPC Identifier | Inspect `/Applications/QuilrAIProxy.app/Contents/Info.plist`; align the .mobileconfig |

---

## 10. Rollback

1. Unscope in **reverse order**: install policy (Part 4) first, then **both** configuration profiles (Part 3), then the CA cert profile (Part 2). Devices remove the policy/profiles on next check-in.
2. Optional cleanup policy with a Files and Processes → Execute Command of: `rm -rf /Applications/QuilrAIProxy.app`.
3. On affected Macs, run `tccutil reset SystemPolicyAllFiles` to clear residual TCC entries.
4. Verify cert removal: `security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr` should return nothing once the cert profile is removed.
5. Verify profile removal: `profiles list | grep -i quilr` should return nothing.

---

## 11. Summary

| Step | Action | Location |
|---|---|---|
| 1 | Obtain install bundle zip | Request URL from Quilr support |
| 2 | Upload root + intermediate CAs (deploy first) | Configuration Profiles → Certificate payload |
| 3 | Upload both mobileconfigs — FDA + NW Extension (deploy second) | Configuration Profiles → Upload (2 separate profiles) |
| 4 | Upload installer .pkg (deploy last) | Settings → Packages → New |
| 5 | Build install policy | Policies → New |
| 6 | Scope cert + 2 profiles + install policy to the same pilot group | Scope tab on each |
| 7 | Validate certs → profiles → agent on a target Mac | `profiles list`, `tccutil`, `openssl s_client` |
| 8 | Expand scope to production rings | Smart/static groups |

---

*Quilr AI — Adapt AI Securely*