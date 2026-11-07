import React, { useState } from 'react';

/**
 * AmendmentSearchBar — Recherche dans le tableau des amendements.
 *
 * Deux critères, utilisables seuls ou ensemble (ET logique) :
 *   • thème   : un mot-clé de la colonne « Commission / Thèmes »
 *               (liste déroulante, avec le nombre d'amendements concernés) ;
 *   • auteur  : texte libre, insensible à la casse et aux accents, avec
 *               suggestions tirées des auteurs chargés.
 *
 * Le filtre ne s'applique qu'à la validation (bouton ou Entrée) ;
 * « Réinitialiser » efface les deux critères.
 */
export default function AmendmentSearchBar({ motsCles = [], auteurs = [], filtre, onRechercher, nbResultats, nbTotal }) {
  const [motCle, setMotCle] = useState(filtre?.motCle ?? '');
  const [auteur, setAuteur] = useState(filtre?.auteur ?? '');

  const filtreActif = Boolean(filtre?.motCle || filtre?.auteur);

  function soumettre(e) {
    e.preventDefault();
    onRechercher({ motCle, auteur: auteur.trim() });
  }

  function reinitialiser() {
    setMotCle('');
    setAuteur('');
    onRechercher({ motCle: '', auteur: '' });
  }

  return (
    <form
      onSubmit={soumettre}
      role="search"
      aria-label="Rechercher des amendements"
      className="border-b border-ink-200 dark:border-ink-700 bg-white dark:bg-surface px-4 py-3"
    >
      <div className="flex flex-col md:flex-row md:items-end gap-3">
        <label className="flex flex-col gap-1 md:w-72">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Thème (Commission / Thèmes)</span>
          <select
            value={motCle}
            onChange={(e) => setMotCle(e.target.value)}
            className="rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2.5 py-1.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40"
          >
            <option value="">Tous les thèmes</option>
            {motsCles.map(({ mot, nb }) => (
              <option key={mot} value={mot}>
                {mot} ({nb})
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 md:w-72">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Auteur</span>
          <input
            type="search"
            value={auteur}
            onChange={(e) => setAuteur(e.target.value)}
            placeholder="Nom de l'auteur…"
            list="amendment-search-auteurs"
            autoComplete="off"
            className="rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2.5 py-1.5 text-sm text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40"
          />
          <datalist id="amendment-search-auteurs">
            {auteurs.map((nom) => (
              <option key={nom} value={nom} />
            ))}
          </datalist>
        </label>

        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="rounded-md bg-[#D91227] px-4 py-1.5 text-sm font-medium text-white hover:bg-[#b80f21] transition-colors"
          >
            Rechercher
          </button>
          <button
            type="button"
            onClick={reinitialiser}
            disabled={!filtreActif && !motCle && !auteur}
            className="rounded-md border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Réinitialiser
          </button>
        </div>
      </div>

      {filtreActif && (
        <p className="mt-2 text-xs text-slate-600 dark:text-slate-400" aria-live="polite">
          {nbResultats} amendement{nbResultats > 1 ? 's' : ''} sur {nbTotal}
          {filtre.motCle && <> · thème « <strong>{filtre.motCle}</strong> »</>}
          {filtre.auteur && <> · auteur « <strong>{filtre.auteur}</strong> »</>}
        </p>
      )}
    </form>
  );
}
