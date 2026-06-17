---
title: macOS Manual Install
description: Manual install for technicians / no-MDM pilots.
---

# Quilr Endpoint Agent — Manual Deployment Guide (macOS)

**Subtitle:** Hands-on, single-Mac installation of the Quilr Endpoint Agent — trusting the CA chain, installing the pkg, and approving the System Extension and Full Disk Access interactively, with no MDM.

**Version:** 2026.05.21

---

## 1. Overview

This guide covers installing the **Quilr Endpoint Agent for macOS** **by hand on a single Mac** — for a pilot machine, a test/lab device, a developer workstation, or any Mac that is **not enrolled in an MDM** (Jamf, Kandji, Intune). You run the installer locally and approve macOS security prompts interactively at the keyboard.

**How this differs from an MDM rollout.** With an MDM, configuration profiles silently pre-trust the CA chain, pre-grant Full Disk Access (PPPC), and pre-approve the System Extension before the agent ever runs — the user sees nothing. **Manually, there is no profile to pre-approve anything**, so you must perform three approvals yourself:

| What MDM does silently | What you do by hand here |
|---|---|
| Pushes the root + intermediate CA to the System keychain | `security add-trusted-cert` into `/Library/Keychains/System.keychain` (Part 2) |
| PPPC profile pre-grants Full Disk Access | Toggle the agent on in **System Settings → Privacy & Security → Full Disk Access** (Part 5) |
| System Extension payload pre-approves the content filter | Click **Allow** in **System Settings → Privacy & Security**, then **Allow** the network filter dialog (Part 4) |

**Order of operations:** trust the **CA certificates first**, then install the **pkg**, then approve the **System Extension** and **Full Disk Access** on first launch. Trusting the CA before the agent runs means its first TLS handshake against the Quilr control plane succeeds — no failed handshake, no retry loop.

> **You must be physically at the Mac.** The System Extension and Full Disk Access approvals require clicking buttons in System Settings — they cannot be done over plain SSH. Use Screen Sharing / a console session if the Mac is remote.

**Benefits:**

- No MDM required — install on any Mac you have admin rights to.
- Same agent, certs, and pkg as the managed rollouts; only the approval mechanism differs.
- Fully scriptable up to the two GUI approvals (extension + FDA).
- Clean, documented uninstall for re-testing.

---

## 2. Prerequisites

| Requirement | Details |
|---|---|
| Local admin | An administrator account on the Mac with `sudo` rights |
| Physical / console access | Screen Sharing or a logged-in console session to click the System Settings approvals (not plain SSH) |
| macOS version | A current macOS release (Apple Silicon or Intel); System Extension approval lives in **System Settings → Privacy & Security** on macOS 13+ |
| Signed installer | `quilr-endpoint-agent-installer.pkg` — Developer ID Installer-signed and notarized (Team ID `W8FHSH4RM5`) |
| Network egress | The Mac can reach the Quilr distribution host and control plane (see *URL Exception List — AI Apps* / *Non-AI Apps* companion guides for SSL-bypass entries) |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip) (see Part 1 for staging steps) |

---

## 3. Part 1 — Download and Stage the Install Bundle

### Step A. Obtain the bundle

The install bundle is distributed by **Quilr support**. Request the download URL and any associated checksum for the current production build (architecture path: `mac/silicon`).

1. **Download the bundle** from [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip).
2. Download the zip onto the target Mac (or copy it across).
3. Verify the checksum provided by Quilr before extracting.
4. Unzip into a working directory, e.g. `~/Downloads/quilr/`.

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

| File | Purpose | Used in this guide |
|---|---|---|
| `certs/quilr-root-ca.crt` | Quilr root CA — anchor of trust | Part 2 (trust manually) |
| `certs/quilr-ea-intermediate-ca.crt` | Quilr intermediate CA — chains to the root | Part 2 (trust manually) |
| `quilr-endpoint-agent-installer.pkg` | Installs the agent to `/Applications` | Part 3 |
| `*.mobileconfig` files | MDM pre-approval payloads | **Not used** in a manual install — you approve interactively in Parts 4–5 |

