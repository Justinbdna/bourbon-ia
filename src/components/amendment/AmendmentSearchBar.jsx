import React, { useState } from 'react';

/**
 * AmendmentSearchBar — Recherche multicritère dans le tableau des amendements.
 *
 * Quatre critères combinables (ET logique) :
 *   • article : article ciblé (ex. 1er, 3 BIS, 5...) ;
 *   • groupe  : groupe parlementaire (ex. EPR, LFI-NFP, RN, GOUVERNEMENT...) ;
 *   • thème   : mot-clé de la colonne « Commission / Thèmes » ;
 *   • auteur  : texte libre avec suggestions.
 */
export default function AmendmentSearchBar({
  motsCles = [],
  auteurs = [],
  articles = [],
  groupes = [],
  filtre,
  onRechercher,
  nbResultats,
  nbTotal
}) {
  const [article, setArticle] = useState(filtre?.article ?? '');
  const [groupe, setGroupe] = useState(filtre?.groupe ?? '');
  const [motCle, setMotCle] = useState(filtre?.motCle ?? '');
  const [auteur, setAuteur] = useState(filtre?.auteur ?? '');

  const filtreActif = Boolean(filtre?.article || filtre?.groupe || filtre?.motCle || filtre?.auteur);

  function soumettre(e) {
    e.preventDefault();
    onRechercher({
      article: article.trim(),
      groupe: groupe.trim(),
      motCle,
      auteur: auteur.trim()
    });
  }

  function reinitialiser() {
    setArticle('');
    setGroupe('');
    setMotCle('');
    setAuteur('');
    onRechercher({ article: '', groupe: '', motCle: '', auteur: '' });
  }

  return (
    <form
      onSubmit={soumettre}
      role="search"
      aria-label="Rechercher des amendements"
      className="border-b border-ink-200 dark:border-ink-700 bg-white dark:bg-surface px-4 py-3"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
        {/* 1. Article */}
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Article</span>
          <select
            value={article}
            onChange={(e) => setArticle(e.target.value)}
            className="h-9 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2.5 py-1.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40"
          >
            <option value="">Tous les articles</option>
            {articles.map(({ article: artNom, nb }) => (
              <option key={artNom} value={artNom}>
                Art. {artNom} ({nb})
              </option>
            ))}
          </select>
        </label>

        {/* 2. Groupe politique */}
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Groupe</span>
          <select
            value={groupe}
            onChange={(e) => setGroupe(e.target.value)}
            className="h-9 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2.5 py-1.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40"
          >
            <option value="">Tous les groupes</option>
            {groupes.map(({ groupe: grpNom, nb }) => (
              <option key={grpNom} value={grpNom}>
                {grpNom} ({nb})
              </option>
            ))}
          </select>
        </label>

        {/* 3. Thème */}
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Thème (Commission)</span>
          <select
            value={motCle}
            onChange={(e) => setMotCle(e.target.value)}
            className="h-9 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2.5 py-1.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40"
          >
            <option value="">Tous les thèmes</option>
            {motsCles.map(({ mot, nb }) => (
              <option key={mot} value={mot}>
                {mot} ({nb})
              </option>
            ))}
          </select>
        </label>

        {/* 4. Auteur */}
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">Auteur</span>
          <input
            type="search"
            value={auteur}
            onChange={(e) => setAuteur(e.target.value)}
            placeholder="Nom de l'auteur…"
            list="amendment-search-auteurs"
            autoComplete="off"
            className="h-9 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-[#12131A] px-2.5 py-1.5 text-sm text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D91227]/40"
          />
          <datalist id="amendment-search-auteurs">
            {auteurs.map((nom) => (
              <option key={nom} value={nom} />
            ))}
          </datalist>
        </label>

        {/* 5. Boutons d'action */}
        <div className="flex items-center gap-2 h-9">
          <button
            type="submit"
            className="h-9 rounded-md bg-[#D91227] px-4 py-1.5 text-sm font-medium text-white hover:bg-[#b80f21] transition-colors shadow-xs"
          >
            Filtrer
          </button>
          <button
            type="button"
            onClick={reinitialiser}
            disabled={!filtreActif && !article && !groupe && !motCle && !auteur}
            className="h-9 rounded-md border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Réinitialiser
          </button>
        </div>
      </div>

      {filtreActif && (
        <p className="mt-2 text-xs text-slate-600 dark:text-slate-400" aria-live="polite">
          {nbResultats} amendement{nbResultats > 1 ? 's' : ''} sur {nbTotal}
          {filtre.article && <> · article « <strong>{filtre.article}</strong> »</>}
          {filtre.groupe && <> · groupe « <strong>{filtre.groupe}</strong> »</>}
          {filtre.motCle && <> · thème « <strong>{filtre.motCle}</strong> »</>}
          {filtre.auteur && <> · auteur « <strong>{filtre.auteur}</strong> »</>}
        </p>
      )}
    </form>
  );
}
