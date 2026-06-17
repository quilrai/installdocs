"""Copy + lightly transform the Quilr Endpoint Agent guides into the Docusaurus docs/ tree.

Run from the quilr-docs-site/ folder:  python build_docs.py
"""

import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(ROOT)
DOCS = os.path.join(ROOT, "docs")

# (source_md, dest_relpath, sidebar_label, blurb)
MAPPING = [
    # Deployment guides
    ("Quilr-Endpoint-Agent-Intune-Windows-Deployment-Guide.md",
        "deployment/intune-windows.md",
        "Microsoft Intune — Windows (MSI)",
        "MDM via Microsoft Intune. CA trust + Win32 app + WFP driver."),
    ("Quilr-Endpoint-Agent-Intune-macOS-Deployment-Guide.md",
        "deployment/intune-macos.md",
        "Microsoft Intune — macOS (pkg)",
        "MDM via Microsoft Intune. CA trust + Configuration Profiles + pkg."),
    ("Quilr-Endpoint-Agent-Jamf-Deployment-Guide.md",
        "deployment/jamf.md",
        "Jamf Pro — macOS",
        "MDM via Jamf Pro. Configuration Profiles + Policy."),
    ("Quilr-Endpoint-Agent-Kandji-Deployment-Guide.md",
        "deployment/kandji.md",
        "Kandji — macOS",
        "MDM via Kandji. Library Items + Custom Apps."),
    ("Quilr-Endpoint-Agent-ManageEngine-MSI-Deployment-Guide.md",
        "deployment/manageengine-msi.md",
        "ManageEngine Endpoint Central — Windows (MSI)",
        "On-prem MDM via ManageEngine Endpoint Central."),
    ("Quilr-Endpoint-Agent-macOS-Manual-Deployment-Guide.md",
        "deployment/macos-manual.md",
        "macOS Manual Install",
        "Manual install for technicians / no-MDM pilots."),
    # Reference
    # NOTE: API Reference page is intentionally NOT published on the docs site (the PDF
    # in the parent directory remains the canonical artefact). Do not re-add this entry
    # without confirmation — see chat history "remove api reference from docusaurus".
    ("Quilr-Endpoint-Agent-Troubleshooting-Guide.md",
        "reference/troubleshooting.md",
        "Troubleshooting",
        "Diagnostics, log paths, common failure modes, and the diag-bundle script."),
    ("Quilr-Endpoint-Agent-URL-Exception-List-AI-Apps.md",
        "reference/url-exceptions-ai.md",
        "URL Exception List — AI Apps",
        "Monitored AI hosts (ChatGPT, Claude, Gemini, etc.) — for SWG SSL-bypass."),
    ("Quilr-Endpoint-Agent-URL-Exception-List-NonAI-Apps.md",
        "reference/url-exceptions-nonai.md",
        "URL Exception List — Non-AI Apps",
        "Non-AI hosts (auth/CDNs) — for SWG SSL-bypass."),
    ("Quilr-Endpoint-Agent-Validate-Installation-Guide.md",
        "reference/validate-installation.md",
        "Validate Installation",
        "Post-install validation steps for Windows + macOS. MDM-agnostic."),
]


def strip_branding_header(text: str) -> str:
    """Drop the leading "# Quilr AI / logo / tagline / ---" block from each guide.

    The Docusaurus navbar already provides the brand mark, so the inline banner
    duplicates it on every page.
    """
    lines = text.splitlines()
    out_idx = 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if line.strip().startswith("# Quilr AI"):
            for j in range(i + 1, len(lines)):
                if lines[j].strip() == "---":
                    out_idx = j + 1
                    break
        break
    return "\n".join(lines[out_idx:]).lstrip("\n")


def drop_remaining_quilricons(text: str) -> str:
    """Just in case any guide references QuilrIcons later in the body."""
    return re.sub(r"!\[[^\]]*\]\(QuilrIcons/[^)]+\)\s*\n?", "", text)


def add_frontmatter(text: str, label: str, blurb: str) -> str:
    """Add Docusaurus frontmatter so the sidebar label and meta description match."""
    fm = "---\n"
    fm += f"title: {label}\n"
    fm += f"description: {blurb}\n"
    fm += "---\n\n"
    return fm + text


