"""Insert a new Endpoint Agent SOP step: 'Step 6 - Enable PAC Routing'.

New EA layout (8 steps; Browser Extension stays 7):
  1 Prereq  2 Validation  3 Manual  4 Verify Install  5 MDM
  6 Enable PAC Routing (NEW)  7 Verify MDM Install  8 Troubleshooting

Content: route monitored AI-app hosts through the agent's local proxy on
127.0.0.1:24080 via a PAC file obtained from Quilr support.

Idempotent. Phases:
  1. rename EA folders  Step 7->8 (Troubleshooting), Step 6->7 (Verify MDM)
  2. create the new Step 6 page
  3. rebuild the sidebar on every page (EA=8 / BE=7, own-section first)
  4. rebuild EA wizard nav (.wstep) + wcount + eyebrow -> 'of 8'
  5. retarget back/next on the affected EA pages (5, new 6, 7, 8)
  6. renumber remaining cross-references (qualified + EA-sibling + root card grid)

Run on the server (ROOT default) or against a local mirror via SOP_ROOT env var.
"""
import os
import re
import shutil
import pathlib

ROOT = pathlib.Path(os.environ.get('SOP_ROOT', '/home/ubuntu/quilr-docs-site/static/sop'))

EA = 'Endpoint Agent'
BE = 'Browser Extension'

def enc(slug):
    return slug.replace(' ', '%20')

# Canonical step tables AFTER the change.
# (num, folder-slug, sidebar-label, wstep-short-label)
EA_STEPS = [
    (1, 'Step 1 - Prerequisites',                  'Prerequisites',            'Prerequisites'),
    (2, 'Step 2 - Prerequisites Validation',       'Prerequisites Validation', 'Validation'),
    (3, 'Step 3 - Manual Installation',            'Manual Installation',      'Manual Install'),
    (4, 'Step 4 - Validation Manual Installation', 'Validate Manual Install',  'Verify Install'),
    (5, 'Step 5 - Installing using MDM',           'Installing using MDM',     'MDM Rollout'),
    (6, 'Step 6 - Enable PAC Routing',             'Enable PAC Routing',       'PAC Routing'),
    (7, 'Step 7 - Verify MDM Install',             'Verify MDM Install',       'Verify MDM'),
    (8, 'Step 8 - Troubleshooting',                'Troubleshooting',          'Troubleshoot'),
]
BE_STEPS = [
    (1, 'Step 1 - Prerequisites',                  'Prerequisites',            'Prerequisites'),
    (2, 'Step 2 - Prerequisites Validation',       'Prerequisites Validation', 'Validation'),
    (3, 'Step 3 - Manual Installation',            'Manual Installation',      'Manual Install'),
    (4, 'Step 4 - Validation Manual Installation', 'Validate Manual Install',  'Verify Install'),
    (5, 'Step 5 - Installing using MDM',           'Installing using MDM',     'MDM Rollout'),
    (6, 'Step 6 - Verify MDM Install',             'Verify MDM Install',       'Verify MDM'),
    (7, 'Step 7 - Troubleshooting',                'Troubleshooting',          'Troubleshoot'),
]
STEPS = {EA: EA_STEPS, BE: BE_STEPS}
EA_NUM_BY_SLUG = {slug: num for num, slug, _l, _w in EA_STEPS}

NEW_SLUG = 'Step 6 - Enable PAC Routing'


# ───────────────────────── shared builders ─────────────────────────
def build_sidebar_block(section_name, current_slug, is_current_section, page_depth):
    prefix = '../' * page_depth if page_depth > 0 else ''
    section_prefix = '../' if is_current_section else f'{prefix}{enc(section_name)}/'
    lines = [f'    <div class="nav-group-title">{section_name}</div>', '    <ul class="nav">']
    for num, slug, label, _w in STEPS[section_name]:
        cls = ' class="active"' if (is_current_section and slug == current_slug) else ''
        href = f'{section_prefix}{enc(slug)}/index.html'
        lines.append(f'      <li><a{cls} href="{href}"><span class="step-num">{num}</span> {label}</a></li>')
    lines.append('    </ul>')
    return '\n'.join(lines) + '\n'


