'use strict';
var assert = require('assert');
var SearchCore = require('../docs/assets/search-core.js');

var db = { v: 1, pages: [
  ['tar', '1', 'an archiving utility', 'man/1/tar.html'],
  ['target', '1', 'systemd target units', 'man/1/target.html'],
  ['star', '1', 'unique standard tape archiver', 'man/1/star.html'],
  ['grep', '1', 'print lines matching a pattern', 'man/1/grep.html'],
  ['fstab', '5', 'static file system information', 'man/5/fstab.html'],
  ['tar', '5', 'format of tape archive files', 'man/5/tar2.html']
], aliases: [ ['untar', '1', 0], ['egrep', '1', 3] ] };

var r = SearchCore.search(db, 'tar', 10);
assert.strictEqual(r[0].name, 'tar', 'exact match first');
assert.strictEqual(r[0].section, '1', 'lower section first among exact matches');
assert.strictEqual(r[1].name, 'tar', 'both exact-name pages precede prefix matches');
assert.strictEqual(r[2].name, 'target', 'prefix beats substring');
assert.ok(r.some(function (x) { return x.name === 'star'; }), 'substring included');
r.forEach(function (x, i) { r.forEach(function (y, j) {
  if (i < j) assert.notStrictEqual(x.path, y.path, 'deduped by path'); }); });

r = SearchCore.search(db, 'archiving', 10);
assert.strictEqual(r[0].name, 'tar', 'description match');

r = SearchCore.search(db, 'untar', 10);
assert.strictEqual(r[0].path, 'man/1/tar.html', 'alias resolves to target page');

r = SearchCore.search(db, 'file system', 10);
assert.strictEqual(r[0].name, 'fstab', 'multi-token AND across desc');

assert.strictEqual(SearchCore.search(db, '', 10).length, 0, 'empty query');
assert.strictEqual(SearchCore.search(db, '   ', 10).length, 0, 'blank query');
assert.strictEqual(SearchCore.search(db, 'tar', 2).length, 2, 'limit respected');
assert.strictEqual(SearchCore.search(db, 'zzzz', 10).length, 0, 'no matches');

r = SearchCore.search(db, 'tar 5', 10);
assert.strictEqual(r.length, 1, 'section filter narrows');
assert.strictEqual(r[0].section, '5', 'tar 5 -> section 5');

r = SearchCore.search(db, '5 tar', 10);
assert.strictEqual(r[0].section, '5', 'filter position free');

r = SearchCore.search(db, 'tar.5', 10);
assert.strictEqual(r[0].section, '5', 'dot syntax splits');

r = SearchCore.search(db, 'e2fsck.conf', 10);
assert.strictEqual(r.length, 0, 'dot only splits when suffix starts with a digit');

r = SearchCore.search(db, '5', 10);
assert.ok(r.length >= 2 && r.every(function (x) { return x.section === '5'; }),
  'bare section lists the section');

r = SearchCore.search(db, 'tar', 10);
assert.deepStrictEqual(r[0].hl, [0, 3], 'exact match highlight span');
r = SearchCore.search(db, 'get', 10);
assert.deepStrictEqual(r.filter(function (x) { return x.name === 'target'; })[0].hl, [3, 3],
  'substring highlight offset');
r = SearchCore.search(db, 'archiving', 10);
assert.strictEqual(r[0].hl, null, 'description-only match has no name highlight');

console.log('search-core: all tests passed');
