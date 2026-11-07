import React, { useState } from 'react';

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

const MAX_VISIBLE = 3;   // au-delà, on replie (« Voir plus ») pour ne pas casser la hauteur de ligne

export default function CommissionKeywords({
  commission,
  commissionLibelle,
  motsCles = [],
  horsChamp = false,
}) {
  const [deplie, setDeplie] = useState(false);
  const keywords = Array.isArray(motsCles) ? motsCles : [];

  // Aucune commission résolue : on n'affiche rien plutôt qu'un faux "—"
  if (!commission && keywords.length === 0) {
    return <span className="text-xs text-slate-400 dark:text-slate-600">—</span>;
  }

  const reste = Math.max(0, keywords.length - MAX_VISIBLE);
  const visibles = deplie ? keywords : keywords.slice(0, MAX_VISIBLE);

  return (
    <div className="flex flex-col gap-1">
      {commission && (
        <span
          className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate max-w-full"
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
            <button
              type="button"
              aria-expanded={deplie}
              // La ligne du tableau est cliquable (sélection) : on isole le clic.
              onClick={(e) => { e.stopPropagation(); setDeplie((v) => !v); }}
              className="inline-flex items-center px-1 py-0.5 text-[11px] font-medium text-[#D91227] hover:underline whitespace-nowrap"
              title={deplie ? undefined : keywords.slice(MAX_VISIBLE).join(', ')}
            >
              {deplie ? 'Voir moins' : `+${reste} Voir plus`}
            </button>
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
