import ImpactBadge from './ImpactBadge'
import GroupeBadge from './GroupeBadge'
import { downloadRtf } from '../utils/exportRtf'

const MAX_VISIBLE_HEIGHT = 1360

function truncate(text, max = 90) {
  if (!text) return '—'
  const flat = text.replace(/\s+/g, ' ').trim()
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
      spans.set(a.id, { span: 1, isStart: true, meta: null })
      i += 1
      continue
    }

    let j = i + 1
    while (j < amendments.length && amendments[j].resultat_ia?.groupe?.groupe_id === g.groupe_id) {
      j += 1
    }
    const size = j - i
    for (let k = i; k < j; k++) {
      spans.set(amendments[k].id, { span: size, isStart: k === i, meta })
    }
    i = j
  }
  return spans
}

export default function AmendmentTable({ amendments, selectedId, onSelect, onReorder, onDelete }) {
  if (amendments.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-ink-300 bg-white p-10 text-center">
        <p className="text-ink-500 text-sm">
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

  return (
    <div className="rounded-lg border border-ink-300 bg-white overflow-hidden">
      <div className="overflow-y-auto scroll-thin" style={{ maxHeight: MAX_VISIBLE_HEIGHT }}>
        <table className="w-full text-sm table-fixed">
          <thead>
            <tr className="bg-marine-50 text-marine-900 text-left">
              <th className="sticky top-0 z-10 bg-marine-50 px-2 py-3 w-8"></th>
              <th className="sticky top-0 z-10 bg-marine-50 px-1 py-3 w-10"></th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-16">Rang</th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-14">Art.</th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-20">N°</th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-46">Auteur(s)</th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-52">Point d'impact</th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-40">Extrait du dispositif</th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-42">Groupe</th>
              <th className="sticky top-0 z-10 bg-marine-50 px-4 py-3 font-semibold w-28">Actions</th>
            </tr>
          </thead>
          <tbody>
            {amendments.map((a, index) => {
              const isSelected = a.id === selectedId
              const res = a.resultat_ia
              const isDoublon = res?.groupe?.type === 'doublon'
              const spanInfo = groupSpans.get(a.id)
              const auteursText = a.rapporteur
                ? 'Rapporteur'
                : (a.auteurs || []).join(', ') || '—'
              const dispositifFull = (a.dispositif || '').replace(/\s+/g, ' ').trim()

              return (
                <tr
                  key={a.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDrop(e, index)}
                  onClick={() => onSelect(a.id)}
                  className={`cursor-pointer border-t border-ink-100 transition-colors ${
                    isSelected ? 'bg-marine-100/70' : 'hover:bg-ink-100/60'
                  }`}
                >
                  <td
                    className="px-2 py-3 cursor-grab active:cursor-grabbing text-center"
                    title="Glisser pour repositionner"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <GripIcon />
                  </td>

                  {spanInfo.isStart && (
                    <td rowSpan={spanInfo.span} className="p-0 align-top">
                      {spanInfo.meta ? (
                        <div className="flex h-full items-stretch gap-1 py-1.5 pl-1.5 pr-0.5 min-h-[2.75rem]">
                          <span
                            className={`text-[10px] font-semibold uppercase tracking-wide flex items-center ${spanInfo.meta.accent}`}
                          >
                            {spanInfo.meta.label}
                          </span>
                          <svg viewBox="0 0 16 100" preserveAspectRatio="none" className="w-4 h-full shrink-0">
                            <path
                              d="M12 6 H6 V94 H12"
                              fill="none"
                              stroke={spanInfo.meta.stroke}
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </div>
                      ) : null}
                    </td>
                  )}

                  <td className="px-4 py-3 font-medium text-ink-900 whitespace-nowrap truncate">
                    {hasClassification ? index + 1 : <span className="text-ink-400 italic">—</span>}
                  </td>
                  <td className="px-4 py-3 font-medium text-ink-900 whitespace-nowrap truncate">
                    {a.article}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap truncate">
                    {a.numero}
                    {a.rectification ? ` ${a.rectification}` : ''}
                  </td>
                  <td
                    className="px-4 py-3 text-ink-700 truncate whitespace-nowrap"
                    title={auteursText}
                  >
                    <span className={a.rapporteur ? 'font-medium text-bronze-600' : ''}>
                      {auteursText}
                    </span>
                  </td>
                  <td className="px-4 py-3 truncate whitespace-nowrap">
                    <ImpactBadge type={a.point_impact?.type} />
                  </td>
                  <td
                    className="px-4 py-3 text-ink-600 truncate whitespace-nowrap max-w-0"
                    title={dispositifFull}
                  >
                    {truncate(a.dispositif)}
                  </td>
                  <td className="px-4 py-3 truncate whitespace-nowrap">
                    {res ? (
                      <GroupeBadge type={res.groupe?.type} />
                    ) : (
                      <span className="text-ink-500 italic text-xs">Non classé</span>
                    )}
                  </td>
                  <td className="px-4 py-3 truncate whitespace-nowrap">
                    {isDoublon && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onDelete(a.id)
                        }}
                        className="text-xs font-medium text-red-600 hover:text-red-800 underline underline-offset-2"
                      >
                        Retirer
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-ink-100 bg-ink-50/50 px-4 py-3">
        <p className="text-xs text-ink-500">
          Export au format du préjaune de l'Assemblée (crochets Dc./Id. reconstruits à partir du classement).
        </p>
        <button
          type="button"
          onClick={handleExportRtf}
          disabled={!hasClassification}
          className="rounded-md border border-marine-700 px-3 py-1.5 text-sm font-medium text-marine-800 hover:bg-marine-50 disabled:border-ink-300 disabled:text-ink-400 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          Exporter en préjaune (.rtf)
        </button>
      </div>
    </div>
  )
}
