"""
ニュース取得モジュールのテスト
"""

from datetime import datetime
from unittest.mock import patch
from src.news_fetcher import fetch_news


class TestFetchNewsSchedule:
    """曜日によるソースフィルタリングのテスト"""

    def _make_config(self):
        return {
            "max_articles": 5,
            "categories": [
                {
                    "name": "生成AI",
                    "enabled": True,
                    "sources": [
                        {
                            "url": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml",
                            "name": "ITmedia",
                            "schedule": "weekday"
                        },
                        {
                            "url": "https://news.google.com/rss/search?q=生成AI",
                            "name": "Google News",
                            "schedule": "weekend"
                        }
                    ]
                }
            ]
        }

    @patch("src.news_fetcher.fetch_from_rss")
    @patch("src.news_fetcher.load_config")
    def test_weekday_uses_itmedia_only(self, mock_load_config, mock_fetch_rss):
        """平日はITmediaのみ使用すること"""
        mock_load_config.return_value = self._make_config()
        mock_fetch_rss.return_value = []

        # 月曜日 (weekday=0)
        with patch("src.news_fetcher.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 16)  # 月曜日
            mock_dt.min = datetime.min
            fetch_news()

        urls_called = [call[0][0] for call in mock_fetch_rss.call_args_list]
        assert "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml" in urls_called
        assert "https://news.google.com/rss/search?q=生成AI" not in urls_called

    @patch("src.news_fetcher.fetch_from_rss")
    @patch("src.news_fetcher.load_config")
    def test_weekend_uses_google_news_only(self, mock_load_config, mock_fetch_rss):
        """土日はGoogle Newsのみ使用すること"""
        mock_load_config.return_value = self._make_config()
        mock_fetch_rss.return_value = []

        # 土曜日 (weekday=5)
        with patch("src.news_fetcher.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 14)  # 土曜日
            mock_dt.min = datetime.min
            fetch_news()

        urls_called = [call[0][0] for call in mock_fetch_rss.call_args_list]
        assert "https://news.google.com/rss/search?q=生成AI" in urls_called
        assert "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml" not in urls_called

    @patch("src.news_fetcher.fetch_from_rss")
    @patch("src.news_fetcher.load_config")
    def test_sunday_uses_google_news_only(self, mock_load_config, mock_fetch_rss):
        """日曜日もGoogle Newsのみ使用すること"""
        mock_load_config.return_value = self._make_config()
        mock_fetch_rss.return_value = []

        # 日曜日 (weekday=6)
        with patch("src.news_fetcher.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 15)  # 日曜日
            mock_dt.min = datetime.min
            fetch_news()

        urls_called = [call[0][0] for call in mock_fetch_rss.call_args_list]
        assert "https://news.google.com/rss/search?q=生成AI" in urls_called
        assert "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml" not in urls_called

    @patch("src.news_fetcher.fetch_from_rss")
    @patch("src.news_fetcher.load_config")
    def test_no_schedule_always_used(self, mock_load_config, mock_fetch_rss):
        """scheduleが未設定のソースは常に使用されること"""
        config = {
            "max_articles": 5,
            "categories": [
                {
                    "name": "テスト",
                    "enabled": True,
                    "sources": [
                        {
                            "url": "https://example.com/rss",
                            "name": "Always Available"
                        }
                    ]
                }
            ]
        }
        mock_load_config.return_value = config
        mock_fetch_rss.return_value = []

        # 平日でもアクセスされる
        with patch("src.news_fetcher.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 16)  # 月曜日
            mock_dt.min = datetime.min
            fetch_news()

        assert mock_fetch_rss.call_count == 1

        mock_fetch_rss.reset_mock()

        # 土日でもアクセスされる
        with patch("src.news_fetcher.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 14)  # 土曜日
            mock_dt.min = datetime.min
            fetch_news()

        assert mock_fetch_rss.call_count == 1
