"""YouTube Data API v3 で関連動画を検索するモジュール."""

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"


def search_youtube(query: str, max_results: int = 1) -> list[str]:
    """YouTube Data APIで動画を検索し、URLリストを返す.

    Args:
        query: 検索クエリ（例: "食堂ごはんと 大分"）
        max_results: 最大取得件数

    Returns:
        YouTube動画URLのリスト。APIキー未設定や取得失敗時は空リスト。
    """
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.info("YOUTUBE_API_KEY が未設定のためYouTube検索をスキップ")
        return []

    params = {
        "part": "snippet",
        "q": f"{query} 大分",
        "type": "video",
        "maxResults": max_results,
        "regionCode": "JP",
        "relevanceLanguage": "ja",
        "key": api_key,
    }

    try:
        response = requests.get(YOUTUBE_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        urls = []
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id:
                urls.append(f"https://www.youtube.com/watch?v={video_id}")
        return urls
    except requests.RequestException:
        logger.exception("YouTube API検索に失敗: %s", query)
        return []


def extract_shop_name(title: str) -> str:
    """記事タイトルから店名を抽出する.

    『店名』の鉤括弧内を取得。なければタイトルそのものを返す。

    Args:
        title: 記事タイトル

    Returns:
        店名文字列
    """
    match = re.search(r"[『「](.+?)[』」]", title)
    if match:
        return match.group(1)
    return title
