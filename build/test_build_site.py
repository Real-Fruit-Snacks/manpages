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

    def test_extract_toc(self):
        self.assertEqual(build_site.extract_toc(FRAG),
                         [('NAME', 'NAME'), ('SEE_ALSO', 'SEE ALSO')])


if __name__ == '__main__':
    unittest.main()
