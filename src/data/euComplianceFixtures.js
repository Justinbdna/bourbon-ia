/**
 * Données de TEST pour la mise en page des badges de conformité UE.
 *
 * ⚠️  DÉVELOPPEMENT UNIQUEMENT — chargées dynamiquement par App.jsx seulement
 * si `import.meta.env.DEV` est vrai ET que l'URL contient `?demoUE`. Le build
 * de production remplace `import.meta.env.DEV` par `false` : ce fichier n'est
 * jamais servi sur la démo publique.
 *
 * Ces verdicts sont FICTIFS. Ils servent à vérifier le rendu des trois états
 * tant que SurtranspositionChecker n'est pas branché à l'API. Ils portent
 * `analysis_mode: "fixture-dev"`, ce qui affiche un bandeau « Données de test »
 * dans le panneau de détail.
 *
 * Forme : identique à SurtranspositionAnalysisResult
 * (src/services/analysis/surtransposition_checker.py).
 */

const MAINTENANT = new Date().toISOString();

const FIXTURES = [
  {
    status: 'STRICT_TRANSPOSITION',
    confidence: 0.91,
    delta_summary:
      "Le dispositif reprend l'obligation d'évaluation environnementale prévue par la directive, sans exigence supplémentaire.",
    matched_sources: [
      {
        celex_id: '32011L0092',
        article_id: '4',
        title: "Directive 2011/92/UE — évaluation des incidences de certains projets sur l'environnement",
        score: 0.88,
        text_snippet: '(extrait reformulé pour test) Les projets énumérés font l’objet d’une évaluation.',
      },
    ],
    target_article: 'Article 5',
    analysis_mode: 'fixture-dev',
    timestamp: MAINTENANT,
  },
  {
    status: 'NATIONAL_ADDITION',
    confidence: 0.74,
    delta_summary:
      "Ajoute une déclaration préalable en préfecture, dans la marge d'appréciation laissée aux États membres.",
    matched_sources: [
      {
        celex_id: '32014L0024',
        article_id: '18',
        title: 'Directive 2014/24/UE — passation des marchés publics',
        score: 0.71,
        text_snippet: '(extrait reformulé pour test) Les pouvoirs adjudicateurs traitent les opérateurs sur un pied d’égalité.',
      },
    ],
    target_article: 'Article 11',
    analysis_mode: 'fixture-dev',
    timestamp: MAINTENANT,
  },
  {
    status: 'SURTRANSPOSITION_ALERT',
    confidence: 0.83,
    delta_summary:
      "Abaisse le seuil d'application de 50 salariés à 10 salariés et impose un rapport annuel ainsi qu'une certification par un organisme agréé, exigences absentes de la directive.",
    matched_sources: [
      {
        celex_id: '32014L0024',
        article_id: '4',
        title: 'Directive 2014/24/UE — passation des marchés publics',
        score: 0.79,
        text_snippet: '(extrait reformulé pour test) La directive s’applique aux marchés dont la valeur atteint les seuils fixés.',
      },
      {
        celex_id: '32000L0060',
        article_id: '11',
        title: 'Directive 2000/60/CE — cadre pour une politique communautaire dans le domaine de l’eau',
        score: 0.52,
        text_snippet: '(extrait reformulé pour test) Chaque État membre établit un programme de mesures.',
      },
    ],
    target_article: 'Article 11',
    analysis_mode: 'fixture-dev',
    timestamp: MAINTENANT,
  },
];

/**
 * Attache un verdict fictif aux trois premiers amendements (un par état).
 * Modifie la liste en place et la renvoie.
 */
export function appliquerFixturesUE(amendements) {
  if (!Array.isArray(amendements)) return amendements;
  FIXTURES.forEach((fixture, i) => {
    if (amendements[i]) amendements[i].eu_compliance = fixture;
  });
  return amendements;
}
