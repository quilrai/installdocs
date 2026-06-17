// Quilr docs — sidebar platform filter.
// Adds a 3-button filter (All / macOS / Windows) to the top of the doc sidebar
// and hides Deployment items whose platform doesn't match the active choice.
// Reference items are untagged → always visible.
//
// State sources (in priority order):
//   1. URL query string `?platform=macos|windows|all`   ← shareable
//   2. localStorage     `quilr.sidebar.platform`        ← sticky across visits
//   3. fallback         `all`
//
// On change, BOTH the URL and localStorage are updated. After any client-side
// route change (Docusaurus React Router strips the query) the param is re-applied
// so the filter follows the user through the site and remains shareable.

import ExecutionEnvironment from '@docusaurus/ExecutionEnvironment';

const STORAGE_KEY = 'quilr.sidebar.platform';
const URL_PARAM = 'platform';
const VALID = new Set(['all', 'macos', 'windows']);

// Per-route → platform mapping. The leaf URLs that appear in the sidebar.
const PLATFORM_BY_PATH = {
  '/deployment/intune-macos':     'macos',
  '/deployment/jamf':             'macos',
  '/deployment/kandji':           'macos',
  '/deployment/macos-manual':     'macos',
  '/deployment/intune-windows':   'windows',
  '/deployment/manageengine-msi': 'windows',
  '/extension/intune-macos':     'macos',
  '/extension/intune-windows':   'windows',
  '/extension/jamf':             'macos',
  '/extension/kandji':           'macos',
  '/extension/manageengine-msi': 'windows',
  '/extension/macos-manual':     'macos',
};

// ─────────────────────── state helpers ───────────────────────

function readFromUrl() {
  try {
    const v = new URL(window.location.href).searchParams.get(URL_PARAM);
    return VALID.has(v) ? v : null;
  } catch (_) { return null; }
}

function readFromStorage() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return VALID.has(v) ? v : null;
  } catch (_) { return null; }
}

function writeStorage(v) {
  try { localStorage.setItem(STORAGE_KEY, v); } catch (_) {}
}

function writeUrl(v) {
  try {
    const url = new URL(window.location.href);
    const current = url.searchParams.get(URL_PARAM);
    if (v === 'all') {
      if (current !== null) {
        url.searchParams.delete(URL_PARAM);
        window.history.replaceState({}, '', url.pathname + (url.search || '') + url.hash);
      }
    } else if (current !== v) {
      url.searchParams.set(URL_PARAM, v);
      window.history.replaceState({}, '', url.pathname + url.search + url.hash);
    }
  } catch (_) {}
}

function getCurrent() {
  return readFromUrl() || readFromStorage() || 'all';
}

// ─────────────────────── apply to DOM ───────────────────────

function applyFilter(v, opts) {
  const value = VALID.has(v) ? v : 'all';
  document.documentElement.setAttribute('data-platform-filter', value);
  writeStorage(value);
  if (!opts || opts.syncUrl !== false) writeUrl(value);
  // Reflect on the widget buttons if it's been injected.
  document.querySelectorAll('.quilr-platform-filter-buttons button').forEach((b) => {
    const sel = b.dataset.platform === value;
    b.classList.toggle('active', sel);
    b.setAttribute('aria-selected', sel ? 'true' : 'false');
  });
  return value;
}

function pathKey(href) {
  try {
    const u = new URL(href, window.location.origin);
    return u.pathname.replace(/\/+$/, '');
  } catch (_) { return href || ''; }
}

function tagSidebar() {
  const menu = document.querySelector('.theme-doc-sidebar-menu');
  if (!menu) return;

  menu.querySelectorAll('a.menu__link[href]').forEach((a) => {
    const platform = PLATFORM_BY_PATH[pathKey(a.getAttribute('href'))];
    const li = a.closest('li');
    if (!li) return;
    if (platform) li.setAttribute('data-platform-item', platform);
    else li.removeAttribute('data-platform-item');
  });

  // Tag single-OS category parents so they collapse along with their children.
  menu.querySelectorAll('li.theme-doc-sidebar-item-category').forEach((cat) => {
    const tagged = cat.querySelectorAll('li[data-platform-item]');
    if (tagged.length === 0) { cat.removeAttribute('data-platform-item'); return; }
    const set = new Set();
    tagged.forEach((li) => set.add(li.getAttribute('data-platform-item')));
    if (set.size === 1) cat.setAttribute('data-platform-item', [...set][0]);
    else cat.removeAttribute('data-platform-item');
  });
}

// ─────────────────────── widget ───────────────────────

function ensureFilterWidget() {
  const menu = document.querySelector('.theme-doc-sidebar-menu');
  if (!menu) return;
  if (menu.parentElement.querySelector('.quilr-platform-filter')) return;

  const wrap = document.createElement('div');
  wrap.className = 'quilr-platform-filter';
  wrap.innerHTML = `
    <div class="quilr-platform-filter-label">FILTER</div>
    <div class="quilr-platform-filter-buttons" role="tablist" aria-label="Filter by platform">
      <button type="button" data-platform="all" role="tab">All</button>
      <button type="button" data-platform="macos" role="tab">macOS</button>
      <button type="button" data-platform="windows" role="tab">Windows</button>
    </div>
  `;
  menu.parentElement.insertBefore(wrap, menu);

  const current = getCurrent();
  wrap.querySelectorAll('button').forEach((btn) => {
    const sel = btn.dataset.platform === current;
    btn.classList.toggle('active', sel);
    btn.setAttribute('aria-selected', sel ? 'true' : 'false');
    btn.addEventListener('click', () => applyFilter(btn.dataset.platform));
  });
}

// ─────────────────────── loop ───────────────────────

let scheduled = false;
function schedule() {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {
    scheduled = false;
    ensureFilterWidget();
    tagSidebar();
    // Docusaurus' React Router strips the ?platform= param on internal
    // navigation. Re-apply it so the filter is shareable from any page.
    const sticky = readFromStorage() || 'all';
    if (sticky !== 'all' && readFromUrl() === null) writeUrl(sticky);
  });
}

function init() {
  applyFilter(getCurrent(), { syncUrl: false });   // initial paint without rewriting
  schedule();

  const obs = new MutationObserver(schedule);
  obs.observe(document.body, { childList: true, subtree: true });

  // Browser back/forward — pick up whatever's in the URL now.
  window.addEventListener('popstate', () => {
    applyFilter(getCurrent(), { syncUrl: false });
  });
}

if (ExecutionEnvironment.canUseDOM) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
}

export default {};
