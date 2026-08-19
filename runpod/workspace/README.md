# RunPod + ComfyUI + MiniMax H3 使い方

動画生成の共有環境です。**使うときだけ Start、終わったら Stop。**

```
Start  →  ComfyUI  →  生成  →  保存  →  Stop
```

---

## ⚠️ いちばん大事なルール

```
DO NOT TERMINATE THE POD.
Always use STOP after finishing your work.
```

- **Terminate は絶対に押さない** — モデル・ワークフロー・生成物が消える可能性があります
- **Stop は必ず押す** — 押し忘れると GPU 課金が流れ続けます
- Stop 中は GPU 課金が止まり、ストレージ代のみになります

---

## 1. 起動する

1. RunPod にログイン
2. Team の Pod を開く
3. **Start** を押す
4. 1〜2分待つ（ComfyUI が自動起動します）
5. Pod の **Connect → HTTP Service [Port 8188]** を開く
6. ComfyUI の画面が出れば OK

> 画面が出ないときは 30秒ほど待ってリロード。それでもダメなら「困ったときは」へ。

---

## 2. 動画を生成する

> 初回だけ「**テンプレート**」のポップアップが出ます。右上の **×** で閉じてください。

### Preview（速い・ラフ確認用）

1. 左端のアイコン列から **ワークフロー**（`w`）を開き、`h3_preview` をクリック
2. **「2件のエラーが見つかりました」と出ますが、正常です**（次の項で直します）
3. **画像を読み込む** ノード **2つとも** にリファレンス画像をセット
4. **Input Text (Prompt)** ノードに作りたい映像の説明を入れる
5. 上部の **実行する** を押す
6. 生成が終わると画面に動画が出る

### ⚠ 最初に必ず出る「2件のエラー」について

ワークフローを開くと、上部に赤くこう出ます。

```
2件のエラーが見つかりました
ワークフローを実行する前に解決してください
```

**壊れていません。** テンプレートに付属のサンプル画像名が入っているだけで、
その実ファイルが Pod に無いためです。次の手順で直ります。

1. **「詳細を表示」** をクリック → 右にパネルが開く
2. `画像を読み込む - image` が **2行** 出る。各行の右の **◇アイコン** を押すと該当ノードへ飛ぶ
3. ノード内の `画像: red_superboy_on_city_roof.png` の**ファイル名部分をクリック**して
   ドロップダウンから自分の画像を選ぶ
   - 動作確認だけなら `test_ref.png` が置いてあります
   - 自分の画像は **「アップロードするファイルを選択」** から
4. **もう1つの「画像を読み込む」も同じように差し替える**

2つとも直すとエラー表示が消え、実行できるようになります。

### Quality（遅い・本番用）

手順は同じで、開くワークフローが `h3_quality` になるだけです。
（こちらも同じく「2件のエラー」が出るので、同様に画像を2つ差し替えてください）

### Preview と Quality の使い分け

| | Preview 🐇 | Quality 🐢 |
|---|---|---|
| 速さ | **約5秒** | 数分 |
| 用途 | 構図・動きのラフ確認 | 最終版 |
| Lightning LoRA | ON | OFF |
| steps | 4 | 20 |
| 解像度 | 608×352 | 1280×736 |
| 長さ | 3秒 | 5秒 |

Preview が速いのは **Lightning LoRA**（少ステップ化）を有効にしているからです。
Quality はこれを切ってフルモデルで回します。

**まず Preview で試して、良さそうなら同じ prompt / seed で Quality。** これが一番速く仕上がります。

---

## 3. 保存先

生成した動画はここに入ります。

```
/workspace/outputs/<あなたの名前>/preview/
/workspace/outputs/<あなたの名前>/quality/
```

ファイル名は次のようになります。

```
shared_preview_00001_.mp4
```

`_00001_` は ComfyUI が自動で付ける連番です。

### 自分専用のフォルダにするには

ターミナルで一発で作れます。

```bash
python3 /workspace/make-workflows.py --user yasu
```

UI で直接変えたい場合は、**Save Video** ノードの `filename_prefix` の
`shared` の部分を自分の名前にしてください。

```
shared/preview/shared_preview
└─┬──┘         └─┬──┘
  ここ            ここ
```

> **他の人の output フォルダは触らないでください。**

### 日時と seed を入れたい場合

ComfyUI の UI からでは、ファイル名に日時や seed を自動で入れることはできません
（`%date:...%` は v0.33 の Save Video では展開されず、
`%ノード名.seed%` は画面上でしか解決されません）。

日時と seed を含む名前が必要なときは、ターミナルから投入してください。

```bash
python3 /workspace/queue-workflow.py --workflow /workspace/workflows/h3_preview.json --image あなたの画像.png --prompt "作りたい映像の説明"
```

この場合はこの形式で保存されます。

```
20260819_073639_shared_preview_12345_00001_.mp4
 └日付   └時刻  └ユーザー └モード  └seed
```

---

## 4. 終了する

1. 生成が終わったのを確認する
2. **必要な動画をダウンロードして保存する**
3. RunPod の画面に戻る
4. **Stop** を押す

Stop しても以下は残ります:

- ✅ モデル
- ✅ ワークフロー
- ✅ これまでの生成物
- ✅ ComfyUI の設定

消えるのは GPU の割り当てだけです。安心して Stop してください。

---

## 5. リファレンス画像の枚数を変える