> **The two `.mobileconfig` files are for MDM rollouts only.** In a manual install you do not load them; instead you grant the same permissions by hand. They are useful as a reference for *what* the agent needs (Full Disk Access + the content-filter System Extension).

---

## 4. Part 2 — Trust the Quilr CA Certificates

The Quilr Endpoint Agent validates TLS against Quilr's internal CA, so the **System keychain** must trust the chain before the agent runs. Add the **root** as a trusted root and the **intermediate** so the chain resolves.

### Step A. Add the certificates (admin Terminal)

```bash
cd ~/Downloads/quilr/quilr-endpoint-agent-install-bundle

# Root CA -> trusted root anchor in the System keychain
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain certs/quilr-root-ca.crt

# Intermediate CA -> present in the System keychain so the leaf chains to root
sudo security add-trusted-cert -d -r trustAsRoot \
  -k /Library/Keychains/System.keychain certs/quilr-ea-intermediate-ca.crt
```

You will be prompted for the admin password (and possibly a keychain authorization). Both certs land in the **System** keychain (not login), so trust is machine-wide.

### Step B. Verify the chain is trusted

```bash
# Expect 2 Quilr certificates in the System keychain
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr | wc -l

# Validate the agent intercepts a monitored AI host (Claude) (chain should verify cleanly)
openssl s_client -connect claude.ai:443 -servername claude.ai </dev/null
```

> **Why both certs:** the agent presents a leaf signed by the Quilr intermediate, which chains to the Quilr root. Trust the **root** so it is an anchor; install the **intermediate** so macOS can build the path from leaf → intermediate → root. Missing the intermediate is the most common cause of `x509: certificate signed by unknown authority` after a manual install.

---

## 5. Part 3 — Install the Agent Package

The package is Developer ID-signed and notarized, so Gatekeeper allows it without lowering security.

### Step A. Install from Terminal (recommended)

#### Pre-install — write the tenant config

Before running `installer -pkg`, write the tenant config to `/tmp` so the agent's postinstall script can enroll the device into the correct Quilr tenant. Run this in Terminal as the admin user:

```bash
#!/bin/bash
TENANT="<TENANT-ID>"   # obtained from Quilr support (support@quilr.ai)
printf '{"tenant_id":"%s","discover_skip":false}\n' "$TENANT" \
  > /tmp/quilr-endpoint-agent.json
exit 0
```

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`).

```bash
sudo installer -pkg quilr-endpoint-agent-installer.pkg -target /
```

The installer writes `QuilrAIProxy.app` to `/Applications`, installs its LaunchDaemon `com.sentinel.agent` under `/Library/LaunchDaemons/`, and registers the network System Extension. The agent service starts automatically (the `quilrai-proxy` child process is spawned by the agent).

### Step B. Or install from the GUI

1. Double-click `quilr-endpoint-agent-installer.pkg`.
2. Follow the installer; authenticate as an administrator when prompted.
3. If Gatekeeper objects (rare for a notarized pkg), **right-click → Open**, or allow it under **System Settings → Privacy & Security**.

### Step C. Confirm the install landed

```bash
ls -d /Applications/QuilrAIProxy.app           # app present
sudo launchctl list | grep -i quilrai               # com.sentinel.agent loaded
pgrep -lf "quilrai|quilrai-proxy"                  # process(es) running
```

> On first launch the agent triggers two macOS approval flows — the **System Extension** (Part 4) and **Full Disk Access** (Part 5). Until you complete both, the agent runs but **cannot intercept traffic or read protected files**. Continue to Part 4 immediately.

---

## 6. Part 4 — Approve the System Extension (Content Filter)

The agent installs a network **System Extension** that performs on-device traffic interception. macOS blocks it until a local admin approves it.

### Step A. Allow the extension

1. On first launch you will see **"System Extension Blocked"** (or a prompt to allow software from *Quilr*).
2. Open **System Settings → Privacy & Security**.
3. Scroll to the **Security** section. Next to the message about the *QuilrAIProxy* / *Quilr* system software, click **Allow**.
4. Authenticate as an administrator.

### Step B. Allow the network content filter

1. macOS then shows **"QuilrAIProxy" would like to filter network content.**
2. Click **Allow**. (Choosing *Don't Allow* leaves the filter inactive — interception will not work.)

### Step C. Verify the extension is active

```bash
systemextensionsctl list | grep -i quilr
# Expect a line ending in [activated enabled]
```

> **If it shows `[activated waiting for user]`,** the approval in Step A was not completed — return to **System Settings → Privacy & Security** and click **Allow**. On Apple Silicon Macs with *Reduced Security*, an additional approval may appear; complete it as prompted.

---

## 7. Part 5 — Grant Full Disk Access

The agent needs **Full Disk Access** to read the TCC database and protected directories during file-upload inspection. Without an MDM PPPC profile, you toggle this on by hand.

### Step A. Enable Full Disk Access

1. Open **System Settings → Privacy & Security → Full Disk Access**.
2. Find **QuilrAIProxy** in the list (the agent registers itself there on first launch).
3. Toggle it **on**. Authenticate as an administrator.
4. If macOS asks you to quit and reopen the app, allow it to restart — or restart the daemon by hand:

```bash
sudo launchctl bootout   system /Library/LaunchDaemons/com.sentinel.agent.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.sentinel.agent.plist
```

### Step B. Verify Full Disk Access was granted

```bash
sqlite3 "/Library/Application Support/com.apple.TCC/TCC.db" \
  "select client, allowed from access \
   where service='kTCCServiceSystemPolicyAllFiles' and client like '%quilr%';"
