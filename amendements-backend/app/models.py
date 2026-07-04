from typing import Literal, Optional

from pydantic import BaseModel, Field

PointImpactType = Literal[
    "suppression_article",
    "redaction_globale_article",
    "suppression_alinea",
    "redaction_globale_alinea",
    "point_restreint",
    "article_entier",
]

GroupeType = Literal[
    "discussion_commune",
    "identiques",
    "doublon",
    "additionnel",
    "isole",
]


class TexteExamine(BaseModel):
    titre: Optional[str] = None
    lecture: Optional[str] = None
    numero_texte: Optional[str] = None


class PointImpact(BaseModel):
    type: Optional[PointImpactType] = None
    alinea: Optional[int] = None


class Amendement(BaseModel):
    """Schéma d'un amendement en entrée — doit rester aligné avec le JSON produit par le front."""

    id: str
    article: str
    numero: str
    rectification: Optional[str] = None
    date_depot: Optional[str] = None
    texte_examine: Optional[TexteExamine] = None
    auteurs: list[str] = Field(default_factory=list)
    rapporteur: bool = False
    avis_commission: Optional[str] = None
    avis_gouvernement: Optional[str] = None
    dispositif: str
    expose_sommaire: Optional[str] = None
    point_impact: Optional[PointImpact] = None
    categorie: Optional[str] = None


class ClassifyRequest(BaseModel):
    amendements: list[Amendement]

    def model_post_init(self, __context) -> None:
        if len(self.amendements) == 0:
            raise ValueError("La liste d'amendements ne peut pas être vide.")


class Groupe(BaseModel):
    type: GroupeType = "isole"
    groupe_id: Optional[str] = None


class AmendementClasse(BaseModel):
    """Résultat de classement pour un amendement donné."""

    id: str
    rang: int
    groupe: Groupe
    justification: str


class ClassifyResponse(BaseModel):
    classement: list[AmendementClasse]
    avertissements: list[str] = Field(default_factory=list)
    modele_utilise: str
