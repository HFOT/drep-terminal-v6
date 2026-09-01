# DRep Governance Terminal

Cardano の DRep（Delegated Representative）を、検証できる数字だけで読むための一枚もの。

**→ https://hfot.github.io/drep-terminal-v6/**

## 何を見るページか

投票権（VP）が誰にどれだけ集まっているかという **ガバナンスの構造** を見るためのもの。
起動するとまず全体像が出る。

- 総投票力、アクティブ DRep 数、ガバナンス参加率
- **Nakamoto 係数** — 51% を支配するのに必要な DRep 数（小さいほど集中している）
- Top 1 / 5 / 10 / 20 の集中度
- 委任者内訳（大口の比率）、委任の流入出、VP 変動の安定度
- 上位 DRep 一覧 → クリックで個別分析（VP 推移チャート、委任者内訳、フロー履歴）

委任のシミュレーション機能は持たない。ここは読むための場所で、実際の委任は
ウォレット（Yoroi / Eternl / Lace 等）や GovTool で行うもの。

## データ

すべて [Koios](https://koios.rest/) の公開 API 由来。API キー不要の無料エンドポイントのみを使う。

`drep-snapshot.json` を GitHub Actions が **1 日 1 回** 作り直してコミットする。
ページは同一オリジンのこの JSON を読む。

なぜ直接 Koios を叩かないか: Koios は実 GET レスポンスに
`Access-Control-Allow-Origin` を返さないため、静的ホスティングに置いた
ページからブラウザで直接 fetch すると CORS で必ず失敗する。
（プリフライトだけは通るので気付きにくい。）

数字の粒度について: Koios は epoch 単位（1 epoch = 5 日）でしか履歴を返さない。
そのため「24 時間の変化」は取得できず、表示しているのは **前 epoch 比**。

`name_ja`（日本語表記）と `category`（企業・機関 / 個人など）はチェーン上に無い
手作業の分類なので、`tools/drep-curated.json` に置いて DRep ID で毎回引き継いでいる。
上位 50 に新しく入った DRep は、分類されるまで英語名・「不明」で表示される。

## 中身

| | |
|---|---|
| `index.html` | ページ本体（単体で開いても動く。その場合は埋め込みデータを使う） |
| `drep-snapshot.json` | 日次スナップショット（Actions が更新） |
| `tools/build-drep-snapshot.py` | 生成スクリプト。stdlib のみ、pip 不要 |
| `tools/check-drep-snapshot.py` | 空・欠損スナップショットのコミットを防ぐ検査 |
| `tools/drep-curated.json` | 日本語名・分類の手作業分 |
| `.github/workflows/drep-snapshot.yml` | 毎日 21:10 UTC（JST 06:10）+ 手動実行 |

手元で作り直す場合:

```bash
DREP_OUT=drep-snapshot.json python tools/build-drep-snapshot.py
DREP_OUT=drep-snapshot.json python tools/check-drep-snapshot.py
```

## ライセンス / 免責

数字は Koios 経由のオンチェーンデータをそのまま集計したもので、投資助言でも
委任先の推奨でもない。判断の材料として使うこと。
