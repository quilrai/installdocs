---
title: Microsoft Intune — macOS (pkg)
description: MDM via Microsoft Intune. CA trust + Configuration Profiles + pkg.
---

# Quilr Endpoint Agent — Microsoft Intune Deployment Guide (macOS / pkg)

**Subtitle:** Mass deployment of the Quilr Endpoint Agent CA trust chain, configuration profiles, and pkg installer via Microsoft Intune on macOS.

**Version:** 2026.05.11

---

## 1. Overview

This guide walks an Intune administrator through deploying the **Quilr Endpoint Agent for macOS** to a fleet of Apple devices using Microsoft Intune. The bundle ships the Quilr CA trust chain, two `.mobileconfig` profiles (Full Disk Access PPPC and Network Extension approval), and the installer package — identical payloads to the Jamf and Kandji rollouts, delivered through Intune objects.

**The deployment order is strict and intentional: CA certificates first, then both configuration profiles, then the installer package.** Following this order means the agent finds a populated trust store and pre-approved system permissions on its very first launch — no failed TLS handshake, no end-user prompt, no blocked network extension dialog.

**Intune terminology used in this guide** *(map to your Jamf/Kandji experience if applicable)*:

| Intune concept | What it is | Jamf / Kandji analogue |
|---|---|---|
| **Trusted Certificate profile** | Device config profile that delivers one root **or** intermediate CA | Certificate Configuration Profile / Certificate Library Item |
| **Custom configuration profile** | Device config profile that uploads a raw `.mobileconfig` / `.xml` | Uploaded Configuration Profile / Custom Profile |
| **Unmanaged macOS PKG app** | App object that deploys a `.pkg` to macOS | Package + Policy / Custom App |
| **Deployment channel** | Device vs User channel for a custom profile | n/a (Jamf level = Computer) |
| **Group assignment** | Targeting a Microsoft Entra ID device / user group | Scope / Blueprint |

**Benefits:**

- Silent, zero-prompt rollout to thousands of macOS endpoints.
- Quilr root and intermediate CAs trusted system-wide before the agent runs.
- Full Disk Access and Network Extension pre-approved via MDM.
- One MDM (Intune) for both Windows and macOS fleets.
- Clean rollback when profiles are unassigned (note the PKG-uninstall caveat in §10).

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| Intune tenant | Microsoft Intune Administrator (or App + Device Configuration write) |
| Apple MDM push certificate | Configured in Intune (**Devices → Enrollment → Apple → Apple MDM push certificate**) |
| MDM enrollment | Target Macs enrolled via Automated Device Enrollment (ADE) or Company Portal, showing **User-Approved MDM** (`profiles status -type enrollment`) |
| Entra ID group | A device or user group for the rollout — e.g. `MAC-Quilr-Pilot` |
| Signed installer | `quilr-endpoint-agent-installer.pkg` signed with a *Developer ID Installer* certificate and notarized; contains a payload + `CFBundleVersion` (required for Intune managed PKG) |
| Network egress | Endpoints can reach the Quilr backplane hosts on TCP 443 — see §3 for the full allowlist (and *URL Exception List — AI Apps* / *Non-AI Apps* for SWG SSL-bypass) |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip) (see Part 1 for staging steps) |
| Profile size | Each `.mobileconfig` must be **< ~1 MB** (Intune custom profile limit) and uploaded as-is — do not re-sign |

---

## 3. Firewall and Network Allowlist

The Quilr Endpoint Agent makes outbound **HTTPS (TCP 443)** to a small set of Quilr backplane hosts. Where the perimeter is enforced — corporate firewall, egress proxy, or TLS-intercepting Secure Web Gateway (Zscaler, Netskope, Symantec, Forcepoint, etc.) — these hosts must be allowed **before** the PKG is deployed in Part 4.

> **Pick the row that matches your tenant.** The host set depends on which Quilr environment your bundle was built against (`bff`, `dlpPrefix`, `updateUrlPrefix`). Confirm with Quilr support if you are unsure which environment applies.

### Step A. Quilr control-plane hosts

**Shared across all environments** — allowlist these regardless of tenant:

