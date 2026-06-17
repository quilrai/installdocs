---
title: ZCC Coexistence
description: Run the Quilr endpoint proxy (quilrai-proxy) alongside Zscaler Client Connector without breaking the Zscaler tunnel.
sidebar_label: ZCC Coexistence
---

# Quilr Endpoint Proxy × Zscaler Client Connector — Coexistence Guide

A coexistence guide for ZCC administrators — run `quilrai-proxy` alongside ZCC without breaking the Zscaler tunnel.

---

## 1. Purpose & audience

This guide explains how to deploy the **Quilr endpoint proxy** (`quilrai-proxy`) on endpoints that already run **Zscaler Client Connector (ZCC)**, so that Quilr applies endpoint-side data-loss prevention (DLP) and policy **without breaking your existing ZCC tunnel to the Zscaler cloud (ZEN)**. It is written for the **ZCC administrator**: it assumes you know Zscaler concepts (Z-Tunnel 1.0/2.0, Forwarding Profiles, App Profiles/PAC, ZIA/ZPA, ZEN) and assumes **no** prior knowledge of Quilr internals. Every Quilr-side requirement that affects you is called out explicitly.

:::note Listen ports used in this guide
Quilr's proxy listens on `127.0.0.1:24080` (HTTP) and `127.0.0.1:24443` (HTTPS). These ports are pinned by the Quilr agent at launch (chosen to avoid collisions with other local proxies such as Fiddler, mitmproxy, or Docker). Use `24080` / `24443` wherever a Quilr proxy port is referenced in this guide.
:::

---

## 2. Why Quilr must inspect before ZCC tunnels

ZCC's job is to take endpoint traffic and tunnel it (encrypted) to a **Zscaler Enforcement Node (ZEN)**. **Once ZCC has wrapped traffic into its tunnel, the payload is opaque** — it has left the endpoint inside Zscaler's encrypted channel and cannot be inspected locally for DLP.

Therefore **Quilr must sit in front of ZCC, locally on the endpoint.** Quilr terminates the application's TLS on the device, inspects the decrypted content, applies policy (allow / warn / block), and then hands the (re-encrypted) traffic onward so that **ZCC still delivers it to ZEN exactly as before**. The Zscaler tunnel guarantee is preserved; Quilr simply adds an inspection step ahead of it.

```
┌────┐  inspect on device  ┌──────────────┐  tunnel unchanged  ┌─────┐  ZEN  ┌──────────┐
│App │ ──── DLP/policy ──► │ quilrai-proxy│ ────────────────► │ ZCC │ ────► │ Internet │
└────┘                     └──────────────┘                    └─────┘       └──────────┘
```

---

## 3. Mandatory prerequisite — whitelist your ZCC tunnel IPs

:::danger Required in all three approaches
You **must** provide your ZCC tunnel / egress IP address(es) and ranges to the Quilr team (the IPs/CIDRs that `ZSATunnel` / ZCC uses to reach ZEN — your ZEN gateway ranges and any related Zscaler egress ranges for your cloud). Quilr will **explicitly exclude (whitelist) those destinations from interception**.

**Why this is non-negotiable:** Quilr's active interception captures outbound traffic on the endpoint. If ZCC's own tunnel traffic to ZEN is *not* excluded, Quilr may try to intercept the very packets ZCC uses to reach the cloud. That causes **interception loops, tunnel timeouts, and can drive ZCC into fail-closed mode** (blocking all traffic). Excluding the tunnel IPs guarantees ZCC's path to ZEN is never touched.
:::

### What Quilr already excludes out of the box (so you don't need to ask for these)

| Range | What it is |
|---|---|
| `165.225.0.0/16` | Zscaler's primary IP block |
| `100.64.0.0/10` | ZCC carrier-grade NAT / control-plane range |
| `167.103.0.0/16` | A ZEN gateway range observed in the field |

### What you must supply

These vary per customer / Zscaler cloud and Quilr cannot guess them:

