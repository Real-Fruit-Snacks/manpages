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
    if (!items.length) { list.hidden = true; list.innerHTML = ''; return; }
    var h = '';
    for (var i = 0; i < items.length; i++) {
      var r = items[i];
      h += '<li class="' + (i === sel ? 'sel' : '') + '">' +
        '<a href="' + esc(root + r.path) + '">' +
        '<span class="r-name">' + esc(r.name) + '</span>' +
        '<span class="badge s' + esc(String(r.section).charAt(0)) + '">' + esc(r.section) + '</span>' +
        '<span class="r-desc">' + esc(r.desc) + '</span></a></li>';
    }
    list.innerHTML = h;
    list.hidden = false;
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
    if (!list.contains(e.target) && e.target !== input) list.hidden = true;
  });

  var pc = document.getElementById('page-count');
  if (pc && window.MANDB) pc.textContent = window.MANDB.pages.length.toLocaleString();
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
    var q = [['nap', true], ['flee', true], ['read', true], ['tricks', true], ['speech', false]];
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
      var cur = onq('twb-pet-' + id, id === 'speech' ? false : true);
      setKey('twb-pet-' + id, cur ? 'off' : 'on');
      sync(); fire();
    });
  })(quirks[i]);
})();
