import { useState, useMemo } from 'react'
import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'
import CommissionKeywords from './amendment/CommissionKeywords'
import PoliticalGroupTag, { resolvePoliticalGroup } from './amendment/PoliticalGroupTag'
import AmendmentSearchBar from './amendment/AmendmentSearchBar'
import { downloadRtf } from '../utils/exportRtf'
import { stripHtmlTags } from '../utils/sanitize'

const PAGE_SIZE = 50

// Extrait du dispositif : 250 caractères au plus (coupés sur un mot), avec
// « Voir plus » pour déplier le texte complet dans la cellule.
const EXTRAIT_MAX = 250

function cleanText(text) {
  return stripHtmlTags(String(text ?? '')).replace(/\s+/g, ' ').trim()
}

function ExtraitDispositif({ text }) {
  const [deplie, setDeplie] = useState(false)
  const clean = cleanText(text)
  if (!clean) return '—'
  if (clean.length <= EXTRAIT_MAX) return clean

  let court = clean.slice(0, EXTRAIT_MAX)
  const dernierEspace = court.lastIndexOf(' ')
  if (dernierEspace > EXTRAIT_MAX * 0.8) court = court.slice(0, dernierEspace)

  return (
    <>
      {deplie ? clean : `${court.trimEnd()}…`}{' '}
      <button
        type="button"
        aria-expanded={deplie}
        // La ligne est cliquable (sélection) et déplaçable : on isole le clic.
        onClick={(e) => { e.stopPropagation(); setDeplie((v) => !v) }}
        className="whitespace-nowrap text-xs font-medium text-[#D91227] hover:underline"
      >
        {deplie ? 'Voir moins' : 'Voir plus'}
      </button>
    </>
  )
}


