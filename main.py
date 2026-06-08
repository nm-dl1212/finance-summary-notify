import os
from datetime import datetime

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from slack_sdk.webhook import WebhookClient


def get_result(symbol, report_date=None):
    """
    report_date:
        None -> 最新日時点
        "2024-08-05" のような文字列
        datetime オブジェクト
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


def _annotate_change(value):
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


def format_summary_report(results):
    if not results:
        return "# 株価レポート\n\nデータ取得に成功した銘柄がありません。"

    lines = ["# 株価レポート", ""]

    headers = ["銘柄", "コード", "現在値", "前日比", "最高値比", "52w高値比"]
    rows = []

    for result in results:
        if result is None:
            rows.append(["データ取得失敗", "-", "-", "-", "-"])
            continue

        rows.append(
            [
                f"`{result.get('name', '')}`", 
                f"`{result.get('symbol', '')}`",
                f"`{result['current']:.2f}`",
                f"`{_annotate_change(result['diff_percentage'])}`",
                f"`{_annotate_change(result['ath_percentage'])}`",
                f"`{_annotate_change(result['high_52w_percentage'])}`",
            ]
        )

    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def build_summary_blocks(results):
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
                {
                    "type": "raw_text",
                    "text": f"{result.get('name', '')}"
                },
                {"type": "raw_text", "text": f"{result.get('symbol', '')}"},
                {"type": "raw_text", "text": f"{result['current']:.2f}"},
                {"type": "raw_text", "text": _annotate_change(result['diff_percentage'])},
                {"type": "raw_text", "text": _annotate_change(result['ath_percentage'])},
                {"type": "raw_text", "text": _annotate_change(result['high_52w_percentage'])},
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
                    {"type": "raw_text", "text": "現在値"},
                    {"type": "raw_text", "text": "前日比"},
                    {"type": "raw_text", "text": "最高値比"},
                    {"type": "raw_text", "text": "52w高値比"},
                ],
                *table_rows,
            ],
        },
    ]


if __name__ == "__main__":

    tickers = {
        "S&P500 (iシェアーズ S&P500 米国株 ETF)": "1655.T",
        "オルカン (iShares MSCI ACWI ETF)": "ACWI",
        "TOPIX (iShares Core TOPIX ETF) ": "1475.T",
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
    report = format_summary_report(results)
    blocks = build_summary_blocks(results)
    print(report)

    load_dotenv()
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    # Slackに送信
    if webhook_url:
        webhook = WebhookClient(webhook_url)
        response = webhook.send(
            text=report,
            blocks=blocks,
        )
        if response.status_code == 200:
            print("レポートをSlackに送信しました。")
        else:
            print(f"レポートの送信に失敗しました。ステータスコード: {response.status_code}")
            print(response.body)
