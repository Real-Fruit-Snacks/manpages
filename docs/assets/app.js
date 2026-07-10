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
