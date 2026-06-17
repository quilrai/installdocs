---
title: Troubleshooting
description: Diagnostics, log paths, common failure modes, and the diag-bundle script.
---

# Quilr Endpoint Agent — Troubleshooting Guide

**Installation and runtime diagnostics for macOS**
*Version 2026.05.11 — companion to the Jamf Pro Deployment Guide*

> Internally the agent's binaries are named `quilrai`, `quilrai-proxy`, and `templating-engine`; on disk they live under `/Library/Application Support/quilrai/` and `/Library/Logs/quilrai/`. The user-facing product name is **Quilr Endpoint Agent**. Both naming conventions appear in this guide because both appear in the field — log paths, process names, and crash reports use the internal name.

---

## 1. How to Use This Guide

| Symptom area | Jump to |
|---|---|
| The pkg won't install or the user sees an installer error | §4 Installation Issues |
| Profile shows "Not Verified" in System Settings | §4.4 / §4.5 |
| Agent is installed but no events reach the Quilr console | §5.2 |
| Browser shows TLS errors after install | §5.4 / §5.5 |
| Need raw log lines to compare against your environment | §7 + `logsamples/` |
| Need to call the Quilr API from a script | See **API Reference** companion document |

Before diving in, run the **30-second triage** in §2 — it covers ~80% of field issues.