# Expect: a row with allowed = 1
```

> If **QuilrAIProxy** does not appear in the Full Disk Access list, launch the app once (`open /Applications/QuilrAIProxy.app`) so it registers, then re-open the pane. You can also drag the app into the list with the **+** button.

---

## 8. Key Fields and Identifiers

| Field | Value |
|---|---|
| Installer package | `quilr-endpoint-agent-installer.pkg` |
| Installed app | `/Applications/QuilrAIProxy.app` |
| LaunchDaemon | `/Library/LaunchDaemons/com.sentinel.agent.plist` (label `com.sentinel.agent`) |
| Agent bundle ID | `ai.quilr.agent.sentinel` |
| Developer Team ID | `W8FHSH4RM5` |
| Root CA file | `certs/quilr-root-ca.crt` → System keychain (`trustRoot`) |
| Intermediate CA file | `certs/quilr-ea-intermediate-ca.crt` → System keychain (`trustAsRoot`) |
| Architecture path (CDN) | `mac/silicon` |
| Log subsystem (unified log) | `ai.quilr.endpoint` |
| Runtime logs | `/Library/Logs/quilrai/` (agent.stderr.log, agent.stdout.log, proxy.log.*, templating-engine.log.*) |
| Installer log | `/Library/Application Support/quilrai/logs/quilrai-endpoint.log` |
| Bundle download | [`https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip`](https://quilr-extensions.quilr.ai/endpoint-agent/prod/mac/installer/quilr-endpoint-agent-install-bundle.zip) |

---

## 9. Validation and Testing

Run these in order; each line should match the expected result.

**CA chain trusted (run first):**

```bash
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr | wc -l   # expect: 2
```

**App installed and daemon loaded:**

```bash
ls -d /Applications/QuilrAIProxy.app
sudo launchctl list | grep -i quilrai
```

**System Extension active:**

```bash
systemextensionsctl list | grep -i quilr   # [activated enabled]
```

**Full Disk Access granted:**

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

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `tls: x509: certificate signed by unknown authority` in the agent log | Only the root was trusted, or the intermediate was skipped | Re-run **both** `add-trusted-cert` commands (Part 2); confirm `find-certificate ... grep -i quilr` returns **2** |
| `systemextensionsctl list` shows `[activated waiting for user]` | The System Extension was never approved | **System Settings → Privacy & Security → Allow** (Part 4); authenticate as admin |
| Network content not intercepted at all | The "would like to filter network content" dialog was declined | Re-trigger by restarting the daemon (`bootout` then `bootstrap` on `/Library/LaunchDaemons/com.sentinel.agent.plist`) and click **Allow** |
| FDA prompt keeps reappearing / file reads fail | Full Disk Access not toggled on for QuilrAIProxy | Enable it in **System Settings → Privacy & Security → Full Disk Access** (Part 5); confirm `TCC.db` shows `allowed = 1` |
| pkg won't open ("cannot be opened") | Gatekeeper quarantine on a copied file | Right-click → **Open**, or allow under **Privacy & Security**; confirm the pkg is the notarized Quilr build |
| Browser shows "Cannot verify identity" for a monitored host | Upstream SWG (Netskope / Zscaler / etc.) is decrypting the same host | Add the host to the SWG's SSL-bypass list — see the *URL Exception List* companion guides |
| Agent installed but no events in the console | Control-plane auth / config fetch failing | Tail `/Library/Logs/quilrai/agent.stderr.log`; see the *Quilr Endpoint Agent Troubleshooting Guide* and `logsamples/` |

For deeper diagnostics, run the bundled collector and send it to Quilr support:

```bash
sudo /Applications/QuilrAIProxy.app/Contents/Resources/diag-bundle.sh \
  -o ~/Desktop/quilr-diag-$(hostname)-$(date +%Y%m%d-%H%M).tar.gz