def build_ea_wstep(current_slug):
    out = []
    for num, slug, _l, wlabel in EA_STEPS:
        cls = 'wstep current' if slug == current_slug else 'wstep'
        out.append(
            f'        <a class="{cls}" href="../{enc(slug)}/index.html">'
            f'<span class="wdot">{num}</span><span class="wlabel">{wlabel}</span></a>'
        )
    return '\n'.join(out)


BE_FIRST_RE = re.compile(
    r'    <div class="nav-group-title">Browser Extension</div>\n    <ul class="nav">\n'
    r'(?:      <li>.*?</li>\n)+    </ul>\n\n?'
    r'    <div class="nav-group-title">Endpoint Agent</div>\n    <ul class="nav">\n'
    r'(?:      <li>.*?</li>\n)+    </ul>\n',
    re.MULTILINE,
)
EA_FIRST_RE = re.compile(
    r'    <div class="nav-group-title">Endpoint Agent</div>\n    <ul class="nav">\n'
    r'(?:      <li>.*?</li>\n)+    </ul>\n\n?'
    r'    <div class="nav-group-title">Browser Extension</div>\n    <ul class="nav">\n'
    r'(?:      <li>.*?</li>\n)+    </ul>\n',
    re.MULTILINE,
)


def rewrite_sidebar(path, text):
    if BE_FIRST_RE.search(text):
        sidebar_re, order = BE_FIRST_RE, [BE, EA]
    elif EA_FIRST_RE.search(text):
        sidebar_re, order = EA_FIRST_RE, [EA, BE]
    else:
        return text, False
    rel = path.relative_to(ROOT).parts
    if len(rel) >= 3 and rel[0] in STEPS:
        cur_section, cur_slug, depth = rel[0], rel[1], len(rel) - 1
    else:
        cur_section, cur_slug, depth = None, None, 0
    block = ''.join(
        build_sidebar_block(sec, cur_slug, sec == cur_section, depth) for sec in order
    )
    return sidebar_re.sub(lambda _m: block, text, count=1), True


# ───────────────────────── phase 1: rename ─────────────────────────
def mv(a, b):
    pa, pb = ROOT / EA / a, ROOT / EA / b
    if pb.exists():
        print(f'[1] {b} already exists — skip')
    elif pa.exists():
        shutil.move(str(pa), str(pb))
        print(f'[1] renamed: {a} -> {b}')
    else:
        print(f'[1] WARN: neither {a} nor {b} present')

mv('Step 7 - Troubleshooting', 'Step 8 - Troubleshooting')
mv('Step 6 - Verify MDM Install', 'Step 7 - Verify MDM Install')


# ───────────────────────── phase 2: new page ─────────────────────────
NEW_DIR = ROOT / EA / NEW_SLUG
NEW_PAGE = NEW_DIR / 'index.html'

