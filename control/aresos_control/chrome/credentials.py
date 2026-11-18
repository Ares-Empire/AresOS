"""Credential words: a typed field whose name holds one is a password-kind field.

Brief 28, item 1 (the name rule). The words are service data, versioned like
the send-word list. The reader carries a copy (`reader.js`,
`credentialNames`); `test_credentials.py` compares the copy with this module.

The reader's older expressions (`credentialStems`, `credentialTokens`) stay
as they are, and either list makes a field password-kind. This list counts
only for a field a person types into (an `input` that isn't hidden, a
`textarea`, an editable area) and never for a hidden field, so a form with a
hidden `csrf_token` field is still sent.

A word matches whole or as a part of a name (`user_password`, `otpCode`),
never inside another word (`shipping` is not `pin`).
"""

CREDENTIAL_WORDS_VERSION = 1

WORDS = ('password passwort kennwort passcode passphrase pwd pin otp totp tan mtan 2fa mfa '
         'secret token seed mnemonic cvv cvc').split()

# A word that counts only beside one of its companions: as neighbours
# ("verification code", "card security code") or written as one word
# ("Einmalcode", "Sicherheitscode").
PAIRS = {
    'code': 'verification verify security sms login auth recovery backup card einmal bestätigung sicherheit'.split(),
    'key': 'private api secret access recovery signing'.split(),
    'phrase': 'recovery seed secret'.split(),
}


def reader_copy():
    """What `reader.js` must hold, as the value of its `credentialNames`."""
    return {'version': CREDENTIAL_WORDS_VERSION, 'words': list(WORDS),
            'pairs': {word: list(beside) for word, beside in PAIRS.items()}}
