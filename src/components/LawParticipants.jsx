import React, { useEffect, useState, useMemo } from 'react';
import PoliticalGroupTag from './amendment/PoliticalGroupTag';

const API_BASE_URL =
  import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000');

/**
 * LawParticipants — Participants d'un TEXTE DE LOI
 *
 * Nom de famille, prénom et groupe politique de chaque parlementaire ayant
 * participé au dossier législatif, avec son rôle (rapporteur, initiateur,
 * auteur, cosignataire) et son niveau d'implication.
 *
 * ⚠️ Granularité : les participants s'attachent au DOSSIER, pas à l'amendement
 * (un texte courant en compte 200+). D'où un panneau dédié, et non une colonne
 * du tableau d'amendements.
 *
 * Source : GET /api/participants?dossier_ref=DLR5L17N54094
 * L'endpoint ne renvoie jamais d'erreur : en cas de coupure réseau la liste est
 * vide et ce panneau l'indique sans bloquer le reste de l'application.
 */
export default function LawParticipants({ dossierRef, amendementUid, titre, limite = 100 }) {
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState(null);
  const [filtreGroupe, setFiltreGroupe] = useState(null);
  const [tout, setTout] = useState(false);

  useEffect(() => {
    // Le lien vers le texte de loi peut venir soit d'une référence de dossier
    // explicite, soit — la plupart du temps — de l'uid d'un amendement, que le
    // backend sait convertir en un seul appel.
    if (!dossierRef && !amendementUid) {
      setDonnees(null);
      return;
    }
    let annule = false;
    const controleur = new AbortController();

    (async () => {
      setChargement(true);
      setErreur(null);
      try {
        const params = new URLSearchParams({ limite: String(limite) });
        if (dossierRef) params.set('dossier_ref', dossierRef);
        else params.set('amendement_uid', amendementUid);

        const res = await fetch(
          `${API_BASE_URL}/api/participants?${params.toString()}`,
          { signal: controleur.signal }
        );
        if (!res.ok) throw new Error(`Erreur API ${res.status}`);
        const json = await res.json();
        if (!annule) setDonnees(json);
      } catch (e) {
        if (e.name !== 'AbortError' && !annule) {
          setErreur(
            e.message.includes('Failed to fetch')
              ? "Back-end injoignable — impossible de charger les participants."
              : e.message
          );
        }
      } finally {
        if (!annule) setChargement(false);
      }
    })();

    // Annulation propre si le dossier change ou si le composant est démonté
    return () => { annule = true; controleur.abort(); };
  }, [dossierRef, amendementUid, limite]);

  const participants = donnees?.participants ?? [];
  const parGroupe = donnees?.par_groupe ?? [];

  const affiches = useMemo(() => {
    const filtres = filtreGroupe
      ? participants.filter((p) => (p.groupe || '—') === filtreGroupe)
      : participants;
    return tout ? filtres : filtres.slice(0, 15);
  }, [participants, filtreGroupe, tout]);

  if (!dossierRef && !amendementUid) return null;

  return (
    <div className="rounded-lg border border-ink-300 bg-white dark:bg-surface dark:border-ink-700 overflow-hidden">
      {/* En-tête */}
      <div className="bg-slate-100/80 dark:bg-slate-900/50 border-b border-ink-200 dark:border-ink-700 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-plume">
          👥 Participants au texte
          {donnees && (
            <span className="ml-2 font-normal text-slate-500 dark:text-slate-400">
              {participants.length} parlementaire{participants.length > 1 ? 's' : ''}
            </span>
          )}
        </h3>
        {titre && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate" title={titre}>
            {titre}
          </p>
        )}
      </div>

      {chargement && (
        <p className="px-4 py-6 text-sm text-slate-500 dark:text-slate-400">
          Chargement des participants…
        </p>
      )}

      {erreur && (
        <p className="px-4 py-4 text-sm text-amber-700 dark:text-amber-300">⚠️ {erreur}</p>
      )}

      {!chargement && !erreur && participants.length === 0 && (
        <p className="px-4 py-6 text-sm text-slate-500 dark:text-slate-400">
          Aucun participant disponible pour ce texte.
        </p>
      )}

      {participants.length > 0 && (
        <>
          {/* Répartition par groupe — cliquable pour filtrer */}
          <div className="flex flex-wrap gap-2 px-4 py-3 border-b border-ink-100 dark:border-ink-700">
            {parGroupe.map((g) => {
              const actif = filtreGroupe === g.groupe;
              return (
                <button
                  key={g.groupe}
                  type="button"
                  onClick={() => setFiltreGroupe(actif ? null : g.groupe)}
                  title={g.libelle}
                  className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium border transition-colors ${
                    actif
                      ? 'bg-slate-800 text-white border-slate-800 dark:bg-slate-200 dark:text-slate-900'
                      : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50 dark:bg-slate-800/50 dark:text-slate-300 dark:border-slate-700 dark:hover:bg-slate-700/50'
                  }`}
                >
                  {g.couleur && (
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: g.couleur }}
                    />
                  )}
                  {g.groupe} <span className="opacity-70">{g.effectif}</span>
                </button>
              );
            })}
            {filtreGroupe && (
              <button
                type="button"
                onClick={() => setFiltreGroupe(null)}
                className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-800 dark:hover:text-slate-200"
              >
                réinitialiser
              </button>
            )}
          </div>

          {/* Liste : NOM DE FAMILLE, PRÉNOM, GROUPE POLITIQUE */}
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 dark:bg-[#1A1B22]">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Nom</th>
                  <th className="px-4 py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Prénom</th>
                  <th className="px-4 py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Groupe politique</th>
                  <th className="px-4 py-2 text-left text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">Rôle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {affiches.map((p) => (
                  <tr key={p.acteur_ref || `${p.nom}-${p.prenom}`} className="hover:bg-slate-50 dark:hover:bg-gray-900/50">
                    <td className="px-4 py-2 font-medium text-slate-900 dark:text-slate-100">{p.nom || '—'}</td>
                    <td className="px-4 py-2 text-slate-700 dark:text-slate-300">{p.prenom || '—'}</td>
                    <td className="px-4 py-2">
                      {p.groupe
                        ? <PoliticalGroupTag group={p.groupe} />
                        : <span className="text-xs text-slate-400">non renseigné</span>}
                    </td>
                    <td className="px-4 py-2">
                      {p.roles?.length ? (
                        <span className="text-xs text-slate-600 dark:text-slate-400">{p.roles.join(' · ')}</span>
                      ) : (
                        <span className="text-xs text-slate-400 dark:text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {(filtreGroupe ? participants.filter((p) => (p.groupe || '—') === filtreGroupe) : participants).length > 15 && (
            <div className="px-4 py-3 border-t border-ink-100 dark:border-ink-700">
              <button
                type="button"
                onClick={() => setTout((v) => !v)}
                className="text-xs text-slate-600 dark:text-slate-300 underline underline-offset-2 hover:text-slate-900 dark:hover:text-white"
              >
                {tout ? 'Réduire la liste' : `Afficher les ${participants.length} participants`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
