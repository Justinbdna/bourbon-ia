import { describe, it, expect, vi, beforeEach } from 'vitest'
import { gunzipSync } from 'node:zlib'
import { apiBase, choisirServeur, modeServeur, postJSON, SERVEUR_LOCAL } from '../api/serveur'

// Stockage minimal (l'environnement de test n'a pas de navigateur).
function stockageEnMemoire() {
  const donnees = new Map()
  return {
    getItem: (k) => (donnees.has(k) ? donnees.get(k) : null),
    setItem: (k, v) => donnees.set(k, String(v)),
    removeItem: (k) => donnees.delete(k),
  }
}

describe('serveur.js — choix du serveur et compression des envois', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    globalThis.localStorage = stockageEnMemoire()
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) })
  })

  it('serveur en ligne par défaut, local sur demande', () => {
    expect(modeServeur()).toBe('en_ligne')
    choisirServeur('local')
    expect(modeServeur()).toBe('local')
    expect(apiBase()).toBe(SERVEUR_LOCAL)
  })

  it('les petits envois partent en JSON simple', async () => {
    await postJSON('/api/normalize', { amendements: [{ id: 'AM1' }] })

    const [url, options] = globalThis.fetch.mock.calls[0]
    expect(url).toMatch(/\/api\/normalize$/)
    expect(options.headers['Content-Encoding']).toBeUndefined()
    expect(JSON.parse(options.body)).toEqual({ amendements: [{ id: 'AM1' }] })
  })

  it('les gros envois sont compressés en gzip, sans perte', async () => {
    const donnees = { amendements: Array.from({ length: 500 }, (_, i) => ({ id: `AM${i}`, dispositif: 'Supprimer cet article.' })) }

    await postJSON('/api/v2/mecanique', donnees)

    const [, options] = globalThis.fetch.mock.calls[0]
    expect(options.headers['Content-Encoding']).toBe('gzip')
    const brut = JSON.stringify(donnees)
    expect(options.body.byteLength).toBeLessThan(brut.length / 5)
    expect(JSON.parse(gunzipSync(Buffer.from(options.body)).toString())).toEqual(donnees)
  })

  it('en mode local, les appels visent le serveur du poste', async () => {
    choisirServeur('local')

    await postJSON('/api/normalize', { amendements: [] })

    expect(globalThis.fetch.mock.calls[0][0]).toBe(`${SERVEUR_LOCAL}/api/normalize`)
  })
})
