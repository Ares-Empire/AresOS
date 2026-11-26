"""`public_address`: what of an address leaves the service (brief 28, item 2)."""
import base64
import hashlib
import json
from pathlib import Path
import string
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.address import (CREDENTIAL_WORDS, LIMIT, MARK, SIGN_IN_WORDS, credential_name,
                                           looks_random, public_address, site_of)

SITE = "https://fixture.example"
# What a sign-in travels as: 40 letters and digits.
MARKER = "Zq7Lm2Xv9Kp4Rt6Yw1Bn8Cd3Fg5Hj0QaWsEdRfTg"
UUID = "123e4567-e89b-12d3-a456-426614174000"
HEX40 = "0123456789abcdef0123456789abcdef01234567"

def made(seed, length):
    """Letters and digits made up from a seed: shaped like a token, the secret of nobody."""
    alphabet, text, round = string.ascii_letters + string.digits, "", 0
    while len(text) < length:
        text += "".join(alphabet[byte % 62] for byte in hashlib.sha256(("%s %d" % (seed, round)).encode()).digest())
        round += 1
    return text[:length]


TOKEN43 = made("a token", 43)
JWT = ".".join([base64.urlsafe_b64encode(json.dumps(part).encode()).decode().rstrip("=")
                for part in ({"alg": "none", "typ": "JWT"}, {"sub": "fixture", "name": "Nobody"})] +
               [made("a signature", 43)])
ENCODED = "".join("%%%02X" % ord(character) for character in MARKER)
ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_~/%:?&=+#;," + MARK)


