---
title: Microsoft Intune — Windows (MSI)
description: MDM via Microsoft Intune. CA trust + Win32 app + WinDivert driver.
---

# Quilr Endpoint Agent — Microsoft Intune Deployment Guide (Windows / MSI)

**Subtitle:** Mass deployment of the Quilr Endpoint Agent CA trust chain and MSI installer via Microsoft Intune on Windows.

**Version:** 2026.05.11

---

## 1. Overview

This guide walks an Intune administrator through deploying the **Quilr Endpoint Agent for Windows** to a fleet of Windows devices. The Windows agent ships as an **MSI** that installs a Windows service plus a WinDivert kernel driver (a WFP-based packet-capture component) for on-device traffic interception.

**How Windows differs from the macOS deployment** *(if you have done the Jamf/Kandji/Intune-macOS rollout)*:

| macOS concept | Windows equivalent |
|---|---|
| `.pkg` installer | `.msi` installer |
| CA chain → System keychain (Configuration Profile) | CA chain → Local Machine **Trusted Root** + **Intermediate** stores (Trusted Certificate profile) |
| Full Disk Access PPPC mobileconfig | **Not required** — the Windows service runs as `LocalSystem` |
| Network Extension approval mobileconfig | **Not required** — the WinDivert driver is installed by the MSI under `LocalSystem`; no separate MDM approval profile |
| System Extension activation | WinDivert filter driver registration (handled inside the MSI) |

**The deployment order is: CA certificates first, then the MSI.** The agent validates TLS against Quilr's internal CA, so the trust store must be populated before the service starts its first outbound connection.

> **Browser coverage on Windows.** The agent-interceptor configuration **excludes** `msedge.exe` and `chrome.exe` from the endpoint agent — traffic originating in Microsoft Edge or Google Chrome is **not** captured by the WinDivert driver. Cover those browsers separately via the Quilr browser extension (out of scope for this guide). Every other process (native apps, Firefox, custom HTTP clients) is captured by the endpoint agent.

**Intune terminology used in this guide:**

| Intune concept | What it is |
|---|---|
| **Win32 app** | A `.intunewin`-packaged installer (recommended for MSI/EXE); supports custom install/uninstall commands and detection rules |
| **Trusted Certificate profile** | A device configuration profile that delivers a single root **or** intermediate CA to the Windows cert store |
| **Group assignment** | Targeting a Microsoft Entra ID device or user group |

**Benefits:**

- Silent, zero-touch rollout to thousands of Windows endpoints.
- Quilr root and intermediate CAs trusted machine-wide before the agent runs.
- WinDivert driver and service installed under `LocalSystem` — no user interaction.
- Win32 detection rule prevents reinstall churn and reports true install state.

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| Intune tenant | Microsoft Intune Administrator (or a custom role with App + Device Configuration write) |
| MDM enrollment | Target PCs enrolled in Intune (Entra hybrid join or Entra join) and showing **Compliant / Managed** |
| Entra ID group | A device or user group for the rollout — e.g. `WIN-Quilr-Pilot` |
| Signed installer | `quilr-endpoint-agent.msi` is signed (Authenticode) by Quilr; the WinDivert driver inside is WHQL/EV-signed |
| Win32 Content Prep Tool | `IntuneWinAppUtil.exe` (latest) to wrap the MSI as `.intunewin` |
| Network egress | Endpoints can reach the Quilr backplane hosts on TCP 443 — see §3 for the full allowlist (and *URL Exception List — AI Apps* / *Non-AI Apps* for SWG SSL-bypass) |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip) (see Part 1 for staging steps) |

---

## 3. Firewall and Network Allowlist

The Quilr Endpoint Agent makes outbound **HTTPS (TCP 443)** to a small set of Quilr backplane hosts. Where the perimeter is enforced — corporate firewall, egress proxy, or TLS-intercepting Secure Web Gateway (Zscaler, Netskope, Symantec, Forcepoint, etc.) — these hosts must be allowed **before** the MSI is deployed in Part 3.

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

