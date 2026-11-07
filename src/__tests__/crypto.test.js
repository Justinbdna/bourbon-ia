import { describe, it, expect, beforeEach } from 'vitest'
import { encrypt, decrypt } from '../utils/crypto'

// Polyfill sessionStorage in Node environment
const storage = new Map()
if (!globalThis.sessionStorage) {
  globalThis.sessionStorage = {
    getItem: (key) => storage.get(key) || null,
    setItem: (key, val) => storage.set(key, String(val)),
    removeItem: (key) => storage.delete(key),
    clear: () => storage.clear(),
  }
}

describe('crypto.js — Chiffrement AES-256-GCM', () => {
  beforeEach(() => {
    storage.clear()
  })

  it('chiffre et déchiffre une chaîne simple avec intégrité', async () => {
    const original = 'Amendement secret confidentiel Assemblée Nationale'
    const encrypted = await encrypt(original)

    expect(typeof encrypted).toBe('string')
    expect(encrypted).not.toBe(original)
    expect(encrypted.length).toBeGreaterThan(16)

    const decrypted = await decrypt(encrypted)
    expect(decrypted).toBe(original)
  })

  it('chiffre et restaure des paramètres JSON volumineux (aiSettings)', async () => {
    const settings = {
      provider: 'local',
      apiKey: 'gsk_secret_1234567890abcdef',
      localUrl: 'http://localhost:1234/v1',
      model: 'mistral-7b-instruct',
    }
    const jsonStr = JSON.stringify(settings)
    const encrypted = await encrypt(jsonStr)

    const decryptedStr = await decrypt(encrypted)
    const restored = JSON.parse(decryptedStr)

    expect(restored).toEqual(settings)
  })

  it('lève une exception sur un ciphertext corrompu ou altéré', async () => {
    const original = 'Texte intact'
    const encrypted = await encrypt(original)

    // Altération de la chaîne base64
    const corrupted = encrypted.slice(0, -4) + 'AAAA'
    await expect(decrypt(corrupted)).rejects.toThrow()
  })
})
