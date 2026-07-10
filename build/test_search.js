'use strict';
var assert = require('assert');
var SearchCore = require('../docs/assets/search-core.js');

var db = { v: 1, pages: [
  ['tar', '1', 'an archiving utility', 'man/1/tar.html'],
  ['target', '1', 'systemd target units', 'man/1/target.html'],
  ['star', '1', 'unique standard tape archiver', 'man/1/star.html'],
  ['grep', '1', 'print lines matching a pattern', 'man/1/grep.html'],
  ['fstab', '5', 'static file system information', 'man/5/fstab.html']
], aliases: [ ['untar', '1', 0], ['egrep', '1', 3] ] };

var r = SearchCore.search(db, 'tar', 10);
assert.strictEqual(r[0].name, 'tar', 'exact match first');
assert.strictEqual(r[1].name, 'target', 'prefix beats substring');
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

console.log('search-core: all tests passed');
