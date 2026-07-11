/* SearchCore — pure man-page index matching. UMD so node tests can load it. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) { module.exports = factory(); }
  else { root.SearchCore = factory(); }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  function scoreName(name, tok) {
    if (name === tok) return 100;
    if (name.indexOf(tok) === 0) return 80;
    if (name.indexOf(tok) !== -1) return 60;
    return 0;
  }

  function search(db, query, limit) {
    limit = limit || 50;
    var q = String(query || '').trim().toLowerCase();
    if (!q || !db || !db.pages) return [];
    var tokens = q.split(/\s+/);
    var results = [];
    var pages = db.pages;
    var i, t, s;

    /* Section filter: "tar 5", "5 tar", "tar.5", or a bare "5" listing. */
    var sectFilter = null;
    var SECT_RE = /^\d[a-z0-9]{0,5}$/;
    if (tokens.length === 1) {
      var dm = tokens[0].match(/^(.+)\.(\d[a-z0-9]{0,5})$/);
      if (dm) { tokens = [dm[1]]; sectFilter = dm[2]; }
    }
    if (!sectFilter) {
      for (t = tokens.length - 1; t >= 0; t--) {
        if (tokens.length > 1 && SECT_RE.test(tokens[t])) {
          sectFilter = tokens[t]; tokens.splice(t, 1); break;
        }
      }
    }
    if (!sectFilter && tokens.length === 1 && SECT_RE.test(tokens[0])) {
      sectFilter = tokens[0]; tokens = [];
    }

    for (i = 0; i < pages.length; i++) {
      if (sectFilter && pages[i][1].toLowerCase().indexOf(sectFilter) !== 0) continue;
      var name = pages[i][0].toLowerCase();
      var desc = (pages[i][2] || '').toLowerCase();
      var total = 0, ok = true, hl = null;
      if (!tokens.length) total = 1; /* bare-section listing */
      for (t = 0; t < tokens.length; t++) {
        s = scoreName(name, tokens[t]);
        if (s && !hl) hl = [name.indexOf(tokens[t]), tokens[t].length];
        if (!s && desc.indexOf(tokens[t]) !== -1) s = 30;
        if (!s) { ok = false; break; }
        total += s;
      }
      if (ok) results.push({ name: pages[i][0], section: pages[i][1],
        desc: pages[i][2] || '', path: pages[i][3], score: total, hl: hl });
    }

    var aliases = tokens.length ? (db.aliases || []) : [];
    for (i = 0; i < aliases.length; i++) {
      if (sectFilter && aliases[i][1].toLowerCase().indexOf(sectFilter) !== 0) continue;
      var an = aliases[i][0].toLowerCase();
      var total2 = 0, ok2 = true;
      for (t = 0; t < tokens.length; t++) {
        s = scoreName(an, tokens[t]);
        if (!s) { ok2 = false; break; }
        total2 += s - 10; /* alias slightly below a real page hit */
      }
      if (ok2) {
        var p = pages[aliases[i][2]];
        if (p) results.push({ name: aliases[i][0], section: aliases[i][1],
          desc: 'alias for ' + p[0] + '(' + p[1] + ')' + (p[2] ? ' — ' + p[2] : ''),
          path: p[3], score: total2, alias: true, hl: null });
      }
    }

    results.sort(function (x, y) {
      if (y.score !== x.score) return y.score - x.score;
      if (x.name.length !== y.name.length) return x.name.length - y.name.length;
      if (x.name !== y.name) return x.name < y.name ? -1 : 1;
      return x.section < y.section ? -1 : 1;
    });

    var seen = {}, out = [];
    for (i = 0; i < results.length && out.length < limit; i++) {
      if (!seen[results[i].path]) { seen[results[i].path] = 1; out.push(results[i]); }
    }
    return out;
  }

  return { search: search };
}));
