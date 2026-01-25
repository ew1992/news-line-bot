"""
毎朝テックニュース配信システム
メインエントリーポイント
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

from src.news_fetcher import fetch_news
from src.summarizer import summarize_articles
from src.line_sender import send_news


def main() -> int:
    """
    メイン処理:
    1. ニュースを取得
    2. AIで要約
    3. LINEで配信
    """
    # .envファイルから環境変数を読み込む（ローカル実行時）
    load_dotenv()

    print("=" * 50)
    print("テックニュース配信システム 開始")
    print("=" * 50)

    # 1. ニュース取得
    print("\n[1/3] ニュースを取得中...")
    config_path = project_root / "config" / "news_sources.yaml"
    articles = fetch_news(config_path=config_path)

    if not articles:
        print("ニュースを取得できませんでした")
        return 1

    print(f"  → {len(articles)}件の記事を取得しました")
    for i, article in enumerate(articles, 1):
        print(f"  {i}. [{article.category}] {article.title[:50]}...")

    # 2. 要約生成
    print("\n[2/3] 記事を要約中...")
    try:
        articles_with_summaries = summarize_articles(articles)
        print(f"  → {len(articles_with_summaries)}件の要約を生成しました")
    except Exception as e:
        print(f"要約の生成に失敗しました: {e}")
        return 1

    # 3. LINE配信
    print("\n[3/3] LINEに配信中...")
    try:
        success = send_news(articles_with_summaries)
        if success:
            print("  → 配信完了!")
        else:
            print("  → 配信に失敗しました")
            return 1
    except Exception as e:
        print(f"LINE配信に失敗しました: {e}")
        return 1

    print("\n" + "=" * 50)
    print("処理完了")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
