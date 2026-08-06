import React from 'react';

export default function AuthorBadge({ data }) {
  if (!data) return null;

  const { auteur_nom, auteur_prenom, auteur_trigramme } = data;
  const initial = (auteur_prenom?.[0] || auteur_nom?.[0] || '?').toUpperCase();
  const fullName = [auteur_prenom, auteur_nom].filter(Boolean).join(' ') || 'Auteur inconnu';

  return (
    <div className="flex items-center gap-2 px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded-md border border-slate-200 dark:border-slate-700 w-max">
      <div className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-300 dark:bg-slate-600 text-slate-700 dark:text-slate-200 text-xs font-bold shrink-0">
        {initial}
      </div>
      <div className="flex flex-col">
        <span className="text-sm font-medium text-slate-900 dark:text-slate-100 leading-tight">
          {fullName}
        </span>
        {auteur_trigramme && (
          <span className="text-[10px] uppercase text-slate-500 dark:text-slate-400 font-mono tracking-wider leading-tight">
            {auteur_trigramme}
          </span>
        )}
      </div>
    </div>
  );
}
