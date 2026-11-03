import { useState, useEffect } from 'react'
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
import { stripHtmlTags } from '../utils/sanitize'

export function formatCleanArticleHeading(article) {
  if (!article) return 'Article —'
  const str = String(article).trim()
  // Dédupliquer les répétitions éventuelles ("Article Article PREMIER" -> "Article PREMIER")
  const clean = str.replace(/^(article\s+|art\.\s*)+/gi, 'Article ')
  // Si la chaîne commence déjà par Article, Art., Avant, Après, Titre ou Intitulé, ne pas préfixer à nouveau
  if (/^(article|art\.|avant\b|apr[eè]s\b|titre\b|intitul[eé]\b)/i.test(clean)) {
    return clean
  }
  return `Article ${clean}`
}

export const formatArticleTitle = formatCleanArticleHeading

export default function AmendmentDetail({
  amendment,
  onClose,
  isLoading,
  aiSettings,
  onAnalyzeSingle,
  analyzingUids,
}) {
  const [euCompliance, setEuCompliance] = useState(amendment?.eu_compliance || null)

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
  const statut = res?.statut || a.statut || ''
  const isDiscussionCommune = statut === 'Discussion commune' || statut === 'Incompatible'
  const isConflitDecrypte = Boolean(a.explication_ia || res?.explication_ia)
  const texteExplicationIA = a.explication_ia || res?.explication_ia || (isConflitDecrypte ? (a.justification || res?.justification) : null)
  const isAnalyzingThis = Boolean(
    analyzingUids && (
      (typeof analyzingUids.has === 'function' && (analyzingUids.has(a.id) || analyzingUids.has(a.uid))) ||
      (Array.isArray(analyzingUids) && (analyzingUids.includes(a.id) || analyzingUids.includes(a.uid)))
    )
  )

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
              <span
                className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-700 px-2.5 py-0.5 text-xs font-semibold font-sans"
                title={a.gage_detecte ? `Gage constitutionnel détecté : ${a.gage_detecte}` : "Amendement gagé au titre de l'Article 40 de la Constitution"}
              >
                💰 Gagé (Art. 40){a.gage_detecte ? ` · ${a.gage_detecte}` : ''}
              </span>
            )}
            {a.alerte_recevabilite_art40 && (
              <div className="group relative inline-flex font-sans">
                <span
                  className="inline-flex items-center gap-1 rounded-full bg-rose-100 text-rose-800 dark:bg-rose-950/70 dark:text-rose-200 border border-rose-300 dark:border-rose-700 px-2.5 py-0.5 text-xs font-semibold cursor-help"
                  title={a.motif_art40 || "Risque d'irrecevabilité financière au titre de l'Article 40 de la Constitution : perte de recettes ou charge publique détectée sans gage valide."}
                >
                  ⚠️ Risque Irrecevabilité Art. 40 (Absence de gage financier)
                </span>
                <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 top-full left-0 mt-2 w-80 whitespace-normal bg-slate-900 text-white text-xs rounded-lg shadow-xl p-3 leading-relaxed">
                  <p className="font-semibold text-rose-300 mb-1">⚖️ Audit Constitutionnel — Article 40</p>
                  <p>{a.motif_art40 || "Perte de recettes publiques ou création de charge détectée sans formule de gage financier valide (Tabac, Alcool, DGF ou Sécurité sociale)."}</p>
                </div>
              </div>
            )}
            {a.alerte_non_normatif && (
              <div className="group relative inline-flex font-sans">
                <span
                  className="inline-flex items-center gap-1 rounded-full bg-sky-100 text-sky-800 dark:bg-sky-950/70 dark:text-sky-200 border border-sky-300 dark:border-sky-700 px-2.5 py-0.5 text-xs font-medium cursor-help"
                  title={a.motif_non_normatif || "Dispositif à faible portée normative (risque de censure pour défaut de normativité, Art. 6 DDHC)."}
                >
                  ℹ️ Portée normative faible
                </span>
                <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 top-full left-0 mt-2 w-80 whitespace-normal bg-slate-900 text-white text-xs rounded-lg shadow-xl p-3 leading-relaxed">
                  <p className="font-semibold text-sky-300 mb-1">ℹ️ Légistique — Portée normative (Art. 6 DDHC)</p>
                  <p>{a.motif_non_normatif || "Dispositif à faible portée normative (risque de censure pour défaut de normativité, Art. 6 DDHC)."}</p>
                </div>
              </div>
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

        {/* ── Contexte législatif (titre tronqué + tooltip) ── */}
        {(a.title || a.dossier_titre) && (
          <LegislativeContext
            title={a.title || a.dossier_titre}
            dossierRef={a.dossier_ref}
          />
        )}

        <div className="flex flex-wrap items-center gap-4 py-2 text-sm text-slate-300">
          {/* ── Auteur enrichi ── */}
          <div>
            <span className="text-xs text-slate-400 block mb-0.5">Auteur(s)</span>
            {a.auteur_nom && a.auteur_nom !== "Inconnu" ? (
              <AuthorBadge data={{
                auteur_nom: a.auteur_nom,
                auteur_prenom: a.auteur_prenom,
                auteur_trigramme: a.auteur_trigramme
              }} />
            ) : (
              <div className="inline-flex items-center px-2.5 py-1 text-xs font-medium bg-gray-100 text-slate-900 dark:bg-[#1A1B22] dark:text-white border border-gray-300 dark:border-gray-700 rounded-md">
                <span>
                  {a.rapporteur ? 'Rapporteur — ' : ''}
                  {(a.auteurs || []).join(', ') || '—'}
                </span>
              </div>
            )}
          </div>

          {/* ── Groupe politique ── */}
          <div>
            <span className="text-xs text-slate-400 block mb-0.5">Groupe</span>
            <div className="flex items-center">
              <PoliticalGroupTag
                group={a.groupe_politique || (typeof a.groupe === 'string' ? a.groupe : '')}
                groupRef={a.groupRef ?? a.groupe_politique_ref}
                auteurs={a.auteurs}
                className="px-2.5 py-1 text-xs"
              />
            </div>
          </div>

          {/* ── Date de dépôt ── */}
          <div>
            <span className="text-xs text-slate-400 block mb-0.5">Date de dépôt</span>
            <span className="inline-flex items-center px-1 py-1 text-xs font-medium text-slate-900 dark:text-slate-100">
              {a.date_depot || '—'}
            </span>
          </div>

          {/* ── Point d'impact ── */}
          <div>
            <span className="text-xs text-slate-400 block mb-0.5">Point d'impact</span>
            <div className="flex items-center">
              <ImpactBadge type={a.point_impact?.type} className="px-2.5 py-1 text-xs" />
            </div>
          </div>
        </div>

        {/* ── Décryptage IA (pour discussion commune) ou Résumé IA classique ── */}
        {isDiscussionCommune ? (
          <section className="rounded-lg bg-slate-50 dark:bg-purple-950/20 border border-purple-300 dark:border-purple-800/50 p-4">
            <h4 className="font-display text-sm uppercase tracking-wide text-purple-900 dark:text-purple-300 font-semibold flex items-center gap-1.5">
              <span>🤖</span> Décryptage du conflit (IA locale)
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Traité par votre IA locale : le texte ne quitte pas votre poste.
            </p>

            {isAnalyzingThis ? (
              <div className="flex items-center gap-2 mt-3 text-xs text-amber-400">
                <span className="inline-block animate-spin">⏳</span>
                <span>Analyse sémantique du conflit en cours par l'IA...</span>
              </div>
            ) : isConflitDecrypte && texteExplicationIA ? (
              <div className="mt-3 bg-purple-950/30 border border-purple-800/40 rounded-lg p-3 text-sm text-purple-200 leading-relaxed whitespace-pre-line">
                {texteExplicationIA}
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onAnalyzeSingle && onAnalyzeSingle(a.uid || a.id)}
                className="mt-3 text-xs font-medium px-3 py-1.5 rounded-md bg-purple-600 hover:bg-purple-500 text-white transition-colors cursor-pointer"
              >
                ⚡ Décrypter ce conflit par IA
              </button>
            )}
          </section>
        ) : (
          <ResumeIA key={a.id ?? a.uid} amendment={a} aiSettings={aiSettings} />
        )}

        {/* ── Conformité européenne (surtransposition) — panneau dépliable ── */}
        <EUCompliancePanel result={euCompliance || a.eu_compliance} />

        {/* ── Résultat IA (avec Chain of Thought) ── */}
        <section className="rounded-md bg-slate-50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-800 p-3.5">
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Résultat du classement
          </h4>
          {res || a.statut ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 flex-wrap">
                {(res?.rang != null || a.rang != null) && (
                  <span className="font-semibold text-slate-900 dark:text-plume">Rang {res?.rang ?? a.rang}</span>
                )}
                <GroupeBadge statut={res?.statut || a.statut} groupe={res?.groupe || a.groupe} type={res?.groupe?.type || a.groupe?.type} />

                {/* ── 💡 Tooltip Chain of Thought ── */}
                {res?.analyse_intention && (
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
              {isDiscussionCommune ? (
                <p className="text-ink-700 dark:text-ink-300 text-xs">
                  {a.justification_mecanique ||
                    ((a.cible_numero || res?.cible_numero)
                      ? `Discussion commune sur cette division avec l'amendement n° ${a.cible_numero || res?.cible_numero}.`
                      : "Amendement en discussion commune.")}
                </p>
              ) : (
                <p className="text-ink-700 dark:text-ink-300">{res?.justification || a.justification}</p>
              )}
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
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Dispositif
          </h4>
          <ScrollableText text={stripHtmlTags(a.dispositif)} />
        </section>

        <section className="bg-gray-50 dark:bg-surface border border-ink-200 dark:border-ink-700 rounded-md p-4">
          <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume mb-2">
            Exposé sommaire
          </h4>
          <ScrollableText text={stripHtmlTags(a.expose_sommaire || a.exposeSommaire)} />
        </section>
      </div>
    </div>
  )
}
