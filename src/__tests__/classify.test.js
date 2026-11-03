import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  normalizeAmendments,
  classifyAmendmentsV2,
  classifyMechanically,
  explainConflictsWithAI,
  analyzeSingleAmendment,
  mergeAiExplanationIntoAmendment,
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

    it('safeParseJson répare automatiquement les JSON tronqués sans accolade fermante', () => {
      // Cas typique de finish_reason: "length" où la fermeture } a été coupée
      const tronque = '{"statut":"Discussion commune","confiance":0.85,"cible":"CD18","justification":"Réécriture concurrente du même alinéa'
      const res = safeParseJson(tronque)
      expect(res.statut).toBe('Discussion commune')
      expect(res.cible).toBe('CD18')
      expect(res.confiance).toBe(0.85)
      expect(res.justification).toContain('Réécriture concurrente')
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

    it('buildLocalChatPayload fabrique un prompt greffier compact avec stop sequences et max_tokens 250', () => {
      const amendement = {
        id: 'AM-1',
        article: 'Article 3',
        dispositif: 'Supprimer cet article.',
        expose_sommaire: 'Exposé des motifs.',
      }
      const payload = buildLocalChatPayload(amendement, [{ id: 'AM-2', dispositif: 'Autre texte' }])

      expect(payload.max_tokens).toBe(250)
      expect(payload.stop).toEqual(LOCAL_STOP_SEQUENCES)
      expect(payload.messages[0].content).toBe(LOCAL_PROMPT_SYSTEM)
      expect(payload.messages[0].content).toContain('Administrateur légistique')
      expect(payload.messages.slice(1, 3)).toEqual(LOCAL_ONE_SHOT_MESSAGES)
      expect(payload.messages[3].content).toContain('Amendement candidat (Article 3)')
      expect(payload.messages[3].content).toContain('[AM-2]')
    })

    it('classifyAmendmentsV2 en mode local traite en séquentiel strict (1 seul slot) avec 0 ms de délai', async () => {
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

          await new Promise((r) => setTimeout(r, 10))
          activeCalls--

          const targetUid = JSON.parse(init.body).target_uid
          return {
            ok: true,
            json: async () => ({
              id: targetUid,
              resultat_ia: {
                id: targetUid,
                statut: 'Isolé',
                confiance: 0.85,
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
      // Cadence séquentielle stricte : exactement 1 appel à la fois
      expect(maxConcurrentCalls).toBe(1)
      // Vérifier que le payload envoyé contient max_tokens 250 et stop sequences
      expect(capturedPayloads[0].max_tokens).toBe(250)
      expect(capturedPayloads[0].stop).toEqual(LOCAL_STOP_SEQUENCES)
      expect(onProgress).toHaveBeenCalled()
    })

    it('classifyAmendmentsV2 active le coupe-circuit en cas de timeout sans bloquer la file', async () => {
      const mechanicalData = [
        { id: 'AM-SLOW', statut_mecanique: 'NOUVEAU', _skipLLM: false },
        { id: 'AM-FAST', statut_mecanique: 'NOUVEAU', _skipLLM: false },
      ]

      globalThis.fetch = vi.fn().mockImplementation(async (url, init) => {
        if (url.includes('/api/v2/mecanique')) {
          return {
            ok: true,
            json: async () => mechanicalData,
          }
        }
        if (url.includes('/api/v2/analyser-llm')) {
          const body = JSON.parse(init.body)
          if (body.target_uid === 'AM-SLOW') {
            // Simule l'interruption par le coupe-circuit unitaire
            const err = new DOMException('The user aborted a request.', 'AbortError')
            // Simuler l'expiration du signal unitaire
            if (init.signal) {
              await new Promise((resolve) => setTimeout(resolve, 5))
            }
            throw err
          }
          return {
            ok: true,
            json: async () => ({
              id: 'AM-FAST',
              resultat_ia: {
                id: 'AM-FAST',
                statut: 'Discussion commune',
                confiance: 0.85,
              },
            }),
          }
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`))
      })

      // Pour le test, on force un timeout ultra-court via signal
      const results = await classifyAmendmentsV2(mechanicalData, {
        aiSettings: { provider: 'local' },
      })

      expect(results.length).toBe(2)
      // Le second amendement a bien été traité malgré l'erreur sur le premier
      expect(results[1].resultat_ia.statut).toBe('Discussion commune')
    })
  })

  describe('Architecture Hybride — classifyMechanically & explainConflictsWithAI', () => {
    it('classifyMechanically interroge POST /api/v2/classer-regles et fusionne statut, groupe_conflit_id et cible_numero', async () => {
      const localAmendments = [
        { id: 'AM-1', numero: '1', article: 'Article PREMIER', dispositif: 'Supprimer cet article.', commission: 'Affaires culturelles' },
        { id: 'AM-2', numero: '2', article: 'Article PREMIER', dispositif: 'Supprimer cet article.', commission: 'Affaires culturelles' },
      ]

      const serverResponse = {
        statut: 'success',
        total: 2,
        duree_ms: 12,
        statistiques: { identiques: 2, discussions_communes: 0, isoles: 0 },
        amendements: [
          {
            id: 'AM-1',
            numero: '1',
            statut: 'Identique',
            confiance: 1.0,
            groupe_conflit_id: 'id_art_1er_abcd1234',
            cible_numero: '2',
            justification: 'Amendement identique au n° 2.',
          },
          {
            id: 'AM-2',
            numero: '2',
            statut: 'Identique',
            confiance: 1.0,
            groupe_conflit_id: 'id_art_1er_abcd1234',
            cible_numero: '1',
            justification: 'Identique à l\'amendement n° 1.',
          },
        ],
      }

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => serverResponse,
      })

      const res = await classifyMechanically(localAmendments)
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/classer-regles'),
        expect.objectContaining({ method: 'POST' })
      )
      expect(res.length).toBe(2)
      expect(res[0].statut).toBe('Identique')
      expect(res[0].groupe_conflit_id).toBe('id_art_1er_abcd1234')
      expect(res[0].cible_numero).toBe('2')
      expect(res[0].commission).toBe('Affaires culturelles')
      expect(res._meta.duree_ms).toBe(12)
    })

    it('explainConflictsWithAI ne recalcule PAS les statuts et cible uniquement les Discussions communes', async () => {
      const classifiedAmendments = [
        {
          id: 'AM-ID',
          numero: '10',
          article: 'Article 1er',
          statut: 'Identique',
          groupe_conflit_id: 'id_art_1er_111',
          cible_numero: '11',
          justification: 'Identique au n° 11.',
          resultat_ia: {
            id: 'AM-ID',
            statut: 'Identique',
            groupe_conflit_id: 'id_art_1er_111',
            cible_numero: '11',
            groupe: { type: 'identiques', groupe_id: 'id_art_1er_111' },
            justification: 'Identique au n° 11.',
          },
        },
        {
          id: 'AM-DC',
          numero: '20',
          article: 'Article 3 BIS',
          statut: 'Discussion commune',
          groupe_conflit_id: 'dc_art_3_bis_p_20',
          cible_numero: '21',
          justification: 'Justification mécanique initiale.',
          resultat_ia: {
            id: 'AM-DC',
            statut: 'Discussion commune',
            groupe_conflit_id: 'dc_art_3_bis_p_20',
            cible_numero: '21',
            groupe: { type: 'discussion_commune', groupe_id: 'dc_art_3_bis_p_20' },
            justification: 'Justification mécanique initiale.',
          },
        },
      ]

      let llmCalls = 0
      globalThis.fetch = vi.fn().mockImplementation(async (url) => {
        if (url.includes('/api/v2/analyser-llm')) {
          llmCalls++
          return {
            ok: true,
            json: async () => ({
              id: 'AM-DC',
              resultat_ia: {
                // Même si le LLM suggère à tort "Isolé", le statut et le groupe déterministes doivent être préservés
                statut: 'Isolé',
                justification: 'Synthèse politique IA : opposition entre exonération totale et plafonnement.',
                analyse_intention: 'Synthèse politique IA : opposition entre exonération totale et plafonnement.',
              },
            }),
          }
        }
        throw new Error(`Unexpected URL: ${url}`)
      })

      const enriched = await explainConflictsWithAI(classifiedAmendments, {
        aiSettings: { provider: 'local' },
      })

      // Seul l'amendement en Discussion commune a sollicité l'IA
      expect(llmCalls).toBe(1)
      // Le statut et le groupe déterministes sont strictement préservés
      expect(enriched[1].statut).toBe('Discussion commune')
      expect(enriched[1].groupe_conflit_id).toBe('dc_art_3_bis_p_20')
      expect(enriched[1].cible_numero).toBe('21')
      expect(enriched[1].resultat_ia.groupe.groupe_id).toBe('dc_art_3_bis_p_20')
      // La justification a bien été enrichie par l'IA
      expect(enriched[1].justification).toContain('Synthèse politique IA')
      expect(enriched[1].resultat_ia.explication_ia).toBe(true)
    })

    it('mergeAiExplanationIntoAmendment préserve rigoureusement le statut et le groupe déterministes', () => {
      const orig = {
        id: 'AM-50',
        statut: 'Discussion commune',
        groupe_conflit_id: 'dc_art_12_p_50',
        cible_numero: '52',
        justification: 'Collision alinéa 3.',
      }
      const merged = mergeAiExplanationIntoAmendment(orig, {
        resultat_ia: {
          statut: 'Isolé',
          justification: 'Concurrence entre deux seuils budgétaires sur l\'alinéa 3.',
        },
      })
      expect(merged.statut).toBe('Discussion commune')
      expect(merged.groupe_conflit_id).toBe('dc_art_12_p_50')
      expect(merged.cible_numero).toBe('52')
      expect(merged.justification).toContain('Concurrence entre deux seuils')
    })

    it('analyzeSingleAmendment cible le cluster de l\'amendement et préserve son statut déterministe', async () => {
      const amendments = [
        {
          id: 'AM-10',
          numero: '10',
          article: 'Article 3 BIS',
          statut: 'Discussion commune',
          groupe_conflit_id: 'dc_art_3_bis_p_10',
          cible_numero: '11',
          justification: 'Collision initiale.',
        },
        {
          id: 'AM-11',
          numero: '11',
          article: 'Article 3 BIS',
          statut: 'Discussion commune',
          groupe_conflit_id: 'dc_art_3_bis_p_10',
          cible_numero: '10',
          justification: 'Collision initiale.',
        },
      ]

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: 'AM-10',
          resultat_ia: {
            statut: 'Isolé',
            justification: 'Explication unitaire par IA du conflit sur l\'article 3 BIS.',
          },
        }),
      })

      const resIa = await analyzeSingleAmendment('AM-10', amendments, { provider: 'local' })
      expect(resIa.statut).toBe('Discussion commune')
      expect(resIa.groupe_conflit_id).toBe('dc_art_3_bis_p_10')
      expect(resIa.justification).toContain('Explication unitaire par IA')
    })
  })
})
