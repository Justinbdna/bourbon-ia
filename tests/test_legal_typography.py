r"""
tests/test_legal_typography.py — Tests unitaires de la Partie 2 du socle légistique
===================================================================================
Couvre :
  1. Chantier 1 : Normalisateur typographique DILA (`api/legal_typography.py`)
     - Typographie des articles et des divisions (Charte JO p. 8-10)
     - Formulation officielle des subdivisions en hiérarchie ascendante
     - Micro-typographie, espaces insécables (\u00A0 / \~) et guillemets à 2 niveaux
  2. Chantier 2 : Détecteur de dispositions non normatives (« neutrons législatifs », Art. 6 DDHC)
  3. Chantier 3 : Générateur d'export Préjaune parlementaire (`api/export_rtf.py` et route `GET /api/v2/export-prejaune`)
"""

from fastapi.testclient import TestClient
import pytest

from api.export_rtf import generer_prejaune_rtf, rtf_escape
from api.index import app
from api.legal_chapeau_parser import (
    MOTIF_NON_NORMATIF_DEFAUT,
    detecter_dispositions_non_normatives,
    parse_chapeau,
)
from api.legal_typography import (
    NBSP,
    convertir_espaces_insecables_rtf,
    normaliser_subdivision,
    normaliser_typographie_jo,
)


# ──────────────────────────────────────────────────────────────────────────
# 1. CHANTIER 1 : Subdivisions et hiérarchie ascendante (Guide de légistique)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "entree,attendu",
    [
        ("Article 5-III", "Le III de l'article 5"),
        ("Art. 5-III", "Le III de l'article 5"),
        ("Article 15-II-6°", "Le 6° du II de l'article 15"),
        ("Art. 15-II-6°", "Le 6° du II de l'article 15"),
        ("Article 20-I-3°-f", "Le f du 3° du I de l'article 20"),
        ("Art. 20-I-3°-f", "Le f du 3° du I de l'article 20"),
        ("Art. 2 (alinéa 4)", "Le quatrième alinéa de l'article 2"),
        ("Article 2 (alinéa 4)", "Le quatrième alinéa de l'article 2"),
        ("Art. 1er (alinéa 1)", "Le premier alinéa de l'article 1er"),
        ("Art. 8 (alinéa 10)", "Le dixième alinéa de l'article 8"),
        ("Art. 5-II (alinéa 3)", "Le troisième alinéa du II de l'article 5"),
    ],
)
def test_normaliser_subdivision_hierarchie_ascendante(entree: str, attendu: str):
    assert normaliser_subdivision(entree) == attendu


def test_normaliser_subdivision_en_contexte_de_phrase():
    texte = "À l'article 15-II-6°, le montant est doublé."
    res = normaliser_subdivision(texte)
    assert "Au 6° du II de l'article 15" in res


# ──────────────────────────────────────────────────────────────────────────
# 2. CHANTIER 1 : Typographie des articles et ordinaux (Charte JO p. 8-10)
# ──────────────────────────────────────────────────────────────────────────


def test_typographie_articles_debut_alinea_et_au_long():
    # En début d'alinéa : Art. 1er. et Art. 2. avec point final et sans 1ier / 1ère / 2ème
    assert normaliser_typographie_jo("Art. 1ier") == f"Art.{NBSP}1er."
    assert normaliser_typographie_jo("Art. 1ère.") == f"Art.{NBSP}1er."
    assert normaliser_typographie_jo("Art. 2ème") == f"Art.{NBSP}2."
    assert normaliser_typographie_jo("Art. 2") == f"Art.{NBSP}2."

    # Articles de lois au long : Article 1er et Article unique
    assert normaliser_typographie_jo("Article 1ier") == "Article 1er"
    assert normaliser_typographie_jo("Article 1ère") == "Article 1er"
    assert normaliser_typographie_jo("Article premier") == "Article 1er"
    assert normaliser_typographie_jo("Art. unique") == "Article unique"
    assert normaliser_typographie_jo("Article unique") == "Article unique"

    # Correction des ordinaux fautifs dans le corps du texte
    res_ord = normaliser_typographie_jo("La 1ère séance et la 2ème lecture du 3ème alinéa.")
    assert "1re" in res_ord
    assert "2e" in res_ord
    assert "3e" in res_ord
    assert "1ère" not in res_ord
    assert "2ème" not in res_ord


