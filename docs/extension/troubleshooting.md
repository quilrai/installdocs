# Troubleshooting — Browser Extension Installation

If [Validate Installation](/extension/validate-installation) **Check 1** (extension visible + enabled in the browser) is failing, work through these checks in order. Each one verifies a link in the install chain: **policy applied → manifest reachable → .crx reachable → browser picks it up**.

If **Check 2** (native messaging agent) or **Check 3** (popup green) is failing, jump to §5 below — they live on the MSI / pkg side of the chain.

---

## 1. Is the browser policy applied?

Open the **browser policy page** on the affected endpoint:

| Browser | URL |
|---|---|
| Google Chrome | `chrome://policy` |
| Microsoft Edge | `edge://policy` |

Search the page for **Quilr** or the extension ID **`piajhjohgigijkddhdpgbjdcfhmammbk`**.

**Expected:**
- An entry for **`ExtensionSettings`** (if you use the JSON policy from [Intune Path B](/extension/intune-windows#3-optional-force-install--lock-via-settings-catalog) / [ManageEngine §4](/extension/manageengine-msi#4-optional-force-install--lock-via-browser-policy)) **or** **`ExtensionInstallForcelist`** (legacy alternative).
- The **value** column contains the extension ID **`piajhjohgigijkddhdpgbjdcfhmammbk`** and the tenant-specific update URL `https://quilr-extensions.quilr.ai/<TENANT-ID>/manifest.xml`.
- The **status** column shows **`OK`**.

### If the policy isn't there

- Click **Reload policies** at the top of `chrome://policy` / `edge://policy`.
- Restart the browser — newly-pushed extension policies are read at browser launch.
- The MDM hasn't applied yet on this device:
  - **Intune** — *Settings → Accounts → Access work or school → Info → **Sync***, or wait for the 8-hour cycle.
  - **ManageEngine** — force a check-in from the Endpoint Central agent tray, or wait for the next scheduled scan.
  - **GPO** — `gpupdate /force` (elevated) then restart the browser.
- Confirm the policy was actually pushed by the MDM — see [Intune Path B](/extension/intune-windows#3-optional-force-install--lock-via-settings-catalog) / [ManageEngine §4](/extension/manageengine-msi#4-optional-force-install--lock-via-browser-policy) and re-check the assignment.

### If the policy is there but status is `Error`

- The JSON in `ExtensionSettings` is malformed. Re-check curly braces / quotes against the canonical snippet in your vendor guide.
- The `update_url` is mistyped. The extension ID and URL are case-sensitive.

---

## 2. Is the manifest URL reachable from this endpoint?

The browser fetches the extension from the URL inside the policy. Verify this device can actually reach it:

### Windows (PowerShell)

```powershell
$TENANT = '<TENANT-ID>'
Invoke-WebRequest "https://quilr-extensions.quilr.ai/$TENANT/manifest.xml" -UseBasicParsing |
  Select-Object StatusCode, StatusDescription, @{n='Bytes';e={$_.RawContentLength}}
```

**Expected:** `StatusCode 200`, `Bytes > 0`. Drop the `-Method Head` flag if you want to print the XML body too.

### macOS (Terminal)

```bash
TENANT='<TENANT-ID>'
curl -fsSL -o /tmp/quilr-manifest.xml \
  "https://quilr-extensions.quilr.ai/${TENANT}/manifest.xml" \
  && head -20 /tmp/quilr-manifest.xml
```

**Expected:** `curl` exits 0 and the first few lines look like XML (`<gupdate xmlns="http://www.google.com/update2/response" …>`).

### If the request fails

| Failure | Likely cause | Fix |
|---|---|---|
| `403` / `404` | Wrong `<TENANT-ID>` in the policy | Confirm the tenant ID with **Quilr support** (`support@quilr.ai`) and re-push the policy from your MDM |
| `Connection timed out` / `Could not resolve host` | Firewall, DNS filter, or proxy blocking `quilr-extensions.quilr.ai` | Allowlist the host. The full URL allow-list lives in [URL Exception List — AI Apps](/reference/url-exceptions-ai) and `quilr-extensions.quilr.ai` should already be there |
| `SSL handshake error` / *issuer mismatch* | An upstream SWG (Netskope, Zscaler, Cisco Umbrella, etc.) is decrypting `quilr-extensions.quilr.ai` and presenting its own leaf cert | Add `quilr-extensions.quilr.ai` to the SWG's **SSL-bypass / Do Not Decrypt** list. See [URL Exception List — AI Apps](/reference/url-exceptions-ai) §3 |
| `HTTP/2 200` but body is HTML, not XML | Captive portal / login page intercepting the request | Same as above — get the SWG out of the way |

---

## 3. Is the `.crx` package URL working?

The manifest from §2 contains a `codebase="..."` attribute pointing to the actual extension package. The current direct URL is:

```
https://quilr-extensions.quilr.ai/<TENANT-ID>/vanguard.crx
```

Test it directly — sometimes the manifest is reachable but the `.crx` (which can route differently through corporate proxies because of its content-type) is not.

### Windows (PowerShell)

```powershell
$TENANT = '<TENANT-ID>'
Invoke-WebRequest "https://quilr-extensions.quilr.ai/$TENANT/vanguard.crx" `
  -Method Head -UseBasicParsing |
  Select-Object StatusCode, @{n='Type';e={$_.Headers.'Content-Type'}}, `
                @{n='Bytes';e={$_.Headers.'Content-Length'}}
```

### macOS (Terminal)

```bash
TENANT='<TENANT-ID>'
curl -fsSL -I "https://quilr-extensions.quilr.ai/${TENANT}/vanguard.crx" | head -5
```

**Expected:** `200 OK` with `Content-Type: application/x-chrome-extension` (or `application/octet-stream` on some CDNs) and a non-zero `Content-Length`.

### (Optional) Confirm the manifest still points at the same `.crx`

If the URL above ever returns `404`, Quilr may have moved the `.crx` to a different filename. Cross-check what the live manifest is advertising:

```bash
# macOS — the codebase attribute should match the URL you just probed
grep -oE 'codebase="[^"]+"' /tmp/quilr-manifest.xml
```

```powershell
# Windows
[xml]$m = Get-Content C:\Windows\Temp\quilr-manifest.xml
$m.gupdate.app.updatecheck.codebase
```

If the `codebase` URL differs from `…/vanguard.crx`, probe that one instead — it is the authoritative source.

### If the `.crx` request fails

Same failure modes as §2 (wrong path, blocked host, SSL inspection). Two extra notes:

- A common silent failure: the corporate SWG **strips** Chrome-extension content-types as part of its file-policy. Confirm `application/x-chrome-extension` and `.crx` downloads aren't on a download-restriction list.
- If the manifest's `codebase` URL points to a **different host** than `quilr-extensions.quilr.ai`, that host must be allow-listed + SSL-bypassed as well — see [URL Exception List — AI Apps](/reference/url-exceptions-ai).

---

## 4. Policy + manifest + .crx all OK — browser still doesn't show the extension

Sometimes the browser just needs to be coaxed into picking up the new policy:

- **Restart the browser**. Force-installed extensions are loaded at startup; an in-flight browser instance won't pick up a freshly-pushed policy until next launch.
- **Edge** → `edge://policy/` → **Reload policies** → close every Edge window → relaunch.
- **Chrome** → `chrome://extensions/` → toggle **Developer mode** on → click **Update**. Then `chrome://policy/` → **Reload policies** → restart Chrome.
- If the device is **roaming / off-network**, the install can be delayed until the device sees the management URL again — bring it on-net or have the user open the Quilr CDN URL once manually.

---

## 5. Extension is visible but popup is red / yellow

If `chrome://extensions` shows the Quilr extension as installed and enabled, but the popup ([Validate Installation Check 3](/extension/validate-installation#check-3-the-extension-popup-reports-persona-active--extension-enabled)) shows a red / yellow status, the WebExtension is installed but the **native messaging agent** isn't running.

That means the MSI / pkg side of the chain is broken, **not** the policy chain you just verified. Jump to:

- [Validate Installation — Check 2](/extension/validate-installation#check-2-the-native-messaging-agent-is-running) — confirm `quilr-native-messaging-agent` is alive.
- Re-deploy the MSI / pkg via your MDM if the process is missing.

The WebExtension and the native agent are **two separate installs** — fixing one does not fix the other.

---

## Escalation

If all four browser-side checks pass and the popup is still not green, click **Report a Bug** inside the extension popup — it auto-attaches `Extension v…` and `Agent v…`. Or e-mail **`support@quilr.ai`** directly with:

- Screenshot of `chrome://policy` / `edge://policy` filtered to *Quilr* (proves §1).
- Output of the two `Invoke-WebRequest` / `curl` commands above (proves §2 and §3).
- Screenshot of the popup (proves §5 if applicable).
- OS, browser, and MDM in use.

For deeper agent-side troubleshooting (logs, process state, kill-switch behaviour, etc.), see the main [Troubleshooting](/reference/troubleshooting) guide — much of it applies to the native agent equally.
