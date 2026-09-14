"""Add an SCCM (Microsoft Configuration Manager) deployment playbook to the
Browser Extension MDM step (Step 5 - Installing using MDM).

SCCM is Windows-only and pushes the same Quilr.msi as the Intune · Windows and
ManageEngine tabs, using the MSI **Application** model. The force-install browser
policy is NOT re-documented here — it references the existing JSON shown in the
Intune · Windows / ManageEngine tabs and points AD-managed fleets at GPO.

Two edits, both idempotent:
  1. static/sop/Browser Extension/Step 5 - Installing using MDM/index.html
       - new "SCCM" tab button after ManageEngine
       - new data-panel="sccm" tab panel after the ManageEngine panel
  2. static/sop/assets/app.js
       - register "sccm" in WIN_PANELS so the platform filter treats it as
         Windows (otherwise the tab is hidden when filtering to Windows)
"""
import pathlib

ROOT = pathlib.Path('/home/ubuntu/quilr-docs-site/static/sop')

# ─────────────────────────────────────────────────────────────
# 1. Step 5 HTML — tab button + tab panel
# ─────────────────────────────────────────────────────────────
p = ROOT / 'Browser Extension' / 'Step 5 - Installing using MDM' / 'index.html'
text = p.read_text(encoding='utf-8')

if 'data-panel="sccm"' in text:
    print('[1] SCCM panel already present — skipping HTML edit')
else:
    # 1a. Tab button — after ManageEngine, before the closing </div> of .tab-btns
    BTN_ANCHOR = (
        '          <button class="tab-btn" data-tab="me"> ManageEngine</button>\n'
        '        </div>'
    )
    BTN_REPL = (
        '          <button class="tab-btn" data-tab="me"> ManageEngine</button>\n'
        '          <button class="tab-btn" data-tab="sccm"> SCCM</button>\n'
        '        </div>'
    )
    if BTN_ANCHOR not in text:
        raise SystemExit('FAIL: ManageEngine tab-button anchor not found verbatim')
    text = text.replace(BTN_ANCHOR, BTN_REPL, 1)

    # 1b. Tab panel — inserted between the ManageEngine panel close and the
    # .tabs close (which is immediately followed by the post-tabs H2).
    SCCM_PANEL = (
        '\n'
        '        <!-- SCCM -->\n'
        '        <div class="tab-panel" data-panel="sccm">\n'
        '          <h3>Microsoft Configuration Manager (SCCM) — Windows</h3>\n'
        '          <div class="part">\n'
        '            <div class="part-head"><span class="part-badge">1</span><h3>Stage the MSI source</h3></div>\n'
        '            <p>Download <code>https://quilr-extensions.quilr.ai/Quilr.msi</code> and place it on a UNC source share the site server can read, e.g. <code>\\\\sccm\\Sources\\Apps\\QuilrExtension\\Quilr.msi</code>.</p>\n'
        '          </div>\n'
        '          <div class="part">\n'
        '            <div class="part-head"><span class="part-badge">2</span><h3>Create the Application (MSI deployment type)</h3></div>\n'
        '            <p><strong>Software Library → Application Management → Applications → Create Application.</strong> Choose type <strong>Windows Installer (*.msi)</strong> and point it at <code>Quilr.msi</code>. Name &ldquo;Quilr Browser Extension,&rdquo; publisher &ldquo;Quilr AI.&rdquo; On the generated deployment type, override the install command line:</p>\n'
        '            <div class="code"><div class="code-head"><span class="label"><span class="dot"></span>cmd</span><button class="copy-btn" data-label="Copy"><span class="cl">Copy</span></button></div>\n'
        '<pre><code>msiexec /i "Quilr.msi" TENANT=&lt;TENANT-ID&gt; /qn /norestart</code></pre></div>\n'
        '            <div class="callout crit"><span class="ico">⛔</span><div><span class="ct">Parameter is TENANT</span> Same MSI and property as the Intune · Windows tab — mandatory, obtain from <a href="mailto:support@quilr.ai">support@quilr.ai</a>. Without it the extension installs but stays idle.</div></div>\n'
        '          </div>\n'
        '          <div class="part">\n'
        '            <div class="part-head"><span class="part-badge">3</span><h3>Detection, install behavior &amp; distribute</h3></div>\n'
        '            <p>Keep the auto-generated <strong>MSI product-code</strong> detection rule. Set installation behavior <em>Install for system</em> and logon requirement <em>Whether or not a user is logged on</em>. <strong>Distribute Content</strong> to your distribution points.</p>\n'
        '          </div>\n'
        '          <div class="part">\n'
        '            <div class="part-head"><span class="part-badge">4</span><h3>Deploy to a device collection</h3></div>\n'
        '            <p><strong>Deploy</strong> the application to the <code>WIN-Quilr-Extension</code> device collection with purpose <strong>Required</strong> and schedule <em>As soon as possible</em>; clients install on the next machine-policy cycle.</p>\n'
        '          </div>\n'
        '          <div class="part">\n'
        '            <div class="part-head"><span class="part-badge">5</span><h3>Optional · enforce via browser policy</h3></div>\n'
        '            <p>SCCM only ships the MSI. To force-install / pin the extension, deliver the <code>ExtensionInstallForcelist</code> / <code>ExtensionSettings</code> policy for extension ID <code>piajhjohgigijkddhdpgbjdcfhmammbk</code> via <strong>Active Directory Group Policy</strong> (Administrative Templates → Edge / Chrome) — the same JSON shown in the Intune · Windows and ManageEngine tabs. AD-managed fleets usually push this through GPO already.</p>\n'
        '          </div>\n'
        '        </div>\n'
    )

    PANEL_ANCHOR = (
        '        </div>\n'          # ManageEngine panel close
        '      </div>\n'            # .tabs close
        '\n'
        '      <h2>Validate after MDM rollout</h2>'
    )
    PANEL_REPL = (
        '        </div>\n'          # ManageEngine panel close
        + SCCM_PANEL
        + '      </div>\n'          # .tabs close
        '\n'
        '      <h2>Validate after MDM rollout</h2>'
    )
    if PANEL_ANCHOR not in text:
        raise SystemExit('FAIL: tabs-close / post-tabs H2 anchor not found verbatim')
    text = text.replace(PANEL_ANCHOR, PANEL_REPL, 1)

    p.write_text(text, encoding='utf-8')
    print(f'[1] OK: SCCM tab + panel inserted — Step 5 now {len(text)} bytes')

# ─────────────────────────────────────────────────────────────
# 2. app.js — register "sccm" as a Windows panel
# ─────────────────────────────────────────────────────────────
jp = ROOT / 'assets' / 'app.js'
js = jp.read_text(encoding='utf-8')

JS_OLD = '  var WIN_PANELS = ["win", "fwin", "cwin", "wman", "intune-win", "me"];'
JS_NEW = '  var WIN_PANELS = ["win", "fwin", "cwin", "wman", "intune-win", "me", "sccm"];'

if '"sccm"' in js and 'WIN_PANELS' in js and JS_OLD not in js:
    print('[2] app.js WIN_PANELS already includes "sccm" — skipping')
elif JS_OLD in js:
    js = js.replace(JS_OLD, JS_NEW, 1)
    jp.write_text(js, encoding='utf-8')
    print('[2] OK: "sccm" added to WIN_PANELS in app.js')
else:
    raise SystemExit('FAIL: WIN_PANELS line not found verbatim in app.js')

print('\nDONE. Rebuild/redeploy the SOP static site to publish.')
