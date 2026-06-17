---
title: URL Exception List — AI Apps
description: Monitored AI hosts (ChatGPT, Claude, Gemini, etc.) — for SWG SSL-bypass.
---

# Quilr Endpoint Agent — Web Proxy / SWG Exception List (AI Apps)

**SSL-inspection bypass list for AI assistants and GenAI file-upload endpoints**
*Version 2026.05.11 — derived from `agent-interceptor` config (id 285, version 64)*

> Companion document: *Quilr-Endpoint-Agent-URL-Exception-List-NonAI-Apps* covers Slack, MS Teams, and other non-AI collaboration apps.

---

## 1. Why This List Exists

The Quilr Endpoint Agent performs **on-device TLS interception** of outbound traffic to a curated list of AI assistants and GenAI file-upload endpoints. It extracts prompt content and uploaded file content (after OCR / PDF / DOCX / XLSX / plaintext extraction), then ships structured events to the Quilr control plane for policy.

If your environment already runs a secure web gateway or CASB — **Netskope**, **Zscaler ZIA**, **Cisco Umbrella SIG / Secure Web Appliance**, **Palo Alto Prisma Access**, **Forcepoint ONE**, **Symantec/Broadcom WSS / Edge SWG (ProxySG)**, **McAfee/Skyhigh SWG**, **Check Point Harmony**, **iboss**, **Cloudflare Gateway**, **Menlo**, etc. — those products also terminate and re-sign TLS for the same hosts. **Two decryptors in the same path do not coexist.** When the upstream SWG presents its own CA, the Quilr agent sees an unexpected leaf certificate, pinning checks fail, request signatures break, and the chain fails closed.

> **The fix:** add every host in §3 to the SWG's **SSL/TLS inspection bypass** (a.k.a. "Do Not Decrypt", "SSL exception", "URL exemption", "Bypass Inspection") policy. Traffic still flows through the SWG — but **end-to-end encrypted** between endpoint and destination. Quilr decrypts on the host, captures the prompt/file, re-encrypts before packets leave the device.

For interception to function correctly, every URL listed here must:

1. Be **reachable** from the endpoint (not blocked by SWG URL filtering, firewall, ZTNA, or DNS filter).
2. Be **bypassed from SSL/TLS inspection** on every SWG / proxy / CASB in the path.
3. Reach the endpoint via the same path the user's browser / native app uses. Split-tunnel routes that bypass the agent will not be observed.

---

## 2. How to Use This List

| Audience | Action |
|---|---|
| **Netskope admin** | Policies → Real-time Protection → SSL Decryption → create a "Do Not Decrypt" rule scoped to the §3 domains. See §3.1. |
| **Zscaler ZIA admin** | Policy → SSL Inspection → add a "Do Not Inspect" rule matching a URL Category that contains the §3 hosts. See §3.2. |
| **Other SWG / proxy admin** | Add §3 domains to your product's "SSL bypass" feature — see §3.3 for the per-vendor cheat sheet. |
| **Firewall / ZTNA admin** | Allow outbound 443 to every host in §3 from the macOS fleet. |
| **EDR / Mac admin** | If a host-based content filter sits in front of Quilr's network extension, allow-list the Quilr agent process. |
| **Compliance / DLP owner** | Use §4 to evidence which AI endpoints are actively monitored for prompt + file content by Quilr on the device. |
| **Quilr admin** | Regenerate this guide when the `agent-interceptor` config version changes. |

---

## 3. AI-App Domains to Allow + Bypass from SSL Inspection

