/* Inject pet markup once per page load (single source of truth; keeps the
   ~60k static pages a few KB lighter each). Must run before pet.js (defer
   order guarantees it). */
(function () {
  'use strict';
  if (document.getElementById('site-pet')) return;
  var EYES = '<g class="pet-eyes-open"><rect x="5" y="6" width="2" height="3"/><rect x="9" y="6" width="2" height="3"/></g>';
  var GHOST = '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg"><path class="pet-body" d="M2 16 V7 Q2 1 8 1 Q14 1 14 7 V16 L12 14.4 L10 16 L8 14.4 L6 16 L4 14.4 Z"/>' + EYES;
  var GHOST_FULL = GHOST +
    '<g class="pet-eyes-closed"><rect x="5" y="8" width="2" height="1"/><rect x="9" y="8" width="2" height="1"/></g>' +
    '<g class="pet-eyes-happy"><path d="M4.6 8 L6 6.6 L7.4 8"/><path d="M8.6 8 L10 6.6 L11.4 8"/></g></svg>';

  var btn = document.createElement('button');
  btn.id = 'pet-open'; btn.type = 'button'; btn.title = 'pet settings';
  btn.setAttribute('aria-haspopup', 'true');
  btn.setAttribute('aria-expanded', 'false');
  btn.innerHTML = GHOST + '</svg>';
  var header = document.querySelector('.site-header');
  if (header) header.appendChild(btn); else document.body.appendChild(btn);

  var panel = document.createElement('div');
  panel.id = 'pet-panel'; panel.hidden = true;
  panel.innerHTML =
    '<div class="settings-head"><span>Pet</span><button id="pet-close" class="menu-close" type="button" aria-label="Close pet panel">&times;</button></div>' +
    '<div class="pet-group-label">Appearance</div>' +
    '<div id="pet-mode" class="pet-seg" role="group" aria-label="Pet mode"><button data-mode="float">Roam</button><button data-mode="cursor">Cursor</button><button data-mode="off">Off</button></div>' +
    '<label class="pet-slider"><span>Size</span><input id="pet-size" type="range" min="16" max="64" step="2"></label>' +
    '<label class="pet-slider"><span>Opacity</span><input id="pet-opacity" type="range" min="15" max="100" step="5"></label>' +
    '<div id="pet-color" class="pet-swatches" role="group" aria-label="Pet color"><button data-color="0" style="--sw:var(--twb-accent)"></button><button data-color="1" style="--sw:var(--twb-accent-alt)"></button><button data-color="2" style="--sw:var(--twb-warm)"></button><button data-color="3" style="--sw:var(--twb-violet)"></button><button data-color="4" style="--sw:var(--twb-orange)"></button><button data-color="5" style="--sw:var(--twb-red)"></button></div>' +
    '<div class="pet-group-label">Behavior</div>' +
    '<button id="pet-q-nap" class="settings-row pet-quirk" type="button"><span class="settings-label">Nap when idle</span><span class="settings-val"></span></button>' +
    '<button id="pet-q-flee" class="settings-row pet-quirk" type="button"><span class="settings-label">Flee from cursor</span><span class="settings-val"></span></button>' +
    '<button id="pet-q-read" class="settings-row pet-quirk" type="button"><span class="settings-label">Read along</span><span class="settings-val"></span></button>' +
    '<button id="pet-q-tricks" class="settings-row pet-quirk" type="button"><span class="settings-label">Do tricks</span><span class="settings-val"></span></button>' +
    '<button id="pet-q-speech" class="settings-row pet-quirk" type="button"><span class="settings-label">Speech bubbles</span><span class="settings-val"></span></button>';
  document.body.appendChild(panel);

  var pet = document.createElement('div');
  pet.id = 'site-pet'; pet.setAttribute('aria-hidden', 'true');
  pet.innerHTML = '<div class="pet-tilt"><div class="pet-sprite" title="pet the ghost to recolor it">' + GHOST_FULL + '</div></div>';
  document.body.appendChild(pet);
})();

