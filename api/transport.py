"""
api/transport.py — Middlewares de transport (compression, serveur local)
========================================================================
1. DecompressionRequetes : le navigateur compresse (gzip) les gros envois
   d'amendements. Sur Vercel, chaque requête est limitée à 4,5 Mo : sans
   compression, une liasse de plus de ~600 amendements était refusée
   (HTTP 413 FUNCTION_PAYLOAD_TOO_LARGE). Le corps est décompressé ici avant
   d'atteindre les routes, avec un plafond pour se protéger des « bombes zip ».

2. ReseauPriveAutorise : permet au site en ligne (https://bourbon-ia.vercel.app)
   d'appeler un serveur Bourbon.IA lancé sur le poste de l'utilisateur
   (http://localhost:8000), option « Serveur Bourbon.IA : sur cet ordinateur ».
   Chrome exige pour cela l'en-tête `Access-Control-Allow-Private-Network`
   en réponse à la requête préalable (Private Network Access).

La compression des RÉPONSES est assurée par le GZipMiddleware de Starlette
(cf. api/index.py).
"""

from __future__ import annotations

import json
import zlib

# Corps décompressé maximal : une liasse de 2 000 amendements pèse ~15 Mo.
MAX_CORPS_DECOMPRESSE = 50 * 1024 * 1024


async def _repondre_erreur(send, statut: int, message: str) -> None:
    corps = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": statut,
        "headers": [(b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(corps)).encode())],
    })
    await send({"type": "http.response.body", "body": corps})


class DecompressionRequetes:
    """Décompresse les requêtes envoyées avec `Content-Encoding: gzip`."""

    def __init__(self, app, max_taille: int = MAX_CORPS_DECOMPRESSE):
        self.app = app
        self.max_taille = max_taille

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        en_tetes = dict(scope.get("headers") or [])
        if en_tetes.get(b"content-encoding", b"").strip().lower() != b"gzip":
            return await self.app(scope, receive, send)

        # Lecture complète du corps compressé
        morceaux = []
        while True:
            message = await receive()
            morceaux.append(message.get("body", b""))
            if not message.get("more_body"):
                break

        # Décompression bornée : on s'arrête dès que le plafond est dépassé.
        decompresseur = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            corps = decompresseur.decompress(b"".join(morceaux), self.max_taille + 1)
        except zlib.error:
            return await _repondre_erreur(send, 400, "Corps de requête gzip invalide.")
        if len(corps) > self.max_taille or decompresseur.unconsumed_tail:
            return await _repondre_erreur(send, 413, "Liasse trop volumineuse (plus de 50 Mo une fois décompressée).")

        # La suite de la chaîne voit une requête JSON ordinaire.
        nouveaux = [(k, v) for k, v in scope["headers"] if k not in (b"content-encoding", b"content-length")]
        nouveaux.append((b"content-length", str(len(corps)).encode()))
        scope = dict(scope, headers=nouveaux)
        envoye = False

        async def recevoir():
            nonlocal envoye
            if envoye:
                return await receive()  # http.disconnect éventuel
            envoye = True
            return {"type": "http.request", "body": corps, "more_body": False}

        return await self.app(scope, recevoir, send)


class ReseauPriveAutorise:
    """Ajoute `Access-Control-Allow-Private-Network: true` aux requêtes préalables qui le demandent."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "OPTIONS":
            return await self.app(scope, receive, send)
        en_tetes = dict(scope.get("headers") or [])
        if en_tetes.get(b"access-control-request-private-network", b"").lower() != b"true":
            return await self.app(scope, receive, send)

        async def envoyer(message):
            if message["type"] == "http.response.start":
                message = dict(message, headers=list(message.get("headers") or [])
                               + [(b"access-control-allow-private-network", b"true")])
            await send(message)

        return await self.app(scope, receive, envoyer)
