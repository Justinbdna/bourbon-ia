// ─────────────────────────────────────────────────────────────
// crypto.js — Chiffrement AES-GCM via Web Crypto API
// Clé volatile stockée en sessionStorage (survit au F5 mais
// pas à la fermeture de l'onglet).
// ─────────────────────────────────────────────────────────────

const KEY_STORAGE = 'bourbon_session_key'

async function getOrCreateKey() {
  const stored = sessionStorage.getItem(KEY_STORAGE)
  if (stored) {
    const raw = Uint8Array.from(atob(stored), c => c.charCodeAt(0))
    return crypto.subtle.importKey('raw', raw, 'AES-GCM', true, ['encrypt', 'decrypt'])
  }
  const key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt'])
  const exported = await crypto.subtle.exportKey('raw', key)
  sessionStorage.setItem(KEY_STORAGE, btoa(String.fromCharCode(...new Uint8Array(exported))))
  return key
}

/**
 * Chiffre une chaîne de texte avec AES-GCM.
 * Retourne une chaîne base64 contenant IV (12 octets) + ciphertext.
 */
export async function encrypt(plaintext) {
  const key = await getOrCreateKey()
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const encoded = new TextEncoder().encode(plaintext)
  const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded)
  const combined = new Uint8Array(iv.length + ciphertext.byteLength)
  combined.set(iv, 0)
  combined.set(new Uint8Array(ciphertext), iv.length)
  return btoa(String.fromCharCode(...combined))
}

/**
 * Déchiffre une chaîne base64 produite par encrypt().
 */
export async function decrypt(base64) {
  const key = await getOrCreateKey()
  const combined = Uint8Array.from(atob(base64), c => c.charCodeAt(0))
  const iv = combined.slice(0, 12)
  const ciphertext = combined.slice(12)
  const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext)
  return new TextDecoder().decode(decrypted)
}
