/**
 * Utilitaires d'export standardisé au format Éloi (Assemblée nationale / LexImpact)
 * Permet l'interopérabilité directe avec les outils de l'hémicycle et des commissions.
 */

export function buildEloiPayload(amendments = []) {
  return {
    format: "ELOI_AN_JSON_v1",
    source: "Bourbon.IA - Assistant Législatif Souverain",
    date_export: new Date().toISOString(),
    total_amendements: amendments.length,
    amendements: amendments.map((a, index) => {
      const statutFinal = a.statut || a.resultat_ia?.statut || "Non classé"
      return {
        index_seance: index + 1,
        id: a.id || a.uid,
        numero: a.numero,
        rectification: a.rectification || null,
        article: a.article,
        point_impact: {
          type: a.point_impact?.type || null,
          numero_alinea: a.point_impact?.numero_alinea || a.alinea || null,
        },
        auteur: {
          nom: a.auteur_nom || (a.auteurs ? a.auteurs[0] : "Inconnu"),
          prenom: a.auteur_prenom || null,
          trigramme: a.auteur_trigramme || null,
          groupe: a.groupe_politique || a.groupe || a.groupRef || "Non inscrit",
          role: a.role || (a.est_rapporteur ? "Rapporteur" : (a.est_gouvernement ? "Gouvernement" : "Député")),
        },
        ordre_de_seance: {
          statut_qualification: statutFinal,
          priorite_appel_art98: a.priorite_appel || 5,
          libelle_priorite: a.libelle_appel || "5. Insertion / Adjonction",
          est_tombant: Boolean(a.tombe_si_adoption || a.alerte_tombant),
          alerte_tombant: a.alerte_tombant || null,
          parent_suppression_numero: a.parent_suppression_numero || null,
          est_cavalier_art45: Boolean(a.est_cavalier_art45 || a.alerte_art45),
          alerte_art45: a.alerte_art45 || null,
          est_gage_art40: Boolean(a.est_gage),
          arbitre_manuellement: Boolean(a.arbitre_manuellement),
          date_arbitrage: a.date_arbitrage || null,
        },
        textes: {
          dispositif: a.dispositif || "",
          expose_sommaire: a.expose_sommaire || "",
          texte_loi_reference: a.texte_loi_reference || null,
        },
        analyse_ia: a.resultat_ia ? {
          statut_ia: a.resultat_ia.statut || null,
          intention_légistique: a.resultat_ia.analyse_intention || null,
          politique: a.resultat_ia.analyse_politique || null,
          niveau_confiance: a.resultat_ia.niveau_confiance ?? null,
          cached: Boolean(a.resultat_ia.cached),
        } : null,
      }
    }),
  }
}

export function downloadEloiJson(amendments, filename = "amendements_eloi.json") {
  const payload = buildEloiPayload(amendments)
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