# ──────────────────────────────────────────────────────────────────────────
# 3. CHANTIER 1 : Micro-typographie, espaces insécables et guillemets
# ──────────────────────────────────────────────────────────────────────────


def test_espaces_insecables_ponctuation_et_unites():
    texte = "À l'alinéa 3, substituer au montant : 10 000 € le taux : 15 % ; séance à 12 h 30 pour 50 ans ! Est-ce conforme ?"
    res = normaliser_typographie_jo(texte)

    # Ponctuation double précédée d'une espace insécable
    assert f"{NBSP}:" in res
    assert f"{NBSP};" in res
    assert f"{NBSP}!" in res
    assert f"{NBSP}?" in res

    # Nombres et symboles / unités
    assert f"10{NBSP}000{NBSP}€" in res
    assert f"15{NBSP}%" in res
    assert f"12{NBSP}h{NBSP}30" in res
    assert f"50{NBSP}ans" in res


def test_espaces_insecables_abreviation_article():
    res1 = normaliser_typographie_jo("Art. 1er. — Le présent code s'applique conformément à l'art. 2.")
    assert f"Art.{NBSP}1er." in res1
    assert f"art.{NBSP}2." in res1

    # Conversion RTF des espaces insécables en \~
    rtf_str = convertir_espaces_insecables_rtf(res1)
    assert r"Art.\~1er." in rtf_str
    assert r"art.\~2." in rtf_str


def test_normalisation_guillemets_deux_niveaux():
    # Guillemets imbriqués : 1er niveau «\u00A0...\u00A0», 2e niveau "..."
    texte_imbrique = "« L'article dispose que « la République garantit » ce principe. »"
    res = normaliser_typographie_jo(texte_imbrique)
    assert res.startswith(f"«{NBSP}")
    assert res.endswith(f"{NBSP}»")
    assert '"la République garantit"' in res

    # Guillemets droits simples convertis en guillemets français au 1er niveau
    texte_droit = 'Remplacer le mot "ancien" par le mot "nouveau".'
    res_droit = normaliser_typographie_jo(texte_droit)
    assert f"«{NBSP}ancien{NBSP}»" in res_droit
    assert f"«{NBSP}nouveau{NBSP}»" in res_droit


# ──────────────────────────────────────────────────────────────────────────
# 4. CHANTIER 2 : Détection des dispositions non normatives (« neutrons législatifs »)
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "dispositif_neutron",
    [
        "L'État a pour objectif de promouvoir le bien-être numérique des citoyens.",
        "La politique publique favorise par son action l'émergence de projets locaux.",
        "Le Gouvernement veille à ce que chaque territoire dispose d'une offre culturelle.",
        "La Nation reconnaît le rôle essentiel des bénévoles associatifs.",
        "Le service public se donne pour mission de renforcer la cohésion sociale.",
        "L'autorité administrative encourage les initiatives visant à développer le covoiturage.",
        "Le présent dispositif a vocation à inspirer les bonnes pratiques professionnelles.",
    ],
)
def test_detection_neutrons_legislatifs(dispositif_neutron: str):
    audit = detecter_dispositions_non_normatives(dispositif_neutron)
    assert audit["alerte_non_normatif"] is True
    assert audit["motif_non_normatif"] == MOTIF_NON_NORMATIF_DEFAUT

    chapeau = parse_chapeau(dispositif_neutron)
    assert chapeau.alerte_non_normatif is True
    assert chapeau.motif_non_normatif == MOTIF_NON_NORMATIF_DEFAUT


def test_dispositif_normatif_prescriptif_sans_alerte():
    dispositif = "À l'alinéa 3, substituer au montant : « 10 000 € » le montant : « 20 000 € »."
    audit = detecter_dispositions_non_normatives(dispositif)
    assert audit["alerte_non_normatif"] is False
    assert audit["motif_non_normatif"] is None