| # | Host | Purpose |
|---|---|---|
| 1 | `chatgpt.com` | ChatGPT chat completions |
| 2 | `*.oaiusercontent.com` | ChatGPT file uploads (raw downloads) |
| 3 | `claude.ai` | Claude chat + file uploads |
| 4 | `api.anthropic.com` | Claude Code / Anthropic API |
| 5 | `openrouter.ai`, `api.openrouter.ai` | OpenRouter chat completions |
| 6 | `api.individual.githubcopilot.com` | GitHub Copilot Web + plugin |
| 7 | `genspark.ai`, `www.genspark.ai` | Genspark agent + image upload |
| 8 | `*genspark*.blob.core.windows.net` | Genspark file upload (Azure blob) |
| 9 | `chat.deepseek.com` | DeepSeek chat + file upload |
| 10 | `kimi.com` | Kimi chat completions |
| 11 | `sp.replit.com` | Replit AI prompts |
| 12 | `ingest.app.coframe.com` | Replit file-upload telemetry |
| 13 | `api.groq.com` | Groq chat completions |
| 14 | `graph.meta.ai`, `meta.ai`, `gateway.meta.ai` | Meta AI Web GraphQL + websocket |
| 15 | `rupload.meta.ai` | Meta AI Web file upload |
| 16 | `gemini.google.com` | Gemini Web chat |
| 17 | `push.clients6.google.com` | Gemini Web file upload |
| 18 | `substrate.office.com`, `substrate.svc.cloud.microsoft` | MS Copilot (Corporate) chat + image upload |
| 19 | `*.sharepoint.com` | MS Copilot file upload (SharePoint personal drive) |

> **Wildcards.** Hosts shown with `*` are matched via regex in the agent and must be expressed as a wildcard rule (or each subdomain enumerated) in your proxy/firewall.

### 3.1 Configuring the bypass in Netskope

1. Sign in to the Netskope tenant admin console.
2. Navigate to **Policies → Real-time Protection → SSL Decryption**.
3. Click **New Policy** (top-right).
4. **Source**: scope to the user group / OU / device group running the Quilr Endpoint Agent.
5. **Destination**: Custom Category named `Quilr Agent Bypass — AI Apps` containing every host from §3 (wildcards for `*.oaiusercontent.com`, `*.sharepoint.com`, `*genspark*.blob.core.windows.net`).
6. **Action**: **Do Not Decrypt**.
7. **Set Order**: place this rule **above** any "Decrypt All" rule.
8. **Save** and **Apply Changes**.
9. Validate via §7.2 — the leaf-cert issuer for `chatgpt.com` should be the real provider CA, not "Netskope Certificate Authority".

### 3.2 Configuring the bypass in Zscaler Internet Access (ZIA)

1. Sign in to the ZIA admin portal.
2. **Administration → Resources → URL Categories → Add URL Category**. Name `Quilr Agent Bypass — AI Apps`; paste every host from §3 as Custom URLs (Zscaler accepts wildcards like `.oaiusercontent.com`, `.sharepoint.com`).
3. **Policy → SSL Inspection → SSL Inspection Policy → Add Rule**: rule name `Quilr Agent AI — Do Not Inspect`; criteria `URL Categories = Quilr Agent Bypass — AI Apps`; scope to the macOS fleet.
4. **Action**: **Do Not Inspect**.
5. **Order**: drag the rule **above** any "Inspect All" rule.
6. **Save** and **Activate**.
7. (Optional) If you use **Cloud App Control** with categories like *AI & ML Applications* or *Generative AI*, add an explicit allow for the §3 hosts there as well — otherwise Cloud App Control can block them before the SSL bypass rule fires.
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

If your vendor is not listed, search the product docs for "SSL decryption bypass", "do not inspect", "TLS exception", or "pass-through" — that's the feature you want.

---

## 4. Monitored AI URL Endpoints by Category

`request_path` is a Python-style regex. The "Friendly URL" column shows the human-readable shape; the "Pattern" column reproduces the exact regex from config so it can be cross-referenced with audit logs.

### 4.1 AI Chat / Prompt Endpoints

