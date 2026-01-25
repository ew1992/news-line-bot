"""
LINE配信モジュールのテスト
"""

import pytest
from datetime import datetime
from unittest.mock import patch
from src.news_fetcher import NewsArticle
from src.line_sender import create_carousel_message, send_news


def create_test_article(
    title: str = "テスト記事タイトル",
    url: str = "https://example.com/article",
    summary: str = "これはテスト記事の要約です。"
) -> tuple[NewsArticle, str]:
    """テスト用の記事と要約のタプルを作成"""
    article = NewsArticle(
        title=title,
        url=url,
        description="",
        published=datetime.now(),
        source="Test Source",
        category="テスト"
    )
    return (article, summary)


class TestCreateCarouselMessage:
    """create_carousel_message関数のテスト"""

    def test_returns_template_type(self):
        """テンプレートタイプがtemplateであること"""
        articles = [create_test_article()]
        result = create_carousel_message(articles)

        assert result["type"] == "template"

    def test_has_alt_text(self):
        """altTextが設定されていること"""
        articles = [create_test_article()]
        result = create_carousel_message(articles)

        assert "altText" in result
        assert len(result["altText"]) > 0

    def test_template_type_is_carousel(self):
        """template.typeがcarouselであること"""
        articles = [create_test_article()]
        result = create_carousel_message(articles)

        assert result["template"]["type"] == "carousel"

    def test_columns_count_matches_articles(self):
        """カラム数が記事数と一致すること"""
        articles = [create_test_article() for _ in range(3)]
        result = create_carousel_message(articles)

        assert len(result["template"]["columns"]) == 3

    def test_max_10_columns(self):
        """最大10カラムまでに制限されること"""
        articles = [create_test_article() for _ in range(15)]
        result = create_carousel_message(articles)

        assert len(result["template"]["columns"]) == 10

    def test_column_has_title(self):
        """各カラムにタイトルがあること"""
        articles = [create_test_article(title="テストタイトル")]
        result = create_carousel_message(articles)

        column = result["template"]["columns"][0]
        assert "title" in column
        assert column["title"] == "テストタイトル"

    def test_column_title_max_40_chars(self):
        """タイトルが40文字以内に切り詰められること"""
        long_title = "あ" * 50
        articles = [create_test_article(title=long_title)]
        result = create_carousel_message(articles)

        column = result["template"]["columns"][0]
        assert len(column["title"]) <= 40

    def test_column_has_text(self):
        """各カラムにテキスト（要約）があること"""
        articles = [create_test_article(summary="テスト要約")]
        result = create_carousel_message(articles)

        column = result["template"]["columns"][0]
        assert "text" in column
        assert "テスト要約" in column["text"]

    def test_column_text_max_60_chars_with_title(self):
        """テキストが60文字以内に切り詰められること（タイトルありの場合）"""
        long_summary = "あ" * 100
        articles = [create_test_article(summary=long_summary)]
        result = create_carousel_message(articles)

        column = result["template"]["columns"][0]
        assert len(column["text"]) <= 60

    def test_column_has_actions(self):
        """各カラムにアクションがあること"""
        articles = [create_test_article()]
        result = create_carousel_message(articles)

        column = result["template"]["columns"][0]
        assert "actions" in column
        assert len(column["actions"]) >= 1

    def test_action_is_uri_type(self):
        """アクションがURIタイプであること"""
        articles = [create_test_article(url="https://example.com/test")]
        result = create_carousel_message(articles)

        action = result["template"]["columns"][0]["actions"][0]
        assert action["type"] == "uri"
        assert action["uri"] == "https://example.com/test"

    def test_action_has_label(self):
        """アクションにラベルがあること"""
        articles = [create_test_article()]
        result = create_carousel_message(articles)

        action = result["template"]["columns"][0]["actions"][0]
        assert "label" in action
        assert len(action["label"]) > 0

    def test_empty_articles_returns_none(self):
        """空の記事リストの場合はNoneを返すこと"""
        result = create_carousel_message([])

        assert result is None

    def test_multiple_articles_creates_multiple_columns(self):
        """複数の記事が複数のカラムになること"""
        articles = [
            create_test_article(title="記事1", url="https://example.com/1"),
            create_test_article(title="記事2", url="https://example.com/2"),
        ]
        result = create_carousel_message(articles)

        columns = result["template"]["columns"]
        assert len(columns) == 2
        assert columns[0]["title"] == "記事1"
        assert columns[1]["title"] == "記事2"


class TestSendNews:
    """send_news関数のテスト"""

    def test_sends_carousel_message(self):
        """カルーセルメッセージが送信されること"""
        articles = [create_test_article()]

        with patch("src.line_sender.send_messages") as mock_send:
            mock_send.return_value = True
            result = send_news(articles, "test_token")

        assert result is True
        mock_send.assert_called_once()

        # 送信されたメッセージがカルーセル形式であることを確認
        sent_messages = mock_send.call_args[0][0]
        assert len(sent_messages) == 1
        assert sent_messages[0]["type"] == "template"
        assert sent_messages[0]["template"]["type"] == "carousel"

    def test_returns_false_when_no_articles(self):
        """記事がない場合はFalseを返すこと"""
        with patch("src.line_sender.send_messages") as mock_send:
            result = send_news([], "test_token")

        assert result is False
        mock_send.assert_not_called()

    def test_passes_token_to_send_messages(self):
        """トークンがsend_messagesに渡されること"""
        articles = [create_test_article()]

        with patch("src.line_sender.send_messages") as mock_send:
            mock_send.return_value = True
            send_news(articles, "my_test_token")

        assert mock_send.call_args[0][1] == "my_test_token"
