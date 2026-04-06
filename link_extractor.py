"""記事HTML内のInstagram/YouTubeリンク抽出モジュール."""

import re
from bs4 import BeautifulSoup


def extract_social_links(html: str) -> dict[str, list[str]]:
    """記事のHTMLコンテンツからInstagramとYouTubeのリンクを抽出する.

    Args:
        html: 記事のHTMLコンテンツ（RSSのcontent:encodedなど）

    Returns:
        {"instagram": [...], "youtube": [...]} のdict。見つからなければ空リスト。
    """
    soup = BeautifulSoup(html, "html.parser")

    instagram_urls: set[str] = set()
    youtube_urls: set[str] = set()

    # 1. aタグのhrefから抽出
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if _is_instagram_url(href):
            instagram_urls.add(_normalize_instagram_url(href))
        elif _is_youtube_url(href):
            youtube_urls.add(_normalize_youtube_url(href))

    # 2. iframeのsrcから抽出（埋め込み）
    for iframe in soup.find_all("iframe", src=True):
        src = iframe["src"]
        if _is_youtube_url(src):
            youtube_urls.add(_normalize_youtube_url(src))

    # 3. blockquoteのdata-instgrm-permalink（Instagram埋め込み）
    for bq in soup.find_all("blockquote"):
        permalink = bq.get("data-instgrm-permalink", "")
        if permalink and _is_instagram_url(permalink):
            instagram_urls.add(_normalize_instagram_url(permalink))

    # 4. テキスト内のURL（正規表現でフォールバック）
    text = str(soup)
    for match in re.finditer(r'https?://(?:www\.)?instagram\.com/[^\s"\'<>]+', text):
        instagram_urls.add(_normalize_instagram_url(match.group()))
    for match in re.finditer(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s"\'<>]+', text):
        youtube_urls.add(_normalize_youtube_url(match.group()))

    return {
        "instagram": sorted(instagram_urls),
        "youtube": sorted(youtube_urls),
    }


def _is_instagram_url(url: str) -> bool:
    return bool(re.match(r'https?://(?:www\.)?instagram\.com/', url))


def _is_youtube_url(url: str) -> bool:
    return bool(re.match(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/', url))


def _normalize_instagram_url(url: str) -> str:
    url = re.sub(r'[?#].*$', '', url)  # クエリパラメータ除去
    return url.rstrip('/')


def _normalize_youtube_url(url: str) -> str:
    # youtu.be/VIDEO_ID → youtube.com/watch?v=VIDEO_ID
    match = re.match(r'https?://youtu\.be/([a-zA-Z0-9_-]+)', url)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(1)}"
    # youtube.com/embed/VIDEO_ID → youtube.com/watch?v=VIDEO_ID
    match = re.match(r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)', url)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(1)}"
    return re.sub(r'[#].*$', '', url)