# ──────────────────────────────────────────────────────────────────────────
# 5. CHANTIER 3 : Générateur d'export Préjaune RTF et route API
# ──────────────────────────────────────────────────────────────────────────


def test_generation_prejaune_rtf_ordonnancement_et_balises():
    amendements = [
        {
            "numero": "40",
            "article": "Article 1er",
            "auteurs": ["M. Martin"],
            "groupe_politique": "DR",
            "dispositif": "Après l'article 1er, insérer l'article suivant : « La Nation reconnaît la valeur du sport. »",
            "expose_sommaire": "Article additionnel déclaratif.",
        },
        {
            "numero": "15",
            "article": "Article 1er",
            "auteurs": ["Mme Bernard"],
            "groupe_politique": "SOC",
            "dispositif": "À l'alinéa 3, supprimer les mots : « à hauteur de 15 % ».",
            "expose_sommaire": "Amendement de précision sur l'alinéa 3.",
        },
        {
            "numero": "2",
            "article": "Article 1er",
            "auteurs": ["M. Dupont"],
            "groupe_politique": "EPR",
            "dispositif": "Supprimer cet article.",
            "expose_sommaire": "Suppression totale de l'article 1er.",
        },
        {
            "numero": "8",
            "article": "Article 1er",
            "auteurs": ["Mme Leroy"],
            "groupe_politique": "LFI-NFP",
            "dispositif": "Supprimer cet article.",
            "expose_sommaire": "Amendement identique de suppression.",
        },
        {
            "numero": "22",
            "article": "Article 1er",
            "auteurs": ["M. Moreau"],
            "groupe_politique": "EcoS",
            "dispositif": "Compléter cet article par l'alinéa suivant : « Un crédit d'impôt de 10 000 € est accordé. »",
            "expose_sommaire": "Création d'un crédit d'impôt non gagé.",
        },
    ]

    rtf = generer_prejaune_rtf(amendements, titre_texte="Projet de loi de finances")

    # 1. Balises RTF valides
    assert rtf.startswith(r"{\rtf1\ansi")
    assert r"{\fonttbl" in rtf
    assert r"\pard" in rtf
    assert r"\par" in rtf
    assert r"\~" in rtf
    assert rtf.strip().endswith("}")

    # 2. Respect strict de l'ordre du dérouleur :
    #    N° 2 et N° 8 (Suppression article, priorité 10) -> N° 15 (Alinéa 3, priorité 60) -> N° 22 (Compléter article, priorité 800) -> N° 40 (Article additionnel, priorité 900)
    pos_2 = rtf.index("Amendement n\\u176?\\~2 ")
    pos_8 = rtf.index("Amendement n\\u176?\\~8 ")
    pos_15 = rtf.index("Amendement n\\u176?\\~15 ")
    pos_22 = rtf.index("Amendement n\\u176?\\~22 ")
    pos_40 = rtf.index("Amendement n\\u176?\\~40 ")

    assert pos_2 < pos_8 < pos_15 < pos_22 < pos_40

    # 3. Statut Identique avec liste des jumeaux, Cible légistique et Alertes en marge
    assert "Identique (amendements jumeaux" in rtf
    assert "SUPPRIMER sur Alin\\u233?a 3" in rtf
    assert "ARTICLE 40" in rtf
    assert "PORT\\u201?E NORMATIVE FAIBLE (Art. 6 DDHC)" in rtf
    assert r"10\~000\~\u8364?" in rtf
    assert r"15\~%" in rtf


def test_endpoint_get_export_prejaune():
    client = TestClient(app)
    response = client.get("/api/v2/export-prejaune")
    assert response.status_code == 200
    assert "application/rtf" in response.headers.get("content-type", "")
    assert "prejaune_seance.rtf" in response.headers.get("content-disposition", "")
    assert response.text.startswith(r"{\rtf1\ansi")
    assert r"\pard" in response.text
