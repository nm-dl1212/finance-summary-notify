# finance-news

`finance-news` は、`yfinance` で取得した株価データを使って、
- 銘柄ごとの株価レポートを表示する
- 積立投資と押し目買いの簡易バックテストを行う
- 価格推移やバックテスト結果をグラフ化する

ための小さな Python プロジェクトです。

## 特徴

- 最新時点の株価レポートを出力
- 過去最高値（ATH）と 52 週間高値との差分を表示
- 月次積立と、ATH からの下落率に応じた追加投資をシミュレーション
- `matplotlib` によるグラフ保存と表示に対応

## 要件

- Python 3.12 以上
- `uv`
- インターネット接続

## セットアップ

依存関係は `uv sync` でインストールします。

```bash
uv sync
```

## 使い方

### 株価レポート

`main.py` を実行すると、`main.py` 内で定義されたティッカーについてレポートを取得し、`summary` として整形した結果を標準出力に表示します。

```bash
uv run python main.py
```

出力内容:
- 現在価格
- 過去最高値
- 52 週間高値
- 前日比
- ATH 比
- 52 週間高値比

ティッカーや銘柄名を変える場合は、`main.py` の `tickers` を編集してください。

### バックテスト

`backtest.py` を実行すると、VTI を対象に以下を行います。
- 10 年分の価格推移を `price.png` に保存
- 5 年分の DCA バックテストを実施
- 5 年分の押し目買いバックテストを実施
- 結果を `dca_backtest.png` と `dip_backtest.png` に保存
- 元金、評価額、損益、収益率を表示

```bash
uv run python backtest.py
```

## 主要関数

### `main.py`

- `get_report(symbol, report_date=None)`
  - 指定銘柄の株価情報を取得し、現在値、ATH、52 週間高値などを返します。

### `backtest.py`

- `plot_price_history(ticker, years=3, output_file=None)`
  - 指定銘柄の価格推移を描画します。
- `backtest_dip(ticker="ACWI", monthly_investment=100_000, years=3, end_date=None, dip_levels=None)`
  - 月次積立と、ATH からの下落率に応じた追加投資をシミュレーションします。
- `plot_result(df, title, output_file)`
  - バックテスト結果をグラフ化します。
- `print_summary(df)`
  - 最終時点の元金、評価額、損益、収益率を表示します。

## 補足

- データ取得は `yfinance` に依存するため、相場データが取得できない場合は失敗します。
- `matplotlib` の `plt.show()` を使うため、GUI 環境がない場合は表示が失敗することがあります。その場合は `output_file` を指定して保存のみ行ってください。
- 現在のスクリプトは CLI 引数を受け取りません。ティッカーや投資額を変える場合は各 `__main__` ブロックの設定値を編集してください。

## ライセンス

未設定です。必要に応じて追記してください。
