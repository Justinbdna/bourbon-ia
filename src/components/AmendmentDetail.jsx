import { useState, useEffect, useMemo } from 'react'
import ScrollableText from './ScrollableText'
import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'
import AuthorBadge from './amendment/AuthorBadge'
import PoliticalGroupTag from './amendment/PoliticalGroupTag'
import LegislativeContext from './amendment/LegislativeContext'
import IdentiqueAlert from './amendment/IdentiqueAlert'
import SkeletonLoader from './amendment/SkeletonLoader'
import EUCompliancePanel from './amendment/EUCompliancePanel'
import ResumeIA from './amendment/ResumeIA'
import { analyzeSurtransposition, runDeepAudit } from '../api/classify'

export function formatCleanArticleHeading(article) {
  if (!article) return 'Article —'
  const str = String(article).trim()
  // Dédupliquer les répétitions éventuelles ("Article Article PREMIER" -> "Article PREMIER")
  let clean = str.replace(/^(article\s+|art\.\s*)+/gi, 'Article ')
  // Vérifie si la chaîne commence déjà par article, art., après l'article ou avant l'article
  if (/^(article|art\.|apr[eè]s\s+l['’]article|avant\s+l['’]article|apr[eè]s\s+l['’]art\.|avant\s+l['’]art\.)/i.test(clean)) {
    return clean
  }
  return `Article ${clean}`
}

export const formatArticleTitle = formatCleanArticleHeading

export function computeWordDiff(text1 = '', text2 = '') {
  if (!text1 && !text2) return []
  const words1 = String(text1).split(/(\s+)/).filter(Boolean)
  const words2 = String(text2).split(/(\s+)/).filter(Boolean)
  const n = words1.length, m = words2.length
  if (n > 600 || m > 600) {
    return [
      { type: 'del', text: text1 },
      { type: 'add', text: text2 },
    ]
  }
  const dp = Array(n + 1).fill(null).map(() => Array(m + 1).fill(0))
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < m; j++) {
      if (words1[i] === words2[j]) {
        dp[i + 1][j + 1] = dp[i][j] + 1
      } else {
        dp[i + 1][j + 1] = Math.max(dp[i + 1][j], dp[i][j + 1])
      }
    }
  }
  let i = n, j = m
  const result = []
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && words1[i - 1] === words2[j - 1]) {
      result.unshift({ type: 'same', text: words1[i - 1] })
      i--; j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ type: 'add', text: words2[j - 1] })
      j--
    } else if (i > 0) {
      result.unshift({ type: 'del', text: words1[i - 1] })
      i--
    }
  }
  return result
}

export function extractTargetedLawSegment(texteLoi = '', dispositif = '') {
  if (!texteLoi) return ''
  const strLoi = String(texteLoi).trim()
  const strDisp = String(dispositif || '')
  const alineaMatch = strDisp.match(/alin[eé]a\s+(\d+)/i)
  if (alineaMatch) {
    const num = alineaMatch[1]
    const lines = strLoi.split('\n')
    const matchedLine = lines.find((l) => l.trim().startsWith(`(${num})`))
    if (matchedLine) {
      return matchedLine.replace(/^\(\d+\)\s*/, '').trim()
    }
  }
  return strLoi
}

