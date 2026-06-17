---
title: URL Exception List — Non-AI Apps
description: Non-AI hosts (auth/CDNs) — for SWG SSL-bypass.
---

# Quilr Endpoint Agent — Web Proxy / SWG Exception List (Non-AI Apps)

**SSL-inspection bypass list for collaboration apps — Slack and Microsoft Teams**
*Version 2026.05.11 — derived from `agent-interceptor` config (id 285, version 64)*

> Companion document: *Quilr-Endpoint-Agent-URL-Exception-List-AI-Apps* covers ChatGPT, Claude, Gemini, Copilot, and all other AI assistants and GenAI file-upload endpoints.

---

## 1. Why This List Exists

In addition to AI assistants, the Quilr Endpoint Agent monitors a small set of **collaboration apps** where sensitive content commonly leaves the organisation as chat messages or file uploads — namely **Slack** and **Microsoft Teams**. The agent intercepts the outbound traffic on the device, extracts message text and any attached files (after OCR / PDF / DOCX / XLSX / plaintext extraction), and ships structured events to the Quilr control plane for policy.

If your environment already runs a secure web gateway or CASB — **Netskope**, **Zscaler ZIA**, **Cisco Umbrella SIG / Secure Web Appliance**, **Palo Alto Prisma Access**, **Forcepoint ONE**, **Symantec/Broadcom WSS / Edge SWG (ProxySG)**, **McAfee/Skyhigh SWG**, **Check Point Harmony**, **iboss**, **Cloudflare Gateway**, **Menlo**, etc. — those products also terminate and re-sign TLS for the same hosts. **Two decryptors in the same path do not coexist.** When the upstream SWG presents its own CA, the Quilr agent sees an unexpected leaf certificate, pinning checks fail, request signatures break, and the chain fails closed.

> **The fix:** add every host in §3 to the SWG's **SSL/TLS inspection bypass**. Quilr decrypts on the host, captures the message/file, re-encrypts before packets leave the device.

For interception to function correctly, every URL listed here must:

1. Be **reachable** from the endpoint (not blocked by SWG URL filtering, firewall, ZTNA, or DNS filter).
2. Be **bypassed from SSL/TLS inspection** on every SWG / proxy / CASB in the path.
3. Reach the endpoint via the same path the user's browser / native app uses.

---

## 2. How to Use This List

| Audience | Action |
|---|---|
| **Netskope admin** | Policies → Real-time Protection → SSL Decryption → create a "Do Not Decrypt" rule for the §3 domains. See §3.1. |
| **Zscaler ZIA admin** | Policy → SSL Inspection → "Do Not Inspect" rule on a URL Category containing the §3 hosts. See §3.2. |
| **Other SWG / proxy admin** | Add §3 domains to your product's "SSL bypass" feature — see §3.3 for the per-vendor cheat sheet. |
| **Firewall / ZTNA admin** | Allow outbound 443 to every host in §3 from the macOS fleet. |
| **EDR / Mac admin** | If a host-based content filter sits in front of Quilr's network extension, allow-list the Quilr agent process. |
| **Compliance / DLP owner** | Use §4 to evidence which collaboration endpoints are actively monitored for message + file content by Quilr on the device. |
| **Quilr admin** | Regenerate this guide when the `agent-interceptor` config version changes. |

---

## 3. Non-AI Domains to Allow + Bypass from SSL Inspection

| # | Host | Purpose |
|---|---|---|
| 1 | `*.slack.com` | Slack `chat.postMessage` (per-workspace subdomain) |
| 2 | `files.slack.com` | Slack file uploads |
| 3 | `teams.microsoft.com` | MS Teams Web message API |
| 4 | `teams.cloud.microsoft` | MS Teams Web message API (ALT host) |

> **Wildcards.** `*.slack.com` is a wildcard rule and must be expressed as a wildcard pattern (or each per-workspace subdomain enumerated) in your proxy/firewall.

### 3.1 Configuring the bypass in Netskope

