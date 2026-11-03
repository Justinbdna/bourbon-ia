import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  normalizeAmendments,
  classifyAmendmentsV2,
  analyzeSurtransposition,
  resumerAmendement,
  safeParseJson,
  buildLocalChatPayload,
  LOCAL_PROMPT_SYSTEM,
  LOCAL_ONE_SHOT_MESSAGES,
  LOCAL_STOP_SEQUENCES,
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

  it('classifyAmendmentsV2 effectue un retry automatique concluant après un statut HTTP 429 (Rate Limit)', async () => {
    const mechanicalData = [
      { id: 'AM-429', statut_mecanique: 'NOUVEAU', _skipLLM: false },
    ]

    const retriedLlmData = {
      id: 'AM-429',
      statut_mecanique: 'NOUVEAU',
      resultat_ia: {
        statut: 'Discussion commune',
        analyse_intention: 'Succès après backoff exponentiel',
        niveau_confiance: 0.96,
      },
    }

    let llmCallCount = 0
    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/api/v2/mecanique')) {
        return Promise.resolve({
          ok: true,
          json: async () => mechanicalData,
        })
      }
      if (url.includes('/api/v2/analyser-llm')) {
        llmCallCount++
        if (llmCallCount === 1) {
          return Promise.resolve({
            ok: false,
            status: 429,
            text: async () => 'Rate limit exceeded',
          })
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => retriedLlmData,
        })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })

    const results = await classifyAmendmentsV2(mechanicalData, {
      aiSettings: { provider: 'groq_auto' },
      throttleDelayMs: 5,
      retryDelayMs: 10,
    })

    expect(llmCallCount).toBe(2)
    expect(results.length).toBe(1)
    expect(results[0].resultat_ia.statut).toBe('Discussion commune')
    expect(results[0].resultat_ia.niveau_confiance).toBe(0.96)
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

  describe('Chantier Local Turbo — Fonctions et Résilience JSON', () => {
    it('safeParseJson extrait correctement un JSON compact sur une seule ligne', () => {
      const raw = '{"statut":"Isolé","confiance":0.95,"cible":null,"justification":"Dispositif indépendant."}'
      const res = safeParseJson(raw)
      expect(res).toEqual({
        statut: 'Isolé',
        confiance: 0.95,
        cible: null,
        justification: 'Dispositif indépendant.',
      })
    })

    it('safeParseJson résiste aux bavardages multi-lignes et balises Markdown de Mistral', () => {
      const raw = '```json\n{"statut":"Discussion commune","confiance":0.9,"cible":"CD68","justification":"Réécriture concurrente."}\n```\nVoici quelques remarques supplémentaires...'
      const res = safeParseJson(raw)
      expect(res.statut).toBe('Discussion commune')
      expect(res.confiance).toBe(0.9)
      expect(res.cible).toBe('CD68')
      expect(res.justification).toContain('Réécriture concurrente.')
    })

    it('safeParseJson replie proprement vers "Isolé" en cas de statut non conforme ou absent', () => {
      const raw = '{"statut":"Inconnu","confiance":0.7}'
      const res = safeParseJson(raw)
      expect(res.statut).toBe('Isolé')
      expect(res.cible).toBeNull()
      expect(res.justification).toBeDefined()
    })

    it('safeParseJson gère les textes vides ou corrompus sans lancer d\'exception', () => {
      const vide = safeParseJson('')
      expect(vide.statut).toBe('Isolé')
      expect(vide.confiance).toBe(0.0)

      const invalide = safeParseJson('Pas de JSON du tout ici !')
      expect(invalide.statut).toBe('Isolé')
      expect(invalide.confiance).toBe(0.0)
    })

    it('buildLocalChatPayload fabrique un prompt greffier compact avec stop sequences et max_tokens 150', () => {
      const amendement = {
        id: 'AM-1',
        article: 'Article 3',
        dispositif: 'Supprimer cet article.',
        expose_sommaire: 'Exposé des motifs.',
      }
      const payload = buildLocalChatPayload(amendement, [{ id: 'AM-2', dispositif: 'Autre texte' }])

      expect(payload.max_tokens).toBe(150)
      expect(payload.stop).toEqual(LOCAL_STOP_SEQUENCES)
      expect(payload.messages[0].content).toBe(LOCAL_PROMPT_SYSTEM)
      expect(payload.messages.slice(1, 3)).toEqual(LOCAL_ONE_SHOT_MESSAGES)
      expect(payload.messages[3].content).toContain('Amendement candidat (Article 3)')
      expect(payload.messages[3].content).toContain('[AM-2]')
    })

    it('classifyAmendmentsV2 en mode local traite avec concurrence x3 et 0 ms de délai', async () => {
      const mechanicalData = [
        { id: 'AM-1', statut_mecanique: 'NOUVEAU', _skipLLM: false },
        { id: 'AM-2', statut_mecanique: 'NOUVEAU', _skipLLM: false },
        { id: 'AM-3', statut_mecanique: 'NOUVEAU', _skipLLM: false },
      ]

      let maxConcurrentCalls = 0
      let activeCalls = 0
      const capturedPayloads = []

      globalThis.fetch = vi.fn().mockImplementation(async (url, init) => {
        if (url.includes('/api/v2/mecanique')) {
          return {
            ok: true,
            json: async () => mechanicalData,
          }
        }
        if (url.includes('/api/v2/analyser-llm')) {
          activeCalls++
          maxConcurrentCalls = Math.max(maxConcurrentCalls, activeCalls)
          capturedPayloads.push(JSON.parse(init.body))

          // Léger délai asynchrone pour vérifier la concurrence
          await new Promise((r) => setTimeout(r, 20))
          activeCalls--

          const targetUid = JSON.parse(init.body).target_uid
          return {
            ok: true,
            json: async () => ({
              id: targetUid,
              resultat_ia: {
                id: targetUid,
                statut: 'Isolé',
                confiance: 0.9,
              },
            }),
          }
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`))
      })

      const onProgress = vi.fn()
      const results = await classifyAmendmentsV2(mechanicalData, {
        aiSettings: { provider: 'local' },
        onProgress,
      })

      expect(results.length).toBe(3)
      // La concurrence x3 s'exécute bien en parallèle
      expect(maxConcurrentCalls).toBeGreaterThanOrEqual(2)
      // Vérifier que le payload envoyé contient max_tokens 150 et stop sequences
      expect(capturedPayloads[0].max_tokens).toBe(150)
      expect(capturedPayloads[0].stop).toEqual(LOCAL_STOP_SEQUENCES)
      expect(onProgress).toHaveBeenCalled()
    })
  })
})
