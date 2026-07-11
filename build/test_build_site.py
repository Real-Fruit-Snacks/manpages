import unittest

import build_site

FRAG = ('<h1 class="Sh" id="NAME"><a class="permalink" href="#NAME">NAME</a></h1>'
        '<p>tar - an archiver</p>'
        '<h1 class="Sh" id="SEE_ALSO"><a class="permalink" href="#SEE_ALSO">SEE ALSO</a></h1>'
        '<p><a class="Xr" href="../1/gzip.html">gzip(1)</a>, '
        '<a class="Xr" href="../1/nope.html">nope(1)</a>, '
        '<a class="Xr" href="../3/foo.html">foo(3ssl)</a></p>')


class TestBuildSite(unittest.TestCase):
    def setUp(self):
        self.pages = [
            {'name': 'gzip', 'sect': '1', 'slug': 'gzip'},
            {'name': 'foo', 'sect': '3ssl', 'slug': 'foo'},
            {'name': 'tar', 'sect': '1', 'slug': 'tar'},
        ]
        self.exact, self.by_base = build_site.build_maps(self.pages)

    def test_slugify_safe_chars(self):
        taken = {}
        self.assertEqual(build_site.slugify('Test::More', taken), 'Test__More')
        self.assertEqual(build_site.slugify('ls', taken), 'ls')

    def test_slugify_case_collision(self):
        taken = {}
        build_site.slugify('ls', taken)
        s = build_site.slugify('LS', taken)  # NTFS is case-insensitive
        self.assertNotEqual(s.lower(), 'ls')

    def test_xr_rewrite_exact_and_miss(self):
        out = build_site.rewrite_xr(FRAG, self.exact, self.by_base, lambda n, s: None)
        self.assertIn('href="../1/gzip.html"', out)
        self.assertIn('<span class="Xr">nope(1)</span>', out)
        self.assertIn('href="../3ssl/foo.html"', out)  # (3ssl) exact section

    def test_xr_base_section_fallback(self):
        frag = '<a class="Xr" href="#">foo(3)</a>'
        out = build_site.rewrite_xr(frag, self.exact, self.by_base, lambda n, s: None)
        self.assertIn('href="../3ssl/foo.html"', out)

    def test_xr_alias_fallback(self):
        frag = '<a class="Xr">bunzip(1)</a>'
        target = self.pages[0]
        out = build_site.rewrite_xr(frag, self.exact, self.by_base,
                                    lambda n, s: target if n == 'bunzip' else None)
        self.assertIn('href="../1/gzip.html"', out)

    def test_linkify_bold_refs(self):
        frag = ('<p><b>gzip</b>(1), <b>nope</b>(1), <i>foo</i>(3ssl), '
                '<b>printf</b>("%s"), <b>word</b>(noun)</p>')
        out = build_site.linkify_refs(frag, self.exact, self.by_base, lambda n, s: None)
        self.assertIn('<a class="Xr" href="../1/gzip.html"><b>gzip</b>(1)</a>', out)
        self.assertIn('<b>nope</b>(1)', out)          # unknown target left alone
        self.assertNotIn('nope.html', out)
        self.assertIn('<a class="Xr" href="../3ssl/foo.html"><i>foo</i>(3ssl)</a>', out)
        self.assertIn('<b>printf</b>("%s")', out)      # function call untouched
        self.assertIn('<b>word</b>(noun)', out)        # non-section parens untouched

    def test_parse_page_rows_tolerates_three_or_four_cols(self):
        rows = build_site.parse_page_rows(['a\t1\t1/a.1', 'b\t1\t1/b.1\tman1/b.1.gz'])
        self.assertEqual(rows[0], ('a', '1', '1/a.1', ''))
        self.assertEqual(rows[1], ('b', '1', '1/b.1', 'man1/b.1.gz'))

    def test_chunk_entries(self):
        entries = [('a%d' % i,) for i in range(3)] + [('b0',), ('c0',)]
        chunks = build_site.chunk_entries(entries, limit=3)
        self.assertEqual([c[0] for c in chunks], ['a', 'b–c'])
        self.assertEqual(sum(len(c[1]) for c in chunks), 5)
        one = build_site.chunk_entries(entries, limit=100)
        self.assertEqual(len(one), 1)
        self.assertEqual(one[0][0], 'a–c')

    def test_case_colliding_sections_share_a_dir(self):
        # NTFS can't hold man/1x and man/1X side by side; both must land in
        # one lowercased dir with unique slugs.
        taken = {}
        s1 = build_site.slugify('foo', taken)   # from section 1x
        s2 = build_site.slugify('FOO', taken)   # from section 1X
        self.assertNotEqual(s1.lower(), s2.lower())

    def test_unwrap_noncorpus_links(self):
        frag = ('<a class="Xr" href="../1/gzip.html">gzip(1)</a> and '
                '<a href="../autopkgtest/README.md">docs</a>')
        out = build_site.unwrap_noncorpus_links(frag, {'1/gzip.html'})
        self.assertIn('href="../1/gzip.html"', out)
        self.assertNotIn('README.md', out)
        self.assertIn('and docs', out)

    def test_extract_toc(self):
        self.assertEqual(build_site.extract_toc(FRAG),
                         [('NAME', 'NAME'), ('SEE_ALSO', 'SEE ALSO')])


if __name__ == '__main__':
    unittest.main()