```

---

## 11. Uninstall

### Option A. Built-in uninstaller (preferred)

```bash
sudo /Applications/QuilrAIProxy.app/Contents/Resources/uninstall.sh
```

### Option B. Manual clean uninstall

```bash
# 1. Stop the agent
sudo launchctl bootout system /Library/LaunchDaemons/com.sentinel.agent.plist 2>/dev/null

# 2. Remove the system extension (Team ID W8FHSH4RM5)
sudo systemextensionsctl uninstall W8FHSH4RM5 ai.quilr.sentinel.netext

# 3. Remove the LaunchDaemon
sudo rm -f /Library/LaunchDaemons/com.sentinel.agent.plist

# 4. Remove the app
sudo rm -rf /Applications/QuilrAIProxy.app

# 5. Remove configuration / cache / logs
sudo rm -rf "/Library/Application Support/QuilrAIProxy"
sudo rm -rf /Library/Logs/QuilrAIProxy
```

### Option C. Remove the manually trusted CAs

```bash
# Find the exact certificate name(s), then delete from the System keychain
security find-certificate -a -c quilr /Library/Keychains/System.keychain | grep -i "labl"
sudo security delete-certificate -c "<exact-cert-common-name>" /Library/Keychains/System.keychain
```

**Confirm clean state:**

```bash
systemextensionsctl list | grep -i quilr                                      # nothing
ls -d /Applications/QuilrAIProxy.app 2>/dev/null                         # nothing
security find-certificate -a /Library/Keychains/System.keychain | grep -i quilr  # nothing
```

---

## 12. Summary

| Step | Action | Where |
|---|---|---|
| 1 | Obtain and unzip the macOS bundle | Request URL from Quilr support |
| 2 | Trust the root + intermediate CA (deploy **first**) | `security add-trusted-cert` → System keychain |
| 3 | Install the agent pkg | `sudo installer -pkg ... -target /` |
| 4 | Approve the System Extension + content filter | System Settings → Privacy & Security → **Allow** |
| 5 | Grant Full Disk Access to QuilrAIProxy | System Settings → Privacy & Security → Full Disk Access |
| 6 | Validate certs → extension → FDA → live intercept | Terminal checks in §9 |

---

## 13. References

| Topic | Resource |
|---|---|
| Approve a System Extension on macOS | Apple — *Manage system and network extensions* (System Settings → Privacy & Security) |
| `security add-trusted-cert` usage | `man security` (macOS) — the `add-trusted-cert` verb and `-r trustRoot` / `trustAsRoot` options |
| Full Disk Access (TCC) | Apple — *Control access to files and folders* (Privacy & Security) |
| Deeper diagnostics & log samples | *Quilr Endpoint Agent Troubleshooting Guide* + `logsamples/` |
| URL / SSL-bypass exceptions | *Quilr Endpoint Agent URL Exception List — AI Apps* / *Non-AI Apps* |

> **MDM counterparts:** to deploy at scale instead of by hand, use the companion *Quilr Endpoint Agent* deployment guides for **Jamf Pro**, **Kandji**, or **Microsoft Intune (macOS / pkg)**.

---

*End of document — Quilr AI | Adapt AI Securely*