> **Prerequisite: every Quilr API endpoint must be allowed by the network and SSL-bypassed by every upstream SWG.** If `quilr-hub.quilr.ai`, `secure.quilr.ai` (or your tenant's `QUILR_BACKEND_BASE_URL`), `dlpone.quilr.ai` (or `QUILR_DLP_ENDPOINT`), the tenant auth host, or `openidconnect.googleapis.com` is blocked, mid-stream-decrypted, or category-filtered, the agent **cannot enroll, cannot fetch its config, cannot detect content, and cannot ship events** — every other symptom in this guide cascades from that. Confirm the allow-list **before** debugging anything else (§1.1).

### 1.1 Required Network Allow-list — Quilr API Endpoints

Every endpoint below must be **(a)** reachable from the macOS fleet over outbound 443, **(b)** allowed by URL-category filtering in any SWG / DNS filter, and **(c)** bypassed from SSL/TLS inspection. Quilr decrypts on the device — a second decryptor mid-stream will break TLS pinning and the agent will fail closed.

| Host | Purpose | Used by |
|---|---|---|
| `quilr-hub.quilr.ai` | Installer + auto-update CDN (`/endpoint-agent/prod/{mac/silicon\|windows/64}/...`) | Installer postinstall, agent self-update |
| `secure.quilr.ai` *(or tenant's `QUILR_BACKEND_BASE_URL`)* | BFF: app-details, interceptor-config, playbook controls, event ingest, heartbeat, kill-switch, auth refresh | `quilrai`, `quilrai-proxy` |
| `dlpone.quilr.ai` *(or tenant's `QUILR_DLP_ENDPOINT`)* | DLP streaming detection (`/dlp/v2/stream/detect`) | `quilrai-proxy` analyzer |
| *(tenant auth host — value of `QUILR_AUTH_API_BASE_URL`)* | OAuth authorization-code exchange (`/auth/oauth/token`) | `quilrai` persona module |
| `openidconnect.googleapis.com` | Google OIDC userinfo lookup | Only when the bound user signs in via Google SSO |

Quick all-in-one probe — every line should return `200`, `401`, or `405` (anything other than a timeout / DNS failure / TLS error means the host is *reachable*):

```bash
for url in \
  https://quilr-hub.quilr.ai/endpoint-agent/prod/mac/silicon/update.json \
  https://secure.quilr.ai/bff/extension-api-service/endpoint-agent/v1/heartbeat?message=true \
  https://dlpone.quilr.ai/dlp/v2/stream/detect ; do
  printf "%-90s -> %s\n" "$url" \
    "$(curl -sS -o /dev/null -w '%{http_code} (%{time_connect}s)' --connect-timeout 5 -X POST -d '{}' -H 'content-type: application/json' "$url" || echo TIMEOUT)"
done
```

If any line returns `TIMEOUT`, `000`, or a TLS error, the network team must (1) allow-list the host on the firewall/SWG/DNS filter and (2) bypass it from SSL inspection. See the *Web Proxy / SWG Exception List — AI Apps* and *Web Proxy / SWG Exception List — Non-AI Apps* companion guides (§3.1 Netskope / §3.2 Zscaler / §3.3 other vendors in each) for the exact configuration steps.

The full list of every API path the agent calls lives in the **API Reference** companion document.

---

## 2. 30-Second Triage

Run the following on the affected Mac. If any line returns "MISSING" or an error, the linked section explains the fix.

```bash
# 1. Agent process running?
pgrep -lf "quilrai|quilrai-proxy" || echo "MISSING: agent process"            # §5.1

# 2. Network Extension loaded and active?
systemextensionsctl list | grep -i quilr                                    # §4.6
# look for "[activated enabled]"

# 3. Content filter shown as enabled?
profiles show -type configuration | grep -A2 -i "ContentFilter"             # §4.6

# 4. CA chain in System keychain?
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr \
  || echo "MISSING: CA chain"                                               # §4.4

# 5. FDA granted to the agent?
sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';" \
  || echo "MISSING: FDA entry"                                              # §4.5

# 6. Can the agent reach EVERY Quilr API host? (see §1.1 for full probe)
curl -sS -o /dev/null -w "cdn:      %{http_code}\n" \
  https://quilr-hub.quilr.ai/endpoint-agent/prod/mac/silicon/update.json     # §1.1
curl -sS -o /dev/null -w "bff:      %{http_code}\n" -X POST -d '{}' \
  -H 'content-type: application/json' \
  "${QUILR_BACKEND_BASE_URL:-https://secure.quilr.ai}/bff/extension-api-service/endpoint-agent/v1/heartbeat?message=true"  # §1.1
curl -sS -o /dev/null -w "dlp:      %{http_code}\n" -X POST -d '{}' \
  -H 'content-type: application/json' \
  "${QUILR_DLP_ENDPOINT:-https://dlpone.quilr.ai}/dlp/v2/stream/detect"      # §1.1

# 7. How many Quilr profiles are installed (expect 3)?
profiles list | grep -i quilr | wc -l                                       # §4.3
```

> Expected healthy state: agent PID present, system extension `[activated enabled]`, content filter listed, 2 Quilr CAs in keychain, FDA `allowed=1`, control plane HTTP 200, 3 profiles installed.

---

## 3. Log Locations

| Source | Path | What to look for |
|---|---|---|
| **Installer log** | `/Library/Application Support/quilrai/logs/quilrai-endpoint.log` | First-launch / update install trace |
| **Agent process (`quilrai`)** | `/Library/Logs/quilrai/agent.stderr.log` | Full agent lifecycle: startup, env init, persona discovery, keystore, vault, IPC, heartbeat, shutdown |
| **IPC broker** | `/Library/Logs/quilrai/agent.stdout.log` | "IPC-Light Message Broker" banner + structured tracing for inter-process comms over Unix sockets |
| **Proxy daemon (`quilrai-proxy`)** | `/Library/Logs/quilrai/proxy.log.YYYY-MM-DD` *(daily rotation)* | DLP engine init, policy loading, DNS cache, kill-switch IPC, TLS interception events, attribution |
| **Templating engine** | `/Library/Logs/quilrai/templating-engine.log.YYYY-MM-DD` *(daily rotation)* | UI template loading, IPC registration, DLP alert popup window create/update — small; active only when an alert fires |
| macOS installer log | `/var/log/install.log` | pkg install success / failure (Gatekeeper, disk space) |
| macOS system log (live) | `sudo log stream --predicate 'subsystem == "ai.quilr.endpoint"' --info` | Live intercept events |
| MDM profile log | `sudo log show --predicate 'subsystem == "com.apple.ManagedClient"' --last 1h` | Profile install / removal |
| TCC (FDA) log | `sudo log show --predicate 'subsystem == "com.apple.TCC"' --last 1h` | FDA grant / deny entries |
| System Extension log | `sudo log show --predicate 'subsystem == "com.apple.sysextd"' --last 1h` | Activation, codesign requirement matching |


### Windows

| Source | Path | What to look for |
|---|---|---|
| **Agent runtime logs** | `%ProgramData%\QuilrAI\` | Agent lifecycle, configuration fetch, interception events, policy decisions |
| **MSI install log** | `%TEMP%\sentinel-msi-install.log` | Install trace — Authenticode / WHQL / driver registration errors |
| **MSI uninstall log** | `%TEMP%\sentinel-msi-uninstall.log` | Uninstall trace |
| **Intune Management Extension log** *(Intune-managed only)* | `%ProgramData%\Microsoft\IntuneManagementExtension\Logs\IntuneManagementExtension.log` | Win32 app install + detection-rule outcome |
| **Windows Event Log** | `eventvwr.msc → Applications and Services Logs` | Service start/stop, driver load failures |

Sample lines from each are stored in **`logsamples/`** alongside this guide. The filename indicates the failure scenario it represents.

---

## 4. Installation Issues

### 4.1 Package install fails immediately (exit 1)

**Symptoms**
- Jamf policy shows red ✗ under *Logs → Package Install*.
- `/var/log/install.log` contains `installer: PackageKit: Install Failed`.

**Causes & fix**
1. **Package not notarized / Gatekeeper denial.** Confirm with `spctl --assess --type install -vvv /path/to/quilr-endpoint-agent-installer.pkg`. If Gatekeeper rejects, request a re-notarized package from Quilr support.
2. **Disk space.** `df -h /Applications` — pkg needs ~300 MB free.
3. **Conflicting install.** A previous Quilr build still resident. Run the uninstall script (§9) and retry.

See `logsamples/install-pkg-failed.log` for a sample of the `install.log` entries you should expect.

### 4.2 Codesign / Team ID mismatch

**Symptoms**
- `codesign --verify -vvv /Applications/QuilrAIProxy.app` returns `code object is not signed at all` or a different Team ID than the PPPC profile expects.

**Fix**
- The PPPC `.mobileconfig` matches the agent's CodeRequirement string. If Quilr re-signs the binary with a new Team ID, the old PPPC profile no longer applies — request the matching bundle from Quilr support.

### 4.3 Profile fails to install via MDM

**Symptoms**
- Jamf says "Profile installed" but `profiles list` doesn't show it on the device.
- System Settings → Privacy & Security → Profiles shows "Verification: Unsigned" or "Not Verified".

**Fix**
1. `sudo profiles renew -type enrollment` — re-pull the MDM payload.
2. Confirm the device is **User-Approved MDM** (`profiles status -type enrollment`). Profiles fail silently on unapproved enrollments.
3. Re-upload the `.mobileconfig` in Jamf — **do not** re-sign it. Jamf re-signs on push.

### 4.4 CA cert not trusted

**Symptoms**
- Agent log: `tls: x509: certificate signed by unknown authority`.
- `openssl s_client -connect claude.ai:443` reports `verify error: unable to get issuer certificate`.

**Fix**
1. Confirm the cert profile is installed: `profiles list | grep -i "Quilr CA"`.
2. Confirm certs landed in the keychain: `security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr` (expect 2 entries — root + intermediate).
3. Validate trust evaluation: `security verify-cert -c <leaf-cert.pem>` should print `...certificate verification successful`.
4. If only one cert is present, re-upload both Certificate payloads in the Jamf profile (root **and** intermediate) and re-scope.

Sample log: `logsamples/ca-not-trusted.log`.

### 4.5 Full Disk Access (FDA) not granted

**Symptoms**
- Agent log: `permission denied: cannot read /Library/Application Support/com.apple.TCC/TCC.db`.
- TCC db query for the agent returns no row, or `allowed=0`.

**Fix**
1. Confirm the PPPC profile is installed (`profiles list | grep -i "Quilr.*Privacy"`).
2. The PPPC `.mobileconfig` must contain a `SystemPolicyAllFiles` entry whose CodeRequirement matches the agent's signing identity. Mismatched Team ID is the most common cause — see §4.2.
3. After the profile lands, the FDA entry appears automatically. There is no user prompt for MDM-delivered FDA — if you see a prompt, the profile didn't apply.
4. Verify: `sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "select client,allowed from access where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"` — must return `allowed=1`.

Sample log: `logsamples/fda-missing.log`.

### 4.6 Network Extension not approved / not active

**Symptoms**
- `systemextensionsctl list` shows the extension as `[activated waiting for user]` or doesn't show it at all.
- Browser traffic is **not** being captured (no events in the Quilr console).

**Fix**
1. Confirm the Network Extension profile is installed (`profiles list | grep -i "Quilr.*Network"`).
2. The mobileconfig must contain both a **SystemExtensions** payload (with the agent's Team ID and bundle ID in `AllowedSystemExtensions`) and a **WebContentFilter** payload referencing the same extension.
3. If the extension shows `[activated waiting for user]`, the SystemExtensions payload is missing the bundle ID. Confirm the bundle ID in the profile matches the binary (`codesign -dr - /Applications/QuilrAIProxy.app/Contents/PlugIns/QuilrNetExt.systemextension`).
4. If the profile is correct but the extension still doesn't activate: `sudo systemextensionsctl reset` (requires Recovery Mode booted into a state that allows this on Apple Silicon) — last-resort only.

Sample log: `logsamples/network-extension-denied.log`.

---

## 6. Diagnostic Commands Cheat Sheet

```bash
# ── Agent process
pgrep -lf "quilrai|quilrai-proxy"
sudo launchctl list | grep ai.quilr
sudo launchctl print system/ai.quilr.endpoint-agent | head -40

# ── Network Extension
systemextensionsctl list
sudo log show --predicate 'subsystem == "com.apple.sysextd"' --last 1h

# ── Profiles & TCC
profiles list
profiles list | grep -i quilr | wc -l
profiles show -type configuration | grep -i quilr -A4
sudo tccutil reset SystemPolicyAllFiles  # ⚠ resets ALL apps' FDA — use only in a test env

# ── Certs
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr
security verify-cert -c /tmp/leaf.pem

# ── Live event stream
sudo log stream --predicate 'subsystem == "ai.quilr.endpoint"' --info

# ── Agent CLI
quilr-cli status
quilr-cli config show
quilr-cli config refresh
quilr-cli flush-cache
quilr-cli enroll --tenant <uuid>

# ── Control plane
curl -sS https://api.quilr.ai/v1/health | jq

# ── Bundle clean-up
sudo /Applications/QuilrAIProxy.app/Contents/Resources/uninstall.sh
```

---

## 7. Log Samples

The `logsamples/` folder next to this document contains real-shape log lines (synthesized, no PII) for the following scenarios:

| File | Scenario |
|---|---|
| `01-healthy-startup.log` | Agent starts cleanly, fetches config, activates filter |
| `02-network-extension-denied.log` | SystemExtensions payload missing or wrong bundle ID |
| `03-fda-missing.log` | PPPC profile not applied; TCC db reads fail |
| `04-ca-not-trusted.log` | Quilr CA chain missing from System keychain |
| `05-successful-interception.log` | A ChatGPT prompt being captured end-to-end |
| `06-control-plane-auth-failure.log` | Device token expired or tenant mismatch |
| `07-config-fetch-failure.log` | Agent cannot retrieve the agent-interceptor config |
| `08-tls-pinning-failure.log` | Upstream SWG decrypting a monitored host |
| `09-install-pkg-failed.log` | `install.log` excerpt for a Gatekeeper / disk-space failure |
| `10-net-ext-crash-loop.log` | Network extension flipping activated/terminated |

Each file starts with a short `# Scenario:` header explaining the failure and the expected fix.

---

## 8. When to Escalate to Quilr Support

Open a support ticket (`support@quilr.ai`) and include the bundle below if:

- The 30-second triage in §2 returns all-green but events still don't arrive in the console.
- An app's URL has changed and a regex in the agent-interceptor config needs updating.
- The Network Extension is crash-looping (§5.8).
- A genuine app outside the monitored list shows TLS errors after install (§5.5).

**Diagnostic bundle**
```bash
sudo /Applications/QuilrAIProxy.app/Contents/Resources/diag-bundle.sh \
  -o ~/Desktop/quilr-diag-$(hostname)-$(date +%Y%m%d-%H%M).tar.gz
```
This script collects logs, profile listing, TCC entries, system extension state, control-plane connectivity probe, and the agent's effective config.

---

## 9. Clean Uninstall (for re-test)

```bash
# 1. Stop the agent
sudo launchctl bootout system/ai.quilr.sentinel 2>/dev/null
sudo launchctl bootout system/ai.quilr.quilrai-proxy 2>/dev/null

# 2. Remove the system extension
sudo systemextensionsctl uninstall <TeamID> ai.quilr.sentinel.netext

# 3. Remove the LaunchDaemons
sudo rm -f /Library/LaunchDaemons/ai.quilr.sentinel.plist
sudo rm -f /Library/LaunchDaemons/ai.quilr.quilrai-proxy.plist

# 4. Remove the app
sudo rm -rf /Applications/QuilrAIProxy.app

# 5. Remove configuration / cache / logs
sudo rm -rf "/Library/Application Support/QuilrAIProxy"
sudo rm -rf /Library/Logs/QuilrAIProxy

# 6. Unscope the profiles in Jamf so MDM removes them automatically
```

> Do **not** delete the CA from the System keychain unless you are also rolling back the cert profile in Jamf — leftover Certificate payloads will silently re-push the CA on the next MDM check-in.

---

*End of document — Quilr AI | Adapt AI Securely*