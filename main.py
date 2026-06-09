import os
from datetime import datetime

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from slack_sdk.webhook import WebhookClient


def get_result(symbol, report_date=None):
    """
    銘柄ごとに株価情報を取得する関数。
    終値ベースで、前日比、最高値 (ATH) 比、52週間高値比を計算する。
    :param symbol: 銘柄コード
    :param report_date: レポート日付（オプション）
    :return: 銘柄の情報を含む辞書
    """

    hist = yf.Ticker(symbol).history(period="max", auto_adjust=False)

    if hist.empty:
        return None

    # タイムゾーンをローカルに変換
    hist.index = hist.index.tz_localize(None)

    # レポート日付が与えられている場合は、その日付までのデータに変換
    if report_date is not None:
        report_date = pd.Timestamp(report_date)
        hist = hist.loc[:report_date]

    # データが2行未満の場合
    if len(hist) < 2:
        return None

    # 出来高0の場合は除く
    hist = hist[hist["Volume"] > 0]

    # 最新とその前日の終値を取得
    current = hist["Adj Close"].iloc[-1]
    prev = hist["Adj Close"].iloc[-2]

    # ATH（過去最高値）を取得
    ath = hist["Adj Close"].max()

    # 52週間高値を取得
    window = min(252, len(hist))
    high_52w = hist["Adj Close"].rolling(window=window).max().iloc[-1]

    # 比率を取得
    diff_pct = (current - prev) / prev * 100
    ath_pct = (current - ath) / ath * 100
    high_52w_pct = (current - high_52w) / high_52w * 100

    return {
        "symbol": symbol,
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "current": float(current),
        "prev": float(prev),
        "ath": float(ath),
        "high_52w": float(high_52w),
        "diff_percentage": float(diff_pct),
        "ath_percentage": float(ath_pct),
        "high_52w_percentage": float(high_52w_pct),
    }


def build_blocks(results):
    """
    Slack送信用に、株価情報をテーブル形式のブロックに変換する関数。
    :param results: 銘柄ごとの株価情報のリスト
    :return: Slackのブロック形式のリスト
    """

    def _annotate_change(value):
        """
        株価の変化率に応じて、絵文字を付与するヘルパー関数。
        """
        if value >= 20:
            return f"🚀 {value:+.2f}%"
        if value >= 10:
            return f"🔥 {value:+.2f}%"
        if value >= 3:
            return f"🌞 {value:+.2f}%"
        if value >= 0:
            return f"↗️ {value:+.2f}%"
        if value >= -3:
            return f"↘️ {value:+.2f}%"
        if value >= -10:
            return f"☔ {value:+.2f}%"
        if value  >= -20:
            return f"⛈️ {value:+.2f}%"
        return f"💥 {value:+.2f}%"
    
    table_rows = []
    for result in results:
        if result is None:
            table_rows.append(
                [
                    {"type": "raw_text", "text": "データ取得失敗"},
                    {"type": "raw_text", "text": "-"},
                    {"type": "raw_text", "text": "-"},
                    {"type": "raw_text", "text": "-"},
                    {"type": "raw_text", "text": "-"},
                    {"type": "raw_text", "text": "-"},
                ]
            )
            continue

        table_rows.append(
            [
                {"type": "raw_text", "text": f"{result.get('name', '')}"},
                {"type": "raw_text", "text": f"{result.get('symbol', '')}"},
                {"type": "raw_text", "text": _annotate_change(result['diff_percentage'])},
                {"type": "raw_text", "text": _annotate_change(result['ath_percentage'])},
                {"type": "raw_text", "text": _annotate_change(result['high_52w_percentage'])},
                {"type": "raw_text", "text": f"{result['current']:.2f}"},
            ]
        )

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "株価レポート",
            },
        },
        {
            "type": "table",
            "column_settings": [
                {"is_wrapped": True},
                {"align": "right"},
                {"align": "right"},
                {"align": "right"},
                {"align": "right"},
                {"align": "right"},
            ],
            "rows": [
                [
                    {"type": "raw_text", "text": "銘柄"},
                    {"type": "raw_text", "text": "コード"},
                    {"type": "raw_text", "text": "前日比"},
                    {"type": "raw_text", "text": "最高値比"},
                    {"type": "raw_text", "text": "52w高値比"},
                    {"type": "raw_text", "text": "現在値"},
                ],
                *table_rows,
            ],
        },
    ]


if __name__ == "__main__":

    tickers = {
        "S&P500": "1655.T",
        "オルカン": "ACWI",
        "TOPIX": "1475.T",
        # "トヨタ": "7203.T",
        # "三菱重工": "7011.T",
        # "東京エレクトロン": "8035.T"
    }

    now_date = datetime.now().strftime("%Y-%m-%d")

    # 各銘柄のレポートを取得してまとめる
    results = []
    for name, symbol in tickers.items():
        result = get_result(symbol, now_date)

        if result is None:
            results.append(None)
            continue

        result["name"] = name
        results.append(result)

    # レポート形式にフォーマット
    blocks = build_blocks(results)

    load_dotenv()
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    # Slackに送信
    if webhook_url:
        webhook = WebhookClient(webhook_url)
        response = webhook.send(
            text="株式サマリー",
            blocks=blocks,
        )
        if response.status_code == 200:
            print("レポートをSlackに送信しました。")
        else:
            print(f"レポートの送信に失敗しました。ステータスコード: {response.status_code}")
            print(response.body)
