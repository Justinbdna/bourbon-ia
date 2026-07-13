import re
import logging

def extraire_action_et_niveau(texte: str):
    """
    Parse le "chapeau" de l'amendement pour extraire la priorité d'action
    selon la Théorie du classement de l'Assemblée nationale.
    
    Hiérarchie stricte du classement déterministe :
    1. Suppression de l'article (impact maximal, fait tomber les autres)
    2. Rédaction globale de l'article
    3. Suppression de l'alinéa
    4. Rédaction globale de l'alinéa
    5. Point d'impact plus restreint (mot, phrase, substitution)
    
    Retourne un tuple (priorite: int, type_action: str)
    """
    texte_lower = texte.lower().strip()
    
    # 1. Suppression de l'article
    if texte_lower.startswith("supprimer cet article") or texte_lower.startswith("supprimer l'article"):
        return (1, "article_suppression")
    
    # 2. Rédaction globale de l'article
    if texte_lower.startswith("rédiger ainsi cet article") or texte_lower.startswith("rédiger ainsi l'article"):
        return (2, "article_redaction")
    
    # 3. Suppression de l'alinéa
    if "supprimer l'alinéa" in texte_lower or "supprimer les alinéas" in texte_lower:
        # On assume ici que c'est l'action principale du chapeau
        return (3, "alinea_suppression")
    
    # 4. Rédaction globale de l'alinéa
    if "rédiger ainsi l'alinéa" in texte_lower or "rédiger ainsi cet alinéa" in texte_lower:
        return (4, "alinea_redaction")
        
    # 5. Point d'impact restreint (substitution de mots, insertion, compléter...)
    # Les verbes : Substituer, Insérer, Compléter, etc.
    return (5, "restreint")

def trier_amendements(liste_amendements: list[dict]) -> list[dict]:
    """
    Moteur de tri déterministe.
    Reçoit un JSON de vrais amendements et applique la doctrine de classement.
    Ce tri est mécanique et strictement sans IA pour garantir le respect 
    des procédures de l'Assemblée nationale.
    """
    def cle_de_tri(amendement):
        texte = amendement.get("texte", "")
        
        # ÉTAPE 1 : Détermination de la priorité d'impact
        priorite, _ = extraire_action_et_niveau(texte)
        
        # Note : Dans un système complet, on extrairait également via regex 
        # le numéro de l'article et de l'alinéa pour trier d'abord par (article_id, alinea_id).
        # Le tri secondaire se fait sur la priorité (1 à 5).
        # Ici on se concentre sur l'illustration de la priorité d'action métier.
        
        # ÉTAPE 2 : Classement stable par numéro d'identifiant en cas d'égalité de priorité
        numero = amendement.get("numero", "")
        
        return (priorite, numero)

    # Tri Python rapide et fiable (complexité O(n log n))
    amendements_tries = sorted(liste_amendements, key=cle_de_tri)
    
    logging.info(f"Tri mécanique terminé pour {len(liste_amendements)} amendements.")
    return amendements_tries