CONTENT_BODY = '''      <span class="eyebrow">Endpoint Agent · Step 6 of 8</span>
      <h1>Enable PAC Routing</h1>
      <p class="lead">To let the Quilr agent inspect AI-app traffic through its proxy path, route the monitored AI &amp;
      collaboration hosts to the agent&rsquo;s <strong>local proxy listening on <code>127.0.0.1:24080</code></strong>. Quilr ships a
      ready Proxy Auto-Config (PAC) file that does exactly this &mdash; <strong>contact Quilr support for the PAC file for your AI apps.</strong></p>

      <div class="callout crit">
        <span class="ico">&#x1F4E9;</span>
        <div><span class="ct">Get the PAC file from Quilr support</span>
        Email <a href="mailto:support@quilr.ai">support@quilr.ai</a> and request the <strong>AI-apps PAC file</strong> for your tenant.
        It is a standard <code>application/x-ns-proxy-autoconfig</code> document with a single <code>FindProxyForURL(url,&nbsp;host)</code>
        that sends monitored AI hosts to <code>PROXY 127.0.0.1:24080</code> and everything else <code>DIRECT</code>.</div>
      </div>

      <div class="callout note">
        <span class="ico">&#x2139;&#xFE0F;</span>
        <div><span class="ct">When is this needed?</span>
        The agent&rsquo;s on-device interception (WinDivert driver on Windows, Network Extension on macOS) captures AI traffic
        without any system proxy. Use PAC routing when your deployment intercepts via the local proxy instead of &mdash; or alongside
        &mdash; an existing SWG. If you already run a PAC-based web filter, <em>merge</em> Quilr&rsquo;s rule rather than replacing your file
        (see <a href="../Step%201%20-%20Prerequisites/index.html">Step&nbsp;1 &middot; Coexisting with an existing PAC</a>). If unsure which model applies, ask Quilr support.</div>
      </div>

      <h2>1 &middot; What the PAC does</h2>
      <p>The support-provided PAC matches the monitored AI &amp; collaboration hosts and returns the local proxy for them,
      leaving all other traffic <code>DIRECT</code>:</p>
      <div class="code"><div class="code-head"><span class="label"><span class="dot"></span>FindProxyForURL &mdash; AI apps</span><button class="copy-btn" data-label="Copy"><span class="cl">Copy</span></button></div>
<pre><code>function FindProxyForURL(url, host) {
    var quilrHosts = [
        "chatgpt.com", "*.oaiusercontent.com",
        "claude.ai", "api.anthropic.com",
        "gemini.google.com", "*.deepseek.com",
        "*.slack.com", "teams.microsoft.com"
        /* full list supplied by Quilr support */
    ];
    for (var i = 0; i &lt; quilrHosts.length; i++) {
        if (shExpMatch(host, quilrHosts[i])) {
            return "PROXY 127.0.0.1:24080; DIRECT";
        }
    }
    return "DIRECT";
}</code></pre></div>
      <div class="callout warn"><span class="ico">&#x26A0;&#xFE0F;</span><div><span class="ct">Keep the host list authoritative</span>
      Use the list inside the PAC file Quilr support sends &mdash; it is kept in sync with the monitored-apps set. The snippet above is
      illustrative and trimmed.</div></div>

      <h2>2 &middot; Point the device at the PAC</h2>
      <p>Host the PAC file where managed devices can reach it (an internal HTTPS URL, or the hosted URL Quilr support provides),
      then set the OS proxy <em>auto-configuration</em> setting to that URL. Push it through your MDM the same way you deployed the
      agent in <a href="../Step%205%20-%20Installing%20using%20MDM/index.html">Step&nbsp;5</a>.</p>
      <div class="tabs">
        <div class="tab-btns">
          <button class="tab-btn active" data-tab="win"> Windows</button>
          <button class="tab-btn" data-tab="mac"> macOS</button>
          <button class="tab-btn" data-tab="manual"> Manual (single device)</button>
        </div>
        <div class="tab-panel active" data-panel="win">
          <p><strong>Intune &rarr; Devices &rarr; Configuration &rarr; Settings Catalog</strong>, search <em>Proxy</em>, enable
          <strong>Configure proxy server settings</strong>:</p>
          <ul>
            <li>Proxy server type: <strong>Automatic proxy configuration</strong></li>
            <li>Setup script address: <code>&lt;your PAC URL&gt;</code></li>
          </ul>
          <p>Or per-browser via Edge/Chrome <code>ProxySettings</code> policy: <code>ProxyMode = "pac_script"</code>,
          <code>ProxyPacUrl = &lt;your PAC URL&gt;</code>.</p>
        </div>
        <div class="tab-panel" data-panel="mac">
          <p>Deploy a Custom Configuration Profile (Device channel) with a <code>com.apple.proxy.AutoConfig.url</code> payload:</p>
          <div class="code"><div class="code-head"><span class="label"><span class="dot"></span>mobileconfig payload</span><button class="copy-btn" data-label="Copy"><span class="cl">Copy</span></button></div>
<pre><code>&lt;key&gt;PayloadType&lt;/key&gt;            &lt;string&gt;com.apple.proxy.AutoConfig.url&lt;/string&gt;
&lt;key&gt;ProxyAutoConfigEnable&lt;/key&gt;  &lt;true/&gt;
&lt;key&gt;ProxyAutoConfigURLString&lt;/key&gt; &lt;string&gt;&lt;your PAC URL&gt;&lt;/string&gt;</code></pre></div>
        </div>
        <div class="tab-panel" data-panel="manual">
          <ul>
            <li><strong>Windows</strong> &mdash; Settings &rarr; Network &amp; internet &rarr; Proxy &rarr; <em>Use setup script</em>, paste the PAC URL.</li>
            <li><strong>macOS</strong> &mdash; System Settings &rarr; Network &rarr; &lt;interface&gt; &rarr; Details &rarr; Proxies &rarr; <em>Automatic Proxy Configuration</em>, paste the PAC URL.</li>
          </ul>
        </div>
      </div>

      <h2>3 &middot; Confirm the route</h2>
      <p>After the PAC applies, a monitored AI host should resolve through the local proxy. Reload the agent&rsquo;s policy or reboot,
      then open an AI site &mdash; the proxy on <code>127.0.0.1:24080</code> handles the TLS and a <code>flow.matched</code> event appears in
      the agent log (see the checks in <a href="../Step%207%20-%20Verify%20MDM%20Install/index.html">Step&nbsp;7 &middot; Verify MDM Install</a>).</p>
      <div class="callout warn"><span class="ico">&#x1F50E;</span><div><span class="ct">Pair with SSL-bypass</span>
      If an upstream SWG sits in front of these hosts, add the monitored AI hosts to its <em>Do Not Decrypt</em> list so it does not
      re-sign the certificate &mdash; otherwise the agent&rsquo;s pinning fails regardless of PAC routing.</div></div>

      <div class="callout tip">
        <span class="ico">&#x2705;</span>
        <div><span class="ct">Exit criteria for Step 6</span>
        PAC file obtained from Quilr support &middot; PAC URL pushed to the pilot device&rsquo;s proxy auto-config setting &middot; a monitored AI
        host routes through <code>127.0.0.1:24080</code>. Then continue to Step&nbsp;7 to verify the rollout.</div>
      </div>

      <div class="wizard-nav">
        <a class="wbtn back" href="../Step%205%20-%20Installing%20using%20MDM/index.html"><span>&larr;</span><span class="wbt"><small>Back</small><b>MDM Rollout</b></span></a>
        <span class="wcount">Step 6 of 8</span>
        <a class="wbtn next" href="../Step%207%20-%20Verify%20MDM%20Install/index.html"><span class="wbt"><small>Next</small><b>Verify MDM Install</b></span><span>&rarr;</span></a>
      </div>
'''