/* UI glue: theme toggle + search box behavior. Depends on SearchCore and MANDB. */
(function () {
  'use strict';
  var root = document.documentElement.getAttribute('data-root') || './';

  var btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.addEventListener('click', function () {
      var cur = document.documentElement.getAttribute('data-theme');
      if (!cur) {
        cur = (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
      }
      var next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('twb-theme', next); } catch (e) { /* private mode */ }
    });
  }

  var input = document.getElementById('search');
  var list = document.getElementById('results');
  if (!input || !list) return;
  var sel = -1, items = [];

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function render() {
    if (!items.length) {
      list.hidden = true; list.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      return;
    }
    var h = '';
    for (var i = 0; i < items.length; i++) {
      var r = items[i];
      var nameHtml;
      if (r.hl) {
        nameHtml = esc(r.name.slice(0, r.hl[0])) + '<mark>' +
          esc(r.name.slice(r.hl[0], r.hl[0] + r.hl[1])) + '</mark>' +
          esc(r.name.slice(r.hl[0] + r.hl[1]));
      } else {
        nameHtml = esc(r.name);
      }
      h += '<li id="opt-' + i + '" role="option" aria-selected="' + (i === sel) + '" class="' + (i === sel ? 'sel' : '') + '">' +
        '<a href="' + esc(root + r.path) + '">' +
        '<span class="r-name">' + nameHtml + '</span>' +
        '<span class="badge s' + esc(String(r.section).charAt(0)) + '">' + esc(r.section) + '</span>' +
        '<span class="r-desc">' + esc(r.desc) + '</span></a></li>';
    }
    list.innerHTML = h;
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    if (sel >= 0) input.setAttribute('aria-activedescendant', 'opt-' + sel);
    else input.removeAttribute('aria-activedescendant');
    var s = list.querySelector('li.sel');
    if (s && s.scrollIntoView) s.scrollIntoView({ block: 'nearest' });
  }

  function update() {
    if (!window.MANDB || !window.SearchCore) return;
    items = window.SearchCore.search(window.MANDB, input.value, 30);
    sel = items.length ? 0 : -1;
    render();
  }

  input.addEventListener('input', update);
  input.addEventListener('focus', function () { if (items.length) list.hidden = false; });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { if (sel < items.length - 1) { sel++; render(); } e.preventDefault(); }
    else if (e.key === 'ArrowUp') { if (sel > 0) { sel--; render(); } e.preventDefault(); }
    else if (e.key === 'Enter') { if (sel >= 0 && items[sel]) location.href = root + items[sel].path; }
    else if (e.key === 'Escape') { input.value = ''; items = []; sel = -1; render(); input.blur(); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== input &&
        !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) {
      input.focus(); input.select(); e.preventDefault();
    }
  });
  document.addEventListener('click', function (e) {
    if (!list.contains(e.target) && e.target !== input) {
      list.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
    }
  });

})();

/* Recently viewed: recorded on man pages, rendered on the home page. */
(function () {
  'use strict';
  var root = document.documentElement.getAttribute('data-root') || './';
  var KEY = 'twb-recent', MAX = 8;
  function load() {
    try { var v = JSON.parse(localStorage.getItem(KEY)); return Array.isArray(v) ? v : []; }
    catch (e) { return []; }
  }
  var m = location.pathname.match(/man\/([^/]+)\/([^/]+)\.html$/);
  if (m && document.querySelector('article.man-content')) {
    var entry = { t: document.title.replace(/\s+—.*$/, ''), p: 'man/' + m[1] + '/' + m[2] + '.html' };
    var list = load().filter(function (e) { return e.p !== entry.p; });
    list.unshift(entry);
    try { localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX))); } catch (e) { /* private mode */ }
  }
  var box = document.getElementById('recent');
  if (!box) return;
  var recent = load();
  if (!recent.length) return;
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  var h = '<span class="recent-label">recent:</span>';
  for (var i = 0; i < recent.length; i++) {
    h += '<a class="recent-chip" href="' + esc(root + recent[i].p) + '">' + esc(recent[i].t) + '</a>';
  }
  box.innerHTML = h;
  box.hidden = false;
})();

