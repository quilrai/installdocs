---
title: PAC (Proxy Auto-Config) — Optional
sidebar_label: PAC Configuration
---

# PAC (Proxy Auto-Config) — Optional

PAC is **only relevant** if your environment **already** uses a Proxy Auto-Config file to route traffic through an existing **web filter / SWG / forward proxy**. In that case the Quilr Endpoint Agent has to share the routing path with that stack and you need to either:

> **Common stacks that use PAC** — if you run any of these, PAC is probably already in your fleet's config:
> **Zscaler** (ZIA / ZPA) · **Netskope** · **Forcepoint** (ONE / Web Security) · **Symantec / Broadcom WSS / Edge SWG (ProxySG)** · **Cisco** (Umbrella SIG / Secure Web Appliance / WSA) · **Palo Alto Networks** (Prisma Access / NGFW) · **McAfee / Skyhigh SWG** · **Check Point** (Harmony Connect / Quantum) · **iboss** · **Menlo Security** · **Cloudflare Gateway** · **Microsoft Defender for Cloud Apps / Edge for Business** · **Akamai ETP** · **on-prem Squid / nginx forward proxy / Blue Coat / Trend Micro IWSVA**.
>
> If your stack isn't listed but it ships a `.pac` file or asks browsers for an "automatic proxy configuration URL", treat it as PAC-based.

For those stacks the choices are:

- **Point the OS at Quilr's hosted PAC** (only if you don't already publish a PAC file), or
- **Merge** Quilr's routing rules into your existing PAC.

> **If you do *not* already use a PAC file, skip this page entirely.** The Quilr agent's on-device interception layers — **WinDivert filter driver** on Windows and **Network Extension** on macOS — capture the right traffic without any system proxy / PAC at all. Adding a PAC where one isn't needed only introduces extra failure modes.

---

## Quilr hosted PAC

| Artefact | URL |
|---|---|
| Quilr PAC | `https://discover.quilrai.dev/pac/<TENANT-ID>` |

Replace `<TENANT-ID>` with the tenant identifier from **Quilr support** (`support@quilr.ai`). The file is a standard `application/x-ns-proxy-autoconfig` document containing one `FindProxyForURL(url, host)` function — the same shape every browser and OS understands.

The Quilr PAC sends **monitored AI + collaboration hosts** through the local Quilr agent's listening port and everything else **DIRECT**. Fetch it to inspect:

```bash
curl -fsSL https://discover.quilrai.dev/pac/<TENANT-ID> | head -40
```

---

## Choosing a path

| Situation | What to do |
|---|---|
| You do **not** currently use a PAC file | Skip PAC. Deploy the agent normally — its WFP / Network Extension layer handles interception. |
| You currently use a PAC file but **no existing web filter** depends on it | **Option A** — point the OS / browser proxy auto-config URL at `https://discover.quilrai.dev/pac/<TENANT-ID>` directly. |
| You currently use a PAC file **and** an upstream web filter / SWG that depends on its routing | **Option B** — **merge** Quilr's rules into your existing PAC (never replace it — you'd lose the upstream-SWG routing). |

---

## Option A — Use the Quilr-hosted PAC directly

Point the OS / browser proxy auto-config setting at:

```
https://discover.quilrai.dev/pac/<TENANT-ID>
```

### Windows (Intune)

**Devices → Configuration → Create → Settings Catalog** → search **"Proxy"** → enable **"Configure proxy server settings"** → set:

- **Proxy server type**: *Automatic proxy configuration*
- **Setup script address**: `https://discover.quilrai.dev/pac/<TENANT-ID>`

Or via Edge's *ProxySettings* policy (per-browser): set `ProxySettings.ProxyMode = "pac_script"` and `ProxySettings.ProxyPacUrl` to the same URL.

### macOS (Custom Configuration Profile via Intune / Jamf / Kandji)

Upload a `.mobileconfig` with a `com.apple.proxy.AutoConfig.url` payload setting `ProxyAutoConfigURLString` to the Quilr PAC URL:

```xml
<dict>
    <key>PayloadType</key>
    <string>com.apple.proxy.AutoConfig.url</string>
    <key>PayloadIdentifier</key>
    <string>ai.quilr.proxy.pac</string>
    <key>PayloadDisplayName</key>
    <string>Quilr Proxy Auto-Config</string>
    <key>PayloadUUID</key>
    <string>00000000-0000-0000-0000-000000000000</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
    <key>ProxyAutoConfigEnable</key>
    <true/>
    <key>ProxyAutoConfigURLString</key>
    <string>https://discover.quilrai.dev/pac/&lt;TENANT-ID&gt;</string>
</dict>
```

Deploy it via your MDM the same way you deploy other custom profiles (Device channel).

### Manual (single device)

- **Windows** — *Settings → Network → Proxy → Use setup script*, paste the Quilr PAC URL.
- **macOS** — *System Settings → Network → \<active interface\> → Details → Proxies → Automatic Proxy Configuration*, paste the Quilr PAC URL.

