// ─────────────────────────────────────────────────────────────
// crypto.js — Chiffrement AES-GCM via Web Crypto API
// Clé volatile stockée en sessionStorage (survit au F5 mais
// pas à la fermeture de l'onglet).
// ─────────────────────────────────────────────────────────────

const KEY_STORAGE = 'bourbon_session_key'

export function bufferToBase64(buffer) {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer)
  const len = bytes.byteLength
  const chunkSize = 8192
  let binary = ''
  for (let i = 0; i < len; i += chunkSize) {
    const chunk = bytes.subarray(i, Math.min(i + chunkSize, len))
    binary += String.fromCharCode.apply(null, chunk)
  }
  return btoa(binary)
}

export function base64ToBuffer(base64) {
  const binary = atob(base64)
  const len = binary.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

async function getOrCreateKey() {
  const stored = sessionStorage.getItem(KEY_STORAGE)
  if (stored) {
    const raw = base64ToBuffer(stored)
    return crypto.subtle.importKey('raw', raw, 'AES-GCM', true, ['encrypt', 'decrypt'])
  }
  const key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt'])
  const exported = await crypto.subtle.exportKey('raw', key)
  sessionStorage.setItem(KEY_STORAGE, bufferToBase64(exported))
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
  return bufferToBase64(combined.buffer)
}

/**
 * Déchiffre une chaîne base64 produite par encrypt().
 */
export async function decrypt(base64) {
  const key = await getOrCreateKey()
  const combined = new Uint8Array(base64ToBuffer(base64))
  const iv = combined.slice(0, 12)
  const ciphertext = combined.slice(12)
  const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext)
  return new TextDecoder().decode(decrypted)
}

export const encryptData = encrypt
export const decryptData = decrypt

/**
 * Récupère et déchiffre les réglages IA sauvegardés dans localStorage.
 * Supporte la version chiffrée (prioritaire) et la version en clair (repli).
 */
export async function getDecryptedSettings() {
  if (typeof window === 'undefined' || !window.localStorage) return null

  const cipher = localStorage.getItem('bourbon_ai_settings_encrypted')
  if (cipher) {
    try {
      const json = await decrypt(cipher)
      const parsed = JSON.parse(json)
      if (parsed && typeof parsed === 'object') {
        return parsed
      }
    } catch (e) {
      console.warn('[Bourbon.ia] Impossible de déchiffrer bourbon_ai_settings_encrypted :', e)
    }
  }

  const plain = localStorage.getItem('bourbon_ai_settings')
  if (plain) {
    try {
      const parsed = JSON.parse(plain)
      if (parsed && typeof parsed === 'object') {
        return parsed
      }
    } catch {
      // ignore
    }
  }

  return null
}
