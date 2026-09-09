import { useState, useMemo } from 'react'
import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'
import PoliticalGroupTag from './amendment/PoliticalGroupTag'
import { downloadRtf } from '../utils/exportRtf'
import SkeletonLoader from './amendment/SkeletonLoader'

const PAGE_SIZE = 50

function stripHtml(text) {
  if (!text || typeof text !== 'string') return text || ''
  return text
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&#160;/g, ' ')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim()
}

function cleanTruncate(text, max = 110) {
  if (!text) return '—'
  const clean = stripHtml(String(text)).replace(/\s+/g, ' ').trim()
  if (!clean) return '—'
  return clean.length > max ? clean.slice(0, max) + '…' : clean
}

function truncate(text, max = 90) {
  return cleanTruncate(text, max)
}

function GripIcon() {
  return (
    <svg width="10" height="16" viewBox="0 0 10 16" fill="currentColor" className="text-ink-300">
      <circle cx="2" cy="2" r="1.3" />
      <circle cx="7" cy="2" r="1.3" />
      <circle cx="2" cy="8" r="1.3" />
      <circle cx="7" cy="8" r="1.3" />
      <circle cx="2" cy="14" r="1.3" />
      <circle cx="7" cy="14" r="1.3" />
    </svg>
  )
}

const GROUP_META = {
  identiques: {
    label: 'Id.',
    accent: 'text-teal-700',
    stroke: '#0d9488',
    tint: 'bg-teal-50/60',
  },
  discussion_commune: {
    label: 'Dc.',
    accent: 'text-purple-700',
    stroke: '#7e22ce',
    tint: 'bg-purple-50/60',
  },
}

function computeGroupSpans(amendments) {
  const spans = new Map()
  let i = 0
  while (i < amendments.length) {
    const a = amendments[i]
    const g = a.resultat_ia?.groupe
    const meta = g?.groupe_id ? GROUP_META[g.type] : null

    if (!meta) {
      spans.set(a.id ?? `anon-${i}`, { span: 1, isStart: true, meta: null })
      i += 1
      continue
    }

    let j = i + 1
    while (j < amendments.length && amendments[j].resultat_ia?.groupe?.groupe_id === g.groupe_id) {
      j += 1
    }
    const size = j - i
    for (let k = i; k < j; k++) {
      spans.set(amendments[k].id ?? `anon-${k}`, { span: size, isStart: k === i, meta })
    }
    i = j
  }
  return spans
}

export default function AmendmentTable({ amendments, selectedId, onSelect, onReorder, onDelete, isClassifying, onExportJson }) {
  const [currentPage, setCurrentPage] = useState(0)

  // Compteurs calculés avec un seul reduce (déplacé AVANT le return conditionnel pour éviter l'erreur #310)
  const counts = useMemo(() => {
    return amendments.reduce((acc, a) => {
      if (!a.resultat_ia) return acc
      acc.total++
      const s = a.resultat_ia.statut
      if (s === 'Incompatible' || s === 'Discussion commune') acc.dc++
      else if (s === 'Identique' || s === 'Identiques') acc.id++
      else if (s === 'Nouveau' || s === 'Isolé') acc.isole++
      return acc
    }, { total: 0, dc: 0, id: 0, isole: 0 })
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

  const totalPages = Math.ceil(amendments.length / PAGE_SIZE)
  const safePage = Math.min(currentPage, totalPages - 1)
  const startIdx = safePage * PAGE_SIZE
  const pageAmendments = amendments.slice(startIdx, startIdx + PAGE_SIZE)

  const hasClassification = amendments.some((a) => a.resultat_ia)
  const groupSpans = computeGroupSpans(amendments)

  function handleDragStart(e, index) {
    e.dataTransfer.setData('text/plain', String(startIdx + index))
    e.dataTransfer.effectAllowed = 'move'
  }

  function handleDrop(e, targetLocalIndex) {
    e.preventDefault()
    const fromIndex = Number(e.dataTransfer.getData('text/plain'))
    const targetIndex = startIdx + targetLocalIndex
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
      {counts.total > 0 && (
        <div className="bg-slate-100/80 dark:bg-slate-900/50 border-b border-ink-200 dark:border-ink-700 px-4 py-3">
          <p className="text-sm font-medium text-slate-900 dark:text-plume">
            {counts.total} amendements classés ({counts.dc} en discussion commune, {counts.id} identiques, {counts.isole} isolés).
          </p>
        </div>
      )}
      <div className="overflow-x-auto scroll-thin">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100 dark:bg-[#1A1B22] border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Rang</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Art.</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">N°</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider max-w-[120px]">Auteur(s)</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Groupe</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider w-40">Point d'impact</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider w-full max-w-md">Extrait du dispositif</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Statut</th>
              <th className="px-4 py-4 text-right text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-[#0B0C10] divide-y divide-gray-200 dark:divide-gray-800">
            {pageAmendments.map((a, index) => {
              const rang = a.rang || a.resultat_ia?.rang
              const statut = a.statut || a.resultat_ia?.statut
              const groupe = a.groupe || a.resultat_ia?.groupe
              const isSelected = a.id === selectedId
              
              const isPending = isClassifying && !a.resultat_ia && !a.statut;
              const statutToDisplay = isPending ? "En cours..." : statut;
              
              let auteursText = a.auteurs
              if (Array.isArray(auteursText)) {
                auteursText = auteursText.join(', ')
              }
              auteursText = auteursText || '—'

              return (
                <tr 
                  key={a.id ?? `fallback-${startIdx + index}`}
                  draggable
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDrop(e, index)}
                  onClick={() => onSelect && onSelect(a.id)}
                  className={`cursor-pointer transition-colors ${isSelected ? 'bg-slate-100 dark:bg-[#1A1B22] border-l-4 border-l-[#D91227]' : 'dark:bg-[#0B0C10] hover:bg-slate-50 dark:hover:bg-gray-900/50'}`}
                >
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-slate-800 dark:text-slate-200">{rang || "—"}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-800 dark:text-slate-200">{a.article || "—"}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-800 dark:text-slate-200">{a.numero}</td>
                  <td className="px-4 py-4 text-sm text-slate-800 dark:text-slate-200 max-w-[120px] truncate" title={auteursText}>{auteursText}</td>
                  <td className="px-4 py-4 text-sm whitespace-nowrap">
                    <PoliticalGroupTag group={a.groupe || a.groupe_politique || (typeof groupe === 'string' ? groupe : groupe?.nom)} groupRef={a.groupRef || a.groupe_politique_ref || groupe?.ref} />
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-800 dark:text-slate-200 w-40"><ImpactBadge type={a.point_impact?.type || a.point_impact} /></td>
                  <td className="px-4 py-4 text-sm text-slate-800 dark:text-slate-200 w-full max-w-md truncate" title={stripHtml(a.dispositif)}>{cleanTruncate(a.dispositif)}</td>
                  <td className="px-4 py-4 text-sm whitespace-nowrap">
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
                  <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onClick={(e) => { e.stopPropagation(); onDelete && onDelete(a.id); }} className="text-gray-400 hover:text-red-600 transition-colors">Retirer</button>
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
            Page {safePage + 1} / {totalPages} — Amendements {startIdx + 1}–{Math.min(startIdx + PAGE_SIZE, amendments.length)} sur {amendments.length}
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
