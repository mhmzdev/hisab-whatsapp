"""Sealed-box decryption for the WhatsApp key ciphertext the portal submits.

The portal encrypts client-side with the runner's public key; only the runner holds the
private key (docs/brainstorm/hosted-portal.md, "Submission/storage contract"). Keypair
custody for this MVP: an environment-variable secret like WHATSAPP_TOKEN/OPENROUTER_API_KEY
(hisab/config.py), generated once by keygen.py, manual rotation, local/dev only.
"""
import base64

import nacl.exceptions
from nacl.public import PrivateKey, PublicKey, SealedBox


class CryptoError(Exception):
    pass


def generate_keypair():
    """Returns (public_key_b64, private_key_b64)."""
    sk = PrivateKey.generate()
    pk_b64 = base64.b64encode(bytes(sk.public_key)).decode("ascii")
    sk_b64 = base64.b64encode(bytes(sk)).decode("ascii")
    return pk_b64, sk_b64


def decrypt(ciphertext_b64, private_key_b64):
    """Decrypts a sealed-box ciphertext with the runner's private key; raises CryptoError on failure."""
    try:
        sk = PrivateKey(base64.b64decode(private_key_b64))
        box = SealedBox(sk)
        plaintext = box.decrypt(base64.b64decode(ciphertext_b64))
        return plaintext.decode("utf-8")
    except (nacl.exceptions.CryptoError, ValueError, TypeError) as e:
        raise CryptoError(f"could not decrypt key ciphertext: {type(e).__name__}") from None


def seal(plaintext, public_key_b64):
    """Encrypts with a runner public key. Used by tests and the keygen helper text; the real
    encryption happens in the portal's browser JS, not here."""
    pk = PublicKey(base64.b64decode(public_key_b64))
    box = SealedBox(pk)
    return base64.b64encode(box.encrypt(plaintext.encode("utf-8"))).decode("ascii")