export default function AmendmentDetail({
  amendment,
  allAmendments = [],
  onClose,
  isLoading,
  aiSettings,
  onArbitrage,
  initialCompareWithLaw = false,
}) {
  const [euCompliance, setEuCompliance] = useState(amendment?.eu_compliance || null)
  const [compareId, setCompareId] = useState(null)
  const [compareWithLaw, setCompareWithLaw] = useState(initialCompareWithLaw)
  const [deepAudit, setDeepAudit] = useState(null)
  const [deepAuditLoading, setDeepAuditLoading] = useState(false)
  const [deepAuditError, setDeepAuditError] = useState(null)

  const amendmentKey = amendment?.uid ?? amendment?.id ?? null

  useEffect(() => {
    setDeepAudit(null)
    setDeepAuditLoading(false)
    setDeepAuditError(null)
  }, [amendmentKey])

  useEffect(() => {
    let isCurrent = true
    setCompareId(null)
    setCompareWithLaw(false)
    if (amendment?.eu_compliance) {
      setEuCompliance(amendment.eu_compliance)
      return () => {
        isCurrent = false
      }
    }
    setEuCompliance(null)
    if (amendment) {
      analyzeSurtransposition(amendment, { aiSettings })
        .then((result) => {
          if (isCurrent && result) {
            setEuCompliance(result)
          }
        })
        .catch(() => {})
    }
    return () => {
      isCurrent = false
    }
  }, [amendmentKey, amendment, aiSettings])

  const a = amendment || {}
  const res = a.resultat_ia

  const concurrents = useMemo(() => {
    if (!amendment || !allAmendments || allAmendments.length === 0) return []
    const monId = a.id ?? a.uid
    return allAmendments.filter((other) => (other.id ?? other.uid) !== monId)
  }, [allAmendments, amendment, a.id, a.uid])

  const concurrentsTries = useMemo(() => {
    return [...concurrents].sort((x, y) => {
      const memeArtX = x.article === a.article ? 0 : 1
      const memeArtY = y.article === a.article ? 0 : 1
      if (memeArtX !== memeArtY) return memeArtX - memeArtY
      return (x.numero || '').localeCompare(y.numero || '', 'fr', { numeric: true })
    })
  }, [concurrents, a.article])

  const targetAmd = useMemo(() => {
    if (!compareId) return null
    return concurrents.find((c) => String(c.id ?? c.uid) === String(compareId)) || null
  }, [compareId, concurrents])

  const diffMots = useMemo(() => {
    if (!targetAmd || !a.dispositif) return null
    return computeWordDiff(a.dispositif, targetAmd.dispositif || '')
  }, [targetAmd, a.dispositif])

  const segmentLoiCible = useMemo(() => {
    if (!a.texte_loi_reference) return ''
    return extractTargetedLawSegment(a.texte_loi_reference, a.dispositif)
  }, [a.texte_loi_reference, a.dispositif])

  const diffLoi = useMemo(() => {
    if (!compareWithLaw || !segmentLoiCible || !a.dispositif) return null
    return computeWordDiff(segmentLoiCible, a.dispositif)
  }, [compareWithLaw, segmentLoiCible, a.dispositif])

  async function handleRunDeepAudit() {
    if (!amendment || deepAuditLoading) return
    setDeepAuditLoading(true)
    setDeepAuditError(null)
    try {
      const data = await runDeepAudit(amendment)
      setDeepAudit(data)
    } catch (err) {
      setDeepAuditError(err?.message || "Impossible d'exécuter le contrôle approfondi.")
    } finally {
      setDeepAuditLoading(false)
    }
  }

  // ── Safe Rendering : Skeleton si en cours de chargement ──
  if (isLoading) {
    return (
      <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-6 h-full">
        <SkeletonLoader type="card" />
      </div>
    )
  }

  if (!amendment) {
    return (
      <div className="rounded-lg border border-dashed border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-8 h-full flex items-center justify-center">
        <p className="text-sm text-ink-500 dark:text-ink-300 text-center">
          Sélectionne un amendement dans le tableau pour voir son détail.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 flex flex-col h-full">
      <div className="border-b border-ink-100 dark:border-ink-700 px-5 py-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-500 dark:text-ink-400">
            {a.texte_examine?.titre}
            {a.texte_examine?.lecture ? ` · ${a.texte_examine.lecture}` : ''}
          </p>
          <h3 className="font-display text-xl text-slate-900 dark:text-plume mt-0.5 flex items-center gap-2 flex-wrap">
            <span>
              {formatCleanArticleHeading(a.article)} — Amendement n° {a.numero}
              {a.rectification ? ` ${a.rectification}` : ''}
            </span>
            {a.est_gage && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-700 px-2.5 py-0.5 text-xs font-semibold">
                💰 Gagé (Art. 40)
              </span>
            )}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-ink-500 hover:text-ink-900 dark:text-ink-400 dark:hover:text-plume text-sm shrink-0"
          aria-label="Fermer le détail"
        >
          Fermer ✕
        </button>
      </div>

      <div className="px-5 py-4 space-y-5 overflow-y-auto scroll-thin">
        {/* ── Alerte Identique Officiel AN ── */}
        <IdentiqueAlert
          isIdentical={a.isIdentical ?? a.est_identique_officiel ?? false}
          discussionId={a.discussionId ?? a.id_discussion_identique}
        />

        {/* ── Alerte Amendement Tombant (Chute par ricochet) ── */}
        {(a.tombe_si_adoption || a.alerte_tombant || (Array.isArray(a.tombe_si_adoption_de) && a.tombe_si_adoption_de.length > 0)) && (
          <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/60 text-amber-900 dark:text-amber-200 text-xs leading-relaxed">
            <span className="text-base shrink-0">⚠️</span>
            <div>
              <span className="inline-flex items-center gap-1 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-200 border border-rose-300 dark:border-rose-700 px-2.5 py-0.5 text-[11px] font-bold">
                ⚠️ Tombe si adoption de {Array.isArray(a.tombe_si_adoption_de) && a.tombe_si_adoption_de.length > 0 ? a.tombe_si_adoption_de.join(', ') : (a.parent_suppression_numero || 'suppression')}
              </span>
              <p className="mt-1">
                {a.alerte_tombant || `Cet amendement tombe automatiquement si l'amendement de suppression ${Array.isArray(a.tombe_si_adoption_de) && a.tombe_si_adoption_de.length > 0 ? a.tombe_si_adoption_de.join(', ') : (a.parent_suppression_numero || '')} est adopté en séance.`}
              </p>
            </div>
          </div>
        )}

        {/* ── Alerte Cavalier Législatif (Art. 45 Constitution) ── */}
        {(a.est_cavalier_art45 || a.alerte_art45) && (
          <div className="flex items-start gap-2.5 p-3 rounded-lg bg-purple-50 dark:bg-purple-950/40 border border-purple-300 dark:border-purple-700/60 text-purple-900 dark:text-purple-200 text-xs leading-relaxed">
            <span className="text-base shrink-0">⚖️</span>
            <div>
              <p className="font-bold uppercase tracking-wider text-[11px] text-purple-800 dark:text-purple-300">
                Risque d'irrecevabilité — Article 45 de la Constitution
              </p>
              <p className="mt-0.5">
                {a.alerte_art45 || "Lien indirect douteux avec le texte en discussion (cavalier législatif potentiel)."}
              </p>
            </div>
          </div>
        )}

        {/* ── Ordre d'appel en séance (Art. 98 Règlement AN) ── */}
        {a.priorite_appel && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-100 dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs">
            <span className="font-semibold text-slate-900 dark:text-plume">🏛️ Ordre d'appel (Art. 98) :</span>
            <span className="px-1.5 py-0.5 rounded text-[11px] font-bold bg-[#D91227]/10 text-[#D91227] dark:bg-[#D91227]/20 dark:text-red-400">
              Priorité {a.priorite_appel}/5
            </span>
            <span className="text-slate-600 dark:text-slate-400 italic">
              {a.libelle_appel || ''}
            </span>
          </div>
        )}

        {/* ── Contexte législatif (titre tronqué + tooltip) ── */}
        {(a.title || a.dossier_titre) && (
          <LegislativeContext
            title={a.title || a.dossier_titre}
            dossierRef={a.dossier_ref}
          />
        )}

        <div className="flex flex-wrap gap-4 text-sm">
          {/* ── Auteur enrichi ── */}
          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs mb-1">Auteur(s) & Rôle</p>
            {a.auteur_nom && a.auteur_nom !== "Inconnu" ? (
              <div className="flex flex-col items-start gap-1">
                <AuthorBadge data={{
                  auteur_nom: a.auteur_nom,
                  auteur_prenom: a.auteur_prenom,
                  auteur_trigramme: a.auteur_trigramme
                }} />
                {(a.est_rapporteur || a.rapporteur || a.role === 'Rapporteur') && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
                    📋 Rapporteur
                  </span>
                )}
                {(a.est_gouvernement || a.role === 'Gouvernement') && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-900 text-amber-200 border border-slate-700">
                    🏛️ Exécutif
                  </span>
                )}
              </div>
            ) : (
              <div className="max-h-24 overflow-y-auto text-sm bg-gray-100 text-slate-900 dark:bg-[#1A1B22] dark:text-white border border-gray-300 dark:border-gray-700 p-2 rounded mt-1">
                <p className="font-medium">
                  {(a.est_rapporteur || a.rapporteur || a.role === 'Rapporteur') ? 'Rapporteur — ' : ''}
                  {(a.est_gouvernement || a.role === 'Gouvernement') ? 'Gouvernement — ' : ''}
                  {(a.auteurs || []).join(', ') || '—'}
                </p>
              </div>
            )}
          </div>

          {/* ── Groupe politique ── */}
          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs mb-1">Groupe</p>
            <PoliticalGroupTag
              group={a.groupe_politique || a.groupe}
              groupRef={a.groupRef ?? a.groupe_politique_ref}
            />
          </div>

          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs">Date de dépôt</p>
            <p className="text-ink-900 dark:text-plume font-medium">{a.date_depot || a.dateDepot || '—'}</p>
          </div>
          <div>
            <p className="text-ink-500 dark:text-ink-400 text-xs">Point d'impact</p>
            <ImpactBadge type={a.point_impact?.type} />
          </div>
        </div>

        {/* ── Résumé IA à la demande (1 à 2 phrases neutres) ── */}
        <ResumeIA key={a.id ?? a.uid} amendment={a} aiSettings={aiSettings} />

        {/* ── Conformité européenne (surtransposition) — panneau dépliable ── */}
        <EUCompliancePanel result={euCompliance || a.eu_compliance} />

        {/* ── Contrôle approfondi (Règles Art. 40/45/98, HATVP & Debunker chronologique) ── */}
        <section
          className="rounded-md bg-slate-50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-700/80 p-3.5 space-y-3"
          data-testid="deep-audit-section"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume">
              🛡️ CONTRÔLE APPROFONDI (RÈGLES, HATVP & HISTORIQUE)
            </h4>
            <button
              type="button"
              data-testid="btn-deep-audit"
              onClick={handleRunDeepAudit}
              disabled={deepAuditLoading}
              className="rounded-md bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-3 py-1.5 text-xs font-semibold hover:bg-slate-800 dark:hover:bg-white transition-colors disabled:opacity-50"
            >
              {deepAuditLoading ? '⏳ Audit en cours...' : "🔍 Lancer l'audit approfondi"}
            </button>
          </div>

          {deepAuditError && (
            <p className="text-xs text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded px-2.5 py-2">
              {deepAuditError}
            </p>
          )}

          {deepAudit && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs" data-testid="deep-audit-cards">
              {/* Carte 1 — Recevabilité & Ordre d'appel (Art. 40 / 45 / 98) */}
              <div className="rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#12131A] p-3 space-y-1.5">
                <p className="font-bold text-slate-900 dark:text-plume">
                  ⚖️ Recevabilité & Ordre d'appel
                </p>
                <p className="text-slate-700 dark:text-slate-300">
                  <span className="font-semibold">Art. 98 RAN :</span> Priorité {deepAudit.rules?.priorite_appel_art98 ?? '—'}/5
                  {deepAudit.rules?.libelle_appel_art98 ? ` (${deepAudit.rules.libelle_appel_art98})` : ''}
                </p>
                <p className={deepAudit.rules?.alerte_art40 ? 'text-rose-700 dark:text-rose-300 font-semibold' : 'text-emerald-700 dark:text-emerald-300'}>
                  {deepAudit.rules?.alerte_art40
                    ? `⚠️ Art. 40 : ${deepAudit.rules?.motif_art40 || 'Risque financier détecté'}`
                    : `✓ Art. 40 : ${deepAudit.rules?.gage_detecte ? `Gagé (${deepAudit.rules.gage_detecte})` : 'Aucune charge non gagée'}`}
                </p>
                <p className={deepAudit.rules?.risque_cavalier_art45 ? 'text-purple-700 dark:text-purple-300 font-semibold' : 'text-slate-600 dark:text-slate-400'}>
                  {deepAudit.rules?.risque_cavalier_art45
                    ? `⚠️ Art. 45 : Risque de cavalier législatif (proximité ${deepAudit.rules?.proximite_texte_score ?? 0})`
                    : `✓ Art. 45 : Lien texte conforme (score ${deepAudit.rules?.proximite_texte_score ?? 1})`}
                </p>
                {Array.isArray(deepAudit.rules?.violations) && deepAudit.rules.violations.length > 0 && (
                  <ul className="pt-1 border-t border-slate-100 dark:border-slate-800 space-y-1 text-[11px] text-slate-600 dark:text-slate-400">
                    {deepAudit.rules.violations.map((v, idx) => (
                      <li key={idx}>• <strong>{v.code_article}</strong> : {v.motif}</li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Carte 2 — Croisement d'intérêt (HATVP) */}
              <div className="rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#12131A] p-3 space-y-1.5">
                <p className="font-bold text-slate-900 dark:text-plume">
                  🕸️ Croisement d'intérêt (HATVP)
                </p>
                {Array.isArray(deepAudit.hatvp?.matches) && deepAudit.hatvp.matches.length > 0 ? (
                  <ul className="space-y-2">
                    {deepAudit.hatvp.matches.map((m) => (
                      <li key={m.rep_id} className="border-b last:border-b-0 border-slate-100 dark:border-slate-800 pb-1.5 last:pb-0">
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-semibold text-slate-800 dark:text-slate-200">{m.organisation}</span>
                          <span className="rounded bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 px-1.5 py-0.5 text-[10px] font-bold">
                            {Math.round((m.score_proximite || 0) * 100)}%
                          </span>
                        </div>
                        {m.secteur && <p className="text-[11px] text-slate-500 dark:text-slate-400">{m.secteur}</p>}
                        {m.objet_declare && <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5">{m.objet_declare}</p>}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-slate-500 dark:text-slate-400 italic">
                    Aucune correspondance déclarée à la HATVP pour cet amendement.
                  </p>
                )}
              </div>

              {/* Carte 3 — Cohérence chronologique (Scrutins & Interventions) */}
              <div className="rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#12131A] p-3 space-y-1.5">
                <p className="font-bold text-slate-900 dark:text-plume">
                  🕰️ Cohérence chronologique
                </p>
                {deepAudit.debunker?.status === 'no_history' || !Array.isArray(deepAudit.debunker?.historique) || deepAudit.debunker.historique.length === 0 ? (
                  <p className="text-slate-500 dark:text-slate-400 italic">
                    {deepAudit.debunker?.answer || 'Information non disponible dans les sources'}
                  </p>
                ) : (
                  <div className="space-y-1.5">
                    <p className={deepAudit.debunker.status === 'contradiction_detected' ? 'text-rose-700 dark:text-rose-300 font-semibold' : 'text-emerald-700 dark:text-emerald-300 font-medium'}>
                      {deepAudit.debunker.message}
                    </p>
                    <ul className="space-y-1.5 pt-1 border-t border-slate-100 dark:border-slate-800">
                      {deepAudit.debunker.historique.map((h) => (
                        <li key={h.entry_id} className="text-[11px] text-slate-600 dark:text-slate-300">
                          <span className="font-semibold">{h.date_seance}</span> ({h.type_entree} · vote « {h.position_vote} ») — {h.sujet}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* ── Résultat IA (avec Chain of Thought & Arbitrage manuel en 1 clic) ── */}
        <section className="rounded-md bg-slate-50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-800 p-3.5">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume">
              Résultat du classement
            </h4>
            {(a.arbitrage_manuel || a.arbitre_manuellement) && (
              <span
                className="inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 px-2.5 py-0.5 text-xs font-semibold"
                data-testid="badge-arbitrage-manuel"
              >
                ✍️ Arbitré manuellement
              </span>
            )}
          </div>
          {res ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-slate-900 dark:text-plume">Rang {res.rang}</span>
                <GroupeBadge statut={res.statut || a.statut} groupe={res.groupe} />

                {/* ── 💡 Tooltip Chain of Thought ── */}
                {res.analyse_intention && (
                  <div className="group relative inline-flex">
                    <span className="cursor-help text-base" title={res.analyse_intention}>💡</span>
                    <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 bg-slate-900 text-white text-xs rounded-lg shadow-xl p-3 leading-relaxed">
                      <p className="font-semibold text-amber-300 mb-1">🧠 Raisonnement de l'IA</p>
                      <p className="mb-1">{res.analyse_intention}</p>
                      {res.analyse_politique && (
                        <p className="text-slate-300 border-t border-slate-700 pt-1 mt-1">{res.analyse_politique}</p>
                      )}
                      {res.niveau_confiance != null && (
                        <p className="text-slate-400 mt-1">Confiance : {(res.niveau_confiance * 100).toFixed(0)}%</p>
                      )}
                      {res.cached && (
                        <p className="text-green-400 mt-1 text-[10px]">📦 Résultat en cache</p>
                      )}
                      <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-[1px] border-4 border-transparent border-t-slate-900" />
                    </div>
                  </div>
                )}
              </div>
              <p className="text-ink-700 dark:text-ink-300">{res.justification}</p>
            </div>
          ) : (
            <p className="text-sm text-ink-500 dark:text-ink-400 italic">
              Pas encore classé — lance le classement depuis le bouton en haut de page.
            </p>
          )}

          {/* ── Sélecteur rapide d'arbitrage manuel (Human-in-the-Loop) ── */}
          <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700/70 flex flex-wrap items-center gap-2 text-xs">
            <label className="font-medium text-slate-700 dark:text-slate-300">
              ✍️ Requalifier manuellement :
            </label>
            <select
              data-testid="select-arbitrage-statut"
              value={res?.statut || a.statut || 'Isolé'}
              onChange={(e) => {
                if (onArbitrage) {
                  onArbitrage(a.id ?? a.uid, e.target.value, a.cible_numero || res?.cible_numero || null)
                }
              }}
              className="h-8 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#D91227]"
            >
              <option value="Isolé">Isolé</option>
              <option value="Discussion commune">Discussion commune</option>
              <option value="Identique">Identique</option>
            </select>

            {concurrentsTries.length > 0 && ((res?.statut || a.statut) === 'Discussion commune' || (res?.statut || a.statut) === 'Identique') && (
              <div className="flex items-center gap-1.5">
                <span className="text-slate-600 dark:text-slate-400">Cible :</span>
                <select
                  data-testid="select-arbitrage-cible"
                  value={a.cible_numero || res?.cible_numero || res?.id_discussion_cible || ''}
                  onChange={(e) => {
                    if (onArbitrage) {
                      onArbitrage(a.id ?? a.uid, res?.statut || a.statut || 'Discussion commune', e.target.value || null)
                    }
                  }}
                  className="h-8 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#D91227]"
                >
                  <option value="">Aucune cible spécifique</option>
                  {concurrentsTries.map((c) => (
                    <option key={c.id ?? c.uid} value={c.numero || c.id}>
                      N° {c.numero || c.id} ({c.article})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </section>

        {a.texte_loi_reference && (
          <section className="bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/40 rounded-md p-4">
            <h4 className="font-display text-sm uppercase tracking-wide text-amber-900 dark:text-amber-200 mb-2 flex items-center gap-1.5">
              <span>📜</span> Texte de loi initial de référence ({formatCleanArticleHeading(a.article)})
            </h4>
            <ScrollableText text={a.texte_loi_reference} />
          </section>
        )}

        <section className="bg-gray-50 dark:bg-surface border border-ink-200 dark:border-ink-700 rounded-md p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume">
              Dispositif
            </h4>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setCompareWithLaw((prev) => !prev)
                  setCompareId(null)
                }}
                className={`rounded border px-2.5 py-1 text-xs font-medium transition-colors ${
                  compareWithLaw
                    ? 'border-[#D91227] bg-[#D91227]/10 text-[#D91227] dark:bg-[#D91227]/20 dark:text-red-300'
                    : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                ⚖️ Comparer avec le texte de loi initial
              </button>
              {concurrentsTries.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <label className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                    Concurrent :
                  </label>
                  <select
                    value={compareId || ''}
                    onChange={(e) => {
                      const val = e.target.value || null
                      setCompareId(val)
                      if (val) setCompareWithLaw(false)
                    }}
                    className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-[#D91227]"
                  >
                    <option value="">Texte seul</option>
                    {concurrentsTries.map((c) => (
                      <option key={c.id ?? c.uid} value={c.id ?? c.uid}>
                        {c.article === a.article ? '🎯 ' : ''}N° {c.numero || c.id} ({c.auteur_nom || c.auteurs?.[0] || 'Inconnu'} - {c.groupe_politique || c.groupe || '—'})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>

          {compareWithLaw ? (
            a.texte_loi_reference && diffLoi ? (
              <div className="space-y-3" data-testid="law-diff-view">
                <div className="flex flex-wrap items-center gap-2 text-xs bg-amber-50 dark:bg-amber-950/30 p-2 rounded border border-amber-200 dark:border-amber-800/50">
                  <span className="font-semibold text-amber-900 dark:text-amber-200">
                    Différentiel Loi initiale ({formatCleanArticleHeading(a.article)}) vs Amendement n° {a.numero || a.id} :
                  </span>
                  <span className="inline-flex items-center gap-1 text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-950/60 px-1.5 py-0.5 rounded font-mono text-[11px]">
                    <del>rouge</del> = texte de loi initial
                  </span>
                  <span className="inline-flex items-center gap-1 text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-950/60 px-1.5 py-0.5 rounded font-mono text-[11px]">
                    <ins className="no-underline font-semibold">+vert</ins> = modification proposée
                  </span>
                </div>
                <div className="max-h-60 overflow-y-auto p-3 rounded bg-white dark:bg-[#0B0C10] border border-slate-200 dark:border-slate-800 font-mono text-xs leading-relaxed">
                  {diffLoi.map((chunk, i) => {
                    if (chunk.type === 'del') {
                      return (
                        <span key={i} className="bg-red-100 text-red-800 dark:bg-red-950/80 dark:text-red-300 line-through px-0.5 rounded mr-0.5">
                          {chunk.text}
                        </span>
                      )
                    }
                    if (chunk.type === 'add') {
                      return (
                        <span key={i} className="bg-green-100 text-green-800 dark:bg-green-950/80 dark:text-green-300 font-semibold px-0.5 rounded mr-0.5">
                          {chunk.text}
                        </span>
                      )
                    }
                    return <span key={i}>{chunk.text}</span>
                  })}
                </div>
              </div>
            ) : (
              <div
                className="p-3 rounded bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 text-xs text-amber-900 dark:text-amber-200"
                data-testid="law-diff-fallback"
              >
                Texte de loi initial non disponible pour cet amendement ({formatCleanArticleHeading(a.article)}). Affichage du dispositif seul :
                <div className="mt-2">
                  <ScrollableText text={a.dispositif} />
                </div>
              </div>
            )
          ) : diffMots && targetAmd ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-xs bg-slate-100 dark:bg-slate-800/80 p-2 rounded border border-slate-200 dark:border-slate-700">
                <span className="font-semibold text-slate-700 dark:text-slate-300">Diff mot-à-mot vs N° {targetAmd.numero || targetAmd.id} :</span>
                <span className="inline-flex items-center gap-1 text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-950/60 px-1.5 py-0.5 rounded font-mono text-[11px]">
                  <del>rouge</del> = propre à {a.numero || 'cet amendement'}
                </span>
                <span className="inline-flex items-center gap-1 text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-950/60 px-1.5 py-0.5 rounded font-mono text-[11px]">
                  <ins className="no-underline font-semibold">+vert</ins> = présent chez N° {targetAmd.numero || targetAmd.id}
                </span>
              </div>
              <div className="max-h-60 overflow-y-auto p-3 rounded bg-white dark:bg-[#0B0C10] border border-slate-200 dark:border-slate-800 font-mono text-xs leading-relaxed">
                {diffMots.map((chunk, i) => {
                  if (chunk.type === 'del') {
                    return (
                      <span key={i} className="bg-red-100 text-red-800 dark:bg-red-950/80 dark:text-red-300 line-through px-0.5 rounded mr-0.5">
                        {chunk.text}
                      </span>
                    )
                  }
                  if (chunk.type === 'add') {
                    return (
                      <span key={i} className="bg-green-100 text-green-800 dark:bg-green-950/80 dark:text-green-300 font-semibold px-0.5 rounded mr-0.5">
                        {chunk.text}
                      </span>
                    )
                  }
                  return <span key={i}>{chunk.text}</span>
                })}
              </div>
            </div>
          ) : (
            <ScrollableText text={a.dispositif} />
          )}
        </section>

        <section className="bg-gray-50 dark:bg-surface border border-ink-200 dark:border-ink-700 rounded-md p-4">
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Exposé sommaire
          </h4>
          <ScrollableText text={a.expose_sommaire} />
        </section>
      </div>
    </div>
  )
}
