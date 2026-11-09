"""
tests/test_transport.py — Compression des échanges et accès depuis le site en ligne
===================================================================================
Requêtes gzip décompressées (avec plafond), réponses compressées, et en-tête
Private Network Access pour le mode « serveur Bourbon.IA sur cet ordinateur ».
"""

import gzip
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from api.index import app
from api.transport import DecompressionRequetes

client = TestClient(app)

AMENDEMENT = {"id": "AM-1", "numero": "1", "article": "Article 5", "dispositif": "Supprimer cet article."}


def test_requete_gzip_decompressee():
    corps = gzip.compress(json.dumps({"amendements": [AMENDEMENT] * 50}).encode())

    r = client.post("/api/normalize", content=corps,
                    headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})

    assert r.status_code == 200
    assert len(r.json()) == 50


def test_gzip_invalide_refuse():
    r = client.post("/api/normalize", content=b"pas du gzip",
                    headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})

    assert r.status_code == 400


def test_plafond_de_decompression():
    mini = FastAPI()

    @mini.post("/echo")
    async def echo(request: Request):
        return {"taille": len(await request.body())}

    mini.add_middleware(DecompressionRequetes, max_taille=1000)
    petit = TestClient(mini)

    ok = petit.post("/echo", content=gzip.compress(b"a" * 900), headers={"Content-Encoding": "gzip"})
    trop = petit.post("/echo", content=gzip.compress(b"a" * 5000), headers={"Content-Encoding": "gzip"})

    assert ok.json() == {"taille": 900}
    assert trop.status_code == 413


def test_reponse_compressee():
    r = client.post("/api/normalize", json={"amendements": [AMENDEMENT] * 50},
                    headers={"Accept-Encoding": "gzip"})

    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "gzip"


def test_acces_reseau_prive_depuis_le_site_en_ligne():
    r = client.options("/api/health", headers={
        "Origin": "https://bourbon-ia.vercel.app",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Private-Network": "true",
    })

    assert r.headers.get("access-control-allow-private-network") == "true"
    assert r.headers.get("access-control-allow-origin") == "https://bourbon-ia.vercel.app"
