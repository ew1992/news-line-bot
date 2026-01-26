"""
LINE配信モジュールのテスト
"""

import pytest
from datetime import datetime
from unittest.mock import patch
from src.news_fetcher import NewsArticle
from src.line_sender import create_flex_carousel_message, send_news


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


class TestCreateFlexCarouselMessage:
    """create_flex_carousel_message関数のテスト"""

    def test_returns_flex_type(self):
        """メッセージタイプがflexであること"""
        articles = [create_test_article()]
        result = create_flex_carousel_message(articles)

        assert result["type"] == "flex"

    def test_has_alt_text(self):
        """altTextが設定されていること"""
        articles = [create_test_article()]
        result = create_flex_carousel_message(articles)

        assert "altText" in result
        assert len(result["altText"]) > 0

    def test_contents_type_is_carousel(self):
        """contents.typeがcarouselであること"""
        articles = [create_test_article()]
        result = create_flex_carousel_message(articles)

        assert result["contents"]["type"] == "carousel"

    def test_bubbles_count_matches_articles(self):
        """バブル数が記事数と一致すること"""
        articles = [create_test_article() for _ in range(3)]
        result = create_flex_carousel_message(articles)

        assert len(result["contents"]["contents"]) == 3

    def test_max_10_bubbles(self):
        """最大10バブルまでに制限されること"""
        articles = [create_test_article() for _ in range(15)]
        result = create_flex_carousel_message(articles)

        assert len(result["contents"]["contents"]) == 10

    def test_bubble_has_body(self):
        """各バブルにbodyがあること"""
        articles = [create_test_article()]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        assert "body" in bubble
        assert bubble["body"]["type"] == "box"

    def test_bubble_has_footer_with_button(self):
        """各バブルにfooter（ボタン付き）があること"""
        articles = [create_test_article(url="https://example.com/test")]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        assert "footer" in bubble
        footer = bubble["footer"]
        assert footer["type"] == "box"

        button = footer["contents"][0]
        assert button["type"] == "button"
        assert button["action"]["type"] == "uri"
        assert button["action"]["uri"] == "https://example.com/test"

    def test_title_text_is_small_size(self):
        """タイトルのフォントサイズが小さいこと"""
        articles = [create_test_article(title="テストタイトル")]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        body_contents = bubble["body"]["contents"]
        title_component = body_contents[0]

        assert title_component["type"] == "text"
        assert title_component["size"] in ["sm", "md"]

    def test_title_text_contains_full_title(self):
        """タイトルが全文表示されること"""
        long_title = "これは非常に長いタイトルで40文字を超えています。全文が表示されるべきです。"
        articles = [create_test_article(title=long_title)]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        title_component = bubble["body"]["contents"][0]
        assert title_component["text"] == long_title

    def test_title_has_wrap_enabled(self):
        """タイトルが折り返し表示されること"""
        articles = [create_test_article()]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        title_component = bubble["body"]["contents"][0]
        assert title_component.get("wrap") is True

    def test_summary_text_contains_full_summary(self):
        """要約が全文表示されること"""
        long_summary = "これは非常に長い要約文で、60文字を超えています。Flex Messageでは全文が表示されるべきです。テンプレートでは切り詰められていましたが、もう切り詰められません。"
        articles = [create_test_article(summary=long_summary)]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        body_contents = bubble["body"]["contents"]
        summary_component = body_contents[1]
        assert summary_component["text"] == long_summary

    def test_summary_has_wrap_enabled(self):
        """要約が折り返し表示されること"""
        articles = [create_test_article()]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        summary_component = bubble["body"]["contents"][1]
        assert summary_component.get("wrap") is True

    def test_body_has_padding(self):
        """bodyにパディングがあること"""
        articles = [create_test_article()]
        result = create_flex_carousel_message(articles)

        bubble = result["contents"]["contents"][0]
        body = bubble["body"]
        assert "paddingAll" in body or "paddingTop" in body

    def test_empty_articles_returns_none(self):
        """空の記事リストの場合はNoneを返すこと"""
        result = create_flex_carousel_message([])

        assert result is None

    def test_multiple_articles_creates_multiple_bubbles(self):
        """複数の記事が複数のバブルになること"""
        articles = [
            create_test_article(title="記事1", url="https://example.com/1"),
            create_test_article(title="記事2", url="https://example.com/2"),
        ]
        result = create_flex_carousel_message(articles)

        bubbles = result["contents"]["contents"]
        assert len(bubbles) == 2


class TestSendNews:
    """send_news関数のテスト"""

    def test_sends_flex_carousel_message(self):
        """Flex Messageカルーセルが送信されること"""
        articles = [create_test_article()]

        with patch("src.line_sender.send_messages") as mock_send:
            mock_send.return_value = True
            result = send_news(articles, "test_token")

        assert result is True
        mock_send.assert_called_once()

        sent_messages = mock_send.call_args[0][0]
        assert len(sent_messages) == 1
        assert sent_messages[0]["type"] == "flex"
        assert sent_messages[0]["contents"]["type"] == "carousel"

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