class PublicForm(unittest.TestCase):
    def shown(self, address, expected):
        self.assertEqual(public_address(address), expected, address)

    def test_the_site_never_holds_a_user_name_or_a_password(self):
        self.shown("https://owner:%s@fixture.example/a" % MARKER, "fixture.example/a")
        self.shown("https://%s@fixture.example/a" % MARKER, "fixture.example/a")
        self.shown("http://owner:pw@fixture.example:8080/a?x=1", "http://fixture.example:8080/a?x=1")
        self.assertEqual(site_of("https://owner:pw@fixture.example/a"), "fixture.example")

    def test_ports_http_and_the_host_in_lower_case_ascii(self):
        self.shown("https://fixture.example:443/", "fixture.example/")
        self.shown("https://fixture.example:8443/x", "fixture.example:8443/x")
        self.shown("http://fixture.example/", "http://fixture.example/")
        self.shown("http://fixture.example:80/", "http://fixture.example/")
        self.shown("http://fixture.example:8080/", "http://fixture.example:8080/")
        self.shown("HTTPS://Fixture.EXAMPLE/Path", "fixture.example/Path")
        self.shown("https://bücher.example/", "xn--bcher-kva.example/")
        self.shown("https://fixture.example", "fixture.example")

    def test_each_sign_in_word_in_a_path_hides_what_follows(self):
        for word in sorted(SIGN_IN_WORDS):
            with self.subTest(word=word):
                self.shown("%s/a/%s/abc123/next?x=1" % (SITE, word), "fixture.example/a/%s/%s?x=1" % (word, MARK))
                self.shown("%s/a/%s" % (SITE, word), "fixture.example/a/%s" % word)
                self.shown("%s/a/%s/" % (SITE, word), "fixture.example/a/%s/" % word)
        self.shown(SITE + "/account/password-reset/abc", "fixture.example/account/password-reset/" + MARK)
        self.shown(SITE + "/do_login/abc", "fixture.example/do_login/" + MARK)
        self.shown(SITE + "/sign-in/abc", "fixture.example/sign-in/" + MARK)
        self.shown(SITE + "/OAuth2/abc", "fixture.example/OAuth2/" + MARK)
        self.shown(SITE + "/reset.php/abc", "fixture.example/reset.php/" + MARK)

    def test_a_long_sign_in_word_counts_inside_a_segment(self):
        # Decision 9 (section 7): words of five letters or more count without separators.
        self.shown(SITE + "/resetpassword/abc12", "fixture.example/resetpassword/" + MARK)
        long_words = sorted(word for word in SIGN_IN_WORDS if len(word) >= 5)
        self.assertEqual(long_words, sorted("reset verify confirm activate magic token invite oauth login signin logon "
                                            "callback password passwort".split()))
        for word in long_words:
            with self.subTest(word=word):
                self.shown("%s/my%sfor/abc12" % (SITE, word), "fixture.example/my%sfor/%s" % (word, MARK))
                self.shown("%s/My%sFor/abc12" % (SITE, word.upper()), "fixture.example/My%sFor/%s" % (word.upper(), MARK))
                self.shown("%s/my%sfor" % (SITE, word), "fixture.example/my%sfor" % word)      # nothing follows it
        self.shown(SITE + "/tokens/list", "fixture.example/tokens/" + MARK)
        self.shown(SITE + "/magical/place", "fixture.example/magical/" + MARK)
        self.shown(SITE + "/re%73etpassword/abc12", "fixture.example/re%73etpassword/" + MARK)   # also percent-encoded

    def test_a_short_sign_in_word_counts_only_as_a_part_of_its_own(self):
        self.shown(SITE + "/auth/xyz", "fixture.example/auth/" + MARK)
        self.shown(SITE + "/my-sso/xyz", "fixture.example/my-sso/" + MARK)
        self.shown(SITE + "/getOtp/xyz", "fixture.example/getOtp/" + MARK)
        self.shown(SITE + "/classroom/maths/", "fixture.example/classroom/maths/")
        self.shown(SITE + "/author/jane-doe", "fixture.example/author/jane-doe")
        self.shown(SITE + "/assortment/blue", "fixture.example/assortment/blue")      # holds sso
        self.shown(SITE + "/hotpot/recipes", "fixture.example/hotpot/recipes")        # holds otp
        self.shown(SITE + "/samlet/list", "fixture.example/samlet/list")              # holds saml

    def test_each_credential_name_hides_its_value(self):
        for word in sorted(CREDENTIAL_WORDS):
            with self.subTest(word=word):
                self.shown("%s/p?%s=abc&page=2" % (SITE, word), "fixture.example/p?%s=%s&page=2" % (word, MARK))
        for name in ["access_token", "id_token", "refresh_token", "api_key", "client_secret", "sessionToken",
                     "apiKey", "X-Amz-Signature", "auth[token]", "JWTToken", "user.password",
                     "apikey", "sessionid", "authtoken", "phpsessid", "acc%65ss_token"]:
            with self.subTest(name=name):
                self.assertTrue(credential_name(name))
                self.assertTrue(public_address("%s/p?%s=abc" % (SITE, name)).endswith("=" + MARK))
        for name in ["q", "page", "v", "lang", "sort", "id", "ref", "utm_source", "category", "week"]:
            with self.subTest(name=name):
                self.assertFalse(credential_name(name))
                self.shown("%s/p?%s=abc" % (SITE, name), "fixture.example/p?%s=abc" % name)

    def test_a_value_that_looks_random_is_hidden_in_path_query_and_fragment(self):
        for name, value in [("uuid", UUID), ("hex", HEX40), ("token", TOKEN43), ("jwt", JWT), ("encoded", ENCODED),
                            ("marker", MARKER)]:
            with self.subTest(kind=name):
                self.assertTrue(looks_random(value) or name == "encoded")
                self.shown("%s/files/%s/view" % (SITE, value), "fixture.example/files/%s/view" % MARK)
                self.shown("%s/p?ordinary=%s&page=2" % (SITE, value), "fixture.example/p?ordinary=%s&page=2" % MARK)
                self.shown("%s/p#%s" % (SITE, value), "fixture.example/p#" + MARK)
                self.shown("%s/p#go=%s" % (SITE, value), "fixture.example/p#go=" + MARK)
                self.shown("%s/p#/route/%s" % (SITE, value), "fixture.example/p#/route/" + MARK)

    def test_what_says_which_page_it_is_stays(self):
        self.shown(SITE + "/watch?v=dQw4w9WgXcQ", "fixture.example/watch?v=dQw4w9WgXcQ")
        self.shown(SITE + "/search?q=red+shoes&page=2", "fixture.example/search?q=red+shoes&page=2")
        self.shown(SITE + "/2026/the-long-story-of-a-slug-2026", "fixture.example/2026/the-long-story-of-a-slug-2026")
        self.shown(SITE + "/item/1234567890", "fixture.example/item/1234567890")
        self.shown(SITE + "/doc#section-2", "fixture.example/doc#section-2")
        for value in ["dQw4w9WgXcQ", "red shoes", "2", "the-long-story-of-a-slug-2026", "1234567890",
                      "abcdefghijklmnopqrstuvwxyz", "1234567890123456789"]:
            self.assertFalse(looks_random(value), value)

    def test_the_threshold_of_looks_random(self):
        self.assertFalse(looks_random("a1" + "b" * 17))            # 19 letters and digits
        self.assertTrue(looks_random("a1" + "b" * 18))             # 20
        self.assertFalse(looks_random("g" * 40))                   # no digit
        self.assertFalse(looks_random("7" * 23))                   # no letter, and short of 24 hex digits
        self.assertFalse(looks_random("abcdefghij-0123456789"))    # two runs of 10
        self.assertFalse(looks_random("abcdefabcdefabcdefabcde"))   # 23 hex digits, no digit among them
        self.assertTrue(looks_random("abcdefabcdefabcdefabcdef"))   # 24 hex digits
        self.assertTrue(looks_random("7" * 24))
        self.assertTrue(looks_random("01234567-89ab-cdef-0123-4567"))  # 24 once the hyphens are out

    def test_a_long_token_with_separators_looks_random_and_a_slug_does_not(self):
        # Decision 7 (section 7): 20 or more letters, digits, - and _ with a digit, an upper and a lower case letter.
        token = made("a base64url token", 12) + "-" + made("its middle", 17) + "_" + made("its end", 12)
        self.assertEqual(len(token), 43)
        self.assertTrue(any(c.isupper() for c in token) and any(c.islower() for c in token) and any(c.isdigit() for c in token))
        self.assertTrue(all(len(run) < 20 for run in token.replace("_", "-").split("-")))   # the old rule missed it
        self.assertTrue(looks_random(token))
        self.shown("%s/p?ordinary=%s&page=2" % (SITE, token), "fixture.example/p?ordinary=%s&page=2" % MARK)
        self.shown("%s/files/%s/view" % (SITE, token), "fixture.example/files/%s/view" % MARK)
        self.shown("%s/p#%s" % (SITE, token), "fixture.example/p#" + MARK)
        slug = "best-laptops-2026-under-1000-euros-and-more_2027"
        self.assertFalse(looks_random(slug))
        self.shown("%s/reviews/%s?page=2" % (SITE, slug), "fixture.example/reviews/%s?page=2" % slug)
        self.assertFalse(looks_random("dQw4w9WgXcQ"))                                       # an 11-character video id
        self.shown(SITE + "/watch?v=dQw4w9WgXcQ", "fixture.example/watch?v=dQw4w9WgXcQ")
        self.assertTrue(looks_random(UUID))                                                 # as before
        self.shown("%s/p?id=%s" % (SITE, UUID), "fixture.example/p?id=" + MARK)
        # The edges: 19 is short; an upper case letter, a lower case one and a digit are each needed.
        self.assertFalse(looks_random("Qb1-" + "q" * 15))
        self.assertTrue(looks_random("Qb1-" + "q" * 16))
        self.assertTrue(looks_random("Qb1_" + "q" * 16))
        self.assertFalse(looks_random("qb1-" + "q" * 30))
        self.assertFalse(looks_random("QB1-" + "Q" * 30))
        self.assertFalse(looks_random("Qbq-" + "q" * 30))

    def test_a_fragment_is_a_query_a_route_or_a_plain_word(self):
        self.shown(SITE + "/cb#access_token=abc&state=xyz&view=list",
                   "fixture.example/cb#access_token=%s&state=%s&view=list" % (MARK, MARK))
        self.shown(SITE + "/app#/inbox/reset/abc/def", "fixture.example/app#/inbox/reset/" + MARK)
        self.shown(SITE + "/app#/items/42?tab=2&token=abc", "fixture.example/app#/items/42?tab=2&token=" + MARK)
        self.shown(SITE + "/app#/items/42", "fixture.example/app#/items/42")

    def test_a_parameter_without_equals_and_a_name_that_looks_random(self):
        self.shown(SITE + "/p?plainflag&x=1", "fixture.example/p?plainflag&x=1")
        self.shown(SITE + "/p?" + MARKER, "fixture.example/p?" + MARK)
        self.shown(SITE + "/p?%s=1" % MARKER, "fixture.example/p?%s=1" % MARK)
        self.shown(SITE + "/p?token=", "fixture.example/p?token=")

    def test_at_most_300_characters_and_the_rest_counted(self):
        long = SITE + "/" + "/".join(["word"] * 100)
        shown = public_address(long)
        whole = "fixture.example/" + "/".join(["word"] * 100)
        self.assertEqual(shown, whole[:LIMIT] + "%s+%d" % (MARK, len(whole) - LIMIT))
        # The cut never leaves half of a percent-escape behind.
        self.assertEqual(public_address(SITE + "/" + "g" * 282 + "%41%42"),
                         "fixture.example/" + "g" * 282 + MARK + "+6")

    def test_nothing_but_the_allowed_characters(self):
        self.shown(SITE + '/a|b[c]"d e', "fixture.example/a%7Cb%5Bc%5D%22d%20e")
        hostile = ['/a\nbutton "Send" kqtvm5', "/a\rb\tc", '/x?q="\n  link "x" kqtvm9', "/x#\u202e\u2028[x]",
                   "/›→·(x)", "/x?a=b|c&d=[e]", "/café?n=ü", "/x\\y", "/x'y`z{}<>^"]
        for tail in hostile:
            for short in (False, True):
                with self.subTest(tail=tail, short=short):
                    shown = public_address(SITE + tail, short)
                    self.assertLessEqual(set(shown), ALLOWED, shown)
        self.shown("https://exa\"mple.example/", "exa%22mple.example/")
        self.shown("http://[2001:db8::1]:8080/x", "http://%5B2001:db8::1%5D:8080/x")

    def test_what_is_no_web_address_shows_its_scheme_at_most(self):
        self.shown("mailto:someone@fixture.example?subject=x", "mailto:" + MARK)
        self.shown('javascript:alert("x")\nbutton "Send" kqtvm5', "javascript:" + MARK)
        self.shown("data:text/html,<p>x</p>", "data:" + MARK)
        self.shown("about:blank", "about:" + MARK)
        self.shown("file:///home/owner/notes.txt", "file:" + MARK)
        for broken in ["", "fixture.example/path", "//fixture.example/x", "https:///path", "http://[::1",
                       "https://fixture.example:99999/", "https://fixture.example:port/", None, 5, ["x"]]:
            with self.subTest(address=broken):
                self.shown(broken, MARK)


