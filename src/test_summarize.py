"""
ニュース取得と要約のテストスクリプト
LINE配信は行わず、ニュース取得→全文取得→AI要約のみテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

from src.news_fetcher import fetch_news, fetch_full_content_for_articles
from src.summarizer import summarize_articles


def main():
    # .envファイルから環境変数を読み込む
    load_dotenv()

    print("=" * 60)
    print("ニュース取得・要約テスト（LINE配信なし）")
    print("=" * 60)

    # 1. ニュース取得（2件だけテスト）
    print("\n[1/3] ニュースを取得中...")
    config_path = project_root / "config" / "news_sources.yaml"
    articles = fetch_news(config_path=config_path, max_articles=2)

    if not articles:
        print("ニュースを取得できませんでした")
        return 1

    print(f"  → {len(articles)}件の記事を取得しました")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. [{article.category}] {article.title[:50]}...")
        print(f"     URL: {article.url}")

    # 2. 全文取得
    print("\n[2/3] 記事の全文を取得中...")
    articles = fetch_full_content_for_articles(articles)

    for i, article in enumerate(articles, 1):
        content_len = len(article.full_content) if article.full_content else 0
        status = f"全文取得成功 ({content_len}文字)" if content_len > 0 else "全文取得失敗（descriptionを使用）"
        print(f"  {i}. {status}")

    # 3. 要約生成
    print("\n[3/3] 記事を要約中...")
    try:
        articles_with_summaries = summarize_articles(articles)
        print(f"  → {len(articles_with_summaries)}件の要約を生成しました")
    except Exception as e:
        print(f"要約の生成に失敗しました: {e}")
        return 1

    # 結果を表示
    print("\n" + "=" * 60)
    print("要約結果")
    print("=" * 60)

    for i, (article, summary) in enumerate(articles_with_summaries, 1):
        print(f"\n【{i}】{article.title}")
        print(f"カテゴリ: {article.category}")
        print(f"URL: {article.url}")
        print(f"全文文字数: {len(article.full_content) if article.full_content else 0}")
        print("-" * 40)
        print("要約:")
        print(summary)
        print("-" * 40)

    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