/* Pet settings panel — same localStorage keys and defaults as the vault site:
   mode float (roam), size 28, opacity 70, color 0 (accent),
   nap/flee/read/tricks on, speech off. Dispatches "twb:pet" so pet.js
   re-reads config live. */
(function () {
  'use strict';
  var open = document.getElementById('pet-open');
  var panel = document.getElementById('pet-panel');
  if (!open || !panel) return;
  var root = document.documentElement;

  function getMode() {
    var a = root.getAttribute('data-pet');
    return a === 'off' || a === 'float' ? a : 'cursor';
  }
  function setMode(m) {
    if (m === 'cursor') root.removeAttribute('data-pet');
    else root.setAttribute('data-pet', m);
    try { if (m === 'float') localStorage.removeItem('twb-pet'); else localStorage.setItem('twb-pet', m); } catch (e) { /* private mode */ }
    sync(); fire();
  }
  function num(k, dflt) { var v = parseInt(localStorage.getItem(k), 10); return isNaN(v) ? dflt : v; }
  function onq(k, dflt) { var v = localStorage.getItem(k); return v === 'on' ? true : v === 'off' ? false : dflt; }
  function setKey(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }

  function sync() {
    var m = getMode();
    var segs = panel.querySelectorAll('#pet-mode button');
    for (var i = 0; i < segs.length; i++) segs[i].classList.toggle('on', segs[i].getAttribute('data-mode') === m);
    panel.querySelector('#pet-size').value = num('twb-pet-size', 28);
    panel.querySelector('#pet-opacity').value = num('twb-pet-opacity', 70);
    var col = num('twb-pet-color', 0);
    var sw = panel.querySelectorAll('#pet-color button');
    for (var j = 0; j < sw.length; j++) sw[j].classList.toggle('on', (+sw[j].getAttribute('data-color')) === col);
    var q = [['nap', true], ['flee', true], ['read', true], ['tricks', true], ['speech', true]];
    for (var n = 0; n < q.length; n++) {
      var b = panel.querySelector('#pet-q-' + q[n][0]);
      if (b) b.classList.toggle('on', onq('twb-pet-' + q[n][0], q[n][1]));
    }
  }
  function fire() { window.dispatchEvent(new Event('twb:pet')); }

  function closePanel() {
    panel.setAttribute('hidden', '');
    open.setAttribute('aria-expanded', 'false');
  }
  function openPanel() {
    sync();
    panel.removeAttribute('hidden');
    open.setAttribute('aria-expanded', 'true');
  }
  open.addEventListener('click', function (e) {
    e.stopPropagation();
    if (panel.hasAttribute('hidden')) openPanel(); else closePanel();
  });
  var petClose = document.getElementById('pet-close');
  if (petClose) petClose.addEventListener('click', function (e) { e.stopPropagation(); closePanel(); });
  document.addEventListener('click', function (e) {
    if (!panel.hasAttribute('hidden') && !panel.contains(e.target) && e.target !== open && !open.contains(e.target)) closePanel();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hasAttribute('hidden')) { closePanel(); open.focus(); }
  });

  panel.querySelector('#pet-mode').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-mode]'); if (b) setMode(b.getAttribute('data-mode'));
  });
  panel.querySelector('#pet-size').addEventListener('input', function () { setKey('twb-pet-size', this.value); fire(); });
  panel.querySelector('#pet-opacity').addEventListener('input', function () { setKey('twb-pet-opacity', this.value); fire(); });
  panel.querySelector('#pet-color').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-color]'); if (!b) return;
    var c = b.getAttribute('data-color');
    try { if (c === '0') localStorage.removeItem('twb-pet-color'); else localStorage.setItem('twb-pet-color', c); } catch (er) { /* private mode */ }
    sync(); fire();
  });
  var quirks = ['nap', 'flee', 'read', 'tricks', 'speech'];
  for (var i = 0; i < quirks.length; i++) (function (id) {
    var b = panel.querySelector('#pet-q-' + id);
    if (!b) return;
    b.addEventListener('click', function () {
      var cur = onq('twb-pet-' + id, true);
      setKey('twb-pet-' + id, cur ? 'off' : 'on');
      sync(); fire();
    });
  })(quirks[i]);
})();
