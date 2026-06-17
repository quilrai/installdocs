---
title: ManageEngine Endpoint Central — Windows (MSI)
description: On-prem MDM via ManageEngine Endpoint Central.
---

# Quilr Endpoint Agent — ManageEngine Endpoint Central Deployment Guide (Windows / MSI)

**Subtitle:** Silent mass deployment of the Quilr Endpoint Agent CA trust chain, MSI installer, and browser extension using the ManageEngine Endpoint Central (formerly Desktop Central) "Install MSI/EXE Software" computer configuration.

**Version:** 2026.05.21

---

## 1. Overview

This guide walks a **ManageEngine Endpoint Central** (formerly **Desktop Central**) administrator through deploying the **Quilr Endpoint Agent for Windows** to a fleet of managed computers. The Windows agent ships as an **MSI** that installs a Windows service plus a WinDivert kernel driver (a WFP-based packet-capture component) for on-device traffic interception.

The deployment uses Endpoint Central's **Software Deployment** module: you add the MSI to the **Software Repository** once, then push it with an **Install MSI/EXE Software** computer configuration to a target group. The Endpoint Central agent on each computer downloads the package from the repository and runs the install silently under the **System User** account — no end-user interaction.

**The deployment order is: CA certificates first, then the MSI.** The agent validates TLS against Quilr's internal CA, so the Windows machine trust store must be populated before the service starts its first outbound connection. The browser extension (Part 5) is independent and can be deployed in parallel.

**Browser coverage note.** On Windows, the agent-interceptor configuration **excludes** `msedge.exe` and `chrome.exe` from the endpoint agent — that traffic is captured by the **Quilr browser extension** instead (Part 5), avoiding double-capture. Every other process (native apps, Firefox, custom HTTP clients) is captured by the endpoint agent's WinDivert driver.

**Endpoint Central terminology used in this guide:**

| Endpoint Central concept | What it is |
|---|---|
| **Software Repository** | The store (Network Share or HTTP) holding packages that agents download before installing |
| **Package** | An MSI/EXE definition created under *Software Deployment → Package Creation → Packages* |
| **Configuration** | A computer- or user-level action (here: *Install MSI/EXE Software*) defined → targeted → deployed |
| **Custom Script** | A computer configuration that runs a script/command (used here to import the CA certs) |
| **Target** | The custom group / OU / domain / set of computers a configuration is applied to |

**Benefits:**

- Silent, zero-touch rollout to thousands of Windows endpoints from a single configuration.
- Quilr root and intermediate CAs trusted machine-wide **before** the agent runs.
- WinDivert driver and service installed under **System User** — no user interaction, no logged-in user required.
- Package stored once in the repository and reused across pilot → production targets.
- Browser extension force-installed in Edge and Chrome with no user opt-out.

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| Endpoint Central server | ManageEngine Endpoint Central with the **Software Deployment** module licensed |
| Admin role | An Endpoint Central role with **Software Deployment** + **Configuration** write permissions |
| Agent enrollment | Target computers have the Endpoint Central agent installed and showing as **Managed / contacted** |
| Software Repository | A configured **Network Share** or **HTTP** repository reachable by agents (or distribution servers for remote offices) |
| Target group | A custom group / OU for the rollout — e.g. `WIN-Quilr-Pilot` |
| Signed installer | `quilr-endpoint-agent.msi` is Authenticode-signed by Quilr; the WinDivert driver inside is WHQL/EV-signed |
| Network egress | Endpoints can reach the Quilr distribution host and control plane (see *URL Exception List — AI Apps* / *Non-AI Apps* companion guides for SSL-bypass entries) |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip) (see Part 1 for staging steps) |

---

## 3. Part 1 — Download and Stage the Install Bundle

### Step A. Obtain the bundle

The Windows install bundle is distributed by **Quilr support**. Contact your Quilr support representative to request the download URL and any associated checksum for the current production build (architecture path: `windows/64`).

1. **Download the bundle** from [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip).
2. Download the zip on the workstation you use to administer Endpoint Central.
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

| File | Purpose | Endpoint Central object | Deploy order |
|---|---|---|---|
| `certs/quilr-root-ca.crt` | Quilr root CA — anchor of trust | **Custom Script** config → machine **Root** store | 1 |
| `certs/quilr-ea-intermediate-ca.crt` | Quilr intermediate CA — chains to the root | **Custom Script** config → machine **Intermediate (CA)** store | 1 |
| `quilr-endpoint-agent.msi` | Installs the Quilr Endpoint Agent service + WinDivert driver | **Software Repository package** → *Install MSI Software* config | 2 |

