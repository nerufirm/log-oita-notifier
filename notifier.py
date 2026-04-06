"""LOG OITA 新着記事通知スクリプト.

https://log-oita.com/ のRSSフィードを監視し、
新着記事をGemini APIで20文字に要約してGmailに通知する。
"""

import json
import logging
import os
import re
import smtplib
import time
from email.mime.text import MIMEText
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

RSS_URL = "https://log-oita.com/feed/"
STATE_FILE = Path(__file__).parent / "last_seen.json"
MAX_SUMMARY_LENGTH = 20


def _load_last_seen() -> set[str]:
    """既に通知済みの記事URLを読み込む."""
    if not STATE_FILE.exists():
        return set()
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return set(data.get("seen_urls", []))


def _save_last_seen(seen_urls: set[str]) -> None:
    """通知済みの記事URLを保存する."""
    data = {"seen_urls": sorted(seen_urls)}
    STATE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _extract_text(html: str) -> str:
    """HTMLからプレーンテキストを抽出する."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text


GEMINI_MAX_RETRIES = 3
GEMINI_RETRY_WAIT_SECONDS = 40


def _summarize_with_gemini(client: genai.Client, text: str) -> str:
    """Gemini APIで記事を20文字以内に要約する.

    レート制限(429)エラー時は最大3回リトライする。
    """
    last_exception: Exception | None = None

    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"以下の記事を20文字以内の日本語で要約してください。要約のみを出力してください。\n\n{text}",
            )
            summary = response.text.strip()
            if len(summary) > MAX_SUMMARY_LENGTH:
                summary = summary[:MAX_SUMMARY_LENGTH - 1] + "…"
            return summary
        except Exception as exc:
            last_exception = exc
            status_code = getattr(exc, "status_code", None) or getattr(
                getattr(exc, "response", None), "status_code", None,
            )
            if status_code == 429 and attempt < GEMINI_MAX_RETRIES - 1:
                logger.warning(
                    "Gemini APIレート制限(429): %d/%d回目リトライまで%d秒待機",
                    attempt + 1,
                    GEMINI_MAX_RETRIES,
                    GEMINI_RETRY_WAIT_SECONDS,
                )
                time.sleep(GEMINI_RETRY_WAIT_SECONDS)
                continue
            break

    logger.exception("Gemini API要約に失敗しました", exc_info=last_exception)
    if len(text) <= MAX_SUMMARY_LENGTH:
        return text
    return text[:MAX_SUMMARY_LENGTH - 1] + "…"


def _fetch_new_articles(
    seen_urls: set[str], gemini_client: genai.Client,
) -> list[dict[str, str]]:
    """RSSフィードから新着記事を取得し、要約する."""
    try:
        rss_response = requests.get(RSS_URL, timeout=30)
        rss_response.raise_for_status()
    except requests.RequestException:
        logger.exception("RSSフィードの取得に失敗しました")
        return []

    feed = feedparser.parse(rss_response.content)

    new_articles = []
    for entry in feed.entries:
        url = entry.get("link", "")
        if not url or url in seen_urls:
            continue

        title = entry.get("title", "タイトルなし")

        content_html = ""
        if hasattr(entry, "content") and entry.content:
            content_html = entry.content[0].get("value", "")
        elif hasattr(entry, "description"):
            content_html = entry.description or ""

        plain_text = _extract_text(content_html)
        summary = _summarize_with_gemini(gemini_client, plain_text)

        new_articles.append({
            "title": title,
            "url": url,
            "summary": summary,
        })

    return new_articles


def _send_gmail(
    smtp_user: str,
    smtp_password: str,
    to_email: str,
    article: dict[str, str],
) -> bool:
    """Gmailでメール通知を送信する."""
    subject = f"LOG OITA 新着:「{article['title']}」"

    body = (
        f"LOG OITA 新着記事\n\n"
        f"「{article['title']}」\n\n"
        f"{article['summary']}\n\n"
        f"{article['url']}"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Gmail通知送信成功: %s", article["title"])
        return True
    except smtplib.SMTPException:
        logger.exception("Gmail通知に失敗: %s", article["title"])
        return False


def main() -> None:
    """メイン処理."""
    smtp_user = os.environ.get("GMAIL_ADDRESS", "")
    smtp_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    to_email = os.environ.get("NOTIFY_TO_EMAIL", smtp_user)

    if not smtp_user or not smtp_password:
        logger.error("環境変数 GMAIL_ADDRESS / GMAIL_APP_PASSWORD が未設定です")
        return

    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    if not gemini_api_key:
        logger.error("環境変数 GEMINI_API_KEY が未設定です")
        return

    gemini_client = genai.Client(api_key=gemini_api_key)

    seen_urls = _load_last_seen()
    logger.info("監視開始: 既知の記事数 = %d", len(seen_urls))

    new_articles = _fetch_new_articles(seen_urls, gemini_client)

    if not new_articles:
        logger.info("新着記事はありません")
        return

    logger.info("新着記事: %d 件", len(new_articles))

    for article in new_articles:
        success = _send_gmail(smtp_user, smtp_password, to_email, article)
        if success:
            seen_urls.add(article["url"])

    _save_last_seen(seen_urls)
    logger.info("完了: %d 件通知しました", len(new_articles))


if __name__ == "__main__":
    main()