### Step D. Validate egress from a pilot device

From an elevated PowerShell on a pilot endpoint, verify reachability **before** installing the MSI:

```powershell
# Replace the first two hosts with the row from Step A that matches your tenant.
$targets = @(
    'app.quilr.ai',              # Base URL
    'dlpone.quilr.ai',           # DLP
    'discover.quilrai.dev',      # Discover (shared)
    'log.quilrai.dev',           # Diagnostic log (shared)
    'quilr-extensions.quilr.ai'  # Update / extension CDN (shared)
)
foreach ($h in $targets) {
    $ok = Test-NetConnection -ComputerName $h -Port 443 `
            -InformationLevel Quiet -WarningAction SilentlyContinue
    "{0,-40}  TCP/443  {1}" -f $h, $(if ($ok) { 'OK' } else { 'BLOCKED' })
}
```

Any `BLOCKED` host means the firewall / SWG / corporate proxy still needs adjustment. Re-run the test after the network team applies the allowlist.

### Note on Windows Defender Firewall

Windows allows **outbound TCP 443 by default**, so per-host outbound rules on Windows Defender Firewall are not normally required. If your fleet runs a block-by-default outbound Defender policy, add **program-path** allow rules for the Quilr agent service binary (Quilr support can confirm the exact install path) — Defender Firewall does not natively support outbound rules by FQDN.

The standard path is to allowlist Quilr backplane FQDNs at the **egress proxy / SWG / corporate firewall**, not on the per-endpoint Defender Firewall.

> **macOS counterpart:** the same allowlist applies to the macOS agent — for the bash validation snippet, mobileconfig payload guidance, and PF postinstall option, see the firewall section in the companion *Quilr Endpoint Agent — Intune macOS / pkg* guide.

---

## 4. Part 1 — Download and Stage the Install Bundle

### Step A. Obtain the bundle

The Windows install bundle is distributed by **Quilr support**. Contact your Quilr support representative to request the download URL and any associated checksum for the current production build (architecture path: `windows/64`).

1. **Download the bundle** from [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip).
2. Download the zip on the workstation you use to administer Intune.
3. Verify the checksum provided by Quilr before extracting.
4. Unzip into a clean staging directory.

### Step B. Bundle contents

```
quilr-endpoint-agent-install-bundle-win/
├── certs/
│   ├── quilr-ea-intermediate-ca.crt
│   └── quilr-root-ca.crt
└── quilr-endpoint-agent.msi
```

| File | Purpose | Intune object | Deploy order |
|---|---|---|---|
| `certs/quilr-root-ca.crt` | Quilr root CA — anchor of trust *(MSI installs it by default — Part 2 is optional)* | **Trusted Certificate profile** (Root store) | 1 *(optional)* |
| `certs/quilr-ea-intermediate-ca.crt` | Quilr intermediate CA — chains to the root *(MSI installs it by default — Part 2 is optional)* | **Trusted Certificate profile** (Intermediate store) | 1 *(optional)* |
| `quilr-endpoint-agent.msi` | Installs the Quilr Endpoint Agent service + WinDivert driver | **Win32 app** (`.intunewin`) | 2 |

> **Order of operations:** Deploy the **MSI Win32 app (Part 3)** — it installs the CA chain into the Local Machine trust store automatically. The Trusted Certificate profiles in **Part 2 are optional** and only needed if you want the chain in place *before* the MSI runs (see §5).

### Step C. Wrap the MSI as a `.intunewin` package

On the admin workstation, with the **Microsoft Win32 Content Prep Tool** (`IntuneWinAppUtil.exe`). Download the latest release from the official Microsoft repository:

- **GitHub:** <https://github.com/microsoft/Microsoft-Win32-Content-Prep-Tool>
- **Microsoft Learn:** [Prepare a Win32 app to be uploaded](https://learn.microsoft.com/en-us/intune/app-management/deployment/create-win32-package)

```powershell
# Place quilr-endpoint-agent.msi in C:\Staging\Quilr\
IntuneWinAppUtil.exe -c C:\Staging\Quilr -s quilr-endpoint-agent.msi -o C:\Staging\Out
# Produces: C:\Staging\Out\quilr-endpoint-agent.intunewin
```

---

## 5. Part 2 — Deploy CA Certificates *(Optional)*

> **Optional — the MSI handles this on its own.** The Quilr MSI installer (Part 3) automatically writes the Quilr root and intermediate CAs into the Local Machine **Trusted Root** and **Intermediate** stores when they are missing. The installer runs as `LocalSystem`, so no admin prompt is shown.
>
> Deploy the Trusted Certificate profiles in this part **only** if any of the following apply:
>
> - You want the CAs in place **before** the MSI lands (so you can probe reachability with `Test-NetConnection` first).
> - You need central control to rotate the CAs without re-running the MSI.
> - Other apps on the fleet also depend on the Quilr chain.
>
> Otherwise, **skip this part** and go straight to **Part 3** — the MSI will install the chain itself.

The Quilr Endpoint Agent validates TLS against Quilr's internal CA, so the root and intermediate must be in the Windows machine cert stores **before** the agent runs. A Trusted Certificate profile delivers **one** certificate each, so create **two** profiles.

> **Microsoft constraint:** an Intune Trusted Certificate profile can deliver **only** a root or an intermediate certificate — exactly what we need here. Provide each `.crt`/`.cer` as a separate profile.

### Step A. Create the Root CA profile

1. **Intune admin center → Devices → Manage devices → Configuration → Create → New Policy**.
2. **Platform**: *Windows 10 and later*. **Profile type**: *Templates → Trusted certificate*.
3. **Name**: *Quilr Root CA*.
4. **Configuration settings**: upload `quilr-root-ca.crt`. **Destination store**: *Computer certificate store — Root*.
5. **Assignments**: add the `WIN-Quilr-Pilot` group.
6. **Review + create**.

### Step B. Create the Intermediate CA profile

Repeat Step A with:
- **Name**: *Quilr Intermediate CA*.
- **File**: `quilr-ea-intermediate-ca.crt`.
- **Destination store**: *Computer certificate store — Intermediate*.

### Step C. Verify the certs landed

On a pilot device (elevated PowerShell / cmd):

```powershell
# Root store
certutil -store Root | findstr /i quilr