> **Order of operations:** Deploy the **"Install MSI Software" configuration (Part 4)** — the MSI installs the CA chain into the Local Machine trust store automatically. The Custom Script in **Part 3 is optional** and only needed if you want the chain in place *before* the MSI runs.

### Step C. Place the source files where Endpoint Central can reach them

Copy the MSI (and the two `.crt` files) to a path the Endpoint Central server / repository can read:

- **Network Share repository** — copy to the configured UNC share, e.g. `\\EPC-SERVER\SoftwareRepository\Quilr\`.
- **HTTP repository / Local upload** — keep the files on the admin workstation; you will upload via the browser in Part 4.

---

## 4. Part 2 — Add the MSI to the Software Repository

Create the package **once**; you reuse it in the Install configuration (Part 6) and for any future version bumps.

### Step A. Start a new Windows package

1. **Software Deployment tab → Package Creation → Packages → Add Package → Windows**.
2. **Package Name**: `Quilr Endpoint Agent`.
3. **Package Type**: *MSI/MSP*.
4. **License Type**: *Commercial* (or per your agreement).

### Step B. Locate the installable

1. **Locate Installable**: choose one —
   - **From Shared Folder** — point to the UNC path where you staged the MSI (Network Share repository), e.g. `\\EPC-SERVER\SoftwareRepository\Quilr\quilr-endpoint-agent.msi`.
   - **From Local Computer** — **Browse** to `quilr-endpoint-agent.msi` on the admin workstation (uploads into the HTTP repository).
2. **MSI/MSP File Name**: auto-filled as `quilr-endpoint-agent.msi`.

### Step C. MSI properties (silent install)

| Field | Value |
|---|---|
| MSI/MSP File Name | `quilr-endpoint-agent.msi` |
| MST File Name | *(leave blank unless Quilr provides a transform)* |
| MSI/MSP Properties (install) | *(blank — Endpoint Central runs MSIs silently; add `KEY=VALUE` pairs only if Quilr specifies them)* |

> **Silent install:** Endpoint Central installs MSI packages silently by default (no `/qn` needed — that is handled by the platform).
>
> **`TENANTID` parameter (required).** In the **MSI/MSP Properties** field of the package, set:
>
> ```
> TENANTID=<TENANT-ID>
> ```
>
> Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`). The MSI's postinstall reads this property and uses it to enroll the device into the correct Quilr tenant. Without `TENANTID`, the agent installs but cannot phone home — it will sit idle.
>
> Add any additional space-separated `PROPERTY=VALUE` pairs in the same field if Quilr support provides further custom MSI properties.

### Step D. Advanced settings and package properties (optional)

- **Advanced Settings**: leave **Exit Code** defaults; set **Architecture** to *64-bit*; raise **Maximum Time Limit for Installation (Hours)** if your fleet is slow.
- **Package Properties**: *Application Name* `Quilr Endpoint Agent`, *Version* (per the build, e.g. `2026.05.08`), *Vendor* `Quilr AI`.
- **Pre-Deployment / Post-Deployment Activities**: not required for a standard install.

### Step E. Save

Click **Add Package**. The package now appears under *Software Deployment → Packages*, ready to be referenced by a configuration.

---

## 5. Part 3 — Deploy the Quilr CA Certificates *(Optional — Custom Script Configuration)*

> **Optional — the MSI handles this on its own.** The Quilr MSI installer (deployed in Part 4) automatically writes the Quilr root and intermediate CAs into the Local Machine **Trusted Root** and **Intermediate** stores when they are missing. The installer runs as `LocalSystem`, so no admin prompt is shown.
>
> Run this Custom Script configuration **only** if any of the following apply:
>
> - You want the CAs in place **before** the MSI lands (so you can probe reachability with `Test-NetConnection` first).
> - You need central control to rotate the CAs without re-running the MSI.
> - Other apps on the fleet also depend on the Quilr chain.
>
> Otherwise, **skip this part** and go straight to **Part 4** — the MSI will install the chain itself.

The agent validates TLS against Quilr's internal CA, so the **root** and **intermediate** must be in the Windows machine cert stores **before** the agent runs. Use an Endpoint Central **Custom Script** computer configuration that runs `certutil` under System.

