# HTML Slide Starter — CLAUDE.md

## 概要

ブラウザで動く16:9 HTMLスライドの汎用テンプレート。
`engine/` と `theme/` は共通資産。デッキごとに `decks/{name}/index.html` を作成する。

## ディレクトリ構成

```
slide-starter/
├── CLAUDE.md              ← このファイル
├── design-guidelines.md   ← デザイン方針
├── plan.md                ← 構築ガイド
├── README.md              ← ユーザー向け説明書
├── engine/
│   ├── slide.css          ← 16:9ロック・ナビUI・PDF出力（触らない）
│   └── slide.js           ← キーボード操作・スケーリング・PDF（触らない）
├── theme/
│   └── sample.css           ← デザイントークン（カスタマイズはここだけ）
├── shared/                ← 共有アセット（画像・テクスチャなど）
└── decks/
    └── {deck-name}/
        └── index.html     ← デッキ本体
```

## 3層分離ルール

| 層 | ファイル | 役割 | 編集 |
|----|----------|------|------|
| Engine | `engine/slide.css`, `engine/slide.js` | 16:9ロック、ナビ、PDF出力、スケーリング | **禁止** |
| Theme | `theme/sample.css` | カラー・フォント・余白の変数、スライドタイプ、ユーティリティ | テーマ変更時のみ |
| Content | `decks/{name}/index.html` | 発表ごとのコンテンツ | **自由** |

## スライドタイプ一覧

| クラス | 用途 |
|--------|------|
| `slide-title` | タイトルスライド（パステルグラデ背景、最初の1枚） |
| `slide-content` | 汎用コンテンツ（本文・箇条書き・カード・図解）。`h2` にドット prefix 自動付与 |
| `slide-section` | セクション区切り（章立て） |
| `slide-statement` | ステートメント・橋渡し（パステルグラデ背景、中央揃え大テキスト） |
| `slide-landing` | 核心の一文（左線バー強調、`slide-statement` より落ち着いた強調） |
| `slide-end` | エンディング（パステルグラデ背景） |

## ユーティリティクラス

| クラス | 効果 |
|--------|------|
| `accent` | プライマリアクセント色テキスト（ブルー） |
| `accent-2` | ピンクテキスト（課題・問題提起） |
| `accent-3` | アンバーテキスト（強調・注意） |
| `accent-4` | グリーンテキスト（解決・ポジティブ） |
| `accent-5` | パープルテキスト（将来・拡張） |
| `muted` | サブ情報（半透明テキスト） |
| `mono` | モノスペースフォント |
| `bold` | 太字 |
| `divider` | 水平線 |
| `cols-2` | 2カラムグリッド |
| `cols-3` | 3カラムグリッド |
| `cols-4` | 4カラムグリッド |
| `list` | アクセント円付き箇条書き |
| `card` | ボーダー付きカード |
| `card-blue` / `card-pink` / `card-yellow` / `card-green` / `card-purple` | 上線カラーカード（フェーズ・ストリーム区分） |
| `badge` | ピルラベル（ブルー）。`badge-pink` / `badge-yellow` / `badge-green` / `badge-purple` バリアントあり |
| `highlight` | インラインキーワードハイライト（ブルー）。`highlight-pink` / `highlight-yellow` / `highlight-green` / `highlight-purple` バリアントあり |
| `flow` / `flow-step` / `flow-arrow` | フローチャート |
| `stat` / `.number` / `.label` | 数字ハイライト（KPIなど） |
| `tag` | モノスペースのタグバッジ |
| `slide-logo` | 左上ロゴ（`<img class="slide-logo">`） |
| `img-box` | 画像コンテナ（`object-fit: cover`） |
| `text-img` | テキスト+画像の横並びレイアウト |

## ロゴの使い方

`shared/logo/logo.png` に配置。スライド内に `<img>` タグで挿入:

```html
<section class="slide slide-content">
  <img class="slide-logo" src="../../shared/logo/logo.png" alt="Logo">
  <div class="body">...</div>
</section>
```

- 左上に半透明で表示される（`opacity: .35`、`height: 20px`）
- タイトル・コンテンツ・エンディングスライドに配置するのが一般的
- ステートメント・セクション区切りには置かないのが推奨

## 画像の使い方

デッキ固有の画像は `decks/{name}/assets/` に配置。

### テキスト+画像の横並び
```html
<div class="text-img">
  <div class="text"><p>テキスト</p></div>
  <div class="img-box"><img src="assets/sample.png" alt="説明"></div>
</div>
```

### 全幅画像スライド
```html
<section class="slide slide-content" style="padding: 0;">
  <div class="img-box" style="border-radius: 0;">
    <img src="assets/sample.png" alt="全幅画像">
  </div>
</section>
```

## 図解パターン

### フローチャート（横並び）
```html
<div class="flow">
  <div class="flow-step"><h3>Step 1</h3><p>説明</p></div>
  <div class="flow-arrow">→</div>
  <div class="flow-step"><h3>Step 2</h3><p>説明</p></div>
</div>
```

