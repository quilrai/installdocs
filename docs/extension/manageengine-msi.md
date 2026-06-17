# Quilr Browser Extension — ManageEngine Endpoint Central (Windows / MSI)

Deploy the Quilr browser extension to a Windows fleet via ManageEngine Endpoint Central. The flow mirrors the agent — Software Repository entry + MSI properties + "Install MSI Software" Configuration.

> **Sister guide:** [ManageEngine Endpoint Central — Windows (MSI)](/deployment/manageengine-msi) for the agent. Same UI, same options; only the artefact + product name differ.

---

## Prerequisites

Same as the Quilr Endpoint Agent rollout — see [Prerequisites](/prerequisites) for the complete checklist (Endpoint Central admin, target Windows endpoints reachable via the Endpoint Central agent, signed MSI, network egress, …). Browser-extension-specific extras:

- **Tenant ID** from **Quilr support** (`support@quilr.ai`) — passed to the MSI as `TENANTID=<TENANT-ID>` in the MSI/MSP Properties field.
- Reachability for `quilr-extensions.quilr.ai` (CDN that hosts the MSI).

---

## 1. Download

| Artefact | URL |
|---|---|
| Installer (MSI) | [`https://quilr-extensions.quilr.ai/Quilr.msi`](https://quilr-extensions.quilr.ai/Quilr.msi) |

Place `Quilr.msi` on the Endpoint Central server's shared location (or upload directly via the UI).

---

## 2. Add the MSI to the Software Repository

### Step A. Start a new Windows package

**Software Deployment → Add Package → Add Windows Package** → name: *Quilr Browser Extension*. **Category**: *Security*.

### Step B. Locate the installable

Browse to `Quilr.msi`.

### Step C. MSI properties (silent install)

> **Silent install:** Endpoint Central installs MSI packages silently by default (no `/qn` needed — that is handled by the platform).
>
> **`TENANTID` parameter (required).** In the **MSI/MSP Properties** field of the package, set:
>
> ```
> TENANTID=<TENANT-ID>
> ```
>
> Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`). Without it the extension installs but stays idle until reinstalled.
>
> Add any additional space-separated `PROPERTY=VALUE` pairs in the same field if Quilr support provides further custom MSI properties.

### Step D. Save

The package now appears in the Software Repository.

---

## 3. Create the "Install MSI Software" Configuration

1. **Configurations → Add Configuration → Install MSI Software** (Windows).
2. **Name**: *Install Quilr Browser Extension*.
3. **Define configuration → MSI Package Name**: select *Quilr Browser Extension* from §2.
4. *(Optional)* Scheduler: leave default unless your maintenance window requires otherwise.
5. **Deployment settings**: run as **System**.
6. **Define target**: target your `WIN-Quilr-Extension` static / custom group.
7. **Deploy**.

---

## 4. (Optional) Force-install + lock via browser policy

**Skip this section unless your organization centrally manages browser extensions via MDM.** The MSI in §1–§3 installs the **browser native messaging agent** (required) **and** loads the WebExtension into Edge / Chrome — the MSI alone is sufficient. This section is purely for shops that want centralized enforcement so users cannot disable, hide, or remove the extension.

Push the browser's `ExtensionSettings` policy alongside the MSI using a **Custom Script Configuration** that writes the registry value. `ExtensionSettings` is a JSON object that controls install mode, update URL override, and toolbar pinning in one shot:

```powershell
$JSON = @'
{
  "piajhjohgigijkddhdpgbjdcfhmammbk": {
    "installation_mode": "force_installed",
    "override_update_url": true,
    "toolbar_state": "force_shown",
    "update_url": "https://quilr-extensions.quilr.ai/<TENANT-ID>/manifest.xml"
  }
}
'@

foreach ($key in @(
    'HKLM:\SOFTWARE\Policies\Microsoft\Edge',
    'HKLM:\SOFTWARE\Policies\Google\Chrome'
)) {
    if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
    Set-ItemProperty -Path $key -Name 'ExtensionSettings' -Value $JSON -Type String
}
```

Replace `<TENANT-ID>` with the tenant identifier supplied by **Quilr support** (`support@quilr.ai`). What each key in the JSON does:

| Key | Effect |
|---|---|
| `installation_mode: "force_installed"` | Installs the extension silently; users cannot disable or remove it. |
| `override_update_url: true` | Forces the browser to fetch the extension from `update_url`, not the public web store. |
| `toolbar_state: "force_shown"` | Pins the Quilr icon to the browser toolbar. |
| `update_url` | Tenant-specific Quilr CDN manifest that ships extension updates. |

Wrap that script in a Custom Script Configuration in Endpoint Central and target the same group.

> **Simpler legacy alternative** — `ExtensionInstallForcelist`: write `piajhjohgigijkddhdpgbjdcfhmammbk;https://quilr-extensions.quilr.ai/<TENANT-ID>/manifest.xml` to `HKLM:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist` (next free index) and the equivalent Chrome key. Force-installs the extension but doesn't pin the toolbar. Still needs the MSI from §1–§3 for the native agent.

---

## 5. Validate

```powershell
# Either path — verify the policy registry value contains the Quilr extension ID
Get-ItemProperty `
  HKLM:\SOFTWARE\Policies\Microsoft\Edge\ExtensionInstallForcelist, `
  HKLM:\SOFTWARE\Policies\Google\Chrome\ExtensionInstallForcelist `
  -ErrorAction SilentlyContinue | Format-List
```

Look for a value containing `piajhjohgigijkddhdpgbjdcfhmammbk`.

Open `edge://extensions` and `chrome://extensions` — Quilr extension present + enabled + *Installed by your organization*. Then send a short test prompt on `https://claude.ai/` — within ~2 seconds the **event should appear in the Quilr console**.

> The browser extension does **not** perform TLS interception — it captures prompts and file uploads at the **DOM level** via the WebExtensions API. The "Issuer = Quilr" cert-chain check from [Validate Installation §4](/reference/validate-installation) applies to the **Endpoint Agent's WinDivert driver**, not the extension.

---

## 6. Rollback

Create an **Uninstall MSI Software** Configuration targeting the same group and pointing at the *Quilr Browser Extension* package, OR delete the registry policy values you created in §4. See [ManageEngine Endpoint Central — Windows (MSI)](/deployment/manageengine-msi) §11 for the equivalent agent rollback.