---

## Option B — Merge Quilr's rules into your existing PAC

If your existing PAC is doing real work (routing internal hosts DIRECT, sending corporate traffic through a SWG, handling captive portals, etc.), you must **keep your file as the source of truth** and add Quilr's routing into it. Pointing the OS at the Quilr PAC instead would silently drop every routing rule your SWG depends on.

### Step 1 — Fetch the Quilr PAC and understand its rules

```bash
curl -fsSL https://discover.quilrai.dev/pac/<TENANT-ID> -o /tmp/quilr.pac
less /tmp/quilr.pac
```

You'll see a `FindProxyForURL(url, host)` function that pattern-matches the monitored hosts (chatgpt.com, claude.ai, etc.) and returns `PROXY <quilr-local-listener>; DIRECT` for them.

### Step 2 — Merge with your existing PAC

The skeleton below shows how to call your existing logic **first** (so corporate / SWG routing keeps working) and **fall through** to Quilr's routing for monitored hosts:

```javascript
function FindProxyForURL(url, host) {
    // ─── 1. Your existing routing — corporate internals stay DIRECT
    if (isPlainHostName(host))                       return "DIRECT";
    if (shExpMatch(host, "*.corp.example.com"))      return "DIRECT";
    if (shExpMatch(host, "10.*"))                    return "DIRECT";

    // ─── 2. Quilr — monitored AI + collaboration hosts go through the
    //     local Quilr agent listener (replace <PORT> with the value
    //     embedded in the Quilr PAC you fetched in Step 1).
    var quilrHosts = [
        "chatgpt.com",     "*.oaiusercontent.com",
        "claude.ai",       "api.anthropic.com",
        "*.openrouter.ai", "api.individual.githubcopilot.com",
        "*.deepseek.com",  "kimi.com",
        "api.groq.com",
        "graph.meta.ai",   "meta.ai",
        "gemini.google.com",
        "substrate.office.com", "substrate.svc.cloud.microsoft",
        "*.slack.com",     "files.slack.com",
        "teams.microsoft.com", "teams.cloud.microsoft"
        /* keep this in sync with /reference/url-exceptions-ai */
    ];
    for (var i = 0; i < quilrHosts.length; i++) {
        if (shExpMatch(host, quilrHosts[i])) {
            return "PROXY 127.0.0.1:<PORT>; DIRECT";
        }
    }

    // ─── 3. Default — your existing upstream SWG / forward proxy
    return "PROXY swg.us.example.com:80; DIRECT";
}
```

### Step 3 — Validate before rolling out

```bash
# Quick smoke test with a JS engine
node -e "
const fn = require('fs').readFileSync('/path/to/merged.pac', 'utf8');
function isPlainHostName(h) { return h.indexOf('.') === -1; }
function shExpMatch(h, p) {
  return new RegExp('^' + p.replace(/\\./g,'\\\\.').replace(/\\*/g,'.*') + '$').test(h);
}
eval(fn);
console.log('chatgpt.com →', FindProxyForURL('https://chatgpt.com/', 'chatgpt.com'));
console.log('intranet →', FindProxyForURL('http://intranet/', 'intranet'));
console.log('example.org →', FindProxyForURL('https://example.org/', 'example.org'));
"
```

Expected: monitored hosts return `PROXY 127.0.0.1:<PORT>; DIRECT`, internal hosts return `DIRECT`, everything else hits your existing upstream.

---

## SWG SSL-bypass note

The PAC routing only addresses **which** path the traffic takes — it does *not* prevent an upstream SWG from re-decrypting `quilr-extensions.quilr.ai`, `discover.quilrai.dev`, or any monitored AI host. Make sure those hosts are also on the SWG's **SSL-bypass / Do Not Decrypt** list:

- [URL Exception List — AI Apps](/reference/url-exceptions-ai)
- [URL Exception List — Non-AI Apps](/reference/url-exceptions-nonai)

If the SWG re-signs the leaf cert, the Quilr agent's pinning will fail and interception will not work — regardless of how the PAC routes the traffic.

---

## When PAC fails to load

```
# Windows
curl -fsSL https://discover.quilrai.dev/pac/<TENANT-ID> -o nul -w "%{http_code}\n"

# macOS
curl -fsSL https://discover.quilrai.dev/pac/<TENANT-ID> -o /dev/null -w "%{http_code}\n"
```

| Result | Cause | Fix |
|---|---|---|
| `200` | Path works | Inspect the body and confirm `FindProxyForURL` is present |
| `404` | Wrong tenant ID | Confirm with Quilr support and re-push |
| `Timeout` / `Could not resolve host` | Firewall / DNS blocking `discover.quilrai.dev` | Allowlist — see the prerequisites checklist |
| `SSL handshake error` | An upstream SWG is decrypting `discover.quilrai.dev` | Add the host to the SWG SSL-bypass list |
