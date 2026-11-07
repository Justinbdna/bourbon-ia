import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  normalizeAmendments,
  classifyAmendmentsV2,
  analyzeSurtransposition,
  resumerAmendement,
  ClassifyError,
} from '../api/classify'

describe('classify.js — Pipeline Orchestrateur Frontend V2', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('normalizeAmendments retourne les données nettoyées de l\'API', async () => {
    const mockData = [{ id: 'AM1', numero: '1' }]
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    })

    const res = await normalizeAmendments([{ uid: 'AM1' }])
    expect(res).toEqual(mockData)
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/normalize'),
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('normalizeAmendments lève ClassifyError sur réponse HTTP 500', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Erreur serveur interne',
    })

    await expect(normalizeAmendments([])).rejects.toThrow(ClassifyError)
  })

  it('classifyAmendmentsV2 orchestre le tri mécanique puis LLM séquentiel', async () => {
    const mechanicalData = [
      { id: 'AM-MEC', statut_mecanique: 'ISOLE_MECANIQUE', _skipLLM: true },
      { id: 'AM-LLM', statut_mecanique: 'NOUVEAU', _skipLLM: false },
    ]

    const singleLlmData = {
      id: 'AM-LLM',
      statut_mecanique: 'NOUVEAU',
      resultat_ia: {
        statut: 'Discussion commune',
        analyse_intention: 'Suppression alinéa',
        niveau_confiance: 0.95,
      },
    }

    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/v2/mecanique')) {
        return Promise.resolve({
          ok: true,
          json: async () => mechanicalData,
        })
      }
      if (url.includes('/api/v2/analyser-llm')) {
        return Promise.resolve({
          ok: true,
          json: async () => singleLlmData,
        })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })

    const onProgress = vi.fn()
    const onMechanical = vi.fn()

    const results = await classifyAmendmentsV2(mechanicalData, {
      aiSettings: { provider: 'local' },
      onProgress,
      onMechanical,
    })

    expect(onMechanical).toHaveBeenCalledWith(mechanicalData)
    expect(onProgress).toHaveBeenCalled()
    expect(results.length).toBe(2)
    expect(results[1].resultat_ia.statut).toBe('Discussion commune')
  })

  it('classifyAmendmentsV2 gère gracieusement une erreur isolée sur une analyse unitaire', async () => {
    const mechanicalData = [
      { id: 'AM-FAIL', statut_mecanique: 'NOUVEAU', _skipLLM: false },
    ]

    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/v2/mecanique')) {
        return Promise.resolve({
          ok: true,
          json: async () => mechanicalData,
        })
      }
      if (url.includes('/api/v2/analyser-llm')) {
        return Promise.resolve({
          ok: false,
          status: 504,
          text: async () => 'Gateway Timeout',
        })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })

    const results = await classifyAmendmentsV2(mechanicalData, {
      aiSettings: { provider: 'local' },
    })

    expect(results.length).toBe(1)
    expect(results[0].resultat_ia.statut).toBe('Erreur IA')
    expect(results[0].resultat_ia.alerte_couleur).toBe('rouge')
  })

  it('analyzeSurtransposition effectue un appel API valide et retourne les données', async () => {
    const mockResult = {
      status: 'STRICT_TRANSPOSITION',
      confidence: 0.88,
      delta_summary: 'Conforme à la directive européenne.',
    }

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResult,
    })

    const res = await analyzeSurtransposition({
      id: 'AM-10',
      dispositif: 'Texte amendement',
      article: 'Article 5',
    })

    expect(res).toEqual(mockResult)
  })

  it('analyzeSurtransposition renvoie null en repli gracieux lors d\'une panne réseau', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network offline'))

    const res = await analyzeSurtransposition({ id: 'AM-10' })
    expect(res).toBeNull()
  })

  it('resumerAmendement envoie l\'amendement et les réglages IA, renvoie le résumé', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ amendement_uid: 'AM-1', resume: 'Supprime l\'article 3.' }),
    })

    const resume = await resumerAmendement(
      { id: 'AM-1', article: 'Article 3', dispositif: 'Supprimer cet article.' },
      { provider: 'groq_auto' }
    )

    expect(resume).toBe('Supprime l\'article 3.')
    const [url, init] = globalThis.fetch.mock.calls[0]
    expect(url).toContain('/api/v2/resumer')
    const corps = JSON.parse(init.body)
    expect(corps).toMatchObject({ amendement_uid: 'AM-1', provider: 'groq_auto', llm_endpoint: 'https://api.groq.com/openai/v1' })
  })

  it('resumerAmendement lève ClassifyError avec le message du serveur', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({ detail: 'Clé API invalide ou expirée. Vérifiez les Réglages IA.' }),
    })

    await expect(resumerAmendement({ id: 'AM-2' }, {})).rejects.toThrow('Clé API invalide')
  })
})
