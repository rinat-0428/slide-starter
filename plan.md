# 構築ガイド — HTML Slide Starter

このドキュメントは、slide-starter テンプレートの設計意図と拡張方法を説明する。

---

## アーキテクチャ

### 3層分離モデル

```
Engine層 (engine/)     ── 表示ロジック（触らない）
  ↑ CSS変数で接続
Theme層 (theme/)       ── デザイントークン（テーマ変更時のみ）
  ↑ classで接続
Content層 (decks/)     ── 発表内容（自由に編集）
```

**なぜ分離するのか:**
- Engine を修正すると全デッキに自動反映される（バグ修正・機能追加）
- Theme を差し替えるだけでデザインを一括変更できる
- Content は他の層に依存しないので、素材に集中できる

### ファイル参照パス

デッキは `decks/{name}/index.html` に配置する。エンジン・テーマへの参照は相対パス:

```html
<link rel="stylesheet" href="../../engine/slide.css">
<link rel="stylesheet" href="../../theme/sample.css">
<script src="../../engine/slide.js"></script>
```

## 新しいデッキを作る手順

1. `decks/` にフォルダを作成（例: `decks/02_my-talk/`）
2. `decks/01_sample/index.html` をコピー
3. スライドの `<section>` を編集・追加・削除
4. `slide-counter` の分母をスライド総数に合わせる
5. ブラウザで開いて確認

## 新しいスライドタイプを追加する手順

1. `theme/sample.css` にスタイルを追加
2. クラス名は `.slide-{type}` の命名規則に従う
3. `<section class="slide slide-{type}">` で使用
4. `CLAUDE.md` のスライドタイプ一覧に追記

## 新しいユーティリティを追加する手順

1. `theme/sample.css` の「ユーティリティクラス」セクションに追加
2. CSS変数を活用して、テーマ変更に追従させる
3. `CLAUDE.md` のユーティリティ一覧に追記

## PDF書き出しの仕組み

### Engine側の処理

1. `slide.js` の `exportPDF()` が `window.print()` を呼ぶ
2. `slide.css` の `@media print` ルールが適用される:
   - 全スライドを `display: flex` で表示（通常は `.is-active` のみ）
   - `position: static` で縦に並べる
   - `break-after: page` でページ区切り
   - ナビUIを非表示

### ページサイズ
- `@page { size: 254mm 142.875mm }` — 16:9比率
- ブラウザの印刷設定で「余白なし」「背景のグラフィック」をONにする

### 印刷で崩れるパターンと対策

| 問題 | 原因 | 対策 |
|------|------|------|
| CSS背景画像が消える | Chromeが `background-image` を無視 | `<img class="slide-bg-print">` をHTML内に配置 |
| フォントが極細になる | weight 300 は画面のAAに依存 | print ルールで 400/600 に正規化（engine 側で対応済み） |
| rgba の薄い色がグレーに | 低透明度の色変換バグ | `@media print` で固定 hex に上書き |
| 丸が楕円になる | aspect-ratio が効かない環境 | print ルールで `aspect-ratio: 1/1` を明示（engine 側で対応済み） |

### スケール調整

URLパラメータで印刷時のスケールを変更可能:

```
index.html?print-scale=120   → 120%に拡大
index.html?print-scale=80    → 80%に縮小
```

## テーマ拡張

### ライトテーマを作る場合

`theme/light.css` を新規作成し、変数を上書き:

```css
:root {
  --color-chrome:  #f5f5f5;
  --color-bg:      #ffffff;
  --color-fg:      #1a1a1a;
  --color-muted:   rgba(26,26,26,.5);
  --color-accent:  #059669;
  --color-border:  rgba(26,26,26,.1);
  --color-card-bg: rgba(0,0,0,.03);
}
```

デッキの `<link>` を `../../theme/light.css` に変更するだけで適用される。

## Vercelデプロイ

```bash
cd slide-starter
vercel
```

- `decks/01_sample/index.html` がそのままURLで共有可能
- 静的ファイルのみなのでビルド不要、数秒でデプロイ完了

## 設計判断メモ

- **なぜピクセル固定か**: CSSの `transform: scale()` でビューポートにフィットさせるため。レスポンシブではなくスケーリング方式を採用
- **なぜ `@media print` か**: ブラウザネイティブのPDF書き出しが最もポータブル。外部ツール不要
- **なぜ番号（`.num`）を廃止したか**: 自動ナンバリングではないため、スライド追加・並べ替え時に手動更新が必要で煩雑。代わりに `tag` クラスで明示的に番号を振る方が柔軟
- **なぜ `shared/` を用意するか**: 複数デッキで共有するアセット（ロゴ、テクスチャ等）の置き場所。デッキごとに画像を重複させない
