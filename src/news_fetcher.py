"""
ニュース取得モジュール
RSSフィードからニュースを取得し、重複を除去して返す
"""

import re
import feedparser
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
import hashlib

from .logger import get_logger

logger = get_logger(__name__)

# 類似度の閾値（0.0〜1.0、高いほど厳しい）
SIMILARITY_THRESHOLD = 0.5


@dataclass
class NewsArticle:
    """ニュース記事のデータクラス"""
    title: str
    url: str
    description: str
    published: Optional[datetime]
    source: str
    category: str

    @property
    def id(self) -> str:
        """記事の一意なIDを生成（URLベース）"""
        return hashlib.md5(self.url.encode()).hexdigest()


def normalize_title(title: str) -> str:
    """タイトルを正規化して比較しやすくする"""
    # 小文字化
    title = title.lower()
    # 記号を除去
    title = re.sub(r'[^\w\s]', '', title)
    # 連続する空白を1つに
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def extract_keywords(title: str) -> set[str]:
    """タイトルからキーワードを抽出"""
    normalized = normalize_title(title)
    # 短い単語（2文字以下）を除去
    words = [w for w in normalized.split() if len(w) > 2]
    return set(words)


def calculate_similarity(title1: str, title2: str) -> float:
    """
    2つのタイトルの類似度を計算（Jaccard係数）

    Returns:
        0.0〜1.0の類似度（1.0が完全一致）
    """
    keywords1 = extract_keywords(title1)
    keywords2 = extract_keywords(title2)

    if not keywords1 or not keywords2:
        return 0.0

    intersection = keywords1 & keywords2
    union = keywords1 | keywords2

    return len(intersection) / len(union)


def is_similar_to_existing(article: "NewsArticle", existing_articles: list["NewsArticle"]) -> bool:
    """既存の記事と類似しているかチェック"""
    for existing in existing_articles:
        similarity = calculate_similarity(article.title, existing.title)
        if similarity >= SIMILARITY_THRESHOLD:
            logger.info(f"Similar article found (similarity={similarity:.2f}):")
            logger.info(f"  - Existing: {existing.title[:50]}...")
            logger.info(f"  - Skipped:  {article.title[:50]}...")
            return True
    return False


def load_config(config_path: Optional[Path] = None) -> dict:
    """設定ファイルを読み込む"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "news_sources.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_published_date(entry: dict) -> Optional[datetime]:
    """記事の公開日時をパースする"""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6])
        except (TypeError, ValueError):
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6])
        except (TypeError, ValueError):
            pass
    return None


def fetch_from_rss(url: str, source_name: str, category: str) -> list[NewsArticle]:
    """単一のRSSフィードから記事を取得"""
    articles = []

    try:
        feed = feedparser.parse(url)

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()

            # descriptionの取得（複数のフィールドを試す）
            description = ""
            for field in ["summary", "description", "content"]:
                if hasattr(entry, field):
                    value = getattr(entry, field)
                    if isinstance(value, list) and value:
                        description = value[0].get("value", "")
                    elif isinstance(value, str):
                        description = value
                    if description:
                        break

            # HTMLタグを簡易的に除去
            description = re.sub(r"<[^>]+>", "", description).strip()
            description = re.sub(r"\s+", " ", description)

            if title and link:
                articles.append(NewsArticle(
                    title=title,
                    url=link,
                    description=description[:500] if description else "",
                    published=parse_published_date(entry),
                    source=source_name,
                    category=category
                ))
    except Exception as e:
        logger.error(f"Error fetching RSS from {url}: {e}")

    return articles


def fetch_news(config_path: Optional[Path] = None, max_articles: Optional[int] = None) -> list[NewsArticle]:
    """
    設定ファイルに基づいてニュースを取得

    Args:
        config_path: 設定ファイルのパス（デフォルトは config/news_sources.yaml）
        max_articles: 取得する最大記事数（デフォルトは設定ファイルの値）

    Returns:
        NewsArticleのリスト（新しい順）
    """
    config = load_config(config_path)

    if max_articles is None:
        max_articles = config.get("max_articles", 5)

    all_articles: list[NewsArticle] = []
    seen_urls: set[str] = set()

    # 有効なカテゴリからニュースを取得
    for category in config.get("categories", []):
        if not category.get("enabled", True):
            continue

        category_name = category.get("name", "Unknown")

        for source in category.get("sources", []):
            url = source.get("url")
            source_name = source.get("name", url)

            if not url:
                continue

            articles = fetch_from_rss(url, source_name, category_name)

            # URL重複を除去しながら追加
            for article in articles:
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    all_articles.append(article)

    logger.info(f"Fetched {len(all_articles)} articles before deduplication")

    # 公開日時でソート（新しい順）、日時がないものは最後に
    all_articles.sort(
        key=lambda a: a.published or datetime.min,
        reverse=True
    )

    # 24時間以内の記事を優先
    recent_cutoff = datetime.now() - timedelta(hours=24)
    recent_articles = [a for a in all_articles if a.published and a.published > recent_cutoff]
    older_articles = [a for a in all_articles if not a.published or a.published <= recent_cutoff]

    # 最新の記事を優先
    sorted_articles = recent_articles + older_articles

    # 類似記事を除去
    unique_articles: list[NewsArticle] = []
    for article in sorted_articles:
        if not is_similar_to_existing(article, unique_articles):
            unique_articles.append(article)
            if len(unique_articles) >= max_articles:
                break

    logger.info(f"Returning {len(unique_articles)} unique articles after deduplication")
    return unique_articles


if __name__ == "__main__":
    # テスト実行
    articles = fetch_news()
    print(f"Fetched {len(articles)} articles:\n")
    for i, article in enumerate(articles, 1):
        print(f"{i}. [{article.category}] {article.title}")
        print(f"   Source: {article.source}")
        print(f"   URL: {article.url}")
        print(f"   Published: {article.published}")
        print(f"   Description: {article.description[:100]}..." if article.description else "   Description: N/A")
        print()