このテンプレートは**リファレンス画像を0枚から何枚でも**受け付けます
（`ref_images` が可変長の入力グループになっているため）。
既定は2枚ですが、用途に合わせて作り直せます。

```bash
# 1枚だけ（キャラ1体を参照）
python3 /workspace/make-workflows.py --user yasu --refs 1 --ref-images achan.png

# 3枚（キャラ + 背景 + 小物 など）
python3 /workspace/make-workflows.py --user yasu --refs 3 --ref-images achan.png bg.png prop.png

# 枚数だけ決めて、画像は UI で選ぶ
python3 /workspace/make-workflows.py --user yasu --refs 1

# プロンプトも一緒に入れる
python3 /workspace/make-workflows.py --user yasu --refs 1 --ref-images achan.png \
  --prompt "Aちゃんが振り向いて笑う。カメラはゆっくり寄る"
```

画像ファイルは ComfyUI の input ディレクトリ（`/workspace/input/`）に置いたものを名前で指定します。
UI からアップロードした画像もここに入ります。

### プロンプトからの参照のしかた（重要）

プロンプト内では **`<Picture 1>` `<Picture 2>` …** で「何枚目の画像か」を指定します。
番号は **1始まり**です。

| ノード | プロンプトでの呼び名 |
|--------|----------------------|
| 1つ目の「画像を読み込む」 | `<Picture 1>` |
| 2つ目の「画像を読み込む」 | `<Picture 2>` |
| 3つ目 | `<Picture 3>` |

書き方の例:

```
Use <Picture 1> as the character reference and <Picture 2> as the background.
<Picture 1> の人物が振り向いて笑う。カメラはゆっくり寄る。
```

**枚数を減らしたら、プロンプト側の `<Picture N>` も必ず直してください。**
存在しない画像を指すと意図しない結果になります。
テンプレート付属の初期プロンプトは `<Picture 1>` と `<Picture 2>` を参照しているので、
1枚に減らす場合は `<Picture 2>` の記述を消す必要があります。

### 0枚にする場合

`--refs 0` でリファレンスなしにできますが、**r2v モデルでの動作は未検証**です。
テキストだけから作りたい場合は、ComfyUI のテンプレート一覧にある
**t2v（text-to-video）** のテンプレートを使う方が確実です。

---

## 6. 設定を変えるときの注意

解像度・長さ・steps は、**Save Video や生成ノードの数字を直接いじっても効きません。**
これらは専用のコントロールノードから供給されています。次のノードを触ってください。

| 変えたいもの | 触るノード |
|--------------|------------|
| 速さ / steps | `Boolean (Enable Lightning LoRA)`（ON=4 steps、OFF=20 steps） |
| 解像度 | `Resolution Selector (Size)` の megapixels（0.2=608×352 … 0.9=1280×736） |
| 長さ | `Float (Duration)`（秒） |
| プロンプト | `Input Text (Prompt)` |

---

## 7. 困ったときは

### ComfyUI の画面が開かない

Pod の **Web Terminal** を開いて、ログを見ます。

```bash
tail -50 $(ls -t /workspace/logs/comfyui_*.log | head -1)
```

手動で起動し直す場合:

```bash
bash /workspace/start-comfyui.sh
```

### 生成が途中で止まる / Out of memory

- Preview に切り替える
- 解像度を下げる（`width` / `height`）
- 長さを短くする（`length`）

### モデルが見つからないと言われる

```bash
bash /workspace/setup.sh
```

冪等なので、何度実行しても大丈夫です（既にあるものはスキップされます）。

### 容量を確認したい

```bash
du -sh /workspace/*
```

```bash
df -h /workspace
```

### 生成物を整理したい

**自分のフォルダだけ** 消してください。

```bash
ls -lh /workspace/outputs/<あなたの名前>/preview/
```

---

## 8. フォルダ構成

```
/workspace/
├── comfyui/            ComfyUI 本体
├── venv/               Python 環境
├── models/h3/          MiniMax H3 のモデル
│   ├── diffusion_models/
│   ├── text_encoders/
│   └── vae/
├── workflows/
│   ├── h3_preview.json
│   └── h3_quality.json
├── outputs/            ← 生成物（ユーザーごと）
│   ├── yasu/
│   ├── member_01/
│   └── shared/
├── input/              ← リファレンス画像の置き場
├── logs/               ComfyUI のログ
├── setup.sh            セットアップ（初回のみ）
├── start-comfyui.sh    起動スクリプト
├── make-workflows.py   ワークフロー生成
├── README.md           このファイル
└── ENVIRONMENT.md      環境の記録
```

---

## 9. 管理者向けメモ

- 初回セットアップ: `bash /workspace/setup.sh`
- 自動起動の設定: Pod の **Container Start Command** に
  ``bash -lc 'mkdir -p /workspace/logs; nohup bash /workspace/start-comfyui.sh >> /workspace/logs/boot.log 2>&1 & exec /start.sh'``
  （`exec /start.sh` を残すのは、SSH / JupyterLab を殺さないため）
- 環境情報の更新: `bash /workspace/record-environment.sh`
- ComfyUI は **0.30.0 以降** が必要（H3 ネイティブ対応は PR #15224 / 2026-08-03 merge）
- モデル配布元: [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)
- ライセンス: MiniMax H3 Community License。**US / EU / UK / 韓国のリージョンでのセルフホストは対象外**。
  Pod は日本リージョン（AP-JP-1 など）で立てること。
