"""
LINE配信モジュール
LINE Messaging APIを使用してニュースを配信する
"""

import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from .news_fetcher import NewsArticle


LINE_API_ENDPOINT = "https://api.line.me/v2/bot/message/broadcast"


def get_channel_access_token(token: Optional[str] = None) -> str:
    """Channel Access Tokenを取得"""
    t = token or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not t:
        raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is not set")
    return t


def create_news_message(articles_with_summaries: list[tuple[NewsArticle, str]]) -> str:
    """
    ニュースメッセージを作成（テキスト形式）

    Args:
        articles_with_summaries: (記事, 要約) のタプルのリスト

    Returns:
        フォーマットされたメッセージ文字列
    """
    today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d")
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    lines = [f"📰 本日の生成AIニュース ({today})", ""]

    for i, (article, summary) in enumerate(articles_with_summaries):
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."

        lines.append(f"{emoji} {article.title}")
        lines.append("")
        lines.append(summary)
        lines.append("")
        lines.append(f"🔗 {article.url}")
        lines.append("")
        lines.append("─" * 20)
        lines.append("")

    return "\n".join(lines).strip()


def truncate_text(text: str, max_length: int) -> str:
    """テキストを指定の長さに切り詰める"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 1] + "…"


def create_carousel_message(articles_with_summaries: list[tuple[NewsArticle, str]]) -> Optional[dict]:
    """
    カルーセルテンプレートメッセージを作成（旧形式、文字数制限あり）

    Args:
        articles_with_summaries: (記事, 要約) のタプルのリスト

    Returns:
        カルーセルテンプレートメッセージのdict、記事がない場合はNone
    """
    if not articles_with_summaries:
        return None

    max_columns = 10
    articles = articles_with_summaries[:max_columns]

    columns = []
    for article, summary in articles:
        title = truncate_text(article.title, 40)
        text = truncate_text(summary, 60)

        column = {
            "title": title,
            "text": text,
            "actions": [
                {
                    "type": "uri",
                    "label": "記事を読む",
                    "uri": article.url
                }
            ]
        }
        columns.append(column)

    today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d")

    return {
        "type": "template",
        "altText": f"本日の生成AIニュース ({today})",
        "template": {
            "type": "carousel",
            "columns": columns
        }
    }


def create_flex_carousel_message(articles_with_summaries: list[tuple[NewsArticle, str]]) -> Optional[dict]:
    """
    Flex Messageカルーセル形式でニュースメッセージを作成

    Args:
        articles_with_summaries: (記事, 要約) のタプルのリスト

    Returns:
        Flex Messageのdict、記事がない場合はNone
    """
    if not articles_with_summaries:
        return None

    max_bubbles = 10
    articles = articles_with_summaries[:max_bubbles]

    bubbles = []
    for article, summary in articles:
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": article.title,
                        "weight": "bold",
                        "size": "md",
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": summary,
                        "size": "sm",
                        "color": "#666666",
                        "margin": "lg",
                        "wrap": True
                    }
                ],
                "paddingAll": "xl"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "action": {
                            "type": "uri",
                            "label": "記事を読む",
                            "uri": article.url
                        }
                    }
                ],
                "paddingAll": "lg"
            }
        }
        bubbles.append(bubble)

    today = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y/%m/%d")

    return {
        "type": "flex",
        "altText": f"本日の生成AIニュース ({today})",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }


def send_messages(messages: list[dict], channel_access_token: Optional[str] = None) -> bool:
    """
    メッセージをブロードキャスト送信

    Args:
        messages: 送信するメッセージのリスト（LINE Messaging API形式）
        channel_access_token: LINE Channel Access Token

    Returns:
        送信成功時True
    """
    token = get_channel_access_token(channel_access_token)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload = {"messages": messages[:5]}  # LINE APIは最大5メッセージまで

    try:
        response = requests.post(LINE_API_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        print("Message broadcast successful")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending LINE message: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}")
        return False


def send_broadcast(message: str, channel_access_token: Optional[str] = None) -> bool:
    """
    全ての友だちにテキストメッセージをブロードキャスト送信

    Args:
        message: 送信するメッセージ
        channel_access_token: LINE Channel Access Token

    Returns:
        送信成功時True
    """
    # LINE APIはメッセージを5000文字まで送信可能
    max_length = 5000
    messages = []

    if len(message) <= max_length:
        messages.append({"type": "text", "text": message})
    else:
        # 分割して送信
        parts = []
        current_part = ""

        for line in message.split("\n"):
            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line + "\n"
            else:
                current_part += line + "\n"

        if current_part:
            parts.append(current_part.strip())

        messages = [{"type": "text", "text": part} for part in parts[:5]]

    return send_messages(messages, channel_access_token)


def send_news(articles_with_summaries: list[tuple[NewsArticle, str]], channel_access_token: Optional[str] = None) -> bool:
    """
    ニュースをLINEでFlex Messageカルーセル形式で配信

    Args:
        articles_with_summaries: (記事, 要約) のタプルのリスト
        channel_access_token: LINE Channel Access Token

    Returns:
        送信成功時True
    """
    if not articles_with_summaries:
        print("No articles to send")
        return False

    flex_message = create_flex_carousel_message(articles_with_summaries)
    if flex_message is None:
        print("Failed to create flex message")
        return False

    return send_messages([flex_message], channel_access_token)


if __name__ == "__main__":
    # テスト用のダミーデータ
    from .news_fetcher import NewsArticle

    test_articles = [
        (
            NewsArticle(
                title="OpenAIが新モデルGPT-5を発表",
                url="https://example.com/gpt5",
                description="",
                published=datetime.now(),
                source="Test Source",
                category="生成AI"
            ),
            "OpenAIは本日、次世代AIモデル「GPT-5」を発表しました。従来のGPT-4と比較して、推論能力が大幅に向上し、より複雑なタスクをこなせるようになっています。"
        ),
        (
            NewsArticle(
                title="Googleが量子コンピュータで新記録",
                url="https://example.com/quantum",
                description="",
                published=datetime.now(),
                source="Test Source",
                category="テクノロジー"
            ),
            "Googleの量子コンピューティングチームが、新しい量子プロセッサで100量子ビットの演算に成功しました。これは商用量子コンピュータの実用化に向けた大きな一歩です。"
        ),
    ]

    message = create_news_message(test_articles)
    print("Generated message:")
    print("=" * 50)
    print(message)
    print("=" * 50)
