import logging

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.mistral_client import (
    MistralError,
    MistralInvalidJSONError,
    call_mistral_for_classification,
)
from app.models import ClassifyRequest, ClassifyResponse
from app.prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger("amendements.classify")

router = APIRouter()


@router.post("/classify", response_model=ClassifyResponse)
async def classify_amendments(
    request: ClassifyRequest,
    settings: Settings = Depends(get_settings),
) -> ClassifyResponse:
    """
    Reçoit une liste d'amendements et renvoie leur classement (rang, groupe,
    chutes détectées, justification), calculé par le modèle Mistral selon la
    théorie de classement de l'Assemblée nationale.
    """
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(request)

    try:
        raw_result = await call_mistral_for_classification(settings, system_prompt, user_prompt)
    except MistralInvalidJSONError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except MistralError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Garde-fou côté serveur : si le modèle a jugé la requête hors-sujet
    # (cf. consigne de périmètre dans le system prompt), on renvoie une 422
    # explicite plutôt que de tenter de forcer le schéma de classement.
    if isinstance(raw_result, dict) and raw_result.get("error") == "hors_sujet":
        raise HTTPException(
            status_code=422,
            detail=raw_result.get(
                "message", "Cette API ne traite que le classement d'amendements législatifs."
            ),
        )

    submitted_ids = {a.id for a in request.amendements}

    try:
        result = ClassifyResponse(modele_utilise=settings.MISTRAL_MODEL, **raw_result)
    except Exception as exc:  # validation Pydantic
        logger.error("Réponse Mistral non conforme au schéma attendu : %s", raw_result)
        raise HTTPException(
            status_code=502,
            detail=f"La réponse du modèle ne respecte pas le format attendu : {exc}",
        ) from exc

    # Vérifie que chaque amendement soumis a bien reçu un classement, et
    # qu'aucun id inconnu n'a été inventé par le modèle.
    returned_ids = {c.id for c in result.classement}
    missing = submitted_ids - returned_ids
    unknown = returned_ids - submitted_ids

    if missing:
        result.avertissements.append(
            f"Amendements non classés par le modèle : {', '.join(sorted(missing))}"
        )
    if unknown:
        result.avertissements.append(
            f"Le modèle a renvoyé des identifiants inconnus, ignorés : {', '.join(sorted(unknown))}"
        )
        result.classement = [c for c in result.classement if c.id in submitted_ids]

    return result
