// Sealed-box encryption of the pasted WhatsApp key, in the browser, with the runner's public key.
// Deliberately the same library family as the runner (libsodium here, PyNaCl's SealedBox there):
// crypto_box_seal on both sides, so a ciphertext that writes fine also opens fine minutes later
// inside the runner. tests/smoke.py asserts the JS→Python round-trip with this exact code path.
import sodium from 'libsodium-wrappers'

export async function sealKey(plaintext, publicKeyB64) {
  await sodium.ready
  const pk = sodium.from_base64(publicKeyB64, sodium.base64_variants.ORIGINAL)
  const sealed = sodium.crypto_box_seal(sodium.from_string(plaintext), pk)
  return sodium.to_base64(sealed, sodium.base64_variants.ORIGINAL)
}

// Six digits, never a leading zero, from the platform CSPRNG.
export function generateNonce() {
  const buf = new Uint32Array(1)
  crypto.getRandomValues(buf)
  return String(100000 + (buf[0] % 900000))
}

export const NONCE_TTL_MS = 10 * 60 * 1000