| Host | Purpose |
|---|---|
| `discover.quilrai.dev` | Tenant / endpoint discovery |
| `log.quilrai.dev` | Diagnostic log shipping (enabled when diagnostics are turned on) |
| `quilr-extensions.quilr.ai` | Browser-extension / agent update distribution (default CDN) |

**Per-environment** — pick the row that matches your tenant:

| Environment | Base URL | DLP Host |
|---|---|---|
| **Quartz** | `https://quartz.quilr.ai` | `https://dlpone.quilr.ai` |
| **Secure** | `https://secure.quilr.ai` | `https://dlpone.quilr.ai` |
| **US POC** | `https://app.quilr.ai` | `https://dlpone.quilr.ai` |
| **IND POC** | `https://platform.quilr.ai` | `https://dlp-platform.quilr.ai` |
| **US Prod** | `https://app.quilrai.com` | `https://dlpone.quilrai.com` |
| **IND Prod** | `https://platform.quilrai.com` | `https://dlp-platform.quilrai.com` |
| **JP POC** | `https://app-jp.quilr.ai` | `https://dlpone-jp-1.quilr.ai` |
| **UAE POC** | `https://trust.quilr.ai` | `https://dlp-platform.quilr.ai` |
> **Dedicated PaaS / on-prem deployments?** If your tenant runs on a customer-owned domain (your own DNS / on-prem control plane), the shared hosts above still apply — Quilr support provides the tailored Base URL + DLP allowlist for your specific deployment. Contact `support@quilr.ai`.

### Step B. Additional update / artifact CDN (env-specific)

Most environments use the default `quilr-extensions.quilr.ai` (already in Step A). A few environments use an additional CDN — allowlist the matching row **in addition to** Step A:

| Host | Used by environments |
|---|---|
| `quilr-extensions.quilrai.com` | `quilr-saas-ind-prod`, `quilr-saas-usa-prod` |
| `quilr-hub.quilr.ai` | `quilr-poc2` |

If your environment is not listed above, Step A alone covers update distribution.

### Step C. TLS-intercepting proxies — SSL-bypass

If your egress sits behind Zscaler / Netskope / Symantec WSS / Forcepoint / iboss / etc., add **every** host from Steps A and B to the **SSL-bypass** (no TLS inspection) list. The agent pins TLS to Quilr's internal CA chain (deployed in Part 2) — re-signing through the SWG's CA breaks the handshake and the agent will fail to connect.

For the *upstream* SWG rules covering monitored **AI** hosts (ChatGPT, Claude, Gemini, etc.), see the companion *URL Exception List — AI Apps* and *URL Exception List — Non-AI Apps* guides — those are about apps the agent **inspects**, not the Quilr backplane itself.

### Step D. Validate egress from a pilot Mac

From Terminal on a pilot Mac, verify reachability **before** installing the PKG:

```bash
# Replace the first two hosts with the row from Step A that matches your tenant.
targets=(
  app.quilr.ai              # Base URL
  dlpone.quilr.ai           # DLP
  discover.quilrai.dev      # Discover (shared)
  log.quilrai.dev           # Diagnostic log (shared)
  quilr-extensions.quilr.ai # Update / extension CDN (shared)
)
for h in "${targets[@]}"; do
  out=$(nc -zv -G 5 "$h" 443 2>&1)
  if [[ "$out" == *succeeded* ]] || [[ "$out" == *open* ]]; then status=OK; else status=BLOCKED; fi
  printf "%-40s  TCP/443  %s\n" "$h" "$status"
done
```

Any `BLOCKED` host means the firewall / SWG / corporate proxy still needs adjustment. Re-run the test after the network team applies the allowlist.

### Note on macOS Application Firewall (mobileconfig + pkg)

The macOS Application Firewall controls **inbound** connections only — outbound TCP 443 is unrestricted on a default install, so per-host outbound rules are normally unnecessary at the endpoint.

**Configuration Profile (`.mobileconfig`)** — pushed by Intune as a Custom configuration profile (see Part 3 for the upload flow). Pick the payload that matches what your perimeter requires:

| Payload type | Purpose |
|---|---|
| `com.apple.security.firewall` | Leave the macOS Application Firewall at default (inbound-only). No outbound config needed. |
| `com.apple.proxy.https.global` / `com.apple.proxy.http.global` | Explicit HTTPS/HTTP proxy with `ExceptionsList` containing every Step A and Step B host so they bypass the upstream SWG. |