def new_page_html():
    sidebar = (
        build_sidebar_block(EA, NEW_SLUG, True, 2)
        + build_sidebar_block(BE, NEW_SLUG, False, 2)
    )
    wstep = build_ea_wstep(NEW_SLUG)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Step 6 · Enable PAC Routing — Quilr Endpoint Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="../../assets/styles.css" />

  <!-- sop-favicon v1 -->
  <link rel="icon" type="image/png" href="/sop/assets/quilr-icon.png" />
  <link rel="apple-touch-icon" href="/sop/assets/quilr-icon.png" />
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="brand">
      <div class="logo">Q</div>
      <div><div class="brand-name">Quilr&nbsp;AI</div><div class="brand-sub">Deployment SOP</div></div>
    </div>
    <div class="nav-group-title">Overview</div>
    <ul class="nav"><li><a href="../../index.html">Start here</a></li></ul>
{sidebar}    <div class="sidebar-foot">
      Source: <a href="https://installdocs.quilrai.dev" target="_blank" rel="noopener">installdocs.quilrai.dev</a><br />
      Support: <a href="mailto:support@quilr.ai">support@quilr.ai</a>
    </div>
  </aside>
  <div class="scrim"></div>

  <main class="main">
    <header class="topbar">
      <button class="menu-btn" aria-label="Open navigation">☰</button>
      <nav class="crumbs">
        <a href="../../index.html">SOP</a><span class="sep">/</span>
        <a href="../../index.html">Endpoint Agent</a><span class="sep">/</span>
        <span class="here">Step 6 · Enable PAC Routing</span>
      </nav>
    </header>

    <div class="content">
      <nav class="wizard" aria-label="Endpoint Agent deployment steps">
{wstep}
      </nav>

{CONTENT_BODY}    </div>
  </main>