1. Sign in to the Netskope tenant admin console.
2. Navigate to **Policies → Real-time Protection → SSL Decryption**.
3. Click **New Policy** (top-right).
4. **Source**: scope to the macOS device group running the Quilr Endpoint Agent.
5. **Destination**: Custom Category `Quilr Agent Bypass — Collab Apps` containing `*.slack.com`, `files.slack.com`, `teams.microsoft.com`, `teams.cloud.microsoft`.
6. **Action**: **Do Not Decrypt**.
7. **Set Order**: place this rule **above** any "Decrypt All" rule.
8. **Save** and **Apply Changes**.
9. Validate via §7.2.

### 3.2 Configuring the bypass in Zscaler Internet Access (ZIA)

1. Sign in to the ZIA admin portal.
2. **Administration → Resources → URL Categories → Add URL Category**. Name `Quilr Agent Bypass — Collab Apps`; add `.slack.com`, `files.slack.com`, `teams.microsoft.com`, `teams.cloud.microsoft` as Custom URLs.
3. **Policy → SSL Inspection → SSL Inspection Policy → Add Rule**: rule name `Quilr Agent Collab — Do Not Inspect`; criteria `URL Categories = Quilr Agent Bypass — Collab Apps`; scope to the macOS fleet.
4. **Action**: **Do Not Inspect**.
5. **Order**: drag the rule **above** any "Inspect All" rule.
6. **Save** and **Activate**.
7. (Optional) Cloud App Control may classify Slack/Teams under built-in categories — confirm those categories allow access through this path.
8. Validate via §7.2.

### 3.3 Cheat sheet — equivalent feature per SWG / CASB vendor

| Vendor / product | Where to add the bypass | Feature name |
|---|---|---|
| **Netskope** | Policies → Real-time Protection → SSL Decryption | *Do Not Decrypt* |
| **Zscaler ZIA** | Policy → SSL Inspection → SSL Inspection Policy | *Do Not Inspect* |
| **Cisco Umbrella SIG** | Policies → Web Policy → SSL Decryption List | *Selective Decryption — Exclude* |
| **Cisco Secure Web Appliance (WSA)** | Web Security Manager → Decryption Policies → URL Filtering | *Pass Through* |
| **Palo Alto Prisma Access / NGFW** | Policies → Decryption | *No Decrypt* on custom URL category |
| **Forcepoint ONE / Web Security** | Web Policies → SSL Decryption → Bypass | *SSL Bypass List* |
| **Symantec / Broadcom WSS, Edge SWG (ProxySG)** | SSL Visibility / Policy → SSL Intercept Layer | *Do Not Intercept* |
| **McAfee / Skyhigh SWG** | Policy → Rule Sets → SSL Scanner | *Stop Cycle* / SSL bypass action |
| **Check Point Harmony Connect / Quantum** | HTTPS Inspection → Exceptions | *Bypass HTTPS Inspection* |
| **iboss** | Web Filters → SSL Decryption → SSL Decryption Bypass | *SSL Decryption Bypass* |
| **Cloudflare Gateway** | Settings → Network → Firewall → HTTP policies | *Do Not Inspect* on a list |
| **Menlo Security** | Web Policy → SSL Inspection → Exceptions | *Bypass* |

---

## 4. Monitored Non-AI URL Endpoints

`request_path` is a Python-style regex.

### 4.1 Collaboration Message Endpoints

| Application | Friendly URL | Pattern (regex) |
|---|---|---|
| Slack | `https://{workspace}.slack.com/api/chat.postMessage` | `[\w-]+\.slack\.com/api/chat\.postMessage` |
| MS Teams Web | `https://teams.microsoft.com/api/chatsvc/amer/v1/users/ME/conversations/{id}/messages` | `teams\.microsoft\.com/api/chatsvc/amer/v1/users/ME/conversations/.+/messages` |
| MS Teams Web (ALT) | `https://teams.cloud.microsoft/api/chatsvc/amer/v1/users/ME/conversations/{id}/messages` | `teams\.cloud\.microsoft/api/chatsvc/amer/v1/users/ME/conversations/.+/messages` |