**Agent `.pkg` postinstall** — for fleets that enforce PF-based egress on the endpoint. The Quilr macOS agent ships as a signed `.pkg`. Its postinstall script can drop a PF anchor at `/etc/pf.anchors/quilr-allowlist`:

```bash
#!/bin/bash
# Postinstall: register PF allowlist for Quilr backplane (Steps A + B)
ANCHOR=/etc/pf.anchors/quilr-allowlist
cat > "$ANCHOR" <<'EOF'
# Shared (Step A)
pass out proto tcp to discover.quilrai.dev port 443
pass out proto tcp to log.quilrai.dev port 443
pass out proto tcp to quilr-extensions.quilr.ai port 443
# Per-tenant (Step A) — fill in your env's Base URL + DLP
# pass out proto tcp to app.quilr.ai port 443
# pass out proto tcp to dlpone.quilr.ai port 443
EOF

# Hook the anchor into the main pf.conf if not already present
grep -q 'quilr-allowlist' /etc/pf.conf || \
  printf '\nanchor "quilr-allowlist"\nload anchor "quilr-allowlist" from "%s"\n' "$ANCHOR" >> /etc/pf.conf

pfctl -f /etc/pf.conf
pfctl -e 2>/dev/null || true
```

Persist PF across reboots: macOS loads `/etc/pf.conf` at boot once it references the anchor. The Quilr agent's existing `/Library/LaunchDaemons/com.sentinel.agent.plist` covers the agent itself.

The standard path on macOS is to allowlist Quilr backplane FQDNs at the **egress proxy / SWG / corporate firewall**, not via endpoint PF rules — use the `.pkg` postinstall path only when fleet policy requires endpoint-side enforcement.

> **Windows counterpart:** for the Windows side of an Intune rollout, see the firewall section in the companion *Quilr Endpoint Agent — Intune Windows / MSI* guide. Step A and Step B host lists are the same on both platforms.

---

## 4. Part 1 — Download and Stage the Install Bundle

### Step A. Obtain the bundle

The install bundle zip is distributed by **Quilr support**. Contact your Quilr support representative to request the download URL and any associated checksum for the current production build (architecture path: `mac/silicon`).

1. **Download the bundle** from [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip).
2. Download the zip on the workstation you use to administer Intune.
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

| File | Purpose | Intune object | Deploy order |
|---|---|---|---|
| `certs/quilr-root-ca.crt` | Quilr root CA — anchor of trust | **Trusted Certificate profile** | 1 |
| `certs/quilr-ea-intermediate-ca.crt` | Quilr intermediate CA — chains to the root | **Trusted Certificate profile** | 1 |
| `quilr-endpoint-agent_FullDiskAccess.mobileconfig` | Pre-grants Full Disk Access + App Management (PPPC) | **Custom configuration profile** | 2 |
| `quilr-endpoint-agent-nw-extension.mobileconfig` | Pre-approves the Network Extension / content filter | **Custom configuration profile** | 2 |
| `quilr-endpoint-agent-installer.pkg` | Installs the Quilr Endpoint Agent to `/Applications` | **Unmanaged macOS PKG app** | 3 |

> **Order of operations:** Always deploy in this sequence — **(1) Trusted Certificate profiles (Part 2), (2) both Custom configuration profiles (Part 3), (3) the PKG app (Part 4).** When the .pkg lands last, the agent inherits a populated trust store and every required system approval on its first launch — no failed TLS handshakes, no user prompts, no blocked extensions.

---

## 5. Part 2 — Deploy CA Certificates to the System Trust Store

The Quilr Endpoint Agent validates TLS against Quilr's internal CA, so the System keychain must trust the chain before the agent runs. A Trusted Certificate profile delivers **one** certificate each, so create **two** profiles.

> **Microsoft constraint:** an Intune Trusted Certificate profile can deliver **only** a root or an intermediate certificate — exactly what we need. Provide each `.crt`/`.cer` as a separate profile.

### Step A. Create the Root CA profile

