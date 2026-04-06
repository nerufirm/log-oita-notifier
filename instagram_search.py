"""Google Custom Search API でInstagramアカウントを検索するモジュール."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


def search_instagram(query: str) -> list[str]:
    """Google Custom Search APIでInstagramの関連ページを検索する.

    Args:
        query: 検索クエリ（例: "食堂ごはんと 大分"）

    Returns:
        Instagram URLのリスト。APIキー未設定や取得失敗時は空リスト。
    """
    api_key = os.environ.get("GOOGLE_SEARCH_API_KEY", "")
    search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID", "")

    if not api_key or not search_engine_id:
        logger.info("Google検索APIキーが未設定のためInstagram検索をスキップ")
        return []

    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": f"{query} 大分 site:instagram.com",
        "num": 3,
    }

    try:
        response = requests.get(GOOGLE_SEARCH_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        urls = []
        for item in data.get("items", []):
            link = item.get("link", "")
            if "instagram.com" in link:
                urls.append(link)
        return urls
    except requests.RequestException:
        logger.exception("Google検索でInstagram検索に失敗: %s", query)
        return []
