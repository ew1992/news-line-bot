"""
ロギングモジュール
ログをファイルに出力する
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 日本時間 (JST = UTC+9)
JST = timezone(timedelta(hours=9))


class JSTFormatter(logging.Formatter):
    """日本時間でログを出力するFormatter"""

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=JST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_logger(name: str) -> logging.Logger:
    """
    ロガーを取得する

    Args:
        name: ロガー名（通常は__name__）

    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)

    # 既に設定済みの場合はそのまま返す
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # 親ロガーへの伝播を無効化

    # ログディレクトリを作成
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # 日付ごとのログファイル（日本時間で日付を取得）
    today = datetime.now(JST).strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.log"

    # ファイルハンドラ
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # フォーマット（日本時間）
    formatter = JSTFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    # 初期化完了をログに記録
    logger.info(f"Logger initialized: {name}")

    return logger