| Application | Friendly URL | Pattern (regex) |
|---|---|---|
| ChatGPT | `https://chatgpt.com/backend-api/f/conversation` | `chatgpt\.com/backend\-api/f/conversation(?:\?\|$)` |
| Claude | `https://claude.ai/api/organizations/{org}/chat_conversations/{conv}/completion` | `claude\.ai/api/organizations/[\w-]+/chat_conversations/[\w-]+/completion` |
| Claude Code (Anthropic API) | `https://api.anthropic.com/v1/messages` | `api\.anthropic\.com/v1/messages` |
| OpenRouter | `https://(api.)?openrouter.ai/api/v1/chat/completions` | `(api\.)?openrouter\.ai/api/v1/chat/completions` |
| GitHub Copilot Web | `https://api.individual.githubcopilot.com/github/chat/threads/{id}/messages` | `api\.individual\.githubcopilot\.com/github/chat/threads/[\w-]+/messages` |
| GitHub Copilot Plugin | `https://api.individual.githubcopilot.com/chat/completions` | `api\.individual\.githubcopilot\.com/chat/completions` |
| GitHub Copilot Plugin (ALT) | `https://api.individual.githubcopilot.com/responses` | `api\.individual\.githubcopilot\.com/responses` |
| Genspark | `https://genspark.ai/api/agent/ask` *(and `/ask_proxy`)* | `genspark\.ai/api/agent/ask(_proxy)?` |
| DeepSeek | `https://chat.deepseek.com/api/v0/chat/completion` | `chat\.deepseek\.com/api/v0/chat/completion` |
| Kimi | `https://kimi.com/api/chat/{id}/completion/stream` | `kimi\.com/api/chat/\w+/completion/stream` |
| Replit | `https://sp.replit.com/v1/t` | `sp\.replit\.com/v1/t` |
| Groq | `https://api.groq.com/openai/v1/chat/completions` | `api\.groq\.com/openai/v1/chat/completions` |
| Meta AI Web | `https://graph.meta.ai/graphql` | `graph\.meta\.ai/graphql` |
| Meta AI Web (ALT) | `https://meta.ai/api/graphql` | `meta\.ai/api/graphql` |
| Meta AI Web (ALT-2) | `wss://gateway.meta.ai/ws/clippy` | `gateway\.meta\.ai/ws/clippy` |
| Gemini Web | `https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate` | `gemini\.google\.com(?:/u/2)?/_/BardChatUi/data/assistant\.lamda\.BardFrontendService/StreamGenerate` |
| MS Copilot (Corporate) | `https://substrate.office.com/m365Copilot/Chathub/{user}@{tenant}` | `substrate\.office\.com/m365Copilot/Chathub/[\w\d-]+@[\w\d-]+` |
| MS Copilot (Corporate, ALT) | `https://substrate.svc.cloud.microsoft/m365Copilot/Chathub/{user}@{tenant}` | `substrate\.svc\.cloud\.microsoft/m365Copilot/Chathub/[\w\d-]+@[\w\d-]+` |

### 4.2 AI File Upload Endpoints

These endpoints carry binary file uploads. The agent runs OCR / PDF / DOCX / XLSX / plain-text extraction on the file body before evaluating policy.

| Application | Friendly URL | Pattern (regex) |
|---|---|---|
| ChatGPT Upload | `{bucket}.oaiusercontent.com/files/{id}/raw` | `[\w-]+\.oaiusercontent\.com/files/[\w-]+/raw(?:\?\|$)` |
| Claude App File Upload | `claude.ai/api/organizations/{org}/convert_document` | `claude\.ai/api/organizations/[\w-]+/convert_document` |
| Claude Web File Upload | `claude.ai/api/{seg}/upload` | `claude\.ai/api/[\w-]+/upload` |
| Claude Web File Upload (ALT) | `claude.ai/api/organizations/{org}/conversations/{conv}/{file}/upload-file` | `claude\.ai/api/organizations/[\w-]+/conversations/[\w-]+/[\w-]+/upload-file` |
| Gemini Web File Upload | `push.clients6.google.com/upload` | `push\.clients6\.google\.com/upload` |
| Meta AI Web File Upload | `rupload.meta.ai/gen_ai_document_gen_ai_tenant/{id}` | `rupload\.meta\.ai/gen_ai_document_gen_ai_tenant/[\w-]+(\?.*)?` |
| DeepSeek File Upload | `chat.deepseek.com/api/v0/file/upload_file` | `chat\.deepseek\.com/api/v0/file/upload_file` |
| Genspark Image Upload | `genspark.ai/api/agent/ask` *(image payload)* | `genspark\.ai/api/agent/ask(_proxy)?` |
| Genspark File Upload (w/ prompt) | `genspark.ai/api/agent/ask` *(private_file payload)* | `genspark\.ai/api/agent/ask(_proxy)?` |
| Genspark File Upload (blob) | `{tenant}.genspark.{*}.blob.core.windows.net/personal/{user}/.../file_upload/{id}` | `[\w-]*genspark[\w-]*\.blob\.core\.windows\.net/personal/[\w-]+/[\w\d-]+/file_upload/[\w\d-]+(\?.*)?` |
| Genspark HEIC Convert | `www.genspark.ai/convert-heic` | `www\.genspark\.ai/convert-heic` |
| MS Copilot Image Upload | `substrate.office.com/m365Copilot/UploadFile` | `substrate\.office\.com/m365Copilot/UploadFile` |
| MS Copilot Image Upload (ALT) | `substrate.svc.cloud.microsoft/m365Copilot/UploadFile` | `substrate\.svc\.cloud\.microsoft/m365Copilot/UploadFile` |
| MS Copilot File Upload (SharePoint UploadSession) | `{tenant}.sharepoint.com/personal/{user}/_api/v2.0/drive/items/{id}/uploadSession` | `[\w-]+\.sharepoint\.com/personal/[\w_]+/_api/v2\.0/drive/items/[\w\d]+/uploadSession` |
| Replit File Upload (telemetry) | `ingest.app.coframe.com/ingest/v2/batched_events/{id}/` | `ingest\.app\.coframe\.com/ingest/v2/batched_events/[\w\d-]+/?` |

