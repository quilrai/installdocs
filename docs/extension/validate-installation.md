# Validate Installation — Browser Extension

Use this page after pushing the Quilr browser extension (and the **MSI / pkg** that installs the native messaging agent) to confirm both pieces are running on the endpoint. Checks 1–3 must pass for the extension to be working end-to-end. On macOS after a v3 install or upgrade, also run Check 2b.

For offline config and Intune v1/v2→v3 upgrade steps, see [macOS v3 QA](/extension/qa-macos-v3).

> The extension is two cooperating pieces — the WebExtension in the browser **and** the `quilr-native-messaging-agent` binary. They talk over Native Messaging. If either one is missing or stopped, the extension installs but captures nothing.

---

## Check 1. The extension is visible in the browser

Open the browser's extensions page:

| Browser | Path |
|---|---|
| Microsoft Edge | `edge://extensions` |
| Google Chrome | `chrome://extensions` |
| Safari (macOS) | Safari → Settings → Extensions |

Look for **Quilr**. It must be:

- Present in the list
- **Enabled**
- *(MDM-pushed installs only)* marked **"Installed by your organization"** with no Remove button

If the extension isn't there at all → re-check the deployment step for your MDM in the **Deployment Guides** section.

---

## Check 2. The native messaging agent is running

The WebExtension only does anything useful when it can talk to the **`quilr-native-messaging-agent`** binary that the MSI / pkg installs. Verify the process is alive on the endpoint:

### Windows

Open **Task Manager → Details** tab and look for **`quilr-native-messaging-agent.exe`**.

Or in **PowerShell**:

```powershell
Get-Process | Where-Object Name -like '*quilr*'
```

You should see at least one row whose name contains `quilr-native-messaging-agent`.

### macOS

Open **Activity Monitor** and search for **`quilr-native-messaging-agent`**.

Or in **Terminal**:

```bash
pgrep -lf 'quilr-native-messaging-agent'
```

You should see a PID and the process path.

> **If the process isn't there**, re-deploy from your MDM (or `msiexec /i Quilr.msi TENANT=<TENANT-ID> /qn` / `sudo installer -pkg quilrai-browser-extension-vYYYY.MM.DD.pkg -target /` with tenant JSON). The native agent is required — the WebExtension is a no-op without it.

---

## Check 2b. Which macOS installer generation is on the Mac

The popup’s Agent version is the native binary. It can change without a new pkg. On macOS, the v3 pkg writes the installer generation next to the tenant config. v1 (Chrome/Edge only) and v2 (Chrome/Edge plus Firefox/Safari) machines have no `installer_generation` until the v3 pkg runs over them.

```bash
python3 -m json.tool "/Library/Application Support/QuilrAIBE/installer-stamp.json"
sudo python3 -m json.tool "/Library/Application Support/QuilrAIBE/be-config.json"
pkgutil --pkg-info ai.quilr.be.browsers
```

**After a v3 install or a v1/v2 upgrade to v3**, both JSON files contain `"installer_generation": "3"` and a `pkg_version` of digits and dots (the pkg receipt version, `YYYY.MM.DD`). `pkgutil` `version` matches `pkg_version`. `installer-stamp.json` is the copy the extension can read; it does not contain the API key.

**Still on v1 or v2:** `installer-stamp.json` is missing, and `be-config.json` has no `installer_generation`. That absence is the signal the v3 pkg has not run. A fresh v3 install and a v1 or v2 upgrade both show generation `3` only after that pkg succeeds. The same files are written for a manual `installer -pkg` and for an MDM pre-install script.

The pkg also writes an install summary to `/var/log/quilr/quilr.log` (`[install-summary]`). That block lists tenant, browsers, generation, pkg version, whether the File-Access and Safari permission profiles are installed, and whether the native agent and Safari utility are on disk. A missing File-Access profile does not fail the install; push `quilr_browser_util_Files_Access.mobileconfig` from MDM, or grant Full Disk Access in System Settings.

---

## Check 3. The extension popup reports "Persona Active & Extension Enabled"

This is the end-to-end check — it proves the WebExtension and the native agent are actually talking to each other. Click the **Quilr icon** in the browser toolbar. The popup should look like this:

![Quilr extension popup — Persona Active & Extension Enabled](/img/quilr-extension-active.png)

### What every part of that popup tells you

| Element | What it means |
|---|---|
| 🟢 **"Persona Active & Extension Enabled"** | The WebExtension *and* the native messaging agent are both running, and the signed-in user (persona) has been resolved. **This is the only "OK" state.** |
| Quilr logo + branding | The popup loaded the bundled assets — proves the WebExtension itself rendered. |
| **"Registered to: \<email\>"** | The user the captured events will be attributed to. |
| `Extension v<…>` (bottom-left) | WebExtension version — bumps when Quilr ships an extension update. |
| `Agent v<…>` (bottom-right) | Native-agent binary version. On macOS the pkg can update this binary without a new installer generation — use Check 2b for the pkg generation. |
| **Report a Bug** (blue link, lower-left) | Opens a pre-filled email to Quilr support with the two version numbers appended automatically — always use this link when escalating an issue so the support team doesn't have to ask for them. |

### When the status isn't green

| What you see | Likely cause | Where to look |
|---|---|---|
| Popup doesn't open at all | WebExtension not installed or disabled | Re-run **Check 1** |
| **Red** dot / *"Extension not connected"* / *"Native host missing"* | Native messaging agent not running | Re-run **Check 2** — restart the device or re-deploy the MSI / pkg |
| **Yellow** dot / *"Persona not resolved"* | User isn't signed into Quilr in this browser | Open `https://app.quilr.ai/` in a tab and complete sign-in, then re-open the popup |
| Missing version numbers (Extension v… / Agent v…) | Popup loaded before the agent responded | Wait 2–3 seconds and retry; if it persists, re-run **Check 2** |
| *"Update available"* banner | Native agent is older than the WebExtension expects | Push the latest MSI / pkg from your MDM |

For deeper diagnostics see [Troubleshooting](/reference/troubleshooting).

---

## Pass / Fail summary

The installation is healthy when **all three** are true on the endpoint:

| # | Check | Method |
|---|---|---|
| 1 | Quilr extension visible **and enabled** in the browser | §Check 1 |
| 2 | `quilr-native-messaging-agent` running in Task Manager / Activity Monitor | §Check 2 |
| 3 | Popup shows green **"Persona Active & Extension Enabled"** with both version strings rendered | §Check 3 |
| 4 | macOS v3 install or upgrade shows `installer_generation` `3` and a matching `pkg_version` | §Check 2b |

If any of the three fails, the events will not reach the Quilr console. The browser extension does **not** perform TLS interception — pass/fail is the green popup and whether the event reaches the console.

---

## Escalation

If the popup status is anything other than green after re-running the three checks, click **Report a Bug** in the popup itself (lower-left) — it auto-attaches `Extension v…` and `Agent v…`. Quilr support can also be reached at **`support@quilr.ai`** with the screenshot of the popup + the OS / browser version of the affected endpoint.
