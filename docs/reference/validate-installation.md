---
title: Validate Installation
description: Post-install validation steps for Windows + macOS. MDM-agnostic.
---

# Quilr Endpoint Agent — Validate Installation (Windows + macOS)

**Subtitle:** Post-install validation steps for the Quilr Endpoint Agent. Works regardless of how the agent was deployed (Intune, Jamf, Kandji, ManageEngine, or manual).

**Version:** 2026.05.11

---

## 1. Overview

Use this page after a fresh install — or any time you need to confirm an existing endpoint is still healthy — to answer one question: **is the Quilr Endpoint Agent installed correctly and actively intercepting traffic?**

Each platform section walks through the same five concerns in order. A check that fails halts the chain; jump to the linked Troubleshooting Guide section for the fix, then come back and re-run from that step.

| # | Concern | What it proves |
|---|---|---|
| 1 | **Binaries / package** installed | The installer ran and placed the agent on disk. |
| 2 | **Service / daemon** running | The agent process is alive under the system account. |
| 3 | **CA trust chain** present | The Quilr root + intermediate CAs are trusted machine-wide. |
| 4 | **Driver / extension** active | Traffic interception layer (WFP on Windows, System Extension on macOS) is loaded. |
| 5 | **Permissions** in place | FDA/PPPC on macOS. |

Section 4 then runs a **functional test** with `claude.ai` that proves the agent is intercepting a real monitored AI host end-to-end.

---

## 2. macOS — Validate Installation

> Run every command in **Terminal** with `sudo` rights (or `sudo -i` for the SQLite read).


**Where the macOS agent writes its logs** — consult these whenever a check below fails. The Quilr "internal" naming for binaries / logs still uses the `Sentinel` family; the user-facing surface uses `QuilrAI`.

| Source | Path | What to look for |
|---|---|---|
| Agent runtime (`sentinel`) | `/Library/Logs/Sentinel/agent.stderr.log` | Startup banner, tenant assignment, daemon lifecycle, config-fetch failures |
| IPC broker | `/Library/Logs/Sentinel/agent.stdout.log` | Inter-process channel between `sentinel` and `sentinel-proxy` |
| Proxy daemon (`sentinel-proxy`) | `/Library/Logs/Sentinel/proxy.log.YYYY-MM-DD` *(daily-rotated)* | TLS interception, policy decisions, monitored-host flows |
| Templating engine | `/Library/Logs/Sentinel/templating-engine.log.YYYY-MM-DD` *(daily-rotated)* | DLP alert UI activity (small; only writes when an alert fires) |
| Installer log | `/Library/Application Support/Sentinel/logs/sentinel-endpoint.log` | First-launch / update install trace |
| macOS installer log | `/var/log/install.log` | pkg install / uninstall failures, Gatekeeper, codesign, disk-space |
| Live intercept stream | `sudo log stream --predicate 'subsystem == "ai.quilr.endpoint"' --info` | Real-time interception events as they happen |

For deeper diagnostics see [Troubleshooting](/reference/troubleshooting).

### Step 1. Agent binaries are installed

```bash
ls -ld /Applications/QuilrAIProxy.app && \
  ls -ld "/Library/Application Support/QuilrAI" && \
  defaults read /Applications/QuilrAIProxy.app/Contents/Info.plist CFBundleShortVersionString
```

