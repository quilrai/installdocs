# Quilr Browser Extension — Kandji (macOS)

Deploy with **two Custom Profiles + one Custom App** (Pre-install script + generic pkg).

> **Sister guide:** [Kandji — macOS](/deployment/kandji) for the endpoint agent.

---

## Prerequisites

- Kandji tenant, enrolled Macs, signed packages, egress to `discover.quilrai.dev` and `quilr-extensions.quilr.ai` — see [Prerequisites](/prerequisites).
- **Tenant ID** from **Quilr support** — written in the Custom App **Pre-install script**. Do **not** set `skip_discovery`.
- Generic pkg `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support.
- Tenant `.mobileconfig` from `https://app.quilr.ai/` → **Settings → Browser Extension → Deployment → MDM** (OS = macOS, MDM = Kandji).

---

## 1. Download the artefacts

| Artefact | Source |
|---|---|
| Generic pkg | `quilrai-browser-extension-vYYYY.MM.DD.pkg` from Quilr support |
| Tenant `.mobileconfig` | Quilr console (above) |
| File-Access mobileconfig | [`https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig`](https://quilr-extensions.quilr.ai/browser-agent/prod/mac/quilr_browser_util_Files_Access.mobileconfig) |

---

## 2. Deploy in Kandji

### Step A. Custom Profiles

For each `.mobileconfig`: **Library → Add Library Item → Custom Profile**. Assign to the Blueprint. Names: *Quilr Browser Extension — Tenant Approval* and *Quilr Browser Extension — File Access*.

### Step B. Custom App

1. **Library → Add Library Item → Custom App**.
2. Upload `quilrai-browser-extension-vYYYY.MM.DD.pkg`.
3. **Pre-install script** — first line `#!/bin/bash`. Use `tenant_id`. Do not set `skip_discovery`.

```bash
#!/bin/bash
set -euo pipefail
mkdir -p /tmp /Users/Shared
cat > /tmp/quilr-be-install.json <<'EOF'
{
  "tenant_id": "<TENANT-ID>",
  "browsers": "chrome,edge,firefox,safari"
}
EOF
cp /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json
chmod 644 /tmp/quilr-be-install.json /Users/Shared/quilr-be-install.json
```

4. Assign to the Blueprint. Profiles first, Custom App last.

---

## 3. Validate

[Validate Installation](/extension/validate-installation): extension enabled, native agent running, green popup, Check 2b, then a `claude.ai` prompt in the console.
