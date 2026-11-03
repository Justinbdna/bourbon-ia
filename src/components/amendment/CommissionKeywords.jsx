import React from 'react';

/**
 * CommissionKeywords — Colonne « Commission / Thèmes »
 *
 * Affiche la commission saisie et tous les mots-clés de son périmètre
 * directement avec un retour à la ligne naturel (sans accordéon masquant).
 */
export default function CommissionKeywords({
  commission,
  commissionLibelle,
  motsCles = [],
  horsChamp = false,
}) {
  const keywords = Array.isArray(motsCles) ? motsCles : [];

  // Aucune commission résolue : on n'affiche rien plutôt qu'un faux "—"
  if (!commission && keywords.length === 0) {
    return <span className="text-xs text-slate-400 dark:text-slate-600">—</span>;
  }

  return (
    <div className="flex flex-col gap-1 max-w-xs">
      {commission && (
        <span
          className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate max-w-full"
          title={commissionLibelle || commission}
        >
          {commission}
        </span>
      )}

      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1 max-w-xs">
          {keywords.map((mot) => (
            <span
              key={mot}
              className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium border
                         bg-emerald-50 text-emerald-800 border-emerald-200
                         dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800"
            >
              {mot}
            </span>
          ))}
        </div>
      )}

      {horsChamp && (
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium border
                     bg-amber-50 text-amber-800 border-amber-200
                     dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800"
          title="Aucun thème du périmètre de cette commission n'apparaît dans l'amendement. Signal faible de cavalier législatif (art. 45) — à vérifier."
        >
          ⚠️ Hors champ
        </span>
      )}
    </div>
  );
}
