import React from 'react';

/**
 * EUComplianceBadge — Verdict de conformité européenne d'un amendement.
 *
 * Consomme tel quel le contrat `SurtranspositionAnalysisResult` produit par
 * src/services/analysis/surtransposition_checker.py, attendu sur l'amendement
 * sous la clé `eu_compliance` :
 *
 *   { status: "STRICT_TRANSPOSITION" | "NATIONAL_ADDITION" | "SURTRANSPOSITION_ALERT",
 *     confidence, delta_summary, matched_sources[], target_article, analysis_mode, … }
 *
 * Tant qu'aucune analyse n'a tourné, on affiche un tiret neutre : on
 * n'invente jamais de verdict de conformité.
 */

export const EU_STATUTS = {
  STRICT_TRANSPOSITION: {
    emoji: '🟢',
    label: 'Transposition stricte',
    description: "Le dispositif reprend la directive sans exigence supplémentaire.",
    classes:
      'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800',
  },
  NATIONAL_ADDITION: {
    emoji: '🟡',
    label: 'Spécificité nationale',
    description: "Ajout national compatible avec la marge laissée par la directive.",
    classes:
      'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800',
  },
  SURTRANSPOSITION_ALERT: {
    emoji: '🔴',
    label: 'Alerte surtransposition',
    description:
      "Le dispositif va au-delà de la directive (charge administrative ou seuil plus strict).",
    classes:
      'bg-red-50 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800',
  },
};

export default function EUComplianceBadge({ result }) {
  const statut = result?.status ? EU_STATUTS[result.status] : null;

  if (!statut) {
    return (
      <span
        className="text-xs text-slate-400 dark:text-slate-600"
        title="Conformité européenne non analysée"
      >
        —
      </span>
    );
  }

  const confiance =
    typeof result.confidence === 'number' ? ` — confiance ${Math.round(result.confidence * 100)} %` : '';

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium border whitespace-normal ${statut.classes}`}
      title={`${statut.description}${confiance}`}
    >
      <span aria-hidden="true">{statut.emoji}</span>
      {statut.label}
    </span>
  );
}