- Your specific **ZEN gateway IPs / ranges** for your Zscaler cloud (e.g. your data-center VIPs).
- Any **additional Zscaler or VPN egress ranges** your endpoints use that fall outside the built-in ranges above.

:::tip How to find them
**Authoritative source (recommended).** Use Zscaler's published Cloud Enforcement Node ranges at `https://config.zscaler.com/zscaler.net/cenr`. On that page, select **your org's ZIA cloud** (e.g. `zscaler.net`, `zscalerone.net`, `zscalertwo.net`, `zscloud.net`, etc. — pick the one configured for your organization) to get the authoritative ZEN/gateway IP ranges. Share the relevant ranges (and any data centers you egress through) with Quilr.

**Cross-check on the endpoint.** While the ZCC tunnel is active, inspect the connections owned by the `ZSATunnel` process (Z-Tunnel 1.0) or ZCC's tunnel process and note the remote IPs/ports it reaches.

**Re-confirm after any Zscaler cloud / data-center change.**
:::

This whitelisting reminder is repeated at the end of each approach below.

---

## 4. Key concepts & glossary

| Term | Meaning |
|---|---|
| `quilrai-proxy` | The Quilr endpoint proxy process. Listens on `127.0.0.1:24080` (HTTP) and `127.0.0.1:24443` (HTTPS). Performs TLS MITM, DLP, and policy on the endpoint. (Process name: `quilrai-proxy.exe` on Windows, `quilrai-proxy` on macOS.) |
| **Active (kernel-level) interception** | Quilr capturing outbound traffic transparently, before the app's packets leave the host — **WinDivert** on Windows, a **Network Extension (transparent proxy provider)** on macOS. No per-app proxy settings required. |
| **PAC-based routing** | Apps read a PAC file and send traffic to a proxy. Used here to point selected traffic at Quilr. |
| **System-proxy honoring** | Quilr reads the OS/system-proxy intent on a **per-connection** basis and routes accordingly, instead of forcing a single fixed upstream. (Windows behavior; no-op on macOS — see notes.) |
| **Dynamic upstream re-origination** | When Quilr intercepts a request that names a proxy (e.g. a `CONNECT` aimed at `127.0.0.1:9000`), Quilr inspects it and then **re-sends the request out through that same proxy** — so the app's original egress choice (e.g. "use the local Zscaler proxy") is preserved. Quilr never chains to its own listen ports (built-in self-loop guard). |
| **IP deny-list (exclusion list)** | The list of destination IPs/CIDRs Quilr will **not** intercept. This is where your ZCC tunnel/egress IPs go (see §3). |
| **Z-Tunnel 1.0 (Tunnel with Local Proxy)** | Older ZCC tunnel mode. Runs `ZSATunnel` as a **local HTTP-CONNECT proxy** on `127.0.0.1:9000`; apps reach it via the system proxy or a PAC URL. `ZSATunnel` maintains the tunnel to ZEN. |
| **Z-Tunnel 2.0** | Newer ZCC tunnel mode. **No local proxy listener.** A kernel-level **Packet Filter driver** intercepts egress from non-bypassed processes and tunnels it to ZEN. Can optionally enforce a system proxy (used here to point apps at Quilr). |
| **ZSATunnel** | The ZCC user-space process for Z-Tunnel 1.0's `:9000` local proxy and the tunnel to ZEN. |
| **ZEN / ZIA / ZPA** | Zscaler Enforcement Node (cloud gateway) / Internet Access / Private Access. |
| **Quilr root-CA trust** | Because Quilr terminates TLS on the endpoint (MITM) with per-domain certificates it generates, every endpoint must trust Quilr's root CA, or apps will see certificate errors. (Handled by Quilr deployment; see §7.) |

:::note macOS note
`system-proxy honoring` / `dynamic upstream re-origination` are **Windows behaviors**. On macOS, Quilr uses the Network Extension for active interception. macOS + ZCC coexistence specifics differ from the Windows flows below — confirm the macOS plan with the Quilr team before rollout.
:::

---

## 5. Quick chooser — which approach fits you