The agent extracts message text from the JSON body (including `properties.subject`, `properties.title`, `properties.importance`) and any embedded file metadata from `properties.files`.

### 4.2 Collaboration File Upload Endpoints

| Application | Friendly URL | Pattern (regex) |
|---|---|---|
| Slack App & Web File Upload | `https://files.slack.com/upload/v1/{id}` | `files\.slack\.com/upload/v1/[\w-]+` |

Files uploaded to Slack are extracted (OCR / PDF / DOCX / XLSX / plain text) before policy evaluation.

---

## 5. Per-OS Application Exclusions

| Application | macOS exclusions | Windows exclusions | Notes |
|---|---|---|---|
| **Slack** (`chat.postMessage`) | *(none)* | `msedge.exe`, `chrome.exe` | Web traffic via Edge/Chrome is captured by the Quilr browser extension instead. The Slack desktop client (not in the exclusion list) is captured by the endpoint agent. |
| **Slack File Upload** (`files.slack.com/upload/v1/...`) | *(none)* | *(none)* | **Special case** — both lists are empty, so every process on every platform is intercepted, including Edge and Chrome on Windows. |
| **MS Teams Web** + **ALT** | *(none)* | `msedge.exe`, `chrome.exe` | Web traffic via Edge/Chrome captured by browser extension. Teams desktop client captured by endpoint agent. |

> **Operational takeaway:** Slack file uploads are intercepted from **every** browser and app on every OS — there is no fall-through to the browser extension for that rule. If a Windows user uploads a file to Slack via Chrome, the endpoint agent captures it.

---

## 6. Configuration Source of Truth

| Field | Value |
|---|---|
| Source name | `agent-interceptor` |
| Source type | `agent` |
| Configuration ID | `285` |
| Tenant | `442e052d-4c60-4cdc-961e-bc9db74a40ca` |
| Version | `64` |
| Created | `2026-02-04T13:28:36 UTC` |
| Last updated | `2026-05-11T07:59:01 UTC` |
| Active | `true` |

When the version above bumps, fetch the latest config from the Quilr control plane and regenerate this document.

---

## 7. Validation

### 7.1 Confirm a URL is being intercepted

On a macOS test endpoint with the agent installed:

```bash
sudo log stream --predicate 'subsystem == "ai.quilr.endpoint"' --info \
  | grep -i 'intercepted\|matched\|slack\|teams'

# In the Slack desktop client, send a short message to a test channel.
# A 'matched' entry should appear within seconds.
```

### 7.2 Confirm a host is reachable and not externally MITM-d

```bash
# Leaf cert issuer should be the real provider CA (DigiCert / Let's Encrypt /
# Microsoft Azure RSA TLS Issuing CA) — NOT your corporate proxy CA.
openssl s_client -connect slack.com:443 -servername slack.com </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer

openssl s_client -connect teams.microsoft.com:443 -servername teams.microsoft.com </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer
```

If the issuer line shows your network proxy's CA, your upstream proxy is decrypting that host — add the host from §3 to the proxy's bypass list.

### 7.3 Confirm Windows browser exclusions are working

1. Open Microsoft Edge → web Slack → send a message. The endpoint agent should **not** capture it (the browser extension does).
2. Repeat in the **Slack desktop client** — the endpoint agent **must** capture it.
3. Upload a file in Edge to Slack — the endpoint agent **must** capture it (file upload has no Edge/Chrome exclusion).

---

## 8. Change Management

- **Adding a URL:** update the `agent-interceptor` source in the Quilr control plane, increment `version`, bump the version line in this document and re-run the generator.
- **Removing a URL:** confirm with policy and compliance owners.
- **Browser exclusions:** toggle `msedge.exe` / `chrome.exe` in `excluded_apps.win` per rule. Section 5 must be updated.
- **Distribution:** ship this guide alongside the Jamf deployment bundle and republish on any source-config version change.

---

*End of document — Quilr AI | Adapt AI Securely*