---

## 5. Per-OS Application Exclusions

Each rule has an `excluded_apps` field that tells the agent not to intercept traffic when the source process matches a listed binary.

| Platform | Excluded processes | Effect |
|---|---|---|
| **macOS** | *(none — empty for every AI rule)* | The Quilr Network Extension intercepts AI traffic regardless of which browser or native app initiated it. |
| **Windows** | `msedge.exe`, `chrome.exe` *(on the majority of AI rules)* | Traffic from Microsoft Edge and Google Chrome is not intercepted by the endpoint agent on Windows — those browsers are covered by the Quilr browser extension instead, avoiding double-capture. |

### AI rules with no Windows exclusions (intercept all processes on both OS)

- **Genspark** (`genspark.ai/api/agent/ask(_proxy)?` — base rule; upload variants *do* exclude Edge/Chrome)
- **Groq** (`api.groq.com/openai/v1/chat/completions`)
- **Meta AI Web (ALT)** (`meta.ai/api/graphql`)
- **Meta AI Web (ALT-2)** (`gateway.meta.ai/ws/clippy`)

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
  | grep -i 'intercepted\|matched'

# In the browser, navigate to chatgpt.com and send a short prompt.
# A 'matched' entry should appear within seconds.
```

### 7.2 Confirm a host is reachable and not externally MITM-d

```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  https://api.anthropic.com/v1/messages -X POST

# Leaf cert issuer should be the real provider CA (Let's Encrypt /
# DigiCert / WE1) — NOT your corporate proxy CA.
openssl s_client -connect chatgpt.com:443 -servername chatgpt.com </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer
```

If the issuer line shows your network proxy's CA, your upstream proxy is decrypting that host — add the host from §3 to the proxy's bypass list.

### 7.3 Confirm Windows browser exclusions are working

1. Open Microsoft Edge → ChatGPT → submit a prompt.
2. Quilr Endpoint Agent log shows **no** interception event (the browser extension captures it instead).
3. Repeat in Chrome — same expected result.
4. Repeat in Firefox or a non-browser app — an interception event **must** appear.

---

## 8. Change Management

- **Adding a URL:** update the `agent-interceptor` source in the Quilr control plane, increment `version`, bump the version line in this document and re-run the generator.
- **Removing a URL:** confirm with policy and compliance owners before retiring an endpoint, since dashboards may depend on the historical app name.
- **Browser exclusions:** toggle `msedge.exe` / `chrome.exe` in `excluded_apps.win` per rule. Section 5 must be updated.
- **Distribution:** ship this guide alongside the Jamf deployment bundle and republish on any source-config version change.

---

*End of document — Quilr AI | Adapt AI Securely*