| Your situation | ZCC tunnel mode | Active interception? | Traffic scope | Approach |
|---|---|---|---|---|
| Simplest setup; ZCC keeps processing **all** traffic | Z-Tunnel 1.0 (local proxy on `:9000`) | **Required** | All traffic | **A — No-config** |
| Both Quilr and ZCC must process all traffic; you run Tunnel 2.0 | Z-Tunnel 2.0 | Optional | All traffic | **B — System-Proxy** |
| Only **selected** traffic (e.g. `claude.ai`) through Quilr | Z-Tunnel 1.0 | Optional | Selected traffic | **C — PAC (fallback)** |

:::tip Rule of thumb
Start with **A** if you're on Z-Tunnel 1.0 and want zero ZCC changes. Use **B** for Z-Tunnel 2.0. Use **C** only when you need selective scoping or when **B** isn't feasible / working.
:::

---

## 6. The three approaches

### Approach A — No-config (preferred / zero-touch)

**Summary.** Quilr's active interception watches ZCC's local proxy port (`127.0.0.1:9000`), captures app traffic *before* it reaches ZCC, performs DLP/MITM, then **dynamically detects** that the app's intended upstream was the local Zscaler proxy and **re-originates** the request out through that same `127.0.0.1:9000`. ZCC then tunnels to ZEN exactly as it always has. **No ZCC admin configuration is required.**

| | |
|---|---|
| **ZCC tunnel mode** | Z-Tunnel 1.0 (`ZSATunnel` local proxy on `:9000`) |
| **Active interception** | **Required** (WinDivert / Network Extension) |
| **Traffic scope** | All traffic ZCC processes |
| **ZCC admin steps** | None Quilr-specific (ZCC keeps its normal PAC / system-proxy → `:9000` setup) |

#### When to use
- You run Z-Tunnel 1.0 and want the simplest, lowest-touch deployment.
- You want ZCC to keep handling all egress, with Quilr inspecting in front of it.

#### When **NOT** to use
- You run Z-Tunnel 2.0 (no `:9000` local proxy exists) → use **Approach B**.
- ZCC's policy will not allow `quilrai-proxy` to reach the local `:9000` proxy (see condition below) → use **B**.

:::warning Condition (must be true)
ZCC must accept traffic originating from `quilrai-proxy` to its local `:9000` proxy. (When Quilr re-originates the request, the connection to `ZSATunnel:9000` is made by `quilrai-proxy`; ZCC must permit that local hop.) In standard Z-Tunnel 1.0 deployments this loopback hop is permitted; if your ZCC policy is unusually restrictive about which local processes may use `:9000`, validate this first.
:::

#### Request flow (HTTPS, Z-Tunnel 1.0)
```
┌────┐ CONNECT :9000  ┌──────────────┐  re-CONNECT  ┌──────────┐  DTLS  ┌─────┐
│App │ ─(captured)──► │ quilrai-proxy│ ──────────► │ ZSATunnel│ ─────► │ ZEN │ → example.com
└────┘                │ :24443 MITM+ │              │   :9000  │        └─────┘
                      │ DLP          │              └──────────┘
                      └──────────────┘
```

1. App resolves its proxy (system proxy or PAC) → decides to use the local Zscaler proxy `127.0.0.1:9000` and sends `CONNECT example.com:443`.
2. Quilr's active interception captures that loopback connection to `:9000` **before** it reaches `ZSATunnel`, and redirects it to `quilrai-proxy:24080`.
3. Quilr performs TLS MITM (per-domain cert), decrypts, and runs **DLP + policy** on the plaintext.
4. Quilr detects the app's original upstream was `127.0.0.1:9000` and **re-originates** the request: it sends its own `CONNECT example.com:443` to `127.0.0.1:9000` (`ZSATunnel`).
5. `ZSATunnel` accepts and tunnels to ZEN; ZEN reaches `example.com`.
6. Responses return the same way; the app is unaware Quilr was in the path.