**Expected:** both the **app bundle** `/Applications/QuilrAIProxy.app` and the **support folder** `/Library/Application Support/QuilrAI` exist, and a version string prints (e.g. `2026.05.08`).
**If it fails:** the pkg never installed — see [Troubleshooting Guide §4.1](/reference/troubleshooting#41-package-install-fails-immediately-exit-1).


**If this check fails — inspect the pkg install log:**

| Log | Path |
|---|---|
| Quilr installer trace | `/Library/Application Support/Sentinel/logs/sentinel-endpoint.log` |
| macOS installer subsystem | `/var/log/install.log` *(filter with `grep -i quilr` or `grep -i Sentinel`)* |

```bash
# Quick failure-mode tail
sudo tail -n 200 /Library/Application\ Support/Sentinel/logs/sentinel-endpoint.log 2>/dev/null

# macOS Installer trace, filtered to the Quilr pkg
sudo grep -i 'quilr\|sentinel' /var/log/install.log | tail -n 100
```

Look for `Gatekeeper`, `codesign`, `package-script`, or `installer:` lines. Most pkg failures are codesign / notarization mismatches (rebuild the bundle) or insufficient disk space.

### Step 2. Agent daemons are running

```bash
pgrep -lf 'quilrai|quilrai-proxy'
sudo launchctl print system/ai.quilr.sentinel       | grep -E 'state =|last exit'
sudo launchctl print system/ai.quilr.quilrai-proxy | grep -E 'state =|last exit'
```

**Expected:** at least **two** PIDs (one `quilrai`, one `quilrai-proxy`); `state = running` on both LaunchDaemons; `last exit code = 0`.
**If it fails:** see [Troubleshooting Guide §5.1](/reference/troubleshooting#51-agent-process-not-running).

### Step 3. Quilr CA chain is in the System keychain

```bash
COUNT=$(security find-certificate -a /Library/Keychains/System.keychain | grep -ci quilr)
echo "Quilr certs in System keychain: $COUNT (expect: 2)"
```

**Expected:** exactly **2** certificates — the Quilr root and intermediate.
**If it fails:** see [Troubleshooting Guide §4.4](/reference/troubleshooting#44-ca-cert-not-trusted).

### Step 4. Network Extension is activated

```bash
systemextensionsctl list | grep -i quilr
```

**Expected:** a line containing `[activated enabled]` (not `[activated waiting for user]`, not absent).
**If it fails:** see [Troubleshooting Guide §4.6](/reference/troubleshooting#46-network-extension-not-approved--not-active).

### Step 5. Full Disk Access (PPPC) is granted via MDM

```bash
sudo sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed, auth_reason from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
```

**Expected:** at least one row with `allowed=1` and `auth_reason=4` (MDM grant). **No user prompt** should ever appear — if the user sees one, the PPPC profile wasn't pre-applied.
**If it fails:** see [Troubleshooting Guide §4.5](/reference/troubleshooting#45-full-disk-access-fda-not-granted).

### macOS one-liner

Paste this whole block in Terminal — every line should report `OK`:

```bash
echo "1. binaries: $(test -d /Applications/QuilrAIProxy.app \
                    && test -d \"/Library/Application Support/QuilrAI\" \
                    && echo OK || echo MISSING)"
echo "2. daemons : $(pgrep -lf 'quilrai|quilrai-proxy' >/dev/null && echo OK || echo NOT-RUNNING)"
echo "3. CAs     : $([ $(security find-certificate -a /Library/Keychains/System.keychain | grep -ci quilr) -eq 2 ] && echo OK || echo MISSING)"
echo "4. netext  : $(systemextensionsctl list | grep -qE 'quilr.*activated enabled' && echo OK || echo NOT-ACTIVE)"
echo "5. FDA     : $(sudo sqlite3 '/Library/Application Support/com.apple.TCC/TCC.db' \
                     "select allowed from access where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%' limit 1;" \
                     2>/dev/null | grep -q '^1$' && echo OK || echo NOT-GRANTED)"
```

---

## 3. Windows — Validate Installation

> Open **PowerShell as Administrator**. The first probe in each step is the fast path; the second confirms detail.

### Step 1. MSI is installed (registry-reported version)

```powershell
Get-ChildItem `
  HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*, `
  HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Get-ItemProperty | Where-Object DisplayName -like '*Quilr*' |
  Select-Object DisplayName, DisplayVersion, Publisher, InstallDate
```

**Expected:** at least one row showing **Quilr Endpoint Agent** with a `DisplayVersion` and `Publisher = Quilr AI`.

**Confirm the install folder is on disk** (the MSI drops binaries here):

```powershell
Get-Item "$env:ProgramFiles\QuilrAI" | Select-Object FullName, LastWriteTime
Get-ChildItem "$env:ProgramFiles\QuilrAI" -Force -ErrorAction SilentlyContinue |
  Select-Object -First 8 Name, Length
```

**Expected:** `%ProgramFiles%\QuilrAI` exists and contains the agent's binaries / configs.
**If it fails:** the MSI never installed — re-check the Intune Win32 / ManageEngine deployment status.


**Where the Windows agent writes its logs:**

| Source | Path |
|---|---|
| Agent runtime | `%ProgramData%\QuilrAI\` |
| MSI install | `%TEMP%\sentinel-msi-install.log` |
| MSI uninstall | `%TEMP%\sentinel-msi-uninstall.log` |


**If this check fails — inspect the MSI install log:**

| When the MSI was run by | Log path |
|---|---|
| The signed-in user (interactive install / right-click → Install) | `C:\Users\<USER>\AppData\Local\Temp\sentinel-msi-install.log` &nbsp;*(= `%TEMP%\sentinel-msi-install.log` in that user's context)* |
| `SYSTEM` (MDM-pushed MSI — Intune Win32 / ManageEngine / GPO) | `C:\Windows\Temp\sentinel-msi-install.log` &nbsp;*(= `%TEMP%\sentinel-msi-install.log` when `%TEMP%` resolves under `LocalSystem`)* |

Tail the last few hundred lines and look for `Error`, `1603`, `1618`, or the MSI return code. If you don't have shell access, fetch the file via your MDM (Intune *Devices → Diagnostic data* / ManageEngine *Remote file fetch*).

```powershell
# Show the last 200 lines of whichever install log exists (covers both paths)
foreach ($p in @(
  "$env:TEMP\sentinel-msi-install.log",
  "C:\Windows\Temp\sentinel-msi-install.log",
  "C:\Users\$env:USERNAME\AppData\Local\Temp\sentinel-msi-install.log"
)) {
  if (Test-Path $p) {
    "==> $p"
    Get-Content $p -Tail 200
    break
  }
}
```

For the *uninstall* equivalent (when rollback fails or you're cleaning up a stuck install), the same paths exist with `sentinel-msi-uninstall.log`.

### Step 2. Windows service is running

```powershell
Get-Service | Where-Object { $_.Name -match 'quilrai|quilr' } |
  Select-Object Name, Status, StartType
```

**Expected:** at least one row with `Status = Running` and `StartType = Automatic`.

If the service exists but isn't running:

```powershell
Get-Service -Name <ServiceName> | Start-Service
```

**If it fails:** confirm the MSI postinstall completed; check the agent log under `%PROGRAMDATA%\quilrai\logs\` (confirm the exact path with Quilr support).

### Step 3. WinDivert filter driver is registered

The fastest check is the service-control query — one line tells you whether the WinDivert kernel driver is installed AND running:

```powershell
sc query WinDivert
```

**Expected** — `TYPE: 1 KERNEL_DRIVER`, `STATE: 4 RUNNING`. If the service doesn't exist, the MSI didn't register it — re-deploy. If `STATE: 1 STOPPED`, run `sc start WinDivert` (elevated). For a deeper view, dump the live WFP state:

```powershell
netsh wfp show state file=$env:TEMP\wfp.xml | Out-Null
Select-String -Path $env:TEMP\wfp.xml -Pattern 'quilr|quilrai' -SimpleMatch | Select -First 5
```

**Expected:** lines describing Quilr/QuilrAIProxy filters or callouts.
**If it fails:** the driver was not installed by the MSI (or was unloaded). Reboot the device; if it still fails, escalate.

### Step 4. Quilr CA chain is in the Local Machine trust store

```powershell
certutil -store Root | Select-String -Pattern 'Quilr' -SimpleMatch
certutil -store CA   | Select-String -Pattern 'Quilr' -SimpleMatch
```

**Expected:** Quilr root in the **Root** store **and** Quilr intermediate in the **CA** (Intermediate) store.
**If it fails:** the Intune Trusted Certificate profiles (or ManageEngine cert deployment) didn't apply. Re-sync the device.

### Windows one-liner

Paste this whole block in **elevated PowerShell** — every line should report `OK`:

```powershell
$msi = (Get-ChildItem HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*,`
                    HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* |
        Get-ItemProperty | ? DisplayName -like '*Quilr*').Count
$svc = (Get-Service | ? { $_.Name -match 'quilrai|quilr' -and $_.Status -eq 'Running' }).Count
$wfp = & netsh wfp show state file=$env:TEMP\wfp.xml | Out-Null
       (Select-String $env:TEMP\wfp.xml -Pattern 'quilr|quilrai' -SimpleMatch).Count
$root = (certutil -store Root 2>$null | Select-String 'Quilr' -SimpleMatch).Count
$mid  = (certutil -store CA   2>$null | Select-String 'Quilr' -SimpleMatch).Count

$dir = Test-Path "$env:ProgramFiles\QuilrAI"
"1. MSI installed   : $(if($msi -gt 0 -and $dir){'OK'}else{'MISSING'})"
"2. service running : $(if($svc -gt 0){'OK'}else{'NOT-RUNNING'})"
"3. WinDivert filters     : $(if($wfp -gt 0){'OK'}else{'NOT-REGISTERED'})"
"4. CA chain        : $(if($root -gt 0 -and $mid -gt 0){'OK'}else{'MISSING'})"
```

---

## 4. Cross-Platform Functional Test (Claude.ai)

This proves the agent is **actively intercepting** an AI host — not just installed.

### macOS

```bash
# Watch the live intercept stream in one Terminal
sudo log stream --predicate 'subsystem == "ai.quilr.endpoint"' --info \
  | grep -iE 'matched|intercepted|claude'
```

Then, in **Safari** or **Firefox** (not Chrome with the extension), open https://claude.ai/, sign in if needed, and send a one-line prompt.

**Expected:** within ~2 seconds the `log stream` output emits a `flow.matched ... claude.ai` line. *No certificate warning* appears in the browser, and Claude responds normally.

### Windows

```powershell
# Watch the agent log (confirm exact path with Quilr support)
Get-Content "$env:PROGRAMDATA\quilrai\logs\proxy.log.*" -Tail 0 -Wait |
  Select-String -Pattern 'matched|claude' -SimpleMatch
```

Then, in **Firefox** or a native HTTPS client (not Edge/Chrome — those use the browser extension instead of the WinDivert driver), open https://claude.ai/ and send a prompt.

**Expected:** a `matched … claude.ai` line in the log within ~2 seconds; no certificate error; Claude responds normally.

### TLS-chain check (both platforms)

The leaf cert presented at `claude.ai` should be Anthropic's real CA, **not** your corporate SWG's CA — otherwise an upstream proxy is decrypting Claude before the Quilr agent sees it, and interception will fail.

```bash
# macOS / Linux
openssl s_client -connect claude.ai:443 -servername claude.ai </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer
```

```powershell
# Windows (PowerShell 7+)
$tcp = New-Object Net.Sockets.TcpClient('claude.ai', 443)
$ssl = New-Object Net.Security.SslStream($tcp.GetStream())
$ssl.AuthenticateAsClient('claude.ai')
$ssl.RemoteCertificate.Issuer
```

**Expected:** the issuer string names a real CA (e.g. `WE1`, `Let's Encrypt`, `DigiCert`, `Cloudflare Inc ECC CA-3`). If it names your SWG (Netskope, Zscaler, etc.), the host needs to be on the SWG's SSL-bypass list — see the *URL Exception List — AI Apps* companion guide.

---

### Quilr CA in the cert chain (browser check — both platforms)

This is the **strongest** end-to-end proof that the agent is actively intercepting AI traffic: when Quilr is in the path, the leaf certificate the browser sees for a monitored host is **signed by the Quilr CA**, not by the site's real CA. Use `claude.ai` as the example — the same procedure works for any monitored host in the *URL Exception List — AI Apps*.

1. Open **https://claude.ai/** in your default browser.
2. Click the **padlock icon** to the left of the URL bar.
3. Drill into the connection / certificate details (path varies by browser):
   - **Chrome / Edge** → *Connection is secure* → *Certificate is valid* → **Details**.
   - **Safari** → *Show Certificate*.
   - **Firefox** → arrow → *More information* → *View Certificate*.
4. Look at the **Issued By** / **Issuer** field of the **leaf** certificate (bottom of the chain).

**Expected:** the issuer is the **Quilr CA** — the friendly name contains *Quilr* and the chain matches the `quilr-root-ca` + `quilr-ea-intermediate-ca` you installed earlier.

**If the issuer is Anthropic's real CA** (e.g. *WE1*, *Let's Encrypt*, *DigiCert*, *Cloudflare Inc ECC CA-3*), the Quilr agent is **not** intercepting that browser flow. Common causes:

- Agent process not running — see §2 Step 2 (macOS) or §3 Step 2 (Windows).
- The browser is excluded from the agent on this platform (Edge/Chrome on Windows are intentionally excluded — they use the Quilr browser extension instead; see the separate [Browser Extension — Validate Installation](/extension/validate-installation) page).
- The browser is using a separate proxy / VPN that bypasses the agent.

**Command-line equivalent (macOS / Linux):**

```bash
echo | openssl s_client -connect claude.ai:443 -servername claude.ai 2>/dev/null \
  | openssl x509 -noout -issuer
# Expected: issuer line contains 'Quilr'
```

**Command-line equivalent (Windows PowerShell 7+):**

```powershell
$tcp = New-Object Net.Sockets.TcpClient('claude.ai', 443)
$ssl = New-Object Net.Security.SslStream($tcp.GetStream(), $false, {param($s,$c,$ch,$e) $true})
$ssl.AuthenticateAsClient('claude.ai')
$ssl.RemoteCertificate.Issuer
# Expected: contains 'Quilr'
```

## 5. Pass / Fail Summary

The installation is **healthy** when every check below returns `OK`:

| Platform | Check | Method |
|---|---|---|
| macOS | `/Applications/QuilrAIProxy.app` + `/Library/Application Support/QuilrAI` present | §2 Step 1 |
| macOS | Daemons running | §2 Step 2 |
| macOS | 2 Quilr CAs in System keychain | §2 Step 3 |
| macOS | Network Extension `[activated enabled]` | §2 Step 4 |
| macOS | FDA granted via MDM (`allowed=1, auth_reason=4`) | §2 Step 5 |
| macOS | Claude.ai prompt produces `flow.matched` log | §4 |
| Windows | Quilr MSI in registry uninstall keys + `%ProgramFiles%\QuilrAI` folder on disk | §3 Step 1 |
| Windows | QuilrAIProxy/Quilr Windows service `Running` | §3 Step 2 |
| Windows | WinDivert filters registered | §3 Step 3 |
| Windows | Quilr root in **Root** store + intermediate in **CA** | §3 Step 4 |
| Windows | Claude.ai prompt produces a `matched` log line | §4 |
| Both | Browser cert on `claude.ai` shows **Quilr** as the Issuer | §4 (Quilr CA in the cert chain) |

If **any** check returns the non-OK string, that's where to start with the *Troubleshooting Guide*.

---

## 6. When to Escalate

Open a support ticket at **`support@quilr.ai`** with the items below if validation still fails after consulting the linked Troubleshooting sections:

- The output of the **macOS one-liner** in §2 (or Windows one-liner in §3).
- The output of the **Claude.ai functional test** in §4.
- For macOS: a copy of `/Library/Logs/quilrai/agent.stderr.log` and `proxy.log.YYYY-MM-DD` for the day of the test.
- For Windows: the most recent file under `%PROGRAMDATA%\quilrai\logs\` (confirm the exact directory with Quilr support) and the **Intune Management Extension** log at `%ProgramData%\Microsoft\IntuneManagementExtension\Logs\IntuneManagementExtension.log`.
- Tenant UUID, device hostname, agent version, time window of the failed test, OS version.
- Whether an upstream SWG (Netskope, Zscaler, Cisco Umbrella, Palo Alto, Forcepoint, …) is in the network path.

---

*End of document — Quilr AI | Adapt AI Securely*