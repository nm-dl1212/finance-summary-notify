import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

def plot_price_history(
    ticker,
    years=3,
    output_file=None,
):
    """
    銘柄価格の推移をグラフ化
    """

    end_date = pd.Timestamp.today()
    start_date = end_date - pd.DateOffset(years=years)

    hist = yf.Ticker(ticker).history(
        start=start_date,
        end=end_date,
        auto_adjust=True,
    )

    if hist.empty:
        raise ValueError(f"データ取得失敗: {ticker}")

    hist.index = hist.index.tz_localize(None)

    plt.figure(figsize=(10, 5))

    plt.plot(
        hist.index,
        hist["Close"],
        label=ticker,
    )

    plt.title(f"{ticker} Price History")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.grid(True)
    plt.legend()

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file)
        print(f"グラフ保存: {output_file}")

    plt.show()
    plt.close()


def backtest_dip(
    ticker="ACWI",
    monthly_investment=100_000,
    years=3,
    end_date=None,
    dip_levels=None
):
    """
    積立 + ATH下落時追加投資バックテスト

    Parameters
    ----------
    ticker : str
        ティッカー

    monthly_investment : int
        毎月の積立額

    years : int
        バックテスト期間

    dip_levels : list[tuple]
        [
            (-10, 200_000),
            (-20, 600_000),
            (-30, 1_000_000),
        ]

        ATHから10%下落で20万円
        ATHから20%下落で60万円
        ATHから30%下落で100万円
    """

    # div_levels が None の場合は空リストにする(単純積み立てのみ)
    if dip_levels is None:
        dip_levels = []

    # 念のため浅い順にソート
    dip_levels = sorted(dip_levels, key=lambda x: x[0], reverse=True)

    # 終了時点、開始時点を指定して株価データを取得
    if end_date is None:
        end_date = pd.Timestamp.today()
    else:
        end_date = pd.Timestamp(end_date)

    start_date = end_date - pd.DateOffset(years=years)

    hist = yf.Ticker(ticker).history(
        start=start_date,
        end=end_date,
        auto_adjust=True,
    )

    if hist.empty:
        raise ValueError(f"データ取得失敗: {ticker}")

    hist.index = hist.index.tz_localize(None)

    total_units = 0.0
    total_invested = 0.0

    ath = 0.0

    # 発動済みレベル
    triggered_levels = set()

    records = []

    current_month = None

    for date, row in hist.iterrows():

        price = row["Close"]

        # ATH更新
        if price > ath:
            ath = price
            triggered_levels.clear()

        drawdown_pct = (price - ath) / ath * 100

        # 月初営業日に積立
        month_key = (date.year, date.month)

        if month_key != current_month:

            current_month = month_key

            units = monthly_investment / price

            total_units += units
            total_invested += monthly_investment

        # 暴落時の追加投資
        for threshold, amount in dip_levels:

            if (
                drawdown_pct <= threshold
                and threshold not in triggered_levels
            ):

                units = amount / price

                total_units += units
                total_invested += amount

                triggered_levels.add(threshold)

                print(
                    f"{date.date()} "
                    f"ATH比 {drawdown_pct:.1f}% "
                    f"→ {amount:,}円追加投入 "
                    f"(閾値 {threshold}%)"
                )

        value = total_units * price

        records.append(
            {
                "date": date,
                "price": price,
                "ath": ath,
                "drawdown_pct": drawdown_pct,
                "invested": total_invested,
                "value": value,
                "units": total_units,
            }
        )

    return pd.DataFrame(records)


def plot_result(
    df,
    title,
    output_file,
):
    """
    バックテスト結果をグラフ化
    """

    plt.figure(figsize=(10, 5))

    plt.plot(
        df["date"],
        df["invested"] / 10000,
        label="Principal",
    )

    plt.plot(
        df["date"],
        df["value"] / 10000,
        label="Portfolio Value",
    )

    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("万円")
    plt.grid(True)
    plt.legend()

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()

    print(f"グラフ保存: {output_file}")


def print_summary(df):
    """
    結果サマリーを表示
    """

    final = df.iloc[-1]

    invested = final["invested"]
    value = final["value"]
    profit = value - invested
    return_pct = (value / invested - 1) * 100

    print(f"元金   : {invested:,.0f} 円")
    print(f"評価額 : {value:,.0f} 円")
    print(f"損益   : {profit:,.0f} 円")
    print(f"収益率 : {return_pct:.2f} %")


if __name__ == "__main__":

    ticker = "VTI"
    
    plot_price_history(
        ticker=ticker,
        years=10,
        output_file=f"price.png",
    ) 

    df_dca = backtest_dip(
        ticker=ticker,
        monthly_investment=10_000,
        years=5,
        end_date="2025-12-31",
        dip_levels=None,  # 単純積み立て
    )

    df_dip = backtest_dip(
        ticker=ticker,
        monthly_investment=0,
        years=5,
        end_date="2025-12-31",
        dip_levels=[
            (-10, 150_000),
            (-20, 300_000),
        ],
    )


    plot_result(
        df_dca,
        title=f"{ticker} DCA Backtest",
        output_file="dca_backtest.png",
    )

    plot_result(
        df_dip,
        title=f"{ticker} DIP Backtest",
        output_file="dip_backtest.png",
    )

    print("\ndca strategy summary:")
    print_summary(df_dca)

    print("\ndip strategy summary:")
    print_summary(df_dip)