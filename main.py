import pandas as pd
import yfinance as yf
from datetime import datetime


def get_report(symbol, report_date=None):
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
        "current": current,
        "diff_pct": diff_pct,
        "ath": ath,
        "ath_pct": ath_pct,
        "high_52w": high_52w,
        "high_52w_pct": high_52w_pct,
    }


def print_report(tickers, report_date=None):

    if report_date is None:
        title_date = datetime.now().strftime("%Y-%m-%d")
    else:
        title_date = str(pd.Timestamp(report_date).date())

    print(f"=== 株価レポート {title_date} ===")

    for name, symbol in tickers.items():

        result = get_report(symbol, report_date)

        if result is None:
            print(f"{name}: データ取得失敗")
            continue

        print(
            f"{name}: {symbol} \n"
            f"* 現在価格 {result['current']:.2f} \n"
            f"* 最高値 {result['ath']:.2f} \n"
            f"* 52週間高値 {result['high_52w']:.2f} \n"
            f"* 前日比 {result['diff_pct']:+.2f}% \n"
            f"* ATH比 {result['ath_pct']:+.2f}% \n"
            f"* 52週間高比 {result['high_52w_pct']:+.2f}% \n"
        )


if __name__ == "__main__":

    tickers = {
        "S&P500 (iシェアーズ S&P500 米国株 ETF)": "1655.T",
        "オルカン (iShares MSCI ACWI ETF)": "ACWI",
        "TOPIX (iShares Core TOPIX ETF) ": "1475.T",
        # "トヨタ": "7203.T",
        # "三菱重工": "7011.T",
        # "東京エレクトロン": "8035.T"
    }

    # 最新レポート
    print_report(tickers)

    # 過去日付レポート例
    print_report(tickers, report_date="2024-08-05")