### Step A. Stage the two `.crt` files

Copy `quilr-root-ca.crt` and `quilr-ea-intermediate-ca.crt` to a share Endpoint Central can attach to the script (the Custom Script configuration lets you associate files that are copied to the endpoint before the command runs).

### Step B. Create the Custom Script configuration

1. **Configurations → Add Configuration → Configuration → (Computer) → Custom Script**.
2. **Name**: `Quilr CA Trust`.
3. **Script Type**: *Batch File* (`.bat`) or *PowerShell*.
4. Associate the two `.crt` files so they are copied to the endpoint, and set the command:

```bat
:: Runs as System; %~dp0 is the script's copied location on the endpoint
certutil -addstore -f Root  "%~dp0quilr-root-ca.crt"
certutil -addstore -f CA    "%~dp0quilr-ea-intermediate-ca.crt"
```

5. **Define Target**: add the `WIN-Quilr-Pilot` group.
6. **Deploy**.

> **Why a script:** `certutil -addstore Root` imports into the machine **Trusted Root** store and `-addstore CA` into the **Intermediate Certification Authorities** store — exactly the two anchors the agent needs. The configuration runs under the System account, so no logged-in user is required.

### Step C. Verify the certs landed

On a pilot device (elevated PowerShell / cmd):

```powershell
certutil -store Root | findstr /i quilr   # root present
certutil -store CA   | findstr /i quilr   # intermediate present
Test-NetConnection claude.ai -Port 443
```

In the Endpoint Central console, the configuration's **status** should show *Applied / Success* on the pilot device before you deploy the MSI in Part 6.

---

## 6. Part 4 — Create the "Install MSI Software" Configuration

Deploy the MSI **after** the CA configuration has applied. This is the configuration described in the ManageEngine "Installing MSI Software" help topic.

### Step A. Name the configuration

1. **Configurations → Add Configuration → Configuration → (Computer) → Install MSI/EXE Software**.
2. **Name**: `Quilr Endpoint Agent — Install`. Add a description.

### Step B. Define configuration

| Field | Value |
|---|---|
| Package type | **MSI** |
| MSI Package Name | `Quilr Endpoint Agent` (the package from Part 2) |
| Operation Type | **Install Completely** |
| Install as | **System User** |
| Allow user to interact with installation window | **No** (silent) |

> **Operation Type options** are *Install Completely*, *Advertise*, and *Remove*. Use **Install Completely** for a full silent install. **Remove** is what you switch to for rollback (Part 11).

### Step C. Scheduler (optional)

Set a **schedule time** for the operation, with an optional **expiry date**, if you want the install to run in a maintenance window rather than at the next agent refresh.

### Step D. Deployment settings