# Intermediate store
certutil -store CA | findstr /i quilr

# Validate the chain resolves against a Quilr-served host
Test-NetConnection claude.ai -Port 443
```

In the Intune console, the profile's **Device status** should show *Succeeded* on the pilot device before you assign the MSI in Part 3.

---

## 6. Part 3 — Deploy the Quilr Endpoint Agent MSI

Add the MSI **last** as a Win32 app so you get a proper detection rule and accurate install reporting. (A line-of-business Windows MSI app also works, but Win32 is Microsoft's recommended path and gives you custom commands + detection rules.)

### Step A. Add the Win32 app

1. **Apps → All apps → Add → App type: Windows app (Win32)**.
2. **App package file**: upload `quilr-endpoint-agent.intunewin`.
3. **Name**: *Quilr Endpoint Agent*. **Publisher**: *Quilr AI*.

### Step B. Program (install / uninstall commands)

| Field | Value |
|---|---|
| Install command | `msiexec /i "quilr-endpoint-agent.msi" /qn /norestart TENANTID=<TENANT-ID>` |
| Uninstall command | `msiexec /x "{QUILR-MSI-PRODUCT-CODE}" /qn /norestart` |
| Install behavior | **System** |
| Device restart behavior | *No specific action* |

> **`TENANTID` parameter (required).** Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`). The MSI's postinstall reads this property and uses it to enroll the device into the correct Quilr tenant. Without `TENANTID`, the agent installs but cannot phone home — it will sit idle until the property is set and the MSI is reinstalled (or until you push the tenant ID via a separate config).

