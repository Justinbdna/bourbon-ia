import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'
import { downloadRtf } from '../utils/exportRtf'

const MAX_VISIBLE_HEIGHT = 1360

function truncate(text, max = 90) {
  if (!text) return '—'
  const flat = String(text).replace(/\s+/g, ' ').trim()
  return flat.length > max ? flat.slice(0, max) + '…' : flat
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

export default function AmendmentTable({ amendments, selectedId, onSelect, onReorder, onDelete }) {
  if (amendments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-ink-300 bg-white dark:bg-surface dark:border-ink-700 p-10 text-center">
        <p className="text-slate-500 dark:text-slate-300 text-sm">
          Aucun amendement chargé pour l'instant. Importe un fichier JSON ci-dessus pour commencer.
        </p>
      </div>
    )
  }

  const hasClassification = amendments.some((a) => a.resultat_ia)
  const groupSpans = computeGroupSpans(amendments)

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
    const dateStr = new Date().toISOString().slice(0, 10)
    downloadRtf(amendments, `prejaune-${dateStr}.rtf`)
  }

  const totalClasses = amendments.filter(a => a.resultat_ia).length
  const countDC = amendments.filter(a => {
    const s = a.resultat_ia?.statut
    return s === 'Incompatible' || s === 'Discussion commune'
  }).length
  const countId = amendments.filter(a => {
    const s = a.resultat_ia?.statut
    return s === 'Identique' || s === 'Identiques'
  }).length
  const countIsole = amendments.filter(a => {
    const s = a.resultat_ia?.statut
    return s === 'Nouveau' || s === 'Isolé'
  }).length

  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 overflow-hidden">
      {totalClasses > 0 && (
        <div className="bg-slate-100/80 dark:bg-slate-900/50 border-b border-ink-200 dark:border-ink-700 px-4 py-3">
          <p className="text-sm font-medium text-slate-900 dark:text-plume">
            {totalClasses} amendements classés ({countDC} en discussion commune, {countId} identiques, {countIsole} isolés).
          </p>
        </div>
      )}
      <div className="overflow-y-auto overflow-x-auto scroll-thin" style={{ maxHeight: MAX_VISIBLE_HEIGHT }}>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100 dark:bg-[#1A1B22] border-b border-gray-200 dark:border-gray-800">
            <tr>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Rang</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Art.</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">N°</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider max-w-[120px]">Auteur(s)</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider w-40">Point d'impact</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider w-full max-w-md">Extrait du dispositif</th>
              <th className="px-4 py-4 text-left text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Groupe</th>
              <th className="px-4 py-4 text-right text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-[#0B0C10] divide-y divide-gray-200 dark:divide-gray-800">
            {amendments.map((a, index) => {
              const rang = a.rang || a.resultat_ia?.rang
              const statut = a.statut || a.resultat_ia?.statut
              const groupe = a.groupe || a.resultat_ia?.groupe
              const isSelected = a.id === selectedId
              
              let auteursText = a.auteurs
              if (Array.isArray(auteursText)) {
                auteursText = auteursText.join(', ')
              }
              auteursText = auteursText || '—'

              return (
                <tr 
                  key={a.id ?? `fallback-${index}`}
                  onClick={() => onSelect && onSelect(a.id)}
                  className={`cursor-pointer transition-colors ${isSelected ? 'bg-slate-100 dark:bg-[#1A1B22] border-l-4 border-l-[#D91227]' : 'dark:bg-[#0B0C10] hover:bg-slate-50 dark:hover:bg-gray-900/50'}`}
                >
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-slate-800 dark:text-slate-200">{rang || "—"}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-800 dark:text-slate-200">{a.article || "—"}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-800 dark:text-slate-200">{a.numero}</td>
                  <td className="px-4 py-4 text-sm text-slate-800 dark:text-slate-200 max-w-[120px] truncate" title={auteursText}>{auteursText}</td>
                  <td className="px-4 py-4 text-sm text-slate-800 dark:text-slate-200 w-40"><ImpactBadge type={a.point_impact?.type || a.point_impact} /></td>
                  <td className="px-4 py-4 text-sm text-slate-800 dark:text-slate-200 w-full max-w-md truncate" title={a.dispositif}>{a.dispositif}</td>
                  <td className="px-4 py-4 text-sm whitespace-nowrap"><GroupeBadge statut={statut} groupe={groupe} /></td>
                  <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onClick={(e) => { e.stopPropagation(); onDelete && onDelete(a.id); }} className="text-gray-400 hover:text-red-600 transition-colors">Retirer</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-ink-100 dark:border-ink-700 bg-ink-50/50 dark:bg-obsidienne/50 px-4 py-3">
        <p className="text-xs text-ink-500 dark:text-ink-300">
          Export au format du préjaune de l'Assemblée (crochets Dc./Id. reconstruits à partir du classement).
        </p>
        <button
          type="button"
          disabled={amendments.length === 0}
          onClick={() => downloadRtf(amendments)}
          className="rounded-md border border-slate-700 dark:border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-900 dark:text-plume hover:bg-slate-100 dark:hover:bg-slate-800 disabled:border-ink-300 disabled:text-ink-400 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          Exporter en préjaune (.rtf)
        </button>
      </div>
    </div>
  )
}
