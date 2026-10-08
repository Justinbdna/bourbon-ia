import React, { useState } from 'react';
import EUComplianceBadge from './EUComplianceBadge';

/**
 * EUCompliancePanel — Détail dépliable de l'analyse de surtransposition.
 *
 * Affiche, à partir de `SurtranspositionAnalysisResult` (clé `eu_compliance`) :
 *   • l'article de directive de référence (matched_sources : CELEX + article),
 *     avec lien vers EUR-Lex ;
 *   • le résumé comparatif (delta_summary), où les seuils chiffrés et les
 *     charges administratives ajoutées sont mis en évidence.
 */

// Termes signalant une charge administrative ou un durcissement par rapport
// à la directive. Volontairement restreint : on surligne, on ne juge pas.
const TERMES_CHARGE =
  // Groupe NON capturant : un groupe capturant ferait dupliquer les mots
  // dans le résultat de String.split() ci-dessous.
  /\b(?:obligation|obligatoire|déclaration|autorisation|agrément|formalité|contrôle|sanction|pénalité|rapport annuel|registre|certification|audit|délai|seuil|plafond|minimum|maximum|interdiction|exigence|supplémentaire|plus strict|renforcé)\w*/gi;
// Seuils chiffrés : « 50 salariés », « 10 000 € », « 3 mois », « 15 % »…
const SEUILS =
  /\b\d[\d\s.,]*\s?(?:%|€|euros?|salariés?|jours?|mois|ans?|ans|heures?|kg|tonnes?|m²|habitants?)\b/gi;

function surligner(texte) {
  if (!texte) return null;
  // On découpe sur les deux motifs en conservant les correspondances.
  const motif = new RegExp(`(${SEUILS.source}|${TERMES_CHARGE.source})`, 'gi');
  const morceaux = String(texte).split(motif);
  return morceaux.map((m, i) => {
    if (!m) return null;
    if (new RegExp(`^(?:${SEUILS.source})$`, 'i').test(m)) {
      return (
        <mark key={i} className="bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200 rounded px-0.5 font-semibold">
          {m}
        </mark>
      );
    }
    if (new RegExp(`^(?:${TERMES_CHARGE.source})$`, 'i').test(m)) {
      return (
        <mark key={i} className="bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200 rounded px-0.5">
          {m}
        </mark>
      );
    }
    return <React.Fragment key={i}>{m}</React.Fragment>;
  });
}

function lienEurLex(celex) {
  return celex
    ? `https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:${encodeURIComponent(celex)}`
    : null;
}

export default function EUCompliancePanel({ result, defaultOpen = false }) {
  const [ouvert, setOuvert] = useState(defaultOpen);

  if (!result?.status) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 dark:border-slate-700 px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
        🇪🇺 Conformité européenne : analyse non disponible pour cet amendement.
      </div>
    );
  }

  const sources = Array.isArray(result.matched_sources) ? result.matched_sources : [];
  const donneesTest = result.analysis_mode === 'fixture-dev';

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* En-tête cliquable */}
      <button
        type="button"
        onClick={() => setOuvert((v) => !v)}
        aria-expanded={ouvert}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-slate-50 dark:bg-slate-900/40 hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors text-left"
      >
        <span className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">🇪🇺 Conformité européenne</span>
          <EUComplianceBadge result={result} />
          {typeof result.confidence === 'number' && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              confiance {Math.round(result.confidence * 100)} %
            </span>
          )}
          {donneesTest && (
            <span className="text-[10px] uppercase tracking-wide font-semibold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
              Données de test
            </span>
          )}
        </span>
        <span className={`text-slate-500 transition-transform ${ouvert ? 'rotate-180' : ''}`} aria-hidden="true">
          ▾
        </span>
      </button>

      {ouvert && (
        <div className="px-4 py-4 space-y-4 text-sm">
          {/* Directive de référence */}
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
              Directive de référence
            </h4>
            {sources.length === 0 ? (
              <p className="text-xs text-slate-500">Aucune source européenne rapprochée.</p>
            ) : (
              <ul className="space-y-2">
                {sources.map((s, i) => (
                  <li
                    key={`${s.celex_id}-${s.article_id}-${i}`}
                    className="rounded border border-slate-200 dark:border-slate-700 px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-3 flex-wrap">
                      <span className="font-medium text-slate-800 dark:text-slate-100">
                        {lienEurLex(s.celex_id) ? (
                          <a
                            href={lienEurLex(s.celex_id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline underline-offset-2 hover:text-blue-700 dark:hover:text-blue-300"
                          >
                            CELEX {s.celex_id}
                          </a>
                        ) : (
                          'Directive'
                        )}
                        {s.article_id ? ` · art. ${s.article_id}` : ''}
                      </span>
                      {typeof s.score === 'number' && (
                        <span className="text-xs text-slate-500" title="Similarité vectorielle avec l'amendement">
                          similarité {Math.round(s.score * 100)} %
                        </span>
                      )}
                    </div>
                    {s.title && <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">{s.title}</p>}
                    {s.text_snippet && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 italic border-l-2 border-slate-300 dark:border-slate-600 pl-2">
                        {s.text_snippet}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Analyse comparative */}
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
              Analyse comparative
            </h4>
            <p className="text-slate-700 dark:text-slate-200 leading-relaxed">
              {result.delta_summary ? surligner(result.delta_summary) : '—'}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2">
              <mark className="bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200 rounded px-0.5 font-semibold">seuil chiffré</mark>
              {' '}
              <mark className="bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200 rounded px-0.5">charge administrative</mark>
              {' '}— repères visuels, à vérifier par l'administrateur.
            </p>
          </section>

          <p className="text-[11px] text-slate-400 dark:text-slate-500">
            {result.analysis_mode ? `Mode : ${result.analysis_mode}` : ''}
            {result.timestamp ? ` · ${new Date(result.timestamp).toLocaleString('fr-FR')}` : ''}
          </p>
        </div>
      )}
    </div>
  );
}