> Get the exact MSI product code from Quilr (or run `Get-AppLockerFileInformation`/`msiexec` against the MSI). It is also auto-detected if you use the MSI detection type below.

### Step C. Requirements

| Field | Value |
|---|---|
| Operating system architecture | x64 |
| Minimum operating system | Windows 10 1809 (or your fleet's floor) |

### Step D. Detection rule

Choose **one**:

- **MSI** (simplest): detection type *MSI*, MSI product code auto-populated from the wrapped package.
- **Registry** (if Quilr publishes a version key): key `HKEY_LOCAL_MACHINE\SOFTWARE\Quilr\EndpointAgent`, value `Version`, *Version comparison ≥ 2026.05.08*. *(Confirm the exact registry path with Quilr support — it is not assumed here.)*

### Step E. Assign and release

1. **Assignments → Required → add the `WIN-Quilr-Pilot` group**.
2. **Review + create.** Intune installs on the next device sync (or force a sync from **Settings → Accounts → Access work or school → Info → Sync**).
3. **App → Device install status** shows *Installed / Failed / Pending* per device.

---

## 7. Key Fields and Identifiers

| Field | Value |
|---|---|
| Installer (MSI) | `quilr-endpoint-agent.msi` |
| MSI product code | Obtain from Quilr support (used in the uninstall command + MSI detection rule) |
| Root CA file | `certs/quilr-root-ca.crt` → Computer **Root** store |
| Intermediate CA file | `certs/quilr-ea-intermediate-ca.crt` → Computer **Intermediate** store |
| Architecture path (CDN) | `windows/64` |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip) |
| Intune group (suggested) | `WIN-Quilr-Pilot` (promote to `WIN-Quilr-Production` after validation) |
| Windows service name | *Confirm with Quilr support — typically a `LocalSystem` service in the `quilrai` family* |

---

## 8. Validation and Testing

**CA chain present (run first):**

```powershell
certutil -store Root | findstr /i quilr   # root present
certutil -store CA   | findstr /i quilr   # intermediate present
```

**MSI installed:**

```powershell
# Fast registry check (Add/Remove Programs uninstall keys)
Get-ChildItem HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* ,`
              HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Get-ItemProperty | Where-Object DisplayName -like '*Quilr*' |
  Select-Object DisplayName, DisplayVersion