#### Pros
- Zero ZCC admin changes; fastest to deploy.
- App's "use Zscaler" intent preserved end-to-end; ZCC tunnel untouched.

#### Cons
- Requires active interception (driver/extension; admin rights on Windows).
- Only applies to Z-Tunnel 1.0 (depends on the `:9000` local proxy existing).

:::warning Whitelist reminder
You must still supply your **ZEN/tunnel egress IPs** to Quilr for exclusion (§3) — otherwise Quilr may try to intercept `ZSATunnel`'s own path to ZEN and cause loops.
:::

---

### Approach B — System-Proxy based

**Summary.** ZCC **enforces Quilr as the system proxy** so all apps send their HTTP/HTTPS traffic to `quilrai-proxy` (`127.0.0.1:24080`). Quilr inspects, then makes a normal outbound connection that **ZCC's Z-Tunnel 2.0 Packet Filter driver tunnels to ZEN** transparently. Both Quilr and ZCC process all traffic.

| | |
|---|---|
| **ZCC tunnel mode** | Z-Tunnel 2.0 (Packet Filter driver) |
| **Active interception** | Optional (not required — ZCC's system-proxy enforcement points apps at Quilr directly) |
| **Traffic scope** | All traffic |
| **ZCC admin steps** | Configure the **Forwarding Profile** (below) |

#### When to use
- You run (or can move to) Z-Tunnel 2.0 and want both Quilr and ZCC to process all traffic.
- You prefer ZCC to push the proxy setting centrally rather than relying on Quilr's kernel interception.

#### When **NOT** to use
- You require only selected traffic through Quilr → use **Approach C**.
- You are on Z-Tunnel 1.0 with the `:9000` local proxy → **Approach A** is simpler.

#### ZCC admin steps (Forwarding Profile — Z-Tunnel 2.0)

These steps and labels are taken from a verified Quilr↔ZCC integration configuration. Confirm exact wording against your ZCC console version.

1. **Open the Forwarding Profile:** ZCC admin portal → **Administration → Client Connector → Forwarding Profile** → create/edit a profile (e.g. "Quilr Tunnel 2.0 Profile").
2. **Windows Driver Selection → Tunnel Driver Type:** set to **Packet Filter-Based**.

:::note
**Packet Filter-Based** is required. The Route-Based driver bypasses the Windows TCP/IP stack at a lower layer and interacts poorly with Quilr's interception.
:::

3. **Forwarding Profile Action for ZIA:** `On-Trusted Network = Tunnel`; **Tunnel version** = **Z-Tunnel 2.0**.
4. **Configure System Proxy Settings:**

| Field | Value |
|---|---|
| Proxy Action Type | **Enforce** |
| Automatically Detect Settings | ☐ Unchecked |
| PAC URL Location | ☐ Unchecked |
| Use Proxy Server for Your LAN | ☑ Checked |
| IP Address or Domain | `127.0.0.1` |
| Port | **`24080`** |

5. **Bypass Proxy Server for Local Addresses:** ☑ Checked (so loopback / RFC1918 / link-local don't loop back through Quilr).
6. **ZPA → On-Trusted Network:** **Tunnel** (ZPA continues to use ZCC's tunnel; unaffected).

After saving, ZCC pushes the proxy setting to endpoints. Verify on an endpoint:

```bat
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer
:: Expected: ProxyServer    REG_SZ    127.0.0.1:24080
```

#### Request flow (HTTPS, Z-Tunnel 2.0)
```
┌────┐ sys proxy :24080  ┌──────────────┐  direct TCP  ┌──────────────┐  tunnel  ┌─────┐
│App │ ────────────────► │ quilrai-proxy│ ───────────► │ ZCC PF driver│ ───────► │ ZEN │ → example.com
└────┘                   │ :24443 MITM+ │              │   (kernel)   │          └─────┘
                         │ DLP          │              └──────────────┘
                         └──────────────┘
```

1. App reads the enforced system proxy → sends `CONNECT example.com:443` to `127.0.0.1:24080`.
2. `quilrai-proxy` accepts, performs TLS MITM, runs **DLP + policy**.
3. Quilr makes a normal outbound TCP/TLS connection toward `example.com`.
4. **ZCC's Packet Filter driver intercepts** Quilr's outbound packets at the kernel layer and tunnels them to ZEN.
5. ZEN reaches `example.com`; responses return through the same path.

:::note Why active interception is optional here
Because ZCC itself sends apps to Quilr via the enforced system proxy, Quilr doesn't need WinDivert / Network Extension to capture them. You may still enable active interception to also catch apps that bypass the system proxy.
:::

#### Pros
- Cleanest, most deterministic deployment on Z-Tunnel 2.0.
- Central control via the ZCC Forwarding Profile; no Quilr-side kernel driver strictly required.

#### Cons
- Requires Z-Tunnel 2.0 and a Forwarding Profile change.
- Apps that ignore the system proxy won't be inspected unless active interception is also enabled.

:::warning Whitelist reminder
Supply your **ZEN/tunnel egress IPs** to Quilr for exclusion (§3), especially if you also enable active interception.
:::

---

### Approach C — PAC based (fallback)

**Summary.** Use a **PAC file** to send only **selected** traffic (e.g. `claude.ai`) to `quilrai-proxy:24080`; everything else continues through ZCC normally. Use this when you want selective scoping, or as a fallback when **Approach B** is not feasible or not working.

| | |
|---|---|
| **ZCC tunnel mode** | Z-Tunnel 1.0 |
| **Active interception** | Optional |
| **Traffic scope** | Selected traffic only (per PAC rules) |
| **ZCC admin steps** | App Profile / PAC + process bypass (below) |

#### When to use
- You want only specific domains/destinations inspected by Quilr.
- Approach B is not available or not working in your environment.

#### When **NOT** to use
- You want all traffic inspected → use **A** (Tunnel 1.0) or **B** (Tunnel 2.0).

#### ZCC admin steps (PAC + bypass)

:::note
The Forwarding Profile path in Approach B is verified; the **App Profile/PAC** and **process/application bypass** screens vary more across ZCC versions. The constructs below are described generically — match them to your console's actual labels.
:::

1. **Author/extend the PAC** so that target traffic resolves to Quilr and everything else keeps its normal ZCC routing. Conceptually:

```javascript
function FindProxyForURL(url, host) {
  // Send only the target app to Quilr:
  if (shExpMatch(host, "*.claude.ai") || shExpMatch(host, "claude.ai")) {
    return "PROXY 127.0.0.1:24080";
  }
  // Everything else: keep existing ZCC behavior
  return "PROXY 127.0.0.1:9000";  // ZSATunnel (Z-Tunnel 1.0), or your existing return
}
```

Publish this PAC the way your environment already distributes PAC (e.g. via the ZCC App Profile / PAC URL setting).

2. **Process-level bypass for `quilrai-proxy`:** if your environment restricts which processes may egress directly to the internet, you **must add a bypass/allow** for the `quilrai-proxy` process so it can reach the upstream after inspection. Use ZCC's **application/process bypass** construct for this. *(Exact menu label varies by ZCC version — confirm in your console.)*
3. *(Optional)* Enable Quilr active interception if you also want to catch non-PAC-aware apps for the selected destinations.

#### Request flow (HTTPS, selected domain)
```
SELECTED DOMAIN (matched by PAC):
┌──────────┐  PAC → :24080  ┌──────────────┐  upstream  ┌──────────┐
│ claude.ai│ ─────────────► │ quilrai-proxy│ ─────────► │ Internet │
└──────────┘                │ :24443 MITM+ │            └──────────┘
                            │ DLP          │
                            └──────────────┘

ALL OTHER APPS (unmatched):
┌──────────┐  unchanged ZCC route  ┌─────┐
│other apps│ ────────────────────► │ ZEN │ → Internet
└──────────┘                       └─────┘
```

1. PAC-aware app requests `https://claude.ai` → PAC returns `PROXY 127.0.0.1:24080` → app sends `CONNECT claude.ai:443` to Quilr.
2. `quilrai-proxy` performs TLS MITM, runs **DLP + policy**.
3. Quilr sends the request upstream; it reaches the internet via your environment's normal path (and ZCC where applicable).
4. All **non-matching** traffic skips Quilr entirely and follows its usual ZCC route.

#### Pros
- Surgical scoping — only the domains you choose are inspected.
- Minimal blast radius; easy to pilot a single app.

#### Cons
- Only covers PAC-aware apps for the matched destinations.
- Requires correct PAC authoring **and** the `quilrai-proxy` process bypass; easy to misconfigure.

:::warning Whitelist reminder
Even in selective mode, supply your **ZEN/tunnel egress IPs** to Quilr for exclusion (§3) if active interception is enabled.
:::

---

## 7. Cross-cutting requirements

These apply regardless of approach.

### 7.1 Quilr root-CA trust (required for TLS)

Quilr terminates TLS on the endpoint and presents per-domain certificates it generates. **Every endpoint must trust Quilr's root CA** (installed in the OS/browser trust store), or users will get certificate warnings/failures on inspected traffic. This is handled by the Quilr deployment/installer; as ZCC admin, just be aware it must be present before inspected traffic will work cleanly.

### 7.2 Avoiding interception loops

A loop occurs if Quilr intercepts traffic that is actually ZCC's own path to ZEN, or its own re-originated upstream. Quilr prevents loops by:

- **Excluding ZCC's processes** from interception (e.g. `ZSATunnel.exe`, `ZSAService.exe`, `ZSAUpdater.exe`, `ZSAUpm.exe`, `ZSATray.exe`, `ZSATrayManager.exe`) and excluding its own process (`quilrai-proxy`).
- **Excluding Zscaler IP ranges** (built-in: `165.225.0.0/16`, `100.64.0.0/10`, `167.103.0.0/16`) **plus the customer-supplied tunnel IPs** (§3).
- **A self-loop guard** that prevents Quilr from chaining to its own listen ports.

**Your responsibility:** supply the customer-specific **ZEN/tunnel egress IPs** (§3). The built-in process and range exclusions cover the rest.

### 7.3 The IP deny-list role

The deny-list (exclusion list) is the single most important coexistence control. Destinations on it are **never intercepted** — they pass straight through to ZCC. Your ZEN/tunnel IPs belong here. Re-confirm the list after any Zscaler cloud or data-center change.

---

## 8. Validation

Confirm **both Quilr and ZCC** are in the path.

### Confirm Quilr is running and listening

```bat
:: Windows
netstat -ano | findstr "24080 24443"
:: Expect quilrai-proxy listening on 127.0.0.1:24080 and :24443
```

### Confirm traffic is flowing through Quilr

- On an inspected site, the served certificate should chain to **Quilr's root CA** (view the cert in the browser).
- Quilr's traffic/DLP logs show the request (ask the Quilr team where logs surface for your build), and DLP prompts appear on test-sensitive content.

### Confirm traffic still reaches ZEN (ZCC intact)

- ZCC client UI shows the tunnel **connected/healthy**.
- Browse to your Zscaler **"Am I behind Zscaler?"** page (e.g. `ip.zscaler.com`) — it should still report your traffic as going through Zscaler.
- ZIA logs in the Zscaler admin portal show the egress for the test traffic.

:::tip For Approach B specifically
Confirm `ProxyServer = 127.0.0.1:24080` is present (the `reg query` in §6/B).
:::

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| ZCC goes fail-closed / widespread timeouts / high CPU shortly after Quilr starts | ZCC tunnel/egress IPs not whitelisted → Quilr is intercepting ZCC's own path to ZEN (loop) | Provide your **ZEN/tunnel IPs/CIDRs** to Quilr for exclusion (§3); confirm they're applied. |
| Inspected requests time out when Quilr re-originates (Approach A) | ZCC is rejecting traffic from `quilrai-proxy` to the local `:9000` proxy | Confirm ZCC permits the local hop from `quilrai-proxy` to `ZSATunnel:9000`; if it can't, switch to **Approach B**. |
| Certificate warnings/errors on inspected sites | Quilr root CA not trusted on the endpoint | Ensure the Quilr root CA is installed in the OS/browser trust store (§7.1). |
| Selected traffic not being inspected (Approach C) | PAC not matching the host, or app isn't PAC-aware | Verify PAC rules / `shExpMatch` patterns and that the app reads the PAC; test with a PAC-aware browser. |
| Selected traffic inspected but then fails to egress (Approach C) | Process bypass missing — `quilrai-proxy` is blocked from direct egress | Add the `quilrai-proxy` process to ZCC's application/process bypass. |
| App that ignores the system proxy isn't inspected (Approach B) | System-proxy enforcement only covers proxy-aware apps | Additionally enable Quilr **active interception** to catch non-proxy-aware apps. |
| Z-Tunnel 2.0 not tunneling Quilr's egress | Wrong Tunnel Driver Type | Set **Tunnel Driver Type = Packet Filter-Based** (not Route-Based) in the Forwarding Profile (§6/B). |
| Local services (e.g. `localhost` DBs) break after enabling Approach B | "Bypass Proxy Server for Local Addresses" not checked | Check that box in the Forwarding Profile (§6/B step 5). |

---

## 10. FAQ

**Q: Does Quilr change where my traffic egresses?**
No. In all approaches the traffic still leaves the endpoint through ZCC to ZEN (or your normal route for selectively-scoped traffic in Approach C). Quilr only adds an inspection step in front.

**Q: Will Quilr break my ZPA (private access) traffic?**
ZPA continues to use ZCC's tunnel as configured. Keep **ZPA → Tunnel** in your Forwarding Profile. Coexistence here is about ZIA / internet egress.

**Q: Do I have to enable active (kernel) interception?**
Only for **Approach A**. For **B** it's optional (ZCC enforces the proxy), and for **C** it's optional (PAC does the routing).

**Q: Which approach should most Z-Tunnel 1.0 customers use?**
**Approach A** (zero-touch). Move to **B** only if ZCC won't accept `quilrai-proxy`'s local hop to `:9000`, or you're on Z-Tunnel 2.0.

**Q: We changed Zscaler cloud / data centers. Anything to do?**
Yes — re-supply your updated **ZEN/tunnel egress IPs** to Quilr (§3) so the exclusion list stays correct.

**Q: macOS?**
Quilr uses a Network Extension for interception on macOS, and the Windows-only system-proxy honoring does not apply. Validate the macOS plan with the Quilr team.

---

## 11. Pre-go-live checklist

- [ ] **Tunnel IPs whitelisted (§3):** ZEN/tunnel egress IPs/CIDRs supplied to Quilr and confirmed applied.
- [ ] **Approach chosen** via the Quick Chooser (§5) and matches your ZCC tunnel mode.
- [ ] **Quilr root CA installed and trusted** on all target endpoints (§7.1).
- [ ] **Ports confirmed:** Quilr listening on `127.0.0.1:24080` / `:24443` (§8).
- [ ] **Approach A:** verified ZCC accepts `quilrai-proxy`'s local hop to `ZSATunnel:9000`.
- [ ] **Approach B:** Forwarding Profile = **Packet Filter-Based** + System Proxy **Enforce** → `127.0.0.1:24080`; "Bypass local addresses" checked; `ProxyServer` registry value verified.
- [ ] **Approach C:** PAC matches the intended hosts; `quilrai-proxy` process bypass added.
- [ ] **Inspection validated:** served cert chains to Quilr root CA; DLP fires on test content.
- [ ] **ZCC validated:** tunnel healthy; "behind Zscaler" check passes; ZIA logs show egress.
- [ ] **Loop check:** no ZCC fail-closed / timeout symptoms during a soak test.
- [ ] **Rollback plan:** know how to disable Quilr interception / revert the Forwarding Profile or PAC if needed.