### カードグリッド（3カラム）
```html
<div class="cols-3">
  <div class="card"><span class="tag">01</span><h3>タイトル</h3><p>説明</p></div>
  <div class="card"><span class="tag">02</span><h3>タイトル</h3><p>説明</p></div>
  <div class="card"><span class="tag">03</span><h3>タイトル</h3><p>説明</p></div>
</div>
```

### 数字ハイライト
```html
<div class="cols-3">
  <div class="stat"><span class="number">42%</span><span class="label">説明</span></div>
  ...
</div>
```

## 新しいデッキを作るとき

1. `decks/` に新しいフォルダを作る（例: `decks/02_my-talk/`）
2. `decks/01_sample/index.html` をコピーして編集
3. `../../engine/` と `../../theme/` へのパスはそのまま維持
4. スライド総数を変えたら `slide-counter` の分母を更新

## PDF書き出し

### 方法
- UIの「PDF」ボタンをクリック、またはブラウザの印刷機能（Ctrl+P）
- URLパラメータ `?print-scale=120` でスケール調整可能

### 印刷時の注意事項

1. **CSS `background-image` は印刷で消える**
   - 背景画像を使う場合は `<img class="slide-bg-print">` をHTML内に埋め込む
   - 画面では非表示、印刷時のみ表示される

2. **フォントweight 300は印刷で極細になる**
   - engine/slide.css の print ルールで 400/600 の2段階に正規化済み

3. **rgba の低透明度は印刷でグレーになる**
   - `rgba(r,g,b, 0.05〜0.08)` は固定 hex に置換すること
   - デッキの `<style>` ブロック内に `@media print {}` で上書き

4. **ページサイズ**: 254mm × 142.875mm（16:9）

## キーボードショートカット

| キー | 操作 |
|------|------|
| → / ↓ / Space | 次のスライド |
| ← / ↑ | 前のスライド |
| F | フルスクリーン切替 |

## ソース素材の変換ルール（必須）

Markdown素材をスライドに変換する際、以下の3つのルールを厳守すること。

### ルール1: 原文表現の厳守

**ソース素材の表現をそのまま使う。言い換え・書き直しは禁止。** スライドは素材の「清書」ではなく「視覚的な再配置」である。

| 操作 | 可否 |
|------|------|
| 文を短く切る・改行で分割する | ○ |
| 箇条書きに再構成する | ○ |
| 説明文を省略して要点だけにする | ○（情報がスライド内のどこかにあれば） |
| です/ます → だ/である に変換 | ○ |
| 単語・比喩・言い回しを別の表現に置き換える | **× 禁止** |
| 口語表現をフォーマルに直す（「仕事」→「業務」等） | **× 禁止** |
| 会話的マーカー（「あ、」「実は」「つまり」等）を削除する | **× 禁止** |
| 具体例を別の例に差し替える | **× 禁止** |
| 結論文を別の文に入れ替える | **× 禁止** |

**特に注意**: ソース内で後のセクションに「伏線」として登場するキーワード（例: 前半で出した用語を後半で回収する構成）は、表現を変えると伏線が切れる。原文のキーワードを必ず保持すること。

**判断基準**: 迷ったら原文のまま。「スライドとして見栄えが良くなる」は変更の正当な理由にならない。

### ルール2: スライド化すべきコンテンツの検出

ソース素材の以下のパターンは**独立したスライド**にすること。隣接スライドに吸収したり省略してはならない。

**A. ステートメント → `slide-statement`**

著者の確信・結論・印象的な一文。スピーカーが間を取って強調するポイント。

検出基準:
- セクションの結論・要約文（「これが〜の理由です」「つまり〜ということだ」）
- 印象的な比喩・キャッチフレーズ（「頭脳に手足を与える」「全部やってくれる」等）
- 新しい概念セクションを導入するメタファー
- 聴衆の価値観を揺さぶる宣言文

**B. ブリッジ（論理的転換） → `slide-statement` または `slide-landing`**

修辞的な問いかけ・セクション間の転換文。聴衆が思考を切り替える「間」を作る。

検出基準:
- 「では、〜するには？」「ここで重要な問いは〜」等の修辞疑問
- 前のトピックを受けて次のトピックへ橋渡しする文

**C. トピック概観 → `slide-diagram` or `slide-grid`**

ソースが複数のサブトピックを列挙してから各論に入る構成の場合、詳細の前に全体像を見せる。

検出基準:
- 「〜と〜の2つがある」「3つのポイントがある」と予告してから各論に入る構成

**D. 比喩＋メカニズムの両立**

ソースが「比喩で説明 → 技術的な仕組みで補足」の構成を取っている場合、スライドでも両方を含める。比喩だけ残してメカニズムを落とさない。

### ルール3: 情報量の完全反映

**ソース素材の情報をスライドに100%反映させること。** 構成案の段階で、素材のすべての論点・具体例・データがいずれかのスライドにマッピングされていることを確認する。

- 素材の情報を省略・要約して間引かない
- 「1スライド1メッセージ」の原則とのバランスは、**スライド枚数を増やすことで解決する**（情報を削るのではなく、スライドを分割する）
- 構成案には、各スライドがソース素材のどの部分に対応するかを明示する