| Field | Recommended value |
|---|---|
| Installation Option | **During or After Startup** (installs at next boot, and immediately if already running) |
| Install Between | *(optional)* restrict to a maintenance window, e.g. 22:00–05:00 |
| Allow Users to Skip Deployment | **No** (set a forced-deployment date if you must allow skips) |
| Reboot Policy | **Do not reboot** (the agent does not require a reboot; choose a reboot option only if your build's release notes call for one) |

### Step E. Define target

Use **Define Target** to add the `WIN-Quilr-Pilot` custom group (or OU / domain / specific computers).

### Step F. Deploy

Click **Deploy** to push immediately, or **Save as Draft** to stage it. Agents install on their next refresh cycle (or trigger a manual agent refresh on a pilot box). Track per-computer state under the configuration's **status** view (*Applied / Yet to Apply / Failed / Retry in Progress*).

---

## 7. Part 5 — Force-Install the Quilr Browser Extension (Edge + Chrome)

Because the agent-interceptor config excludes `msedge.exe` and `chrome.exe` on Windows, those two browsers are covered by the **Quilr browser extension**. Force-install it via a **Registry** computer configuration that writes the `ExtensionInstallForcelist` policy keys. (If you license **Browser Security Plus**, you can manage extensions there instead.)

### Step A. Microsoft Edge — `ExtensionInstallForcelist`

1. **Configurations → Add Configuration → Configuration → (Computer) → Registry**.
2. **Name**: `Quilr Extension — Edge Force Install`.
3. Add the value:
   - **Key**: `HKLM\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist`
   - **Value name**: `1`
   - **Type**: `REG_SZ`
   - **Value data**: `<edge-extension-id>;https://edge.microsoft.com/extensionwebstorebase/v1/crx`
4. **Define Target**: `WIN-Quilr-Pilot`. **Deploy**.

### Step B. Google Chrome — `ExtensionInstallForcelist`

1. New **Registry** configuration: `Quilr Extension — Chrome Force Install`.
2. Add the value:
   - **Key**: `HKLM\SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist`
   - **Value name**: `1`
   - **Type**: `REG_SZ`
   - **Value data**: `<chrome-extension-id>;https://clients2.google.com/service/update2/crx`
3. **Define Target**: `WIN-Quilr-Pilot`. **Deploy**.

> Get the exact extension ID and update URL from Quilr support. For a self-hosted extension, use `<extension-id>;https://<quilr-update-host>/updates.xml` as the value data.

### Step C. Verify

On a pilot device, open `edge://extensions` and `chrome://extensions` — the Quilr extension must be present, **enabled**, and marked *Installed by your organization* (no remove button).

---

## 8. Key Fields and Identifiers

| Field | Value |
|---|---|
| Installer (MSI) | `quilr-endpoint-agent.msi` |
| Repository package name | `Quilr Endpoint Agent` (Part 2) |
| Root CA file | `certs/quilr-root-ca.crt` → machine **Root** store (`certutil -addstore Root`) |
| Intermediate CA file | `certs/quilr-ea-intermediate-ca.crt` → machine **CA / Intermediate** store (`certutil -addstore CA`) |
| Architecture path (CDN) | `windows/64` |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/windows/installer/quilr-endpoint-agent-win-install-bundle.zip) |
| Browser extension ID + update URL | Obtain from Quilr support |
| Endpoint Central target (suggested) | `WIN-Quilr-Pilot` (promote to `WIN-Quilr-Production` after validation) |
| Operation Type (install) | **Install Completely** |
| Operation Type (rollback) | **Remove** |
| Windows service name | *Confirm with Quilr support — typically a System service in the `quilrai` family* |

---

## 9. Validation and Testing

**CA chain present (run first):**

```powershell
certutil -store Root | findstr /i quilr   # root present
certutil -store CA   | findstr /i quilr   # intermediate present
```

**MSI installed:**

```powershell
Get-ChildItem HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* ,`
              HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Get-ItemProperty | Where-Object DisplayName -like '*Quilr*' |
  Select-Object DisplayName, DisplayVersion
```

**Service + WinDivert driver running:**

```powershell
Get-Service | Where-Object { $_.Name -match 'quilrai|quilr' }
netsh wfp show state | findstr /i "WinDivert quilr"
```

**Live intercept (functional test):** In **Firefox** or a native app (not Edge/Chrome — those go through the extension), reach a monitored AI host (e.g. send a prompt). Confirm the event appears in the Quilr console.

**Browser extension active:** `edge://extensions` and `chrome://extensions` show the Quilr extension *Installed by your organization*, enabled.

**Endpoint Central reporting:**

- The *Install MSI Software* configuration **status** = *Applied / Success* per computer.
- The *Quilr CA Trust* Custom Script configuration = *Applied / Success*.
- The Edge/Chrome Registry configurations = *Applied / Success*.

