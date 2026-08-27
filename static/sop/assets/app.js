/* Quilr Deployment SOP — interactions:
   copy buttons · platform tabs · mobile nav · per-step Platform + Environment filter */
(function () {
  "use strict";

  /* ---------- Tenant environments (base + DLP hosts) ---------- */
  var ENVS = {
    quartz:  { label: "Quartz",   base: "quartz.quilr.ai",      dlp: "dlpone.quilr.ai", auth: "trust.quilr.ai" },
    secure:  { label: "Secure",   base: "secure.quilr.ai",      dlp: "dlpone.quilr.ai", auth: "secure.quilr.ai" },
    uspoc:   { label: "US POC",   base: "app.quilr.ai",         dlp: "dlpone.quilr.ai", auth: "auth-extension.quilr.ai" },
    indpoc:  { label: "IND POC",  base: "platform.quilr.ai",    dlp: "dlp-platform.quilr.ai", auth: "auth-platform.quilr.ai" },
    usprod:  { label: "US Prod",  base: "app.quilrai.com",      dlp: "dlpone.quilrai.com", auth: "app.quilrai.com" },
    indprod: { label: "IND Prod", base: "platform.quilrai.com", dlp: "dlp-platform.quilrai.com", auth: "platform.quilrai.com" },
    jppoc:   { label: "JP POC",   base: "app-jp.quilr.ai",      dlp: "dlpone-jp-1.quilr.ai", auth: "app-jp.quilr.ai" },
    uaepoc:  { label: "UAE POC",  base: "trust.quilr.ai",       dlp: "dlp-platform.quilr.ai", auth: "trust.quilr.ai" }
  };
  // Legacy keys persisted in localStorage from the previous 4-env build.
  var ENV_ALIASES = { us: "uspoc", usa: "usprod", japan: "jppoc", india: "indprod" };

  /* ---------- Which OS each tab panel belongs to ---------- */
  var WIN_PANELS = ["win", "fwin", "cwin", "wman", "intune-win", "me", "sccm"];
  var MAC_PANELS = ["mac", "fmac", "cmac", "mman", "intune-mac", "jamf", "kandji"];
  function panelOS(key) {
    if (WIN_PANELS.indexOf(key) !== -1) return "win";
    if (MAC_PANELS.indexOf(key) !== -1) return "mac";
    return "any";
  }

  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function recall(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }

  /* ---------- Copy-to-clipboard ---------- */
  function wireCopy() {
    document.querySelectorAll(".copy-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var block = btn.closest(".code");
        var pre = block && block.querySelector("pre");
        if (!pre) return;
        var text = pre.innerText;
        var done = function () {
          btn.classList.add("copied");
          var lbl = btn.querySelector(".cl");
          if (lbl) lbl.textContent = "Copied";
          setTimeout(function () {
            btn.classList.remove("copied");
            if (lbl) lbl.textContent = btn.dataset.label || "Copy";
          }, 1600);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, fallback);
        } else { fallback(); }
        function fallback() {
          var ta = document.createElement("textarea");
          ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
          document.body.appendChild(ta); ta.select();
          try { document.execCommand("copy"); done(); } catch (e) {}
          document.body.removeChild(ta);
        }
      });
    });
  }

  /* ---------- Tabs (manual click within a group) ---------- */
  function wireTabs() {
    document.querySelectorAll(".tabs").forEach(function (group) {
      var btns = group.querySelectorAll(".tab-btn");
      var panels = group.querySelectorAll(".tab-panel");
      btns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          if (btn.hidden) return;
          var target = btn.dataset.tab;
          btns.forEach(function (b) { b.classList.toggle("active", b === btn); });
          panels.forEach(function (p) { p.classList.toggle("active", p.dataset.panel === target); });
        });
      });
    });
  }

  /* ---------- Platform filter: drive every tab group at once ---------- */
  function applyPlatform(os) {   /* os = "all" | "win" | "mac" */
    document.querySelectorAll(".tabs").forEach(function (group) {
      var btns = Array.prototype.slice.call(group.querySelectorAll(".tab-btn"));
      var panels = Array.prototype.slice.call(group.querySelectorAll(".tab-panel"));
      var visibleBtns = [];

      btns.forEach(function (btn) {
        var key = btn.dataset.tab;
        var show = (os === "all") || panelOS(key) === "any" || panelOS(key) === os;
        btn.hidden = !show;
        if (show) visibleBtns.push(btn);
      });

      // activate the first visible tab in this group
      var activeKey = visibleBtns.length ? visibleBtns[0].dataset.tab : null;
      btns.forEach(function (b) { b.classList.toggle("active", b.dataset.tab === activeKey); });
      panels.forEach(function (p) { p.classList.toggle("active", p.dataset.panel === activeKey); });

      // hide the button row when filtering leaves a single choice
      var bar = group.querySelector(".tab-btns");
      if (bar) bar.style.display = (os !== "all" && visibleBtns.length <= 1) ? "none" : "";

      // if a whole group has no matching panel, hide it entirely
      group.style.display = visibleBtns.length === 0 ? "none" : "";
    });

    // free-form platform-specific content (sections, rows, callouts)
    document.querySelectorAll("[data-os]").forEach(function (el) {
      var t = el.getAttribute("data-os");
      el.hidden = !(os === "all" || t === "any" || t === os);
    });
  }

  /* ---------- Environment filter: rewrite tenant hosts in code blocks ---------- */
  function snapshotCode() {
    document.querySelectorAll(".code pre").forEach(function (pre) {
      if (pre.dataset.orig === undefined) pre.dataset.orig = pre.innerHTML;
    });
    // Inline <code> elements outside <pre> blocks (table cells, list items,
    // paragraph spans). Their text may include env-sensitive hosts and we
    // want applyEnv() to rewrite them too.
    document.querySelectorAll("code").forEach(function (el) {
      if (el.closest("pre")) return;
      if (el.dataset.orig === undefined) el.dataset.orig = el.innerHTML;
    });
  }
  function applyEnv(envKey) {
    var resolvedKey = ENV_ALIASES[envKey] || envKey;
    var env = ENVS[resolvedKey] || ENVS.uspoc;
    function rewrite(el) {
      var html = el.dataset.orig;
      if (html === undefined) return;
      // originals use the US-default hosts as tokens; uspoc is the env-key sentinel
      html = html.split("app.quilr.ai").join(env.base)
                 .split("dlpone.quilr.ai").join(env.dlp)
                 .split("auth-extension.quilr.ai").join(env.auth)
                 .split("uspoc").join(resolvedKey);
      el.innerHTML = html;
    }
    function rewriteHref(a) {
      if (a.dataset.origHref === undefined) a.dataset.origHref = a.getAttribute("href") || "";
      var h = a.dataset.origHref;
      h = h.split("app.quilr.ai").join(env.base)
           .split("dlpone.quilr.ai").join(env.dlp)
           .split("auth-extension.quilr.ai").join(env.auth);
      a.setAttribute("href", h);
    }
    document.querySelectorAll(".code pre").forEach(rewrite);
    document.querySelectorAll("code").forEach(function (el) {
      if (el.closest("pre")) return;
      rewrite(el);
    });
    document.querySelectorAll("a[data-env-link]").forEach(rewriteHref);
    // highlight the matching row in any environment table
    document.querySelectorAll("table tr").forEach(function (tr) {
      tr.classList.toggle("env-active", tr.textContent.indexOf(env.base) !== -1);
    });
    // environment-specific content (table rows, notes) tagged with data-env
    document.querySelectorAll("[data-env]").forEach(function (el) {
      var t = el.getAttribute("data-env");
      el.hidden = !(t === "any" || t === envKey);
    });
  }

  /* ---------- Build the filter bar into the top bar ---------- */
  function buildFilterBar() {
    var wizard = document.querySelector(".wizard");
    var topbar = document.querySelector(".topbar");
    if (!wizard || !topbar) return;   // only on step pages

    var osVal = recall("quilr.os", "all");
    var envVal = recall("quilr.env", "uspoc"); envVal = ENV_ALIASES[envVal] || envVal;

    var bar = document.createElement("div");
    bar.className = "filterbar";

    var osSel = document.createElement("select");
    osSel.id = "f-os"; osSel.setAttribute("aria-label", "Filter by platform");
    [["all", "All platforms"], ["win", "Windows"], ["mac", "macOS"]].forEach(function (o) {
      var opt = document.createElement("option");
      opt.value = o[0]; opt.textContent = o[1]; if (o[0] === osVal) opt.selected = true;
      osSel.appendChild(opt);
    });

    var envSel = document.createElement("select");
    envSel.id = "f-env"; envSel.setAttribute("aria-label", "Select environment");
    Object.keys(ENVS).forEach(function (k) {
      var opt = document.createElement("option");
      opt.value = k; opt.textContent = ENVS[k].label; if (k === envVal) opt.selected = true;
      envSel.appendChild(opt);
    });

    var l1 = document.createElement("label"); l1.className = "fl"; l1.innerHTML = "<span>Platform</span>"; l1.appendChild(osSel);
    var l2 = document.createElement("label"); l2.className = "fl"; l2.innerHTML = "<span>Environment</span>"; l2.appendChild(envSel);
    bar.appendChild(l1); bar.appendChild(l2);
    topbar.appendChild(bar);

    osSel.addEventListener("change", function () { store("quilr.os", osSel.value); applyPlatform(osSel.value); });
    envSel.addEventListener("change", function () { store("quilr.env", envSel.value); applyEnv(envSel.value); });

    applyPlatform(osVal);
    applyEnv(envVal);
  }

  /* ---------- Mobile nav (no-op now panel is removed; harmless) ---------- */
  function wireNav() {
    var btn = document.querySelector(".menu-btn");
    if (btn) btn.addEventListener("click", function () { document.body.classList.toggle("nav-open"); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    wireCopy();
    wireTabs();
    wireNav();
    snapshotCode();
    buildFilterBar();
  });
})();


