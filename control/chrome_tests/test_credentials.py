"""Brief 28, item 1: the credential words and the reader's copy of them."""
import json
import re
import unicodedata
import unittest
from pathlib import Path

from aresos_control.chrome import credentials, policy

ROOT = Path(__file__).resolve().parents[2]
READER = ROOT / 'control/chrome/extension/reader.js'


class CredentialWordsTest(unittest.TestCase):
    def copy(self):
        found = re.findall(r'^  const credentialNames=(\{.*\});$', READER.read_text(encoding='utf-8'), re.M)
        self.assertEqual(len(found), 1, 'reader.js holds the copy once, as one line of JSON')
        return json.loads(found[0])

    def test_the_readers_copy_is_the_definitions(self):
        self.assertEqual(self.copy(), credentials.reader_copy())
        self.assertEqual(self.copy()['version'], credentials.CREDENTIAL_WORDS_VERSION)

    def test_version_1_is_the_briefs_list(self):
        # A change of the words is a new version, here and in the reader's copy.
        self.assertEqual(credentials.CREDENTIAL_WORDS_VERSION, 1)
        self.assertEqual(credentials.WORDS, [
            'password', 'passwort', 'kennwort', 'passcode', 'passphrase', 'pwd', 'pin', 'otp', 'totp', 'tan', 'mtan',
            '2fa', 'mfa', 'secret', 'token', 'seed', 'mnemonic', 'cvv', 'cvc'])
        self.assertEqual(credentials.PAIRS, {
            'code': ['verification', 'verify', 'security', 'sms', 'login', 'auth', 'recovery', 'backup', 'card',
                     'einmal', 'bestätigung', 'sicherheit'],
            'key': ['private', 'api', 'secret', 'access', 'recovery', 'signing'],
            'phrase': ['recovery', 'seed', 'secret']})

    def test_every_word_is_one_plain_lower_case_word(self):
        every = credentials.WORDS + list(credentials.PAIRS) + [word for beside in credentials.PAIRS.values() for word in beside]
        for word in every:
            with self.subTest(word=word):
                self.assertEqual(word, unicodedata.normalize('NFKC', word).lower())
                self.assertTrue(word.isalnum(), 'a word has no separator in it')
        self.assertEqual(len(set(credentials.WORDS)), len(credentials.WORDS))
        for word, beside in credentials.PAIRS.items():
            self.assertEqual(len(set(beside)), len(beside))
            # A paired word alone is an ordinary word ("Postal code", "Key result").
            self.assertNotIn(word, credentials.WORDS)

    def test_the_send_words_are_another_list(self):
        # policy.py's classification can't change through this list.
        self.assertEqual(set(credentials.WORDS) & {word.lower() for word in policy.WORDS}, set())
        self.assertFalse(hasattr(policy, 'CREDENTIAL_WORDS_VERSION'))


if __name__ == '__main__':
    unittest.main()
