"""Gemini APIでInstagramアカウントを検索するモジュール."""

import logging
import re

from google import genai

logger = logging.getLogger(__name__)


def search_instagram(query: str, gemini_client: genai.Client | None = None) -> list[str]:
    """Gemini APIで店名からInstagramアカウントURLを推測する.

    Args:
        query: 店名（例: "食堂ごはんと"）
        gemini_client: Gemini APIクライアント

    Returns:
        Instagram URLのリスト。取得失敗時は空リスト。
    """
    if gemini_client is None:
        logger.info("Geminiクライアント未設定のためInstagram検索をスキップ")
        return []

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=(
                f"「{query}」という大分県のお店のInstagramアカウントURLを教えてください。"
                "確実に存在するURLのみを1つ返してください。"
                "わからない場合は「なし」とだけ答えてください。"
                "URL以外の説明は不要です。"
            ),
        )
        text = response.text.strip()

        if "なし" in text or "わかりません" in text or "不明" in text:
            return []

        urls = re.findall(r"https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?", text)
        return urls[:1]
    except Exception:
        logger.exception("Gemini APIでInstagram検索に失敗: %s", query)
        return []