```

**Service + WinDivert driver running:**

```powershell
Get-Service | Where-Object { $_.Name -match 'quilrai|quilr' }
# WinDivert filters/callouts registered by the driver:
netsh wfp show state | findstr /i "WinDivert quilr"
```

**Live intercept (functional test):**

In **Firefox** or a native app, reach a monitored AI host (e.g. send a prompt). Confirm the event appears in the Quilr console. *Edge/Chrome are excluded from the endpoint agent on Windows — use a different browser for this test.*

**Intune reporting:**

- **Apps → Quilr Endpoint Agent → Device install status** = *Installed*.
- **Devices → Configuration** → both Trusted Certificate profiles = *Succeeded*.

> **Agent logs:** the Windows agent writes logs under its ProgramData directory (in the `quilrai` family, e.g. `%PROGRAMDATA%\quilrai\logs\`) and emits to the Windows **Event Log**. Confirm the exact path with Quilr support / the Windows release notes — it is not assumed here.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `certutil -store Root` shows no Quilr cert | Trusted Certificate profile not applied, or wrong destination store | Confirm the Root profile targets *Computer store — Root* and the Intermediate profile targets *Computer store — Intermediate*; re-sync the device |
| Agent service won't start / TLS errors in Event Log | CA chain incomplete (intermediate missing) | Confirm **both** Trusted Certificate profiles show *Succeeded* in Intune; the intermediate is required to chain the leaf |
| Win32 app stuck at *Pending* | Device hasn't synced since assignment | Settings → Accounts → Access work or school → Info → **Sync**, or wait for the 8-hour default cycle |
| Win32 app reports *Failed* (exit 1603/1618) | MSI install error (1618 = another install in progress; 1603 = generic failure) | Re-run sync; check `%WINDIR%\Temp\` MSI logs and the Intune Management Extension log at `%ProgramData%\Microsoft\IntuneManagementExtension\Logs\IntuneManagementExtension.log` |
| Browser shows "Cannot verify identity" for a monitored host | Upstream SWG (Netskope / Zscaler / etc.) is decrypting the same host | Add the host to the SWG's SSL-bypass list — see the *URL Exception List — AI Apps* (or *Non-AI Apps*) companion guide |

For deeper diagnostics, see the *Quilr Endpoint Agent Troubleshooting Guide* and the `logsamples/` folder.

---

## 10. Rollback

1. **Change the MSI app assignment from *Required* to *Uninstall*** for the `WIN-Quilr-Pilot` group. Intune runs the MSI uninstall command on next sync. *(Win32 apps support the Uninstall assignment intent — unlike macOS PKG apps.)*
2. **Unassign both Trusted Certificate profiles.** Intune removes the CAs from the Windows trust store on next sync.
3. *Confirm clean state:*
   - `certutil -store Root | findstr /i quilr` returns nothing
   - `certutil -store CA | findstr /i quilr` returns nothing
   - `Get-Service | ? Name -match 'quilrai|quilr'` returns nothing

---

## 11. Summary

| Step | Action | Where in Intune |
|---|---|---|
| 1 | Obtain Windows install bundle (MSI + certs) | Request URL from Quilr support |
| 2 | Wrap the MSI as `.intunewin` | `IntuneWinAppUtil.exe` on the admin workstation |
| 3 | *(Optional)* Create Root CA Trusted Certificate profile — skip if you let the MSI install it | Devices → Configuration → Trusted certificate (Root store) |
| 4 | *(Optional)* Create Intermediate CA Trusted Certificate profile — skip if you let the MSI install it | Devices → Configuration → Trusted certificate (Intermediate store) |
| 5 | Add the MSI as a Win32 app with MSI detection (deploy **second**) | Apps → Add → Windows app (Win32) |
| 6 | Assign all items to `WIN-Quilr-Pilot`; validate certs → MSI | Each item → Assignments |
| 7 | Promote to `WIN-Quilr-Production` | Reassign the production group |

---

## 12. References — Microsoft Documentation

| Section | Microsoft Learn documentation |
|---|---|
| §4C / §6 Win32 app — prepare the package | [Prepare a Win32 app to be uploaded](https://learn.microsoft.com/en-us/intune/app-management/deployment/create-win32-package) |
| §4C Win32 Content Prep Tool (`IntuneWinAppUtil.exe`) | [microsoft/Microsoft-Win32-Content-Prep-Tool (GitHub)](https://github.com/microsoft/Microsoft-Win32-Content-Prep-Tool) |
| §6 Win32 app — add and assign | [Add and assign Win32 apps](https://learn.microsoft.com/en-us/intune/app-management/deployment/add-win32) |
| §6 Win32 app — management overview | [Win32 app management](https://learn.microsoft.com/en-us/intune/app-management/deployment/win32) |
| §5 Trusted Certificate profile (root / intermediate) | [Create trusted certificate profiles](https://learn.microsoft.com/en-us/intune/device-configuration/certificates/trusted-root-profiles) |
| §5 Certificate types supported by Intune | [Types of certificate supported by Intune](https://learn.microsoft.com/en-us/intune/intune-service/protect/certificates-configure) |

> **macOS counterpart:** for the Apple side of an Intune rollout, use the dedicated companion *Quilr Endpoint Agent — Microsoft Intune Deployment Guide (macOS / pkg)*.

---

*End of document — Quilr AI | Adapt AI Securely*