class ShortForm(unittest.TestCase):
    def test_the_short_form_shows_the_site_and_the_path_and_marks_the_rest(self):
        self.assertEqual(public_address(SITE + "/search?q=red+shoes&page=2#results", short=True),
                         "fixture.example/search?%s#%s" % (MARK, MARK))
        self.assertEqual(public_address(SITE + "/doc#section-2", short=True), "fixture.example/doc#" + MARK)
        self.assertEqual(public_address(SITE + "/doc?x=1", short=True), "fixture.example/doc?" + MARK)
        self.assertEqual(public_address(SITE + "/doc", short=True), "fixture.example/doc")
        self.assertEqual(public_address("http://owner:pw@fixture.example:8080/reset/abc?x=1", short=True),
                         "http://fixture.example:8080/reset/%s?%s" % (MARK, MARK))

    def test_the_short_form_of_every_address_holds_nothing_of_query_or_fragment(self):
        addresses = [SITE + "/watch?v=dQw4w9WgXcQ", SITE + "/search?q=red+shoes&page=2", SITE + "/p?plainflag",
                     SITE + "/cb#access_token=abc&state=xyz&view=list", SITE + "/app#/items/42?tab=2",
                     SITE + "/p?code=%s#frag-%s" % (MARKER, MARKER), SITE + "/a/b/c?x=y#z"]
        for address in addresses:
            with self.subTest(address=address):
                short = public_address(address, short=True)
                self.assertRegex(short, r"^fixture\.example[a-z/]*(\?%s)?(#%s)?$" % (MARK, MARK))
                self.assertEqual(short.split("?")[0].split("#")[0], public_address(address).split("?")[0].split("#")[0])