def process_one(src_name: str, dest_relpath: str, label: str, blurb: str) -> None:
    src_path = os.path.join(SRC, src_name)
    dest_path = os.path.join(DOCS, dest_relpath)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(src_path, encoding="utf-8") as f:
        text = f.read()
    text = strip_branding_header(text)
    text = drop_remaining_quilricons(text)
    text = add_frontmatter(text, label, blurb)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"copied {src_name} -> docs/{dest_relpath}")


def write_prerequisites() -> None:
    """Build a top-level common Prerequisites page (MDM- and platform-agnostic).

    Each deployment guide still owns its small platform-specific prereqs table
    (Win32 Content Prep Tool, APNs cert, etc.) — this page consolidates what
    every rollout needs regardless of MDM or OS.
    """
    lines = []
    lines.append("---")
    lines.append("title: Prerequisites")
    lines.append("description: Shared prerequisites for every Quilr Endpoint Agent deployment (Windows + macOS, all MDMs).")
    lines.append("---")
    lines.append("")
    lines.append("# Prerequisites")
    lines.append("")
    lines.append(
        "Common requirements that apply to **every** Quilr Endpoint Agent rollout — "
        "Windows or macOS, Intune / Jamf / Kandji / ManageEngine / manual. Each "
        "deployment guide additionally lists a short **platform-specific** prereq "
        "table (e.g. Intune Win32 Content Prep Tool, Jamf inventory freshness)."
    )
    lines.append("")
    lines.append("## What you need before starting")
    lines.append("")
    lines.append("| Requirement | Details |")
    lines.append("|---|---|")
    lines.append("| **Quilr environment** | Know which Quilr tenant your bundle was built against (e.g. `quilr-saas-usa-prod`, `quilr-saas-japan`, `quilr-saas-ind-prod`). The environment determines which backplane hosts you allowlist in [§ Firewall and Network Allowlist](#firewall-and-network-allowlist). Confirm with Quilr support if unsure. |")
    lines.append("| **Install bundle** | Latest signed install bundle obtained from Quilr support (`support@quilr.ai`). Verify the checksum before extracting. Bundle contents differ by platform &mdash; Windows: `quilr-endpoint-agent.msi` + 2 CA `.crt`s. macOS: `quilr-endpoint-agent-installer.pkg` + 2 CA `.cer`s + Configuration Profile templates. |")
    lines.append("| **MDM access** | Admin rights on your MDM platform: *Microsoft Intune* (Intune Administrator), *Jamf Pro* (Site or Cloud admin), *Kandji* (admin), *ManageEngine Endpoint Central* (admin). For macOS the device must be **MDM-supervised** (DEP / Automated Device Enrollment is preferred so System / Network Extensions are auto-approved). |")
    lines.append("| **Endpoint OS** | **Windows:** 10 1809+ or 11, x64 only. **macOS:** 12 Monterey or later, Apple Silicon or Intel. Older OS versions are not supported by the agent's WFP driver / System Extension. |")
    lines.append("| **Network egress (TCP 443)** | Endpoints must reach the Quilr backplane hosts on TCP 443. The full allowlist (shared hosts + per-tenant Base URL / DLP) is in [§ Firewall and Network Allowlist](#firewall-and-network-allowlist) below. |")
    lines.append("| **TLS-intercepting SWG** (if used) | Zscaler / Netskope / Symantec WSS / Forcepoint / iboss must **SSL-bypass** every Quilr backplane host. The agent pins TLS against Quilr's internal CA chain (deployed in Part 2 of each guide) &mdash; SWG re-signing breaks the handshake. |")
    lines.append("| **Pilot group** | A small group of devices (suggested naming `Quilr-Pilot`) to validate against before broad rollout. Promote to `Quilr-Production` after validation. |")
    lines.append("| **CA trust deployment** | The agent's leaf cert chains to a Quilr root + intermediate that must land in the system trust store **before** the agent service starts. Each deployment guide's *Part 2* covers this. |")
    lines.append("")
    lines.append("## Platform-specific add-ons")
    lines.append("")
    lines.append(
        "Each guide lists the tools / preconditions unique to that MDM. Quick "
        "pointer to where the platform-specific prereqs live:"
    )
    lines.append("")
    lines.append("| MDM / path | Platform-specific prereqs in |")
    lines.append("|---|---|")
    lines.append("| Microsoft Intune (Windows) | [Intune — Windows guide § Prerequisites](/deployment/intune-windows#2-prerequisites) |")
    lines.append("| Microsoft Intune (macOS) | [Intune — macOS guide § Prerequisites](/deployment/intune-macos#2-prerequisites) |")
    lines.append("| Jamf Pro | [Jamf Pro guide § Prerequisites](/deployment/jamf#2-prerequisites) |")
    lines.append("| Kandji | [Kandji guide § Prerequisites](/deployment/kandji#2-prerequisites) |")
    lines.append("| ManageEngine Endpoint Central | [ManageEngine guide § Prerequisites](/deployment/manageengine-msi#2-prerequisites) |")
    lines.append("| Manual macOS install | [Manual install guide § Prerequisites](/deployment/macos-manual#2-prerequisites) |")
    lines.append("")
    # ─── Firewall and Network Allowlist (inlined, common across all guides) ───
    lines.append("## Firewall and Network Allowlist")
    lines.append("")
    lines.append(
        "The Quilr Endpoint Agent makes outbound **HTTPS (TCP 443)** to a small set of "
        "Quilr backplane hosts. Where the perimeter is enforced — corporate firewall, "
        "egress proxy, or TLS-intercepting Secure Web Gateway (Zscaler, Netskope, "
        "Symantec, Forcepoint, etc.) — these hosts must be allowed **before** the agent "
        "installer is deployed."
    )
    lines.append("")
    lines.append(":::info Pick the row that matches your tenant")
    lines.append(
        "The host set depends on which Quilr environment your bundle was built against "
        "(`bff`, `dlpPrefix`, `updateUrlPrefix`). Confirm with Quilr support if you are "
        "unsure which environment applies."
    )
    lines.append(":::")
    lines.append("")
    lines.append("### Step A. Quilr control-plane hosts")
    lines.append("")
    lines.append("**Shared across all environments** — allowlist these regardless of tenant:")
    lines.append("")
    lines.append("| Host | Purpose |")
    lines.append("|---|---|")
    lines.append("| `discover.quilrai.dev` | Tenant / endpoint discovery |")
    lines.append("| `log.quilrai.dev` | Diagnostic log shipping (enabled when diagnostics are turned on) |")
    lines.append("| `quilr-extensions.quilr.ai` | Browser-extension / agent update distribution (default CDN) |")
    lines.append("")
    lines.append("**Per-environment** — pick the row that matches your tenant:")
    lines.append("")
    lines.append("| Environment | Base URL | DLP |")
    lines.append("|---|---|---|")
    lines.append("| `quilr-saas` (US — default) | `app.quilr.ai` | `dlpone.quilr.ai` |")
    lines.append("| `quilr-saas-ind` (IN) | `platform.quilr.ai` | `dlp-platform.quilr.ai` |")
    lines.append("| `quilr-saas-ind-prod` (IN, `.com`) | `platform.quilrai.com` | `dlp-platform.quilrai.com` |")
    lines.append("| `quilr-saas-usa-prod` (US, `.com`) | `app.quilrai.com` | `dlpone.quilrai.com` |")
    lines.append("| `quilr-saas-japan` | `app-jp.quilr.ai` | `dlpone-jp-1.quilr.ai` |")
    lines.append("| `poc-saas-uae` | `trust.quilr.ai` | `dlp-platform.quilr.ai` |")
    lines.append("| `quilr-saas-psr` (pre-prod) | `psr.quilr.ai` | `dlppreprod.quilr.ai` |")
    lines.append("| `quartz` | `quartz.quilr.ai` | `dlpone.quilr.ai` |")
    lines.append("| `quilr-poc2` | `secure.quilr.ai` | `dlpone.quilr.ai` |")
    lines.append("")
    lines.append(":::note Dedicated PaaS / on-prem deployments")
    lines.append(
        "If your tenant runs on a customer-owned domain (your own DNS / on-prem control "
        "plane), the shared hosts above still apply — Quilr support provides the tailored "
        "Base URL + DLP allowlist for your specific deployment. Contact `support@quilr.ai`."
    )
    lines.append(":::")
    lines.append("")
    lines.append("### Step B. Additional update / artifact CDN (env-specific)")
    lines.append("")
    lines.append(
        "Most environments use the default `quilr-extensions.quilr.ai` (already in Step A). "
        "A few environments use an additional CDN — allowlist the matching row **in "
        "addition to** Step A:"
    )
    lines.append("")
    lines.append("| Host | Used by environments |")
    lines.append("|---|---|")
    lines.append("| `quilr-extensions.quilrai.com` | `quilr-saas-ind-prod`, `quilr-saas-usa-prod` |")
    lines.append("| `quilr-hub.quilr.ai` | `quilr-poc2` |")
    lines.append("")
    lines.append("If your environment is not listed above, Step A alone covers update distribution.")
    lines.append("")
    lines.append("### Step C. TLS-intercepting proxies — SSL-bypass")
    lines.append("")
    lines.append(
        "If your egress sits behind Zscaler / Netskope / Symantec WSS / Forcepoint / iboss "
        "/ etc., add **every** host from Steps A and B to the **SSL-bypass** (no TLS "
        "inspection) list. The agent pins TLS to Quilr's internal CA chain (deployed in "
        "Part 2 of each deployment guide) — re-signing through the SWG's CA breaks the "
        "handshake and the agent will fail to connect."
    )
    lines.append("")
    lines.append(
        "For the *upstream* SWG rules covering monitored **AI** hosts (ChatGPT, Claude, "
        "Gemini, etc.), see the companion [URL Exception List — AI Apps](/reference/url-exceptions-ai) "
        "and [URL Exception List — Non-AI Apps](/reference/url-exceptions-nonai) — those "
        "cover apps the agent **inspects**, not the Quilr backplane itself."
    )
    lines.append("")
    lines.append("### Step D. Validate egress from a pilot device")
    lines.append("")
    lines.append("From a pilot endpoint, verify reachability **before** installing the agent:")
    lines.append("")
    lines.append("**Windows (PowerShell, elevated):**")
    lines.append("")
    lines.append("```powershell")
    lines.append("# Replace the first two hosts with the row from Step A that matches your tenant.")
    lines.append("$targets = @(")
    lines.append("    'app.quilr.ai',              # Base URL")
    lines.append("    'dlpone.quilr.ai',           # DLP")
    lines.append("    'discover.quilrai.dev',      # Discover (shared)")
    lines.append("    'log.quilrai.dev',           # Diagnostic log (shared)")
    lines.append("    'quilr-extensions.quilr.ai'  # Update / extension CDN (shared)")
    lines.append(")")
    lines.append("foreach ($h in $targets) {")
    lines.append("    $ok = Test-NetConnection -ComputerName $h -Port 443 `")
    lines.append("            -InformationLevel Quiet -WarningAction SilentlyContinue")
    lines.append("    \"{0,-40}  TCP/443  {1}\" -f $h, $(if ($ok) { 'OK' } else { 'BLOCKED' })")
    lines.append("}")
    lines.append("```")
    lines.append("")
    lines.append("**macOS (same allowlist applies — the agent backplane is platform-agnostic):**")
    lines.append("")
    lines.append("```bash")
    lines.append("for h in app.quilr.ai dlpone.quilr.ai discover.quilrai.dev log.quilrai.dev quilr-extensions.quilr.ai; do")
    lines.append("  out=$(nc -zv -G 5 \"$h\" 443 2>&1)")
    lines.append("  if [[ \"$out\" == *succeeded* ]] || [[ \"$out\" == *open* ]]; then status=OK; else status=BLOCKED; fi")
    lines.append("  printf \"%-40s  TCP/443  %s\\n\" \"$h\" \"$status\"")
    lines.append("done")
    lines.append("```")
    lines.append("")
    lines.append(
        "Any `BLOCKED` host means the firewall / SWG / corporate proxy still needs "
        "adjustment. Re-run the test after the network team applies the allowlist."
    )
    lines.append("")
    lines.append("### Notes on endpoint firewalls")
    lines.append("")
    lines.append(
        "On a default install of either Windows or macOS, outbound TCP 443 is "
        "unrestricted — per-host outbound rules on the endpoint firewall are normally "
        "**not required**. The standard path is to allowlist Quilr backplane FQDNs at "
        "the **egress proxy / SWG / corporate firewall**, not on the per-endpoint "
        "Defender Firewall (Windows) or PF (macOS)."
    )
    lines.append("")
    lines.append(
        "If your fleet enforces an outbound block-by-default policy on the endpoint, each "
        "deployment guide's *Section 3* covers the platform-specific path: program-path "
        "allow rules for Windows Defender Firewall, PF anchors via the agent `.pkg` "
        "postinstall on macOS."
    )
    lines.append("")
    lines.append("## See also")
    lines.append("")
    lines.append("- [Validate Installation](/reference/validate-installation) &mdash; what to confirm after the rollout.")
    lines.append("- [Troubleshooting](/reference/troubleshooting) &mdash; common failure modes.")
    lines.append("- [URL Exception List — AI Apps](/reference/url-exceptions-ai) &mdash; AI hosts the agent monitors (SWG SSL-bypass on these too).")
    lines.append("")
    with open(os.path.join(DOCS, "prerequisites.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote docs/prerequisites.md")


def write_index() -> None:
    """Build the docs home page (becomes /index)."""
    lines = []
    lines.append("---")
    lines.append("title: Quilr Endpoint Agent")
    lines.append("description: Deployment, configuration, and troubleshooting guides for the Quilr Endpoint Agent (Windows + macOS).")
    lines.append("slug: /")
    lines.append("---")
    lines.append("")
    lines.append("# Quilr Endpoint Agent — Documentation")
    lines.append("")
    lines.append(
        "Operator-facing deployment, configuration, and troubleshooting guides for the "
        "**Quilr Endpoint Agent** (Windows + macOS). Use the sidebar or the tables below to jump in."
    )
    lines.append("")
    lines.append(":::tip Where to start")
    lines.append("- **First time deploying?** Read [Prerequisites](/prerequisites) first &mdash; it covers what every rollout needs regardless of platform or MDM.")
    lines.append("- **Rolling out Windows endpoints?** *Microsoft Intune — Windows (MSI)* or *ManageEngine Endpoint Central — Windows (MSI)*.")
    lines.append("- **Rolling out Macs?** Pick the MDM you use: *Intune — macOS*, *Jamf Pro*, or *Kandji*. Use *macOS Manual Install* for one-off / pilot machines.")
    lines.append("- **Already deployed?** See *Troubleshooting* and the *URL Exception Lists* under **Reference**.")
    lines.append(":::")
    lines.append("")
    lines.append("## Deployment Guides")
    lines.append("")
    lines.append("| Guide | Platform | Notes |")
    lines.append("|---|---|---|")
    platform = {
        "deployment/intune-windows": "Windows / MSI",
        "deployment/intune-macos": "macOS / pkg",
        "deployment/jamf": "macOS / pkg",
        "deployment/kandji": "macOS / pkg",
        "deployment/manageengine-msi": "Windows / MSI",
        "deployment/macos-manual": "macOS / pkg",
    }
    for src, dest, label, blurb in MAPPING:
        slug = dest.replace(".md", "")
        if not slug.startswith("deployment/"):
            continue
        lines.append(f"| [{label}](/{slug}) | {platform.get(slug, '—')} | {blurb} |")
    lines.append("")
    lines.append("## Reference")
    lines.append("")
    lines.append("| Guide | What it covers |")
    lines.append("|---|---|")
    for src, dest, label, blurb in MAPPING:
        slug = dest.replace(".md", "")
        if not slug.startswith("reference/"):
            continue
        lines.append(f"| [{label}](/{slug}) | {blurb} |")
    lines.append("")
    with open(os.path.join(DOCS, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote docs/index.md")


def main() -> None:
    # Clean docs/ to avoid stale files (keep .gitkeep if present)
    for entry in os.listdir(DOCS):
        path = os.path.join(DOCS, entry)
        if entry == ".gitkeep":
            continue
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    for src, dest, label, blurb in MAPPING:
        try:
            process_one(src, dest, label, blurb)
        except FileNotFoundError as e:
            print(f"SKIP (not found): {e}")
    write_prerequisites()
    write_index()


if __name__ == "__main__":
    main()
