import React from 'react';

/**
 * CommissionKeywords — Colonne « Commission / Thèmes »
 *
 * Affiche la commission saisie et les mots-clés de SON périmètre qui sont
 * réellement présents dans le texte de l'amendement (corrélation calculée
 * côté backend par api/commissions_resolver.py, 100 % déterministe).
 *
 * Lecture attendue par l'administrateur :
 *   • des puces vertes  → l'amendement est bien dans le champ de la commission
 *   • « Hors champ »    → aucun thème du périmètre retrouvé dans le texte,
 *                         signal faible de cavalier législatif (art. 45).
 *                         C'est une PISTE DE RELECTURE, pas un verdict.
 *   • rien              → commission sans périmètre thématique propre
 *                         (séance publique) ou non résolue.
 */

const MAX_VISIBLE = 3;   // au-delà, on replie pour ne pas casser la hauteur de ligne

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

  const visibles = keywords.slice(0, MAX_VISIBLE);
  const reste = keywords.length - visibles.length;

  return (
    <div className="flex flex-col gap-1">
      {commission && (
        <span
          className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate max-w-[150px]"
          title={commissionLibelle || commission}
        >
          {commission}
        </span>
      )}

      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {visibles.map((mot) => (
            <span
              key={mot}
              className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium border
                         bg-emerald-50 text-emerald-800 border-emerald-200
                         dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800"
            >
              {mot}
            </span>
          ))}
          {reste > 0 && (
            <span
              className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium
                         bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
              title={keywords.join(', ')}
            >
              +{reste}
            </span>
          )}
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
