import { useState, useMemo } from 'react'
import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'
import CommissionKeywords from './amendment/CommissionKeywords'
import PoliticalGroupTag from './amendment/PoliticalGroupTag'
import AmendmentSearchBar from './amendment/AmendmentSearchBar'
import BilanClassement from './amendment/BilanClassement'
import { calculerBilan, categorieAmendement, estDoublon, estEcarte, estSeancePleniere } from '../utils/bilan'
import { TRIS, trierEntrees } from '../utils/tri'
import { downloadRtf } from '../utils/exportRtf'
import { stripHtmlForDisplay } from '../utils/sanitize'

const PAGE_SIZE = 25

// Extrait du dispositif : 250 caractères au plus (coupés sur un mot), avec
// « Voir plus » pour déplier le texte complet dans la cellule.
const EXTRAIT_MAX = 250

function cleanText(text) {
  return stripHtmlForDisplay(String(text ?? '')).replace(/\s+/g, ' ').trim()
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

<<<<<<< HEAD
export default function AmendmentTable({ amendments, source, selectedId, onSelect, onReorder, onDelete, onDeleteDoublons, isClassifying, onExportJson }) {
=======
function formaterArticle(art) {
  if (!art) return '—'
  const texte = String(art).trim()
  if (/^article\s+premier$/i.test(texte) || /^premier$/i.test(texte)) return '1er'
  return texte.replace(/^article\s+/i, '')
}

export default function AmendmentTable({ amendments, selectedId, onSelect, onReorder, onDelete, onDeleteDoublons, isClassifying, onExportJson }) {
>>>>>>> origin/main
  const [currentPage, setCurrentPage] = useState(0)
  const [filtre, setFiltre] = useState({ motCle: '', auteur: '' })
  const [masquerEcartes, setMasquerEcartes] = useState(false)
  // Catégorie choisie dans le bandeau de bilan ('' = toutes).
  const [categorieFiltre, setCategorieFiltre] = useState('')
  const [tri, setTri] = useState('recent')

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
    const liste = amendments
      .map((a, idx) => ({ a, idx }))
      .filter(({ a }) => {
        if (masquerEcartes && (estDoublon(a) || estEcarte(a))) return false
        if (categorieFiltre === 'seance') {
          if (!estSeancePleniere(a)) return false
        } else if (categorieFiltre && categorieAmendement(a) !== categorieFiltre) return false
        if (filtre.motCle && !(a.commission_mots_cles || []).includes(filtre.motCle)) return false
        if (auteurCherche && !normaliser(auteursEnListe(a).join(', ')).includes(auteurCherche)) return false
        return true
      })
    return trierEntrees(liste, tri)
  }, [amendments, filtre, masquerEcartes, categorieFiltre, tri])

  function handleRechercher(nouveauFiltre) {
    setFiltre(nouveauFiltre)
    setCurrentPage(0)
  }

  // Les écartés et doublons seraient invisibles avec « Masquer les écartés » :
  // filtrer sur ces catégories réaffiche donc les écartés.
  function handleFiltrerCategorie(categorie) {
    setCategorieFiltre(categorie)
    if (categorie === 'ecarte' || categorie === 'doublon') setMasquerEcartes(false)
    setCurrentPage(0)
  }

  // Calculé AVANT le return conditionnel (règle des hooks, erreur React #310).
  const bilan = useMemo(() => calculerBilan(amendments), [amendments])

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
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-900 dark:text-plume">
            {bilan.classes > 0 ? `${bilan.classes} amendements classés` : `${amendments.length} amendements chargés`}
          </p>
          {/* Origine de la liasse (dossier législatif et étape, fichier, exemple) */}
          {source && (
            <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400 break-words" title={source}>
              📁 {source}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
            Trier :
            <select
              value={tri}
              onChange={(e) => { setTri(e.target.value); setCurrentPage(0) }}
              className="rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2 py-1 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40"
            >
              {TRIS.map((t) => <option key={t.cle} value={t.cle}>{t.libelle}</option>)}
            </select>
          </label>
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
            onClick={() => {
              if (!masquerEcartes && (categorieFiltre === 'ecarte' || categorieFiltre === 'doublon')) setCategorieFiltre('')
              setMasquerEcartes(v => !v)
              setCurrentPage(0)
            }}
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
      <BilanClassement bilan={bilan} categorieActive={categorieFiltre} onFiltrer={handleFiltrerCategorie} />
      <AmendmentSearchBar
        motsCles={optionsRecherche.motsCles}
        auteurs={optionsRecherche.auteurs}
        filtre={filtre}
        onRechercher={handleRechercher}
        nbResultats={filtres.length}
        nbTotal={amendments.length}
      />
      <div data-demo="tableau" className="overflow-x-auto scroll-thin">
        <table className="w-full divide-y divide-gray-200 dark:divide-gray-800 text-left">
          <thead className="bg-gray-100 dark:bg-[#1A1B22] border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th data-demo="col-art-num" className="px-2 py-3.5 text-center text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-16">Art.</th>
              <th data-demo="col-art-num" className="px-2 py-3.5 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-20">N°</th>
              <th data-demo="col-auteur-groupe" className="px-3 py-3.5 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-44 max-w-[180px]">Auteur(s)</th>
              <th data-demo="col-auteur-groupe" className="px-3 py-3.5 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-28">Groupe</th>
              <th data-demo="col-impact" className="px-3 py-3.5 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-36">Point d'impact</th>
              <th data-demo="col-commission" className="px-3 py-3.5 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-64 max-w-[260px]">Commission / Thèmes</th>
              <th data-demo="col-extrait" className="px-4 py-3.5 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider min-w-[240px]">Extrait du dispositif</th>
              <th data-demo="col-statut" className="px-3 py-3.5 text-left text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-36 whitespace-nowrap">Statut</th>
              <th data-demo="col-actions" className="px-3 py-3.5 text-center text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider w-24 whitespace-nowrap">Actions</th>
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
              const statut = a.statut || a.resultat_ia?.statut
              const groupe = a.groupe_politique || a.groupe || a.resultat_ia?.groupe_politique || a.resultat_ia?.groupe
              const isSelected = a.id === selectedId
              
              const isPending = isClassifying && !a.resultat_ia && !a.statut;
              const statutToDisplay = isPending ? "En cours..." : statut;
              
              let auteursText = a.auteurs
              if (Array.isArray(auteursText)) {
                auteursText = auteursText.join(', ')
              }
              auteursText = auteursText || '—'

              const estRapporteur = a.est_rapporteur || a.rapporteur || a.role === 'Rapporteur' || a.typeAuteur === 'Rapporteur'
              const estGouvernement = a.est_gouvernement || a.role === 'Gouvernement' || groupe === 'GOUVERNEMENT' || a.typeAuteur === 'Gouvernement'

              return (
                <tr 
                  key={a.id ?? `fallback-${idx}`}
                  draggable={tri === 'texte'}
                  title={tri === 'texte' ? undefined : 'Pour réordonner par glisser-déposer, triez par « Ordre du texte ».'}
                  onDragStart={(e) => handleDragStart(e, idx)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDrop(e, idx)}
                  onClick={() => onSelect && onSelect(a.id)}
                  className={`cursor-pointer transition-colors ${isSelected ? 'bg-slate-100 dark:bg-[#1A1B22] border-l-4 border-l-[#D91227]' : 'dark:bg-[#0B0C10] hover:bg-slate-50 dark:hover:bg-gray-900/50'}`}
                >
                  <td className="px-2 py-3 w-16 text-xs font-semibold text-slate-800 dark:text-slate-200 text-center align-top whitespace-nowrap" title={a.article}>
                    {formaterArticle(a.article)}
                  </td>
                  <td className="px-2 py-3 w-20 text-xs font-semibold text-slate-900 dark:text-white align-top whitespace-nowrap" title={a.numero}>
                    {a.numero}
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-800 dark:text-slate-200 w-44 max-w-[180px] align-top">
                    <div className="flex flex-col items-start gap-1">
                      <span className="break-words leading-snug" title={auteursText}>{auteursText}</span>
                      {estRapporteur && (
                        <span
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-700 shadow-xs"
                          title="Amendement déposé en qualité de Rapporteur au nom de la commission"
                        >
                          <span aria-hidden="true">📋</span> Rapporteur
                        </span>
                      )}
                      {estGouvernement && (
                        <span
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 shadow-xs"
                          title="Amendement d'initiative gouvernementale (Exécutif)"
                        >
                          <span aria-hidden="true">🏛️</span> Exécutif
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-800 dark:text-slate-200 w-28 align-top">
                    {(groupe || a.groupe_politique_ref || a.groupRef) ? (
                      <div className="flex items-start">
                        <PoliticalGroupTag
                          group={groupe}
                          groupRef={a.groupe_politique_ref || a.groupRef}
                        />
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-800 dark:text-slate-200 w-36 align-top">
                    <ImpactBadge
                      type={
                        typeof a.point_impact === 'string'
                          ? a.point_impact
                          : (a.point_impact?.type || '')
                      }
                    />
                  </td>
                  <td className="px-3 py-3 text-xs w-64 max-w-[260px] align-top">
                    <CommissionKeywords
                      commission={a.commission}
                      commissionLibelle={a.commission_libelle}
                      motsCles={a.commission_mots_cles}
                      horsChamp={a.commission_hors_champ}
                    />
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-800 dark:text-slate-200 min-w-[240px] align-top whitespace-normal break-words leading-relaxed">
                    <ExtraitDispositif text={a.dispositif} />
                  </td>
                  <td className="px-3 py-3 text-xs whitespace-nowrap align-top w-36">
                    <div className="flex items-center gap-1">
                      <GroupeBadge statut={statutToDisplay} groupe={groupe} isPending={isPending} />
                      {/* 💡 Tooltip Chain of Thought (inline) */}
                      {a.resultat_ia?.analyse_intention && (
                        <div className="group relative inline-flex">
                          <span className="cursor-help text-sm" title={a.resultat_ia.analyse_intention}>💡</span>
                          <div className="pointer-events-none absolute z-50 opacity-0 group-hover:opacity-100 transition-opacity duration-200 bottom-full right-0 mb-2 w-64 bg-slate-900 text-white text-xs rounded-lg shadow-xl p-2.5 leading-relaxed">
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
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap text-center text-xs font-medium w-24 align-top">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); if (onDelete) onDelete(a.id); }}
                      className="inline-flex items-center justify-center rounded-md px-2 py-0.5 text-xs font-medium text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                      title="Retirer cet amendement de la liste de travail"
                    >
                      Retirer
                    </button>
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
