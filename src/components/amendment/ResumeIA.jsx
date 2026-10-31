import React, { useState } from 'react';
import { resumerAmendement } from '../../api/classify';

/**
 * ResumeIA — Résumé neutre d'un amendement (1 à 2 phrases), généré à la demande.
 *
 * Le résumé n'est PAS calculé automatiquement : chaque appel sollicite l'IA
 * (et, en mode Groq, envoie le texte hors de l'UE). Les résumés obtenus sont
 * gardés en mémoire pour la session, par amendement.
 */

const CACHE_RESUMES = new Map();

export default function ResumeIA({ amendment, aiSettings }) {
  const cle = amendment?.id || amendment?.uid;
  const [resume, setResume] = useState(() => CACHE_RESUMES.get(cle) || null);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState(null);

  const cloud = (aiSettings?.provider || 'local') !== 'local';

  async function lancer() {
    setEnCours(true);
    setErreur(null);
    try {
      const texte = await resumerAmendement(amendment, aiSettings);
      CACHE_RESUMES.set(cle, texte);
      setResume(texte);
    } catch (e) {
      setErreur(e?.message || "Résumé indisponible.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <section className="rounded-md border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/20 p-3.5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h4 className="font-display text-sm uppercase tracking-wide text-slate-900 dark:text-plume">
          ✨ Résumé IA
        </h4>
        {!resume && (
          <button
            type="button"
            onClick={lancer}
            disabled={enCours}
            className="rounded-md border border-indigo-300 bg-white px-3 py-1.5 text-xs font-semibold text-indigo-800 hover:bg-indigo-50 disabled:opacity-60 disabled:cursor-wait dark:border-indigo-800 dark:bg-[#12131A] dark:text-indigo-300 dark:hover:bg-indigo-950/50 transition-colors"
          >
            {enCours ? 'Résumé en cours…' : 'Résumer cet amendement'}
          </button>
        )}
      </div>

      {resume && (
        <p className="mt-2 text-sm text-slate-800 dark:text-slate-200 leading-relaxed">{resume}</p>
      )}
      {erreur && (
        <p className="mt-2 text-xs text-red-700 dark:text-red-400" role="alert">
          ⚠️ {erreur}
        </p>
      )}
      <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
        {resume
          ? "Généré par l'IA à partir du dispositif et de l'exposé sommaire — à vérifier."
          : cloud
            ? "Le texte de l'amendement sera envoyé à Groq (États-Unis), hors du mode souverain."
            : "Traité par votre IA locale : le texte ne quitte pas votre poste."}
      </p>
    </section>
  );
}
