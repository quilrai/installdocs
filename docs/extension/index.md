---
title: Quilr Browser Extension — Overview
sidebar_label: Overview
---

# Quilr Browser Extension

The Quilr browser extension installs into **Microsoft Edge** and **Google Chrome** (and **Safari** on macOS). It covers browser flows that the Quilr Endpoint Agent intentionally excludes from on-device interception. The extension captures AI prompts and uploads at the page level and ships events to the Quilr control plane.

> **The pkg / MSI is required.** The extension talks to a **native messaging agent** on the device (installed by `Quilr.msi` on Windows or the macOS pkg). Without that agent the extension is a no-op.
>
> **MDM browser policy** (`ExtensionSettings` / `ExtensionInstallForcelist`) is optional. Use it only if you already centrally manage browser extensions and want to lock the Quilr extension.

The **macOS pkg is tenant-agnostic**. Tenant comes from install JSON (`tenant_id` in `/tmp/quilr-be-install.json` or `/Users/Shared/quilr-be-install.json`). Windows MSI still uses `TENANT=` as documented in the Windows guides.

## Artefacts

| Platform | Artefacts | Source |
|---|---|---|
| **macOS** | Generic pkg `quilrai-browser-extension-vYYYY.MM.DD.pkg` + tenant `.mobileconfig` (extension approval) + shared File-Access `.mobileconfig` | Pkg from Quilr support; tenant `.mobileconfig` from the Quilr console; File-Access mobileconfig from the public URL below |
| **Windows** | `Quilr.msi` | [`https://quilr-extensions.quilr.ai/Quilr.msi`](https://quilr-extensions.quilr.ai/Quilr.msi) |

## Pick your MDM

| Platform | MDM | Guide |
|---|---|---|
| macOS | Microsoft Intune | [Microsoft Intune — macOS](/extension/intune-macos) |
| macOS | Jamf Pro | [Jamf Pro — macOS](/extension/jamf) |
| macOS | Kandji | [Kandji — macOS](/extension/kandji) |
| macOS | *(no MDM / manual)* | [macOS Manual Install](/extension/macos-manual) |
| Windows | Microsoft Intune | [Microsoft Intune — Windows (MSI)](/extension/intune-windows) |
| Windows | ManageEngine Endpoint Central | [ManageEngine Endpoint Central — Windows (MSI)](/extension/manageengine-msi) |

## Key fields

| Field | Value |
|---|---|
| **Tenant ID** | From **Quilr support** (`support@quilr.ai`). Windows: `TENANT=<TENANT-ID>`. macOS: `tenant_id` in `/tmp/quilr-be-install.json`. |
| Extension ID (Edge / Chrome) | `piajhjohgigijkddhdpgbjdcfhmammbk` |
| Chrome/Edge update manifest | `https://quilr-extensions.quilr.ai/<TENANT-ID>/manifest.xml` |
| Windows installer (MSI) | [`https://quilr-extensions.quilr.ai/Quilr.msi`](https://quilr-extensions.quilr.ai/Quilr.msi) |
| macOS installer (pkg) | `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support (one generic pkg for every tenant) |
| File-Access mobileconfig (macOS) | [`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig) |

## Reference

| Guide | What it covers |
|---|---|
| [Validate Installation](/extension/validate-installation) | Extension enabled, native agent running, green popup, installer generation stamp |
| [macOS v3 QA](/extension/qa-macos-v3) | Offline config matrix and Intune v1/v2→v3 upgrade checklist |
| [Troubleshooting](/extension/troubleshooting) | Common failure modes |
