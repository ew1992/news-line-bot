"""
ニュース要約モジュール
Google Gemini APIを使用してニュース記事を要約する
"""

import os
import time
import traceback
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from typing import Optional

from .news_fetcher import NewsArticle
from .logger import get_logger

logger = get_logger(__name__)

# 設定
MODEL_NAME = "gemini-2.5-flash-lite"
MAX_RETRIES = 3
RETRY_DELAY = 30  # 秒
REQUEST_DELAY = 2  # リクエスト間の遅延（秒）


def init_gemini(api_key: Optional[str] = None) -> None:
    """Gemini APIを初期化"""
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        logger.error("GEMINI_API_KEY is not set")
        raise ValueError("GEMINI_API_KEY is not set")

    try:
        genai.configure(api_key=key)
        logger.info(f"Gemini API initialized (key: {key[:8]}...)")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API: {type(e).__name__}: {e}")
        raise


def summarize_article(article: NewsArticle, api_key: Optional[str] = None) -> str:
    """
    単一の記事を要約する（リトライ機能付き）

    Args:
        article: 要約する記事
        api_key: Gemini API Key（省略時は環境変数から取得）

    Returns:
        要約文（日本語、3-4行程度）
    """
    init_gemini(api_key)

    model = genai.GenerativeModel(
        MODEL_NAME,
        generation_config={
            "temperature": 0.3,
            "max_output_tokens": 256,
        },
    )

    prompt = f"""以下のニュース記事を日本語で3〜4行で要約してください。
要点を簡潔にまとめ、読者が内容を素早く理解できるようにしてください。

タイトル: {article.title}
カテゴリ: {article.category}
内容: {article.description if article.description else "（本文なし）"}

要約:"""

    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Requesting summary for: {article.title[:50]}... (attempt {attempt + 1}/{MAX_RETRIES})")
            response = model.generate_content(prompt)

            # レスポンスの検証
            if not response:
                logger.error("Empty response from Gemini API")
                raise ValueError("Empty response from API")

            if not response.text:
                logger.error(f"Response has no text. Response: {response}")
                if hasattr(response, 'prompt_feedback'):
                    logger.error(f"Prompt feedback: {response.prompt_feedback}")
                if hasattr(response, 'candidates') and response.candidates:
                    for i, candidate in enumerate(response.candidates):
                        logger.error(f"Candidate {i}: finish_reason={candidate.finish_reason}, safety_ratings={candidate.safety_ratings}")
                raise ValueError("Response text is empty")

            summary = response.text.strip()

            if not summary:
                logger.error("Empty summary text")
                raise ValueError("Empty summary text")

            logger.info(f"Summary generated successfully ({len(summary)} chars)")
            return summary

        except ResourceExhausted as e:
            last_exception = e
            logger.warning(f"Rate limit exceeded (attempt {attempt + 1}/{MAX_RETRIES}). Waiting {RETRY_DELAY}s...")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            continue

        except Exception as e:
            last_exception = e
            error_type = type(e).__name__
            logger.error(f"Failed to summarize article '{article.title}'")
            logger.error(f"Exception type: {error_type}")
            logger.error(f"Exception message: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            break

    # 全てのリトライが失敗した場合のフォールバック
    logger.error(f"All {MAX_RETRIES} attempts failed for article '{article.title}'")
    if article.description:
        fallback = article.description[:200] + "..." if len(article.description) > 200 else article.description
        logger.warning("Using fallback: description excerpt")
        return fallback
    logger.warning("Using fallback: error message")
    return f"（要約を生成できませんでした）"


def summarize_articles(articles: list[NewsArticle], api_key: Optional[str] = None) -> list[tuple[NewsArticle, str]]:
    """
    複数の記事を要約する（レートリミット対策付き）

    Args:
        articles: 要約する記事のリスト
        api_key: Gemini API Key（省略時は環境変数から取得）

    Returns:
        (記事, 要約文) のタプルのリスト
    """
    results = []
    for i, article in enumerate(articles):
        # 最初のリクエスト以外は遅延を入れる
        if i > 0:
            logger.info(f"Waiting {REQUEST_DELAY}s before next request...")
            time.sleep(REQUEST_DELAY)

        summary = summarize_article(article, api_key)
        results.append((article, summary))
    return results


if __name__ == "__main__":
    # テスト実行
    from .news_fetcher import fetch_news

    print("Fetching news...")
    articles = fetch_news(max_articles=2)

    if not articles:
        print("No articles found")
        exit(1)

    print(f"Summarizing {len(articles)} articles...\n")

    for article, summary in summarize_articles(articles):
        print(f"Title: {article.title}")
        print(f"Summary: {summary}")
        print("-" * 50)
