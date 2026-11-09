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
import { analyzeSurtransposition } from '../api/classify'

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

export default function AmendmentDetail({ amendment, allAmendments = [], onClose, isLoading, aiSettings }) {
  const [euCompliance, setEuCompliance] = useState(amendment?.eu_compliance || null)
  const [compareId, setCompareId] = useState(null)

  useEffect(() => {
    let isCurrent = true
    if (amendment?.eu_compliance) {
      setEuCompliance(amendment.eu_compliance)
      return
    }
    if (amendment) {
      analyzeSurtransposition(amendment)
        .then((result) => {
          if (isCurrent && result) {
            setEuCompliance(result)
          }
        })
        .catch(() => {})
    } else {
      setEuCompliance(null)
    }
    return () => {
      isCurrent = false
    }
  }, [amendment])

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

  const a = amendment
  const res = a.resultat_ia

  const concurrents = useMemo(() => {
    if (!allAmendments || allAmendments.length === 0) return []
    const monId = a.id ?? a.uid
    return allAmendments.filter((other) => (other.id ?? other.uid) !== monId)
  }, [allAmendments, a])

  const concurrentsTries = useMemo(() => {
    return [...concurrents].sort((x, y) => {
      const memeArtX = x.article === a.article ? 0 : 1
      const memeArtY = y.article === a.article ? 0 : 1
      if (memeArtX !== memeArtY) return memeArtX - memeArtY
      return (x.numero || '').localeCompare(y.numero || '', 'fr', { numeric: true })
    })
  }, [concurrents, a])

  const targetAmd = useMemo(() => {
    if (!compareId) return null
    return concurrents.find((c) => String(c.id ?? c.uid) === String(compareId)) || null
  }, [compareId, concurrents])

  const diffMots = useMemo(() => {
    if (!targetAmd || !a.dispositif) return null
    return computeWordDiff(a.dispositif, targetAmd.dispositif || '')
  }, [targetAmd, a.dispositif])

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
        {(a.tombe_si_adoption || a.alerte_tombant) && (
          <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/60 text-amber-900 dark:text-amber-200 text-xs leading-relaxed">
            <span className="text-base shrink-0">⚠️</span>
            <div>
              <p className="font-bold uppercase tracking-wider text-[11px] text-amber-800 dark:text-amber-300">
                Amendement tombant (Chute par ricochet)
              </p>
              <p className="mt-0.5">
                {a.alerte_tombant || `Cet amendement tombe automatiquement si l'amendement de suppression ${a.parent_suppression_numero || ''} est adopté en séance.`}
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
            <p className="text-ink-900 dark:text-plume font-medium">{a.date_depot || '—'}</p>
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

        {/* ── Résultat IA (avec Chain of Thought) ── */}
        <section className="rounded-md bg-slate-50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-800 p-3.5">
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Résultat du classement
          </h4>
          {res ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-slate-900 dark:text-plume">Rang {res.rang}</span>
                <GroupeBadge type={res.groupe?.type} />

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
            {concurrentsTries.length > 0 && (
              <div className="flex items-center gap-1.5">
                <label className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                  ⚖️ Comparer avec :
                </label>
                <select
                  value={compareId || ''}
                  onChange={(e) => setCompareId(e.target.value || null)}
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

          {diffMots && targetAmd ? (
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