</div>
<script src="../../assets/app.js"></script>
</body>
</html>
'''

if NEW_PAGE.exists():
    print(f'[2] {NEW_SLUG} already exists — skip create')
else:
    NEW_DIR.mkdir(parents=True, exist_ok=True)
    NEW_PAGE.write_text(new_page_html(), encoding='utf-8')
    print(f'[2] created: {NEW_SLUG}/index.html')


# ───────────────────────── phases 3-6 over every page ─────────────────────────
WIZ_RE = re.compile(r'<nav class="wizard" aria-label="Endpoint Agent deployment steps">[\s\S]*?</nav>')
WCOUNT_RE = re.compile(r'<span class="wcount">Step \d+ of \d+</span>')
EYEBROW_RE = re.compile(r'(<span class="eyebrow">Endpoint Agent · Step )\d+ of \d+(</span>)')

# Phase-5 targeted back/next edits, keyed by EA directory slug.
BACKNEXT = {
    'Step 5 - Installing using MDM': [
        ('<a class="wbtn next" href="../Step%206%20-%20Verify%20MDM%20Install/index.html"><span class="wbt"><small>Next</small><b>Verify MDM Install</b></span><span>→</span></a>',
         '<a class="wbtn next" href="../Step%206%20-%20Enable%20PAC%20Routing/index.html"><span class="wbt"><small>Next</small><b>Enable PAC Routing</b></span><span>→</span></a>'),
    ],
    'Step 7 - Verify MDM Install': [
        ('<a class="wbtn back" href="../Step%205%20-%20Installing%20using%20MDM/index.html"><span>←</span><span class="wbt"><small>Back</small><b>MDM Rollout</b></span></a>',
         '<a class="wbtn back" href="../Step%206%20-%20Enable%20PAC%20Routing/index.html"><span>←</span><span class="wbt"><small>Back</small><b>Enable PAC Routing</b></span></a>'),
        ('<a class="wbtn next" href="../Step%207%20-%20Troubleshooting/index.html"><span class="wbt"><small>Next</small><b>Troubleshooting</b></span><span>→</span></a>',
         '<a class="wbtn next" href="../Step%208%20-%20Troubleshooting/index.html"><span class="wbt"><small>Next</small><b>Troubleshooting</b></span><span>→</span></a>'),
    ],
    'Step 8 - Troubleshooting': [
        ('<a class="wbtn back" href="../Step%206%20-%20Verify%20MDM%20Install/index.html"><span>←</span><span class="wbt"><small>Back</small><b>Verify MDM Install</b></span></a>',
         '<a class="wbtn back" href="../Step%207%20-%20Verify%20MDM%20Install/index.html"><span>←</span><span class="wbt"><small>Back</small><b>Verify MDM Install</b></span></a>'),
    ],
}

sb_count = wiz_count = 0
for path in sorted(ROOT.rglob('index.html')):
    rel = path.relative_to(ROOT).parts
    section = rel[0] if (len(rel) >= 3 and rel[0] in STEPS) else None
    slug = rel[1] if section else None
    text = original = path.read_text(encoding='utf-8')

    # Phase 3 — sidebar rebuild (all pages)
    text, did = rewrite_sidebar(path, text)
    if did:
        sb_count += 1

    if section == EA:
        # Phase 4 — EA wizard nav + counters
        new_num = EA_NUM_BY_SLUG.get(slug)
        if new_num:
            text = WIZ_RE.sub(
                lambda _m: ('<nav class="wizard" aria-label="Endpoint Agent deployment steps">\n'
                            + build_ea_wstep(slug) + '\n      </nav>'),
                text, count=1)
            text = WCOUNT_RE.sub(f'<span class="wcount">Step {new_num} of 8</span>', text, count=1)
            text = EYEBROW_RE.sub(lambda m: f'{m.group(1)}{new_num} of 8{m.group(2)}', text, count=1)
            wiz_count += 1

        # Phase 5 — targeted back/next (BEFORE the sibling renumber in phase 6)
        for old, new in BACKNEXT.get(slug, []):
            if old in text:
                text = text.replace(old, new, 1)

        # Phase 6b — EA-sibling link renumber for the shifted steps (prose links)
        text = text.replace('../Step%206%20-%20Verify%20MDM%20Install', '../Step%207%20-%20Verify%20MDM%20Install')
        text = text.replace('../Step%207%20-%20Troubleshooting', '../Step%208%20-%20Troubleshooting')

    # Phase 6a — qualified cross-section refs (safe on every page: sidebar, root card grid, prose)
    text = text.replace('Endpoint%20Agent/Step%206%20-%20Verify%20MDM%20Install', 'Endpoint%20Agent/Step%207%20-%20Verify%20MDM%20Install')
    text = text.replace('Endpoint%20Agent/Step%207%20-%20Troubleshooting', 'Endpoint%20Agent/Step%208%20-%20Troubleshooting')

    if text != original:
        path.write_text(text, encoding='utf-8')

print(f'[3] sidebar rebuilt on {sb_count} pages')
print(f'[4/5/6] EA wizard/nav updated on {wiz_count} pages')
print('\nDONE.')