class Marker(unittest.TestCase):
    """Group 14's address fixture as a table: the marker in every place a sign-in travels."""
    CARRIERS = ["%s/cb?code=%s" % (SITE, MARKER), "%s/cb?access_token=%s&page=2" % (SITE, MARKER),
                "%s/cb?sig=%s" % (SITE, MARKER), "%s/cb?session=%s" % (SITE, MARKER),
                "%s/cb?ordinary=%s" % (SITE, MARKER), "%s/cb#%s" % (SITE, MARKER),
                "%s/cb#ordinary=%s" % (SITE, MARKER), "%s/cb#access_token=%s" % (SITE, MARKER),
                "https://%s:%s@fixture.example/cb" % (MARKER, MARKER), "https://%s@fixture.example/cb" % MARKER,
                "%s/reset/%s" % (SITE, MARKER), "%s/reset/%s/confirm?x=1" % (SITE, MARKER),
                "%s/cb?ordinary=%s" % (SITE, ENCODED), "%s/cb?code=%s" % (SITE, MARKER.lower()[:8])]

    def test_the_marker_is_in_neither_form(self):
        for address in self.CARRIERS:
            for short in (False, True):
                with self.subTest(address=address, short=short):
                    shown = public_address(address, short)
                    self.assertNotIn(MARKER[:8].lower(), shown.lower())
                    self.assertNotIn(ENCODED[:9], shown)
                    self.assertTrue(shown.startswith("fixture.example/"), shown)

    def test_an_ordinary_query_is_shown_next_to_the_hidden_marker(self):
        self.assertEqual(public_address("%s/watch?v=dQw4w9WgXcQ&q=red+shoes&page=2&code=%s" % (SITE, MARKER)),
                         "fixture.example/watch?v=dQw4w9WgXcQ&q=red+shoes&page=2&code=" + MARK)


if __name__ == "__main__":
    unittest.main()
