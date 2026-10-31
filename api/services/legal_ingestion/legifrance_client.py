"""
Légifrance API Client (PISTE Portal Interface)
=============================================
Provides access to French national baseline law (Codes, articles de loi)
via the PISTE API (https://api.piste.gouv.fr/dila/legifrance/lf-engine).
Supports air-gapped local fallback when PISTE credentials are not provided.
"""

from __future__ import annotations
import os
import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

PISTE_OAUTH_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
LEGIFRANCE_API_BASE = "https://api.piste.gouv.fr/dila/legifrance/lf-engine"


class LegifranceClient:
    """API Client for fetching French legal articles from Légifrance PISTE Portal."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        api_base_url: str = LEGIFRANCE_API_BASE
    ):
        self.client_id = client_id or os.getenv("PISTE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("PISTE_CLIENT_SECRET")
        self.api_base_url = api_base_url
        self._access_token: Optional[str] = None

    def get_token(self, timeout: int = 5) -> Optional[str]:
        """Fetch OAuth2 token from PISTE portal if credentials are standard."""
        if not self.client_id or not self.client_secret:
            return None

        if self._access_token:
            return self._access_token

        try:
            res = requests.post(
                PISTE_OAUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "openid"
                },
                timeout=timeout
            )
            if res.status_code == 200:
                self._access_token = res.json().get("access_token")
                return self._access_token
        except Exception as e:
            logger.warning(f"Failed to obtain PISTE Légifrance OAuth token: {e}")

        return None

    def fetch_article(
        self,
        article_num: str,
        code_name: str = "Code du travail",
        timeout: int = 10,
        mock_fallback: bool = True
    ) -> Dict[str, Any]:
        """Fetch a specific French legal code article by article number and code name."""
        token = self.get_token(timeout=timeout)
        if token:
            try:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                payload = {
                    "id": article_num,
                    "code": code_name
                }
                res = requests.post(
                    f"{self.api_base_url}/consult/getArticle",
                    json=payload,
                    headers=headers,
                    timeout=timeout
                )
                if res.status_code == 200:
                    data = res.json()
                    article_data = data.get("article", {})
                    return {
                        "article_id": article_data.get("num", article_num),
                        "code_name": code_name,
                        "title": f"{code_name} - Article {article_data.get('num', article_num)}",
                        "content": article_data.get("texte", ""),
                        "source": "PISTE_LEGIFRANCE"
                    }
            except Exception as err:
                logger.warning(f"Légifrance API query failed for {article_num}: {err}")

        if mock_fallback:
            return self._generate_mock_article(article_num, code_name)

        return {
            "article_id": article_num,
            "code_name": code_name,
            "title": f"{code_name} - Article {article_num}",
            "content": "",
            "source": "PISTE_LEGIFRANCE"
        }

    def search_code_articles(
        self,
        query: str,
        code_name: str = "Code du travail",
        limit: int = 5,
        mock_fallback: bool = True
    ) -> List[Dict[str, Any]]:
        """Search national baseline articles matching a query within a legal code."""
        token = self.get_token()
        if token:
            try:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                payload = {
                    "searchField": query,
                    "code": code_name,
                    "pageSize": limit
                }
                res = requests.post(
                    f"{self.api_base_url}/search",
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    return [
                        {
                            "article_id": item.get("num", "Art."),
                            "code_name": code_name,
                            "title": item.get("title", f"{code_name} - {item.get('num')}"),
                            "content": item.get("extract", ""),
                            "source": "PISTE_LEGIFRANCE"
                        }
                        for item in results[:limit]
                    ]
            except Exception as err:
                logger.warning(f"Légifrance search failed: {err}")

        if mock_fallback:
            return [
                self._generate_mock_article("L. 1121-1", code_name),
                self._generate_mock_article("L. 1132-1", code_name)
            ]

        return []

    def _generate_mock_article(self, article_num: str, code_name: str) -> Dict[str, Any]:
        """Baseline French national legal code article mock for air-gapped local execution."""
        return {
            "article_id": article_num,
            "code_name": code_name,
            "title": f"{code_name} - Article {article_num}",
            "content": f"Nul ne peut apporter aux droits des personnes et aux libertés individuelles et collectives de restrictions qui ne seraient pas justifiées par la nature de la tâche à accomplir ni proportionnées au but recherché. (Ref: {article_num}).",
            "source": "MOCK_AIRGAPPED"
        }
