import { describe, it, expect, beforeEach } from 'vitest'
import { encrypt, decrypt, bufferToBase64, base64ToBuffer } from '../utils/crypto'

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

  it('chiffre et déchiffre une charge JSON lourde (> 2 Mo) sans RangeError (Maximum call stack size exceeded)', async () => {
    // Création d'un payload > 2,2 Mo (dépasse largement la limite de pile ~65 Ko de Safari/WebKit)
    const repeatBlock = JSON.stringify({
      uid: 'AMANR5L17PO419604B1641P0D1N000137',
      article: 'Article PREMIER',
      dispositif: 'Supprimer cet article. '.repeat(40),
    })
    const heavyJson = '[' + Array.from({ length: 2200 }, () => repeatBlock).join(',') + ']'
    expect(heavyJson.length).toBeGreaterThan(2 * 1024 * 1024)

    const encrypted = await encrypt(heavyJson)
    expect(typeof encrypted).toBe('string')
    expect(encrypted.length).toBeGreaterThan(2 * 1024 * 1024)

    const decrypted = await decrypt(encrypted)
    expect(decrypted.length).toBe(heavyJson.length)
    expect(decrypted.slice(0, 200)).toBe(heavyJson.slice(0, 200))

    // Vérification directe des helpers par blocs de 8192 octets
    const rawBuf = new Uint8Array(150_000).fill(65).buffer
    const b64 = bufferToBase64(rawBuf)
    const restoredBuf = base64ToBuffer(b64)
    expect(restoredBuf.byteLength).toBe(150_000)
  })
})