// Recherche insensible à la casse et aux accents (« Élisa » = « elisa »).
function normaliser(texte) {
  return String(texte ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
}

function auteursEnListe(a) {
  if (Array.isArray(a.auteurs)) return a.auteurs.filter(Boolean)
  return a.auteurs ? [String(a.auteurs)] : []
}

// Doublon = même texte, même auteur, même commission (moteur déterministe).
function estDoublon(a) {
  return a.statut_mecanique === 'DOUBLON_MECANIQUE' || a.resultat_ia?.statut === 'Doublon'
}

export default function AmendmentTable({ amendments, selectedId, onSelect, onReorder, onDelete, onDeleteDoublons, isClassifying, analyzingUids, onExportJson, onAnalyzeSingle }) {
  const [currentPage, setCurrentPage] = useState(0)
  const [filtre, setFiltre] = useState({ motCle: '', auteur: '' })
  const [masquerEcartes, setMasquerEcartes] = useState(false)

  // Options de la recherche : mots-clés (avec effectif) et auteurs distincts.
  const optionsRecherche = useMemo(() => {
    const parMot = new Map()
    const auteurs = new Set()
    for (const a of amendments) {
      for (const mot of new Set(a.commission_mots_cles || [])) parMot.set(mot, (parMot.get(mot) || 0) + 1)
      for (const nom of auteursEnListe(a)) auteurs.add(nom)
    }
    return {
      motsCles: [...parMot].map(([mot, nb]) => ({ mot, nb })).sort((x, y) => x.mot.localeCompare(y.mot, 'fr')),
      auteurs: [...auteurs].sort((x, y) => x.localeCompare(y, 'fr')),
    }
  }, [amendments])

  // On garde l'index d'origine de chaque amendement : le glisser-déposer
  // (onReorder) travaille sur la liste complète, pas sur la liste filtrée.
  const filtres = useMemo(() => {
    const auteurCherche = normaliser(filtre.auteur)
    return amendments
      .map((a, idx) => ({ a, idx }))
      .filter(({ a }) => {
        if (masquerEcartes) {
          const statutLower = String(a.statut || a.resultat_ia?.statut || a.statut_mecanique || '').toLowerCase()
          const sortLower = String(a.sort || a.raw_dict?.sort || '').toLowerCase()
          const justifLower = String(a.justification_mecanique || '').toLowerCase()
          const isEcarte = (
            statutLower.includes('irrecevable') ||
            statutLower.includes('retiré') ||
            statutLower.includes('retire') ||
            statutLower.includes('doublon') ||
            justifLower.includes('irrecevable') ||
            justifLower.includes('doublon') ||
            justifLower.includes('retiré') ||
            justifLower.includes('retire') ||
            sortLower.includes('retiré') ||
            sortLower.includes('retire') ||
            a.statut_mecanique === 'DOUBLON_MECANIQUE'
          )
          if (isEcarte) return false
        }
        if (filtre.motCle && !(a.commission_mots_cles || []).includes(filtre.motCle)) return false
        if (auteurCherche && !normaliser(auteursEnListe(a).join(', ')).includes(auteurCherche)) return false
        return true
      })
  }, [amendments, filtre, masquerEcartes])

  function handleRechercher(nouveauFiltre) {
    setFiltre(nouveauFiltre)
    setCurrentPage(0)
  }

  // Compteurs calculés avec un seul reduce (déplacé AVANT le return conditionnel pour éviter l'erreur #310)
  const counts = useMemo(() => {
    return amendments.reduce((acc, a) => {
      if (!a.resultat_ia) return acc
      acc.total++
      const s = a.resultat_ia.statut
      if (s === 'Incompatible' || s === 'Discussion commune') acc.dc++
      else if (s === 'Identique' || s === 'Identiques') acc.id++
      else if (s === 'Doublon') acc.doublon++
      else if (s === 'Nouveau' || s === 'Isolé') acc.isole++
      return acc
    }, { total: 0, dc: 0, id: 0, doublon: 0, isole: 0 })
  }, [amendments])

  if (amendments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-10 text-center">
        <p className="text-slate-500 dark:text-slate-300 text-sm">
          Aucun amendement chargé pour l'instant. Importe un fichier JSON ci-dessus pour commencer.
        </p>
      </div>
    )
  }

  const totalPages = Math.max(1, Math.ceil(filtres.length / PAGE_SIZE))
  const safePage = Math.min(currentPage, totalPages - 1)
  const startIdx = safePage * PAGE_SIZE
  const pageItems = filtres.slice(startIdx, startIdx + PAGE_SIZE)

  const idsDoublons = amendments.filter(estDoublon).map((a) => a.id)

  // Les index transmis sont ceux de la liste complète (cf. `filtres`).
  function handleDragStart(e, index) {
    e.dataTransfer.setData('text/plain', String(index))
    e.dataTransfer.effectAllowed = 'move'
  }

  function handleDrop(e, targetIndex) {
    e.preventDefault()
    const fromIndex = Number(e.dataTransfer.getData('text/plain'))
    if (Number.isNaN(fromIndex) || fromIndex === targetIndex) return
    onReorder(fromIndex, targetIndex)
  }

  function handleExportRtf() {
    const fileName = window.prompt("Comment souhaitez-vous nommer ce fichier d'export ?", "amendements_export")
    if (fileName === null) return
    const finalName = fileName.trim() || "amendements_export"
    downloadRtf(amendments, `${finalName}.rtf`)
  }

  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 overflow-hidden">
      <div className="bg-slate-100/80 dark:bg-slate-900/50 border-b border-ink-200 dark:border-ink-700 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        {counts.total > 0 ? (
          <p className="text-sm font-medium text-slate-900 dark:text-plume">
            {counts.total} amendements classés ({counts.dc} en discussion commune, {counts.id} identiques, {counts.doublon} doublon{counts.doublon > 1 ? 's' : ''}, {counts.isole} isolés).
          </p>
        ) : (
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {amendments.length} amendements chargés
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2">
          {idsDoublons.length > 0 && onDeleteDoublons && (
            <button
              type="button"
              onClick={() => onDeleteDoublons(idsDoublons)}
              title="Retire les copies redéposées par le même auteur devant la même commission ; l'amendement d'origine est conservé."
              className="shrink-0 rounded-md border border-rose-300 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-800 hover:bg-rose-100 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300 dark:hover:bg-rose-900/50 transition-colors whitespace-nowrap"
            >
              Supprimer les doublons ({idsDoublons.length})
            </button>
          )}
          <button
            type="button"
            onClick={() => { setMasquerEcartes(v => !v); setCurrentPage(0); }}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md border transition-colors ${
              masquerEcartes
                ? 'bg-amber-100 text-amber-900 border-amber-300 dark:bg-amber-950/60 dark:text-amber-200 dark:border-amber-700 shadow-sm'
                : 'bg-white text-slate-700 border-slate-300 dark:bg-[#12131A] dark:text-slate-300 dark:border-slate-600 hover:bg-slate-50'
            }`}
            title="Masquer les amendements écartés (irrecevables, retirés ou doublons) pour afficher uniquement la séance"
          >
            <span>{masquerEcartes ? '⚖️ Séance seule (écartés masqués)' : '👁️ Masquer les amendements écartés'}</span>
          </button>
        </div>
      </div>
      <AmendmentSearchBar
        motsCles={optionsRecherche.motsCles}
        auteurs={optionsRecherche.auteurs}
        filtre={filtre}
        onRechercher={handleRechercher}
        nbResultats={filtres.length}
        nbTotal={amendments.length}
      />
      <div className="overflow-x-auto scroll-thin">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100 dark:bg-[#1A1B22] border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className="px-2 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[80px] min-w-[80px] max-w-[80px] sticky z-20 bg-gray-100 dark:bg-[#1A1B22] left-0">Art.</th>
              <th className="px-2 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[75px] min-w-[75px] max-w-[75px] sticky z-20 bg-gray-100 dark:bg-[#1A1B22] left-[80px]">N°</th>
              <th className="px-3 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[180px] min-w-[180px] max-w-[180px] sticky z-20 bg-gray-100 dark:bg-[#1A1B22] left-[155px] shadow-[2px_0_4px_-2px_rgba(0,0,0,0.15)]">Auteur(s)</th>
              <th className="px-3 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[90px] min-w-[90px]">Groupe</th>
              <th className="px-3 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[140px] min-w-[140px]">Point d'impact</th>
              <th className="px-3 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[200px] min-w-[200px] max-w-[200px]">Commission / Thèmes</th>
              <th className="px-3 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-auto min-w-[200px]">Extrait du dispositif</th>
              <th className="px-3 py-3 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[220px] min-w-[200px]">Statut</th>
              <th className="px-3 py-3 text-right text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-[80px] min-w-[80px]">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-[#0B0C10] divide-y divide-gray-200 dark:divide-gray-800">
            {pageItems.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
                  Aucun amendement ne correspond à cette recherche.
                </td>
              </tr>
            )}
            {pageItems.map(({ a, idx }) => {
              const statut = a.resultat_ia?.statut || a.statut
              const groupeStatut = a.resultat_ia?.groupe
              const groupePolitique = resolvePoliticalGroup(
                a.groupe_politique || (typeof a.groupe === 'string' ? a.groupe : ''),
                a.groupe_politique_ref || a.groupRef,
                a.auteurs
              )
              const isSelected = a.id === selectedId
              
              const isPending = isClassifying && !a.resultat_ia && !a.statut;
              const statutToDisplay = isPending ? "En cours..." : statut;
              
              let auteursText = a.auteurs
              if (Array.isArray(auteursText)) {
                auteursText = auteursText.join(', ')
              }
              auteursText = auteursText || '—'

              const isAnalyzingSingle = Boolean(
                analyzingUids && (
                  (typeof analyzingUids.has === 'function' && (analyzingUids.has(a.id) || analyzingUids.has(a.uid))) ||
                  (Array.isArray(analyzingUids) && (analyzingUids.includes(a.id) || analyzingUids.includes(a.uid)))
                )
              )
              const isConflitDecrypte = Boolean(a.explication_ia || a.resultat_ia?.explication_ia)

              return (
                <tr 
                  key={a.id ?? `fallback-${idx}`}
                  draggable
                  onDragStart={(e) => handleDragStart(e, idx)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDrop(e, idx)}
                  onClick={() => {
                    if (onSelect) onSelect(a.id)
                    setTimeout(() => {
                      const el = document.getElementById('ia-analysis-block') || document.getElementById('amendment-detail-section')
                      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                    }, 50)
                  }}
                  className={`cursor-pointer transition-colors ${isSelected ? 'bg-slate-100 dark:bg-[#1A1B22] border-l-4 border-l-[#D91227]' : 'dark:bg-[#0B0C10] hover:bg-slate-50 dark:hover:bg-gray-900/50'}`}
                >
                  <td className={`px-2 py-3.5 w-[80px] min-w-[80px] max-w-[80px] text-sm text-slate-800 dark:text-slate-200 truncate sticky left-0 z-10 align-middle ${isSelected ? 'bg-slate-100 dark:bg-[#1A1B22]' : 'bg-white dark:bg-[#0B0C10]'}`} title={a.article}>{String(a.article || "—").replace(/^Article\s+/i, "")}</td>
                  <td className={`px-2 py-3.5 w-[75px] min-w-[75px] max-w-[75px] text-xs text-slate-800 dark:text-slate-200 truncate sticky left-[80px] z-10 align-middle ${isSelected ? 'bg-slate-100 dark:bg-[#1A1B22]' : 'bg-white dark:bg-[#0B0C10]'}`} title={a.numero}>{a.numero}</td>
                  <td className={`px-3 py-3.5 text-sm text-slate-800 dark:text-slate-200 w-[180px] min-w-[180px] max-w-[180px] align-middle sticky left-[155px] z-10 shadow-[2px_0_4px_-2px_rgba(0,0,0,0.15)] ${isSelected ? 'bg-slate-100 dark:bg-[#1A1B22]' : 'bg-white dark:bg-[#0B0C10]'}`}>
                    <span className="break-words leading-snug" title={auteursText}>{auteursText}</span>
                  </td>
                  <td className="px-3 py-3.5 text-sm text-slate-800 dark:text-slate-200 w-[90px] min-w-[90px] align-middle">
                    {groupePolitique ? (
                      <div className="flex items-center">
                        <PoliticalGroupTag
                          group={groupePolitique}
                          groupRef={a.groupe_politique_ref || a.groupRef}
                        />
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-3 py-3.5 text-sm text-slate-800 dark:text-slate-200 w-[140px] min-w-[140px] align-middle">
                    <ImpactBadge
                      type={
                        typeof a.point_impact === 'string'
                          ? a.point_impact
                          : (a.point_impact?.type || '')
                      }
                    />
                  </td>
                  <td className="px-3 py-3.5 text-sm w-[200px] min-w-[200px] max-w-[200px] align-middle">
                    <CommissionKeywords
                      commission={a.commission}
                      commissionLibelle={a.commission_libelle}
                      motsCles={a.commission_mots_cles}
                      horsChamp={a.commission_hors_champ}
                    />
                  </td>
                  <td className="px-3 py-3.5 text-sm text-slate-800 dark:text-slate-200 w-auto min-w-[200px] align-middle whitespace-normal break-words leading-snug"><ExtraitDispositif text={a.dispositif} /></td>
                  <td className="px-3 py-3.5 text-sm w-[220px] min-w-[200px] align-middle">
                    <div className="flex flex-col items-start gap-1.5 py-1">
                      <div className="inline-flex items-center gap-1.5">
                        <GroupeBadge statut={statutToDisplay} groupe={groupeStatut} isPending={isPending} />
                        {/* 💡 Tooltip Chain of Thought (inline) */}
                        {a.resultat_ia?.analyse_intention && (
                          <div className="group relative inline-flex items-center">
                            <span className="cursor-help text-xs leading-none" title={a.resultat_ia.analyse_intention}>💡</span>
                            <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full right-0 mb-2 w-64 whitespace-normal bg-slate-900 text-white text-xs rounded-lg shadow-xl p-2.5 leading-relaxed">
                              <p className="font-semibold text-amber-300 mb-1">
                                {(statutToDisplay === 'Identique' || a.resultat_ia.analyse_intention?.startsWith('Détecté mécaniquement')) ? '⚙️ Tri Mécanique' : '🧠 Raisonnement IA'}
                              </p>
                              <p>{a.resultat_ia.analyse_intention}</p>
                              {a.resultat_ia.niveau_confiance != null && (
                                <p className="text-slate-400 mt-1">Confiance : {(a.resultat_ia.niveau_confiance * 100).toFixed(0)}%</p>
                              )}
                              <div className="absolute top-full right-4 -mt-[1px] border-4 border-transparent border-t-slate-900" />
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Déclencheur contextuel pour expliciter la concurrence légistique */}
                      {statutToDisplay === 'Discussion commune' && (
                        <div className="w-full">
                          {isAnalyzingSingle ? (
                            <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium inline-flex items-center gap-1.5 border border-amber-500/40 bg-amber-950/40 text-amber-300 mt-1 animate-pulse">
                              ⏳ Analyse en cours...
                            </span>
                          ) : isConflitDecrypte ? (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                if (onSelect) onSelect(a.id)
                                setTimeout(() => {
                                  const el = document.getElementById('ia-analysis-block') || document.getElementById('amendment-detail-section')
                                  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                                }, 50)
                              }}
                              className="text-[11px] px-2.5 py-1 rounded-full font-semibold inline-flex items-center gap-1.5 border border-purple-500/50 bg-purple-950/50 text-purple-200 hover:bg-purple-800 hover:border-purple-300 hover:text-white transition-all duration-150 cursor-pointer mt-1 shadow-sm hover:shadow-purple-500/30 hover:scale-[1.03] active:scale-[0.97]"
                              title="Voir l'explication du conflit dans la fiche"
                            >
                              ✓ Conflit décrypté (IA)
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                if (onSelect) onSelect(a.id)
                                if (onAnalyzeSingle) onAnalyzeSingle(a.uid || a.id)
                                setTimeout(() => {
                                  const el = document.getElementById('ia-analysis-block') || document.getElementById('amendment-detail-section')
                                  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                                }, 50)
                              }}
                              className="text-[11px] px-2.5 py-1 rounded-full font-semibold inline-flex items-center gap-1.5 border border-blue-500/50 bg-blue-950/40 text-blue-300 hover:bg-blue-600 hover:border-blue-300 hover:text-white transition-all duration-150 cursor-pointer mt-1 shadow-sm hover:shadow-blue-500/30 hover:scale-[1.03] active:scale-[0.97]"
                              title="Expliquer la concurrence de fond avec l'IA"
                            >
                              🔍 Décrypter le conflit (IA)
                            </button>
                          )}
                        </div>
                      )}

                      {a.alerte_recevabilite_art40 && (
                        <div className="group relative inline-flex">
                          <span
                            className="text-[11px] px-2.5 py-0.5 rounded-full font-medium inline-flex items-center gap-1.5 border border-red-500/40 bg-red-950/40 text-red-300 whitespace-nowrap cursor-help"
                            title={a.motif_art40 || "Risque d'irrecevabilité financière au titre de l'Article 40 de la Constitution : perte de recettes ou charge publique détectée sans gage valide."}
                          >
                            ⚠️ Art. 40 (sans gage)
                          </span>
                          <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full right-0 mb-2 w-72 whitespace-normal bg-slate-900 text-white text-xs rounded-lg shadow-xl p-2.5 leading-relaxed">
                            <p className="font-semibold text-rose-300 mb-1">⚖️ Audit Constitutionnel — Article 40</p>
                            <p>{a.motif_art40 || "Perte de recettes publiques ou création de charge détectée sans formule de gage financier valide (Tabac, Alcool, DGF ou Sécurité sociale)."}</p>
                            <div className="absolute top-full right-4 -mt-[1px] border-4 border-transparent border-t-slate-900" />
                          </div>
                        </div>
                      )}
                      {a.alerte_non_normatif && (
                        <div className="group relative inline-flex">
                          <span
                            className="text-[11px] px-2.5 py-0.5 rounded-full font-medium inline-flex items-center gap-1.5 border border-sky-300 bg-sky-100 text-sky-800 dark:border-sky-500/40 dark:bg-sky-950/40 dark:text-sky-300 whitespace-nowrap cursor-help"
                            title={a.motif_non_normatif || "Dispositif à faible portée normative (risque de censure pour défaut de normativité, Art. 6 DDHC)."}
                          >
                            ℹ️ Portée faible
                          </span>
                          <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full right-0 mb-2 w-72 whitespace-normal bg-slate-900 text-white text-xs rounded-lg shadow-xl p-2.5 leading-relaxed">
                            <p className="font-semibold text-sky-300 mb-1">ℹ️ Légistique — Portée normative (Art. 6 DDHC)</p>
                            <p>{a.motif_non_normatif || "Dispositif à faible portée normative (risque de censure pour défaut de normativité, Art. 6 DDHC)."}</p>
                            <div className="absolute top-full right-4 -mt-[1px] border-4 border-transparent border-t-slate-900" />
                          </div>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3.5 w-[80px] min-w-[80px] text-right text-sm font-medium align-middle">
                    <button onClick={(e) => { e.stopPropagation(); if (onDelete) onDelete(a.id); }} className="text-gray-400 hover:text-red-600 transition-colors">Retirer</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── PAGINATION ── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-ink-200 dark:border-ink-700 bg-slate-50 dark:bg-[#12131A] px-4 py-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Page {safePage + 1} / {totalPages} — Amendements {startIdx + 1}–{Math.min(startIdx + PAGE_SIZE, filtres.length)} sur {filtres.length}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={safePage === 0}
              onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
              className="rounded-md border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              ← Précédent
            </button>
            <button
              type="button"
              disabled={safePage >= totalPages - 1}
              onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
              className="rounded-md border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Suivant →
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-t border-ink-100 dark:border-ink-700 bg-ink-50/50 dark:bg-obsidienne/50 px-4 py-3">
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
            {amendments.length} amendement{amendments.length > 1 ? 's' : ''} chargé{amendments.length > 1 ? 's' : ''}
          </span>
          <span className="text-xs text-ink-500 dark:text-ink-300">
            Export au format du préjaune de l'Assemblée (RTF) ou en JSON (sauvegarde complète).
          </span>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
          {onExportJson && (
            <button
              type="button"
              disabled={amendments.length === 0}
              onClick={onExportJson}
              className="w-full sm:w-auto rounded-md bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 px-3 py-1.5 text-xs sm:text-sm font-medium hover:bg-slate-700 dark:hover:bg-slate-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap text-center"
            >
              Exporter en JSON
            </button>
          )}
          <button
            type="button"
            disabled={amendments.length === 0}
            onClick={handleExportRtf}
            className="w-full sm:w-auto rounded-md border border-slate-700 dark:border-slate-300 px-3 py-1.5 text-xs sm:text-sm font-medium text-slate-900 dark:text-plume hover:bg-slate-100 dark:hover:bg-slate-800 disabled:border-ink-300 disabled:text-ink-400 disabled:cursor-not-allowed transition-colors whitespace-nowrap text-center"
          >
            Exporter en préjaune (.rtf)
          </button>
        </div>
      </div>
    </div>
  )
}
