---
title: Quilr Browser Extension — Overview
sidebar_label: Overview
---

# Quilr Browser Extension

The Quilr browser extension installs into **Microsoft Edge** and **Google Chrome** (and **Safari** on macOS). It exists to cover browser flows that the Quilr Endpoint Agent intentionally **excludes** from its on-device interception scope — by default, that's `msedge.exe` and `chrome.exe` on Windows, plus Safari and the WebKit-based browsers on macOS. The extension intercepts AI prompts and uploads at the page level and ships the events to the same Quilr control plane.

This section mirrors the *Endpoint Agent* section — pick your MDM, get vendor-specific deployment steps.

> **The pkg / MSI is the install path. The MDM browser policy is optional.**
>
> The Quilr browser extension is not a stand-alone WebExtension — it talks to a small **browser native messaging agent** on the device (installed by `Quilr.msi` on Windows or `quilr-installer-mac.pkg` on macOS) over Chrome/Edge's [Native Messaging API](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging). Without the native agent the extension is a no-op — no prompt capture, no upload extraction, no events shipped.
>
> So **every rollout must ship the pkg / MSI**. The native-agent installer also takes care of getting the WebExtension into Edge / Chrome — you do *not* need a second MDM step for that.
>
> **MDM browser policy (`ExtensionSettings` / `ExtensionInstallForcelist`) is only relevant if your organization already centrally manages browser extensions via MDM** and wants to enforce / lock the Quilr extension through the same channel (toolbar-pinned, user can't disable or remove it). If you don't manage extensions via MDM today, skip the policy sections — the MSI / pkg alone is sufficient.

## Artefacts you will deploy

| Platform | Artefacts | Where to get them |
|---|---|---|
| **macOS** | Tenant pkg + tenant `.mobileconfig` (extension approval) + shared `.mobileconfig` (File Access) | Pkg from a tenant-specific URL (see below); tenant `.mobileconfig` from the Quilr console; File-Access mobileconfig from a public URL |
| **Windows** | `Quilr.msi` | Public URL: [`https://quilr-extensions.quilr.ai/Quilr.msi`](https://quilr-extensions.quilr.ai/Quilr.msi) |

## Pick your MDM

| Platform | MDM | Guide |
|---|---|---|
| macOS | Microsoft Intune | [Microsoft Intune — macOS](/extension/intune-macos) |
| macOS | Jamf Pro | [Jamf Pro — macOS](/extension/jamf) |
| macOS | Kandji | [Kandji — macOS](/extension/kandji) |
| macOS | *(no MDM / manual)* | [macOS Manual Install](/extension/macos-manual) |
| Windows | Microsoft Intune | [Microsoft Intune — Windows (MSI)](/extension/intune-windows) |
| Windows | ManageEngine Endpoint Central | [ManageEngine Endpoint Central — Windows (MSI)](/extension/manageengine-msi) |

## Key fields (all guides)

| Field | Value |
|---|---|
| **Tenant ID** | Obtain from **Quilr support** (`support@quilr.ai`). Used as `TENANT=<TENANT-ID>` (Windows MSI) and as a path segment in the tenant-specific macOS pkg URL. |
| Extension ID (Edge / Chrome) | `piajhjohgigijkddhdpgbjdcfhmammbk` |
| Update manifest URL | `https://quilr-extensions.quilr.ai/<TENANT-ID>/manifest.xml` |
| Windows installer (MSI) | [`https://quilr-extensions.quilr.ai/Quilr.msi`](https://quilr-extensions.quilr.ai/Quilr.msi) |
| macOS installer (pkg) | `https://quilr-extensions.quilr.ai/<TENANT-ID>/browser-util/quilr-installer-mac.pkg` |
| File-Access mobileconfig (macOS only, shared) | [`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig) |