> **Agent logs:** the Windows agent writes logs under its ProgramData directory (in the `quilrai` family, e.g. `%PROGRAMDATA%\quilrai\logs\`) and emits to the Windows **Event Log**. Confirm the exact path with Quilr support / the Windows release notes — it is not assumed here.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `certutil -store Root` shows no Quilr cert | Custom Script config not applied, or `-addstore` used the wrong store | Confirm the script imports root with `-addstore Root` and intermediate with `-addstore CA`; re-deploy / refresh the agent |
| Agent service won't start / TLS errors in Event Log | CA chain incomplete (intermediate missing) | Confirm **both** certs imported (`certutil -store Root` and `-store CA`); the intermediate is required to chain the leaf |
| Configuration stuck at *Yet to Apply* | Agent hasn't refreshed since deployment | Trigger a manual **agent refresh** on the endpoint, or wait for the next refresh cycle |
| Configuration reports *Failed* | Package not reachable, MSI error (1603 generic / 1618 another install in progress), or wrong architecture | Confirm the package downloaded to the agent's repository cache; check the endpoint's MSI logs under `%WINDIR%\Temp\`; re-deploy |
| Package never downloads to the endpoint | Software Repository (Network Share / HTTP) unreachable from the agent or distribution server | Verify the repository path/URL and that the agent (or its distribution server) can reach it |
| Browser shows "Cannot verify identity" for a monitored host | Upstream SWG (Netskope / Zscaler / etc.) is decrypting the same host | Add the host to the SWG's SSL-bypass list — see the *URL Exception List — AI Apps* (or *Non-AI Apps*) companion guide |
| Edge/Chrome traffic not captured at all | Expected — Edge/Chrome are excluded from the endpoint agent on Windows | Confirm the **browser extension** (Part 5) is force-installed and enabled; the extension, not the WinDivert driver, covers those browsers |
| Extension missing from `edge://extensions` | Registry force-list policy not applied, or wrong extension ID / update URL | Re-check the `ExtensionInstallForcelist` value (`ID;UPDATE_URL`) against what Quilr support provided; re-deploy |

For deeper diagnostics, see the *Quilr Endpoint Agent Troubleshooting Guide* and the `logsamples/` folder.

---

## 11. Rollback

1. **Uninstall the agent:** edit the *Install MSI Software* configuration and change **Operation Type** to **Remove** (using the same `Quilr Endpoint Agent` package), then re-deploy to `WIN-Quilr-Pilot`. Endpoint Central runs the MSI uninstall on the next refresh.
2. **Remove the browser-extension policy:** delete (or suspend) the Edge/Chrome **Registry** configurations so `ExtensionInstallForcelist` is no longer enforced.
3. **Remove the CAs:** deploy a Custom Script that runs `certutil -delstore Root <thumbprint-or-name>` and `certutil -delstore CA <thumbprint-or-name>` (or suspend the *Quilr CA Trust* config and clean up).
4. **Confirm clean state:**
   - `certutil -store Root | findstr /i quilr` returns nothing
   - `certutil -store CA | findstr /i quilr` returns nothing
   - `Get-Service | ? Name -match 'quilrai|quilr'` returns nothing
   - Quilr extension absent from `edge://extensions` / `chrome://extensions`

---

## 12. Summary

| Step | Action | Where in Endpoint Central |
|---|---|---|
| 1 | Obtain Windows install bundle (MSI + certs) | Request URL from Quilr support |
| 2 | Add the MSI to the Software Repository | Software Deployment → Package Creation → Packages → Add Package → Windows |
| 3 | Deploy the two CA certs (run **first**) | Configurations → Custom Script (certutil -addstore) |
| 4 | Create the *Install MSI Software* config (run **second**) | Configurations → Install MSI/EXE Software |
| 5 | Force-install the Quilr browser extension (Edge + Chrome) | Configurations → Registry (ExtensionInstallForcelist) |
| 6 | Define target = `WIN-Quilr-Pilot`; validate certs → MSI → extension | Each configuration → Define Target |
| 7 | Promote to `WIN-Quilr-Production` | Re-target the configurations |

---

## 13. References — ManageEngine Documentation

| Section | ManageEngine documentation |
|---|---|
| §6 Install MSI/EXE Software configuration | [Installing MSI Software](https://www.manageengine.com/products/desktop-central/help/computer_configuration/installing_msi_software.html#Install-MSI-Package) |
| §4 Create software packages (MSI) | [Create Software Packages](https://www.manageengine.com/products/desktop-central/help/software_installation/create-software-packages.html) |
| §2 Software Repository (Network Share / HTTP) | [Software Repository](https://www.manageengine.com/products/desktop-central/software-repository.html) |
| §2 Configuring software repositories | [Configuring Software Repositories](https://www.manageengine.com/products/desktop-central/help/configuring_desktop_central/edit_network_shared_path.html) |
| §4 Manage MSI files | [Manage MSI Files](https://www.manageengine.com/products/desktop-central/help/configuring_desktop_central/managing_msi_files.html) |
| §3/§5 Custom Script & Registry configurations | [Computer Configurations](https://www.manageengine.com/products/desktop-central/help/computer_configuration/computer_configuration.html) |
| §6 Defining targets for a configuration | [Defining Targets](https://www.manageengine.com/products/desktop-central/help/configurations/defining_targets.html) |

> **Microsoft Intune counterpart:** for an Intune-based rollout, use the companion *Quilr Endpoint Agent — Microsoft Intune Deployment Guide (Windows / MSI)*.

---

*End of document — Quilr AI | Adapt AI Securely*