/* sop-feedback-widget v1 */
(function () {
  "use strict";

  var JIRA_BASE    = "https://quilr.atlassian.net";
  var JIRA_PROJECT = "PMM";

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") n.className = attrs[k];
      else if (k === "html") n.innerHTML = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else n.setAttribute(k, attrs[k]);
    });
    if (children) children.forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function build() {
    if (document.querySelector(".fb-btn")) return;  // idempotent

    var btn = el("button", {
      "class": "fb-btn",
      "type": "button",
      "aria-label": "Suggest an improvement or feature",
      "title": "Suggest an improvement (opens Jira PMM)",
      "html": '<span class="fb-ico" aria-hidden="true">\u2728</span><span class="fb-label">Suggest</span>'
    });
    // Park the button in the topbar so it sits next to the Platform/Env
    // selectors. Deferred to a microtask so we run after buildFilterBar()
    // (the filterbar is left-margin:auto, so anything after it lands far right).
    function placeBtn() {
      var topbar = document.querySelector(".topbar");
      if (topbar) { topbar.appendChild(btn); }
      else { document.body.appendChild(btn); btn.classList.add("fb-floating"); }
    }
    setTimeout(placeBtn, 0);

    var modal = el("div", { "class": "fb-modal", "role": "dialog", "aria-modal": "true", "aria-labelledby": "fb-title" });
    modal.innerHTML =
      '<div class="fb-modal-card">' +
        '<div class="fb-modal-head">' +
          '<h3 id="fb-title">Suggest improvement / feature</h3>' +
          '<button class="fb-close" type="button" aria-label="Close">\u00d7</button>' +
        '</div>' +
        '<p class="fb-sub">Files a ticket in the <strong>' + JIRA_PROJECT + '</strong> project on <code>quilr.atlassian.net</code>. Atlassian opens in a new tab &mdash; sign in if prompted and pick <strong>' + JIRA_PROJECT + '</strong> as the project; summary &amp; description are pre-filled (and copied to clipboard as a backup).</p>' +
        '<form class="fb-form" novalidate>' +
          '<label class="fb-l">Type' +
            '<select name="fb-type">' +
              '<option value="Improvement">Improvement</option>' +
              '<option value="Feature Request">Feature Request</option>' +
              '<option value="Bug">Bug</option>' +
              '<option value="Documentation">Documentation gap</option>' +
            '</select>' +
          '</label>' +
          '<label class="fb-l">Summary' +
            '<input name="fb-summary" type="text" maxlength="200" required placeholder="Short title (one line)" />' +
          '</label>' +
          '<label class="fb-l">Details' +
            '<textarea name="fb-description" rows="6" placeholder="What is the change, why does it matter, any links / screenshots?"></textarea>' +
          '</label>' +
          '<div class="fb-actions">' +
            '<button type="button" class="fb-cancel">Cancel</button>' +
            '<button type="submit" class="fb-submit">Open in Jira</button>' +
          '</div>' +
          '<p class="fb-hint" aria-live="polite"></p>' +
        '</form>' +
      '</div>';
    document.body.appendChild(modal);

    var summaryI = modal.querySelector('[name="fb-summary"]');
    var descT    = modal.querySelector('[name="fb-description"]');
    var typeS    = modal.querySelector('[name="fb-type"]');
    var hint     = modal.querySelector('.fb-hint');

    function pageContext() {
      var title = (document.title || "SOP page").trim();
      // Drop the trailing " | Quilr ..." breadcrumb if any.
      title = title.split(" \u00b7 ")[0].split(" | ")[0];
      return "--- Source ---\nPage: " + title + "\nURL: " + window.location.href + "\n\n--- Description ---\n";
    }

    function open() {
      if (!descT.value) descT.value = pageContext();
      modal.classList.add("fb-open");
      document.body.style.overflow = "hidden";
      setTimeout(function () { summaryI.focus(); }, 60);
    }
    function close() {
      modal.classList.remove("fb-open");
      document.body.style.overflow = "";
      hint.textContent = "";
    }
    btn.addEventListener("click", open);
    modal.querySelector(".fb-close").addEventListener("click", close);
    modal.querySelector(".fb-cancel").addEventListener("click", close);
    modal.addEventListener("click", function (e) { if (e.target === modal) close(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal.classList.contains("fb-open")) close();
    });

    modal.querySelector(".fb-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var summary = summaryI.value.trim();
      if (!summary) { summaryI.focus(); summaryI.classList.add("fb-err"); return; }
      summaryI.classList.remove("fb-err");
      var desc = descT.value.trim();
      var type = typeS.value;
      var fullSummary = "[" + type + "] " + summary;
      var clipboardBody = "Project: " + JIRA_PROJECT + "\nIssue Type: " + type + "\nSummary: " + summary + "\n\n" + desc;

      // Try clipboard so the user can paste if Jira's prefill is suppressed.
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try { navigator.clipboard.writeText(clipboardBody); } catch (err) {}
      }

      // Jira Cloud legacy prefill URL — accepts summary + description params.
      // Project + Issue Type left for the user to pick (we display the hint).
      var qs = "summary=" + encodeURIComponent(fullSummary) +
               "&description=" + encodeURIComponent(desc);
      var url = JIRA_BASE + "/secure/CreateIssueDetails!init.jspa?" + qs;
      window.open(url, "_blank", "noopener");

      hint.textContent = "Opened Jira in a new tab. Pick \"" + JIRA_PROJECT + "\" project. Content also copied to clipboard.";
      setTimeout(close, 1800);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