1. **Intune admin center → Devices → Manage devices → Configuration → Create → New Policy**.
2. **Platform**: *macOS*. **Profile type**: *Templates → Trusted certificate*.
3. **Name**: *Quilr Root CA*.
4. **Configuration settings**: upload `quilr-root-ca.crt`.
5. **Assignments**: add the `MAC-Quilr-Pilot` group.
6. **Review + create**.

### Step B. Create the Intermediate CA profile

Repeat Step A with **Name** *Quilr Intermediate CA* and file `quilr-ea-intermediate-ca.crt`.

### Step C. Verify the certs landed and are trusted

```bash
# List managed certs in the System keychain
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr   # expect 2

# Validate the agent intercepts a monitored AI host (Claude)
openssl s_client -connect claude.ai:443 -servername claude.ai </dev/null
```

In the Intune console, both Trusted Certificate profiles should show *Succeeded* on the pilot device before you continue to Part 3.

---

## 6. Part 3 — Deploy the Configuration Profiles

Upload each `.mobileconfig` from the bundle root as a **Custom configuration profile** **after** the certs have landed and **before** the PKG app. Upload them as **two separate** custom profiles — do not merge their payloads, since each one is signed by Quilr and corresponds to a distinct system control surface.

### Step A. General workflow for every `.mobileconfig`

For each `.mobileconfig`, repeat the following:

1. **Devices → Configuration → Create → New Policy**.
2. **Platform**: *macOS*. **Profile type**: *Templates → Custom*.
3. **Custom configuration profile name**: as listed in Step B (this is what shows on the device and in Intune status).
4. **Deployment channel**: **Device channel** *(PPPC and System Extension payloads must be device-scoped)*.
5. **Configuration profile file**: upload the `.mobileconfig`.
6. **Assignments**: add the `MAC-Quilr-Pilot` group. **Review + create**.

> **Channel warning:** once you save a custom profile you **cannot change** its deployment channel. Both Quilr profiles must be on the **Device** channel — if you pick User by mistake, delete and recreate.

### Step B. Profile-by-profile reference

| Bundle file | Intune profile name | Purpose |
|---|---|---|
| `quilr-endpoint-agent_FullDiskAccess.mobileconfig` | *Quilr Endpoint Agent — Full Disk Access (PPPC)* | Pre-grants Full Disk Access and App Management for the agent's binaries |
| `quilr-endpoint-agent-nw-extension.mobileconfig` | *Quilr Endpoint Agent — Network Extension* | Approves the System Extension and activates its content-filter payload |

### Step C. What the PPPC profile grants

| TCC service | Why the agent needs it |
|---|---|
| `kTCCServiceSystemPolicyAllFiles` (Full Disk Access) | Read the TCC database, read protected directories during file-upload extraction |
| `kTCCServiceAppManagement` | Manage the installed agent binaries on macOS 14+ where App Management is gated |

Both entries are matched against the agent's CodeRequirement (Team ID + bundle ID + designated requirement). If Quilr re-signs with a new Team ID, the profile must be re-issued.

### Step D. Confirm both profiles are applied on a pilot device

```bash
profiles list | grep -i quilr
profiles show -type configuration | grep -i quilr -A 4

# FDA entry should appear (allowed=1) within ~1 minute of profile install
sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed, auth_reason from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
```

In the Intune console: both custom profiles should show *Succeeded* under **Devices → Configuration**.

---

## 6. Part 4 — Deploy the `quilr-endpoint-agent-installer.pkg`

Add the package **last** as an **Unmanaged macOS PKG app**. (A *managed* line-of-business PKG also works if the package is a signed component package with a payload and `CFBundleVersion`; the unmanaged path is more forgiving for vendor installers.)

### Step A. Pre-install — write the tenant config

Before the `.pkg` runs, the agent's postinstall reads `/tmp/quilr-endpoint-agent.json` to enroll into the correct Quilr tenant. In the unmanaged macOS PKG app config, expand **Pre-install script** and paste the snippet below.

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`).

```bash
#!/bin/bash
TENANT="<TENANT-ID>"   # obtained from Quilr support (support@quilr.ai)
printf '{"tenant_id":"%s","discover_skip":false}\n' "$TENANT" \
  > /tmp/quilr-endpoint-agent.json
