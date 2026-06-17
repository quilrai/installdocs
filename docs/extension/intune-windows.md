# Quilr Browser Extension — Microsoft Intune (Windows / MSI)

Deploy the Quilr browser extension to a Windows fleet via Microsoft Intune.

> **Sister guide:** the agent equivalent is [Microsoft Intune — Windows (MSI)](/deployment/intune-windows). The Win32 + Settings Catalog patterns documented there apply 1-to-1 to the extension.

> **The MSI is the install path. The browser policy is optional.**
>
> `Quilr.msi` installs the **browser native messaging agent** on the device — that binary is what the Edge / Chrome extension talks to over the [Native Messaging API](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging) to capture prompts and uploads. The MSI also takes care of loading the WebExtension into the browsers, so the MSI alone is sufficient.
>
> - **§2 is mandatory** — push the MSI to every endpoint that needs the extension.
> - **§3 is optional** — only relevant if your organization already centrally manages browser extensions via Intune (force-install lists, allow/block-lists, toolbar locks). If you do, push the `ExtensionSettings` policy alongside the MSI so users cannot disable or hide the Quilr extension. If you don't manage browser extensions via MDM today, **skip §3** — the MSI handles the extension load.

---

## Prerequisites

Same as the Quilr Endpoint Agent rollout — see [Prerequisites](/prerequisites) for the complete checklist (Intune admin, Entra-joined Windows endpoints, Win32 Content Prep Tool, signed MSI, network egress, …). Browser-extension-specific extras:

- **Tenant ID** from **Quilr support** (`support@quilr.ai`) — passed to the MSI as `TENANT=<TENANT-ID>`.
- Reachability for `quilr-extensions.quilr.ai` (CDN that hosts `Quilr.msi`).

---

## 1. Download

| Artefact | URL |
|---|---|
| Installer (MSI) | [`https://quilr-extensions.quilr.ai/Quilr.msi`](https://quilr-extensions.quilr.ai/Quilr.msi) |

---

## 2. Deploy the MSI as a Win32 app (required — installs the native agent)

### Step A. Wrap the MSI as `.intunewin`

```powershell
# Place Quilr.msi in C:\Staging\QuilrExtension\
IntuneWinAppUtil.exe -c C:\Staging\QuilrExtension -s Quilr.msi -o C:\Staging\Out
# Produces: C:\Staging\Out\Quilr.intunewin
```

### Step B. Add the Win32 app

1. **Apps → All apps → Add → App type: Windows app (Win32)**.
2. Upload `Quilr.intunewin`.
3. **Name**: *Quilr Browser Extension*. **Publisher**: *Quilr AI*.

### Step C. Program (install / uninstall)

| Field | Value |
|---|---|
| Install command | `msiexec /i Quilr.msi TENANT=<TENANT-ID> /qn /norestart` |
| Uninstall command | `msiexec /x "{QUILR-BROWSER-EXT-PRODUCT-CODE}" /qn /norestart` |
| Install behavior | **System** |
| Device restart behavior | *No specific action* |

> **`TENANT` parameter (required).** Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`). Without it the extension installs but stays idle.

### Step D. Detection rule

Choose **one**:

- **MSI** — detection type *MSI*, product code auto-populated from the wrapped package.
- **Registry** — `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist` value containing `piajhjohgigijkddhdpgbjdcfhmammbk`.

### Step E. Assign

**Assignments → Required → `WIN-Quilr-Extension`** Entra ID group (or reuse the agent group). **Review + create**.

---

## 3. (Optional) Force-install + lock via Settings Catalog

**Skip this section unless your organization centrally manages browser extensions via MDM.** The MSI in §2 already loads the extension; the policy here is purely for shops that want centralized enforcement so users cannot disable, hide, or remove the extension.

Deploy **alongside** the MSI from §2. This forces the browser to install the WebExtension from the Quilr CDN, pins it to the toolbar, and stops the user from disabling or removing it:

1. **Devices → Configuration → Create → New Policy**.
2. **Platform**: *Windows 10 and later*. **Profile type**: *Settings catalog*.
3. **Name**: *Quilr Browser Extension — Force Install*.
4. Add the setting **Configure extension management settings** under *Microsoft Edge → Extensions* **and** the equivalent under *Google Chrome → Extensions*. Paste the following JSON as the value:

```json
{
  "piajhjohgigijkddhdpgbjdcfhmammbk": {
    "installation_mode": "force_installed",
    "override_update_url": true,
    "toolbar_state": "force_shown",
    "update_url": "https://quilr-extensions.quilr.ai/<TENANT-ID>/manifest.xml"
  }
}
```

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`). What each key does:

| Key | Effect |
|---|---|
| `installation_mode: "force_installed"` | Installs the extension silently; users cannot disable or remove it. |
| `override_update_url: true` | Forces the browser to fetch the extension from `update_url` instead of the public web store. |
| `toolbar_state: "force_shown"` | Pins the Quilr icon to the browser toolbar — users cannot hide it. |
| `update_url` | Tenant-specific Quilr CDN manifest that ships extension updates. |

5. **Assignments → `WIN-Quilr-Extension`** (the same group as the MSI in §2). **Review + create**.

> **Simpler legacy alternative:** the [`ExtensionInstallForcelist`](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-browser-policies/extensioninstallforcelist) policy also works — set the *Control which extensions are installed silently* setting to `piajhjohgigijkddhdpgbjdcfhmammbk;https://quilr-extensions.quilr.ai/<TENANT-ID>/manifest.xml`. It force-installs the WebExtension part but does **not** pin the toolbar icon, and (like §3) it still requires the MSI from §2 for the native agent.

---

## 2. Validate

On a pilot Windows endpoint:

```powershell
# MSI path — installed registry entry
Get-ChildItem `
  HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*, `
  HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* |
  Get-ItemProperty | ? DisplayName -like '*Quilr*Browser*'

# Settings-Catalog path — policy registry entry
Get-ItemProperty `
  HKLM:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist, `
  HKLM:\SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist `
  -ErrorAction SilentlyContinue
```

Open `edge://extensions` and `chrome://extensions` — the Quilr extension must be **present, enabled, "Installed by your organization"**.

Then send a short test prompt on `https://claude.ai/` (or any monitored AI host). Within ~2 seconds the **prompt event should appear in the Quilr console**.

> The browser extension does **not** perform TLS interception — it captures prompts and file uploads at the **DOM level** via the WebExtensions API. The "Issuer = Quilr" cert-chain check from [Validate Installation §4](/reference/validate-installation) applies to the **Endpoint Agent's WinDivert driver**, not the extension. For the extension, the source of truth is *"did the event reach the console?"*.

---

## 3. Rollback

**Path A (MSI):** change the Win32 app assignment from *Required* to *Uninstall* for the group. Intune runs the MSI uninstall on next sync.

**Path B (Settings Catalog):** unassign or delete the configuration policy. The browser drops the extension on next launch.