exit 0
```

### Step B. Add the PKG app

1. **Apps → All apps → Add → App type: macOS app (PKG)** *(unmanaged PKG)*.
2. **App package file**: upload `quilr-endpoint-agent-installer.pkg`.
3. **Name**: *Quilr Endpoint Agent*. **Publisher**: *Quilr AI*.
4. *(Optional)* **Pre-install / post-install scripts**: leave default unless Quilr supplies them.

### Step B. App information / detection

- For an unmanaged PKG, Intune uses the bundle/version metadata inside the package. Ensure the package's `PackageInfo` carries `CFBundleVersion` and an install-location, or Intune cannot report install state.

### Step C. Assign and release

1. **Assignments → Required → add the `MAC-Quilr-Pilot` group**.
2. **Review + create.** Intune installs on the next device check-in.
3. **App → Device install status** shows *Installed / Failed / Pending* per device.

> **Sequencing safety:** configuration profiles apply faster than app installs, so even if you create all objects together, the certs and PPPC/NetExt profiles almost always land before the PKG downloads. To be strict, assign the PKG app ~5 minutes after the profiles report *Succeeded* on the pilot.

---

## 7. Key Fields and Identifiers

| Field | Value |
|---|---|
| Installer package name | `quilr-endpoint-agent-installer.pkg` |
| PPPC mobileconfig | `quilr-endpoint-agent_FullDiskAccess.mobileconfig` |
| Network Extension mobileconfig | `quilr-endpoint-agent-nw-extension.mobileconfig` |
| Root CA file | `certs/quilr-root-ca.crt` |
| Intermediate CA file | `certs/quilr-ea-intermediate-ca.crt` |
| Architecture path (CDN) | `mac/silicon` |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip) |
| Deployment channel (custom profiles) | **Device** |
| Intune group (suggested) | `MAC-Quilr-Pilot` (promote to `MAC-Quilr-Production` after validation) |

---

## 8. Validation and Testing

**Cert profiles installed (run first):**

```bash
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr | wc -l   # expect: 2
```

**Both custom profiles installed:**

```bash
profiles list | grep -i quilr | wc -l   # expect: profiles for 2 certs + 2 mobileconfigs
```

**Network Extension active:**

```bash
systemextensionsctl list | grep -i quilr   # [activated enabled]
```

**Full Disk Access granted via MDM (no user prompt):**

```bash
sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
# expect: 1 (allowed)
```

**Agent process running:**

```bash
pgrep -lf "quilrai|quilrai-proxy"   # expect: 2+ PIDs
```

**Live intercept stream (functional test):**

```bash
sudo log stream --predicate 'subsystem == "ai.quilr.endpoint"' --info
# In Safari/Chrome, visit chatgpt.com and send a short prompt; a 'matched' event must appear within ~2s
```

**Intune reporting:**

- **Apps → Quilr Endpoint Agent → Device install status** = *Installed*.
- **Devices → Configuration** → both Trusted Certificate profiles + both custom profiles = *Succeeded*.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `tls: x509: certificate signed by unknown authority` in the agent log | Only one of the two CA profiles applied (root or intermediate missing) | Confirm both Trusted Certificate profiles show *Succeeded* in Intune; the intermediate is required to chain the leaf |
| Network Extension stuck at `[activated waiting for user]` | NetExt custom profile not applied, on the wrong channel, or wrong Team/bundle ID | Confirm the profile is on the **Device** channel and *Succeeded*; bundle ID must match the binary in `QuilrEndpointAgent.app/Contents/PlugIns/` |
| FDA prompt shown to the user on first launch | PPPC custom profile not applied, or CodeRequirement does not match a re-signed binary | Confirm the FDA profile is *Succeeded* on the **Device** channel; if the binary was re-signed, request a refreshed PPPC bundle |
| Custom profile fails to apply | Profile on wrong channel, or `.mobileconfig` > ~1 MB | Recreate on the **Device** channel; channel can't be changed after save. Confirm file size |
| Browser shows "Cannot verify identity" for a monitored host | Upstream SWG (Netskope / Zscaler / etc.) is decrypting the host | Add the host to the SWG's SSL-bypass list — see the *URL Exception List — AI Apps* (or *Non-AI Apps*) companion guide |
| PKG app stuck at *Pending* | Device hasn't checked in since assignment | Open **Company Portal → Devices → Check status / Sync**, or wait for the next MDM check-in |
| PKG reports *Installed* in Intune but app missing on device | Package lacks `CFBundleVersion`/install-location, so Intune mis-reports | Request a correctly-built package from Quilr support |

For deeper diagnostics, see the *Quilr Endpoint Agent Troubleshooting Guide* and the `logsamples/` folder.

---

## 10. Rollback

> **Important Intune-macOS caveat:** the **Uninstall** assignment intent is **not available for macOS PKG apps** (only *Required* and *Available*). To remove the agent you must push an uninstall script or remove the device from management — unassigning the PKG app does **not** uninstall it.

1. **Remove the agent binaries.** Deploy a **macOS shell script** (Devices → Scripts) running the *Clean Uninstall* block from §9 of the *Troubleshooting Guide* (`launchctl bootout` + `rm -rf /Applications/QuilrAIProxy.app` + remove `/Library/Application Support/QuilrAIProxy`). Assign to `MAC-Quilr-Pilot`, confirm execution, then remove the script.
2. **Unassign the PKG app** so it is no longer *Required* (prevents reinstall).
3. **Unassign both custom configuration profiles** (FDA + Network Extension). Intune removes them on next check-in, dropping the PPPC entries from `TCC.db` and deactivating the system extension.
4. **Unassign both Trusted Certificate profiles.** Intune removes the CAs from the System keychain.
5. *Confirm clean state:*
   - `profiles list | grep -i quilr` returns nothing
   - `systemextensionsctl list | grep -i quilr` returns nothing
   - `security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr` returns nothing

---

## 11. Summary

| Step | Action | Where in Intune |
|---|---|---|
| 1 | Obtain macOS install bundle zip | Request URL from Quilr support |
| 2 | Create Root CA Trusted Certificate profile (deploy **first**) | Devices → Configuration → Trusted certificate |
| 3 | Create Intermediate CA Trusted Certificate profile (deploy **first**) | Devices → Configuration → Trusted certificate |
| 4 | Upload both mobileconfigs as Custom profiles — FDA + NW Extension, **Device channel** (deploy **second**) | Devices → Configuration → Templates → Custom |
| 5 | Add the .pkg as an Unmanaged macOS PKG app (deploy **last**) | Apps → Add → macOS app (PKG) |
| 6 | Assign all objects to `MAC-Quilr-Pilot`; validate certs → profiles → agent | Each object → Assignments |
| 7 | Promote to `MAC-Quilr-Production` | Reassign the production group |

---

## 12. References — Microsoft Documentation

| Section | Microsoft Learn documentation |
|---|---|
| §4 Trusted Certificate profile (root / intermediate) | [Create trusted certificate profiles](https://learn.microsoft.com/en-us/intune/device-configuration/certificates/trusted-root-profiles) |
| §4 Certificate types supported by Intune | [Types of certificate supported by Intune](https://learn.microsoft.com/en-us/intune/intune-service/protect/certificates-configure) |
| §5 Custom configuration profile (upload .mobileconfig) | [Add custom settings to macOS devices](https://learn.microsoft.com/en-us/intune/intune-service/configuration/custom-settings-macos) · [Add custom settings to Apple devices](https://learn.microsoft.com/en-us/intune/intune-service/configuration/custom-settings-apple) |
| §6 Deploy an unmanaged macOS PKG app | [Add an unmanaged macOS PKG app](https://learn.microsoft.com/en-us/intune/intune-service/apps/macos-unmanaged-pkg) |
| §6 Managed macOS LOB PKG (alternative) | [Add macOS line-of-business apps](https://learn.microsoft.com/en-us/intune/app-management/deployment/add-lob-macos) |
| §10 Rollback — macOS shell scripts | [Use shell scripts on macOS devices](https://learn.microsoft.com/en-us/intune/intune-service/apps/macos-shell-scripts) |

> **Windows counterpart:** for the Windows side of an Intune rollout, use the companion *Quilr Endpoint Agent — Microsoft Intune Deployment Guide (Windows / MSI)*.

---

*End of document — Quilr AI | Adapt AI Securely*