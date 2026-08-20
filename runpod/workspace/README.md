# RunPod + ComfyUI + MiniMax H3 使い方

動画生成の共有環境です。**使うときだけ Start、終わったら Stop。**

```
Start  →  ComfyUI  →  生成  →  保存  →  Stop
```

---

## ⚠️ いちばん大事なルール

- **終わったら必ず Stop** — 押し忘れると GPU 課金が流れ続けます（1時間$3〜5）
- Stop 中は GPU 課金が止まり、ストレージ代のみになります

### Terminate について

**データは Network Volume（`h3-shared`）にあるので、Terminate しても消えません。**
モデル65GBもワークフローも生成物も残ります。

ただし、**他の人が使っている最中かもしれない**ので、
Terminate する前に一声かけてください。

> 以前は「Terminate 絶対禁止」でしたが、
> データがボリューム側にある構成に変えたのでルールを更新しました。

### Start できないときは作り直す

「**Your Pod's GPUs are no longer available**」が出ることがあります。
AP-JP-1 は GPU の台数が少なく、Stop 中に他の人に取られると起きます。

このとき出る選択肢のうち、**「Automatically migrate your Pod data」は選ばないでください。**
ボリュームが外れて、モデルも生成物も見えなくなります。

**「Do nothing」を選んで閉じ、作り直してください。**

1. Pods → ⋮ → **Terminate Pod**

   > ### 🚨 ここだけ絶対に間違えないでください
   >
   > 確認ダイアログに、このチェックボックスがあります。
   >
   > ```
   > ☐ Also delete attached network volume ⚠ (h3-shared) (200 GB)
   > ```
   >
   > **必ずオフのままにしてください。** 既定はオフです。
   > チェックを入れると **モデル65GB・ワークフロー・生成物がすべて消えます**
   > （再構築に1時間以上かかります）。
   >
   > オフなら、消えるのは Pod の設定とコンテナだけです。

2. **Deploy** を押す
3. **Pod template を必ず `h3-comfyui` に変更する**

   > ### 🚨 ここも絶対に忘れないでください
   >
   > Deploy 画面の Pod template は、既定で **`Runpod Pytorch 2.4.0`** になっています。
   > **これは今回使うテンプレートではありません。**
   >
   > **`Change template` を押して `h3-comfyui` を選び直してください。**
   >
   > 変更し忘れると、こうなります。
   >
   > - **ComfyUI が自動起動しない**（起動コマンドが入っていないため）
   > - **Port 8188 が開かない**（ポート設定が入っていないため）
   > - PyTorch が 2.4.0（2024年相当）で、H3 には古い
   >
   > 一見デプロイは成功するので、**8188 が Ready にならなくて初めて気づきます。**
   > その場合は作り直しになるので、Deploy を押す前に必ず確認してください。
   >
   > **確認方法**: Deploy ボタンの上の Pod summary に
   > **`Template overrides applied`** のバッジが出ていればOKです。

4. Network volume に **`h3-shared`** を選ぶ（リージョンは自動で AP-JP-1 になります）
5. GPU は **H100 SXM** か **H200 SXM** の空いている方
6. **Deploy** を押す前に、もう一度この2つを目視で確認する
   - Pod template = **`h3-comfyui`**
   - Network volume = **`h3-shared`**
7. Deploy

**セットアップのやり直しは不要**です。1〜2分で ComfyUI が自動起動し、
すぐ生成できます。Stop→Start より作り直しの方が成功しやすいので、
遠慮なく作り直してください。

### GPU が空いているかを確認する方法

Deploy する前に、いま使える GPU を確認できます。

**1.** RunPod コンソール → **Pods** → **Deploy**

**2.** 上の **Network volume** ドロップダウンから **`h3-shared`** を選ぶ

選ぶとこう表示されます。

> Region is locked to AP-JP-1 because network volume "h3-shared" is attached.

**この絞り込みが重要です。** リージョンが AP-JP-1 に固定され、
**実際に使える範囲だけ**が表示されます。絞り込まないと世界中の在庫が出てしまい、
「空いている」と思って選んでもデプロイできません。

**3.** GPU カードの右下のバッジを見る

| 表示 | 意味 |
|------|------|
| **Unavailable**（灰色） | **使えない**。選択できません |
| **Low**（赤） | 空きは少ないが **使えます** |
| **Medium**（橙） | 余裕あり |
| **High**（緑） | 潤沢 |

> **⚠ 赤い「Low」は「使えない」という意味ではありません。**
> 空きが少ないだけで、Deploy は通ります。
> 本当にダメなのは灰色の **Unavailable** だけです。

**どちらを選ぶか**

| GPU | VRAM | 価格 | 備考 |
|-----|------|------|------|
| **H100 SXM** | 80GB | $3.29/hr | **こちらで十分**。実測 Preview 約5秒 / Quality 約7分 |
| H200 SXM | 141GB | $4.59/hr | H100 が Unavailable のとき |

**空いていれば H100 を選んでください。** 安いうえ、性能的にも足りています。

**補足: 「N max」の意味**

`2 max` `4 max` という表示は、**1つの Pod に何枚 GPU を載せられるか**です。
空き台数ではありません。今回は1枚しか使わないので**無視して構いません**。

**⚠ この表示は数分で変わります。** さっき Unavailable だったものが
数分後には Low になっていることが普通にあります。
**Deploy する直前に見る**のが正しい使い方で、事前に確認して時間を置くと意味がありません。


---

## 1. 起動する

1. RunPod にログイン
2. Pods を開く
3. Pod があれば **Start**。無ければ **Deploy**（下の「作り直す」参照）
4. 1〜2分待つ（ComfyUI が自動起動します）
5. Pod の **Connect → HTTP Service [Port 8188]** を開く
6. ComfyUI の画面が出れば OK

> 画面が出ないときは 30秒ほど待ってリロード。それでもダメなら「困ったときは」へ。

---

## 2. 動画を生成する

> 初回だけ「**テンプレート**」のポップアップが出ます。右上の **×** で閉じてください。

### 用意されているワークフロー

左サイドバーの **ワークフロー**（`w`）に4本あります。**用途で選んでください。**

| 名前 | 内容 |
|------|------|
| `h3_preview` | 標準・速い確認用（画像2枚） |
| `h3_quality` | 標準・本番用（画像2枚） |
| **`h3_preview_6ref_audio`** | **画像6枚 + 音声1つ**・速い確認用 |
| **`h3_quality_6ref_audio`** | **画像6枚 + 音声1つ**・本番用 |

`6ref_audio` 版は、**ノードの追加や配線はすべて済んでいます。**
開いたら画像7か所（画像6 + 音声1）のファイルを差し替えて、プロンプトを書くだけです。

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

> 次に使う人のことを考えると、Terminate してしまう方が親切な場合もあります。
> Stop 中の Pod は特定のマシンを押さえたままになるためです。
> 迷ったら Stop で構いません。

Stop しても以下は残ります:

- ✅ モデル
- ✅ ワークフロー
- ✅ これまでの生成物
- ✅ ComfyUI の設定

消えるのは GPU の割り当てだけです。安心して Stop してください。

---

## 5. リファレンス画像を何枚つけるか

このワークフローは**リファレンス画像を0枚から何枚でも**受け付けます。
既定は**2枚**です。用途に合わせて変えてください。

| 枚数 | よくある用途 |
|------|--------------|
| 1枚 | キャラを1体だけ参照させる |
| 2枚（既定） | キャラ + 背景 / 2カット目の指定 など |
| 3枚以上 | キャラ + 背景 + 小物、複数キャラ など |

### 先に: 画像の置き場所

リファレンス画像は ComfyUI の **input フォルダ**に入っている必要があります。

```
/workspace/input/
```

**UI からアップロードすれば自動でここに入ります**（「画像を読み込む」ノードの
`アップロードするファイルを選択` ボタン）。Jupyter のファイルブラウザから
`/workspace/input/` に直接置いてもOKです。

---

### ケースA: 1枚だけ使う

**方法1: ターミナルで作り直す（かんたん）**

```bash
python3 /workspace/make-workflows.py --user yasu --refs 1 --ref-images achan.png
```

**方法2: UI だけで済ませる**

1. ワークフローを開く
2. 「画像を読み込む」ノードが**2つ**あるので、**2つ目を選択して Delete キー**で削除
3. 残った1つに画像をセット
4. **プロンプトから `<Picture 2>` の記述を消す**（下の「プロンプトの書き方」参照）

> 削除せずに、**2つとも同じ画像**を入れる手もあります。いちばん手数が少ないですが、
> モデルには「同じ画像が2枚」と伝わるので、厳密に1枚にしたいなら削除してください。

---

### ケースB: 2枚使う（既定・そのまま使える）

作り直し不要です。ワークフローを開いて、**2つの「画像を読み込む」ノードに
それぞれ画像をセット**するだけです。

ターミナルから画像も指定してしまう場合:

```bash
python3 /workspace/make-workflows.py --user yasu --refs 2 --ref-images achan.png bg.png
```

---

### ケースC: 3枚以上使う

**方法1: ターミナルで作り直す（推奨）**

```bash
# 3枚
python3 /workspace/make-workflows.py --user yasu --refs 3 \
  --ref-images achan.png bg.png prop.png

# 4枚
python3 /workspace/make-workflows.py --user yasu --refs 4 \
  --ref-images a.png b.png c.png d.png
```

必要な数の「画像を読み込む」ノードが自動で作られ、正しい入力につながります。

**方法2: UI で1つずつ足す**

`MiniMax H3 Reference To Video` ノードの入力側を見ると、
使っていない **`ref_image_2`** という空きスロットがあります（常に1つ空いています）。

1. キャンバスの何もない所を**ダブルクリック** → 検索窓に **`画像`** と入力し、
   **「画像を読み込む」** を選ぶ
2. 追加した「画像を読み込む」の **IMAGE 出力**から、
   `ref_image_2` の**入力の丸**へドラッグしてつなぐ
3. つなぐと、その下に新しい空きスロット `ref_image_3` が自動で増えます
4. 4枚目以降も同じ繰り返し

> 画像を指定するだけならターミナルの方が速くて確実です。
> UI で足すのは、既に作業中のワークフローに1枚だけ追加したいときに向いています。

---

### 音声リファレンス（.wav など）を付ける

このノードには**音声用の入力スロット**（`ref_audios.ref_audio_0`）も用意されています。
「この声で喋らせる」「このBGMに合わせる」といった参照に使えます。

**ターミナルで作る**

```bash
# 画像6枚 + 音声1つ
python3 /workspace/make-workflows.py --user yasu \
  --refs 6 --ref-images a.png b.png c.png d.png e.png f.png \
  --ref-audios voice.wav
```

**音声だけ足す**（画像はテンプレートのまま2枚）

```bash
python3 /workspace/make-workflows.py --user yasu --ref-audios voice.wav
```

**UI で足す**（実機で確認済みのノード名）

1. キャンバスの空白を**ダブルクリック** → 検索窓に **`音声`** と入力
2. 一番上に出る **「音声を読み込む」**（カテゴリ: オーディオ）を選ぶ
3. `MiniMax H3 Reference To Video` ノードの **`ref_audio_0`** の入力の丸へ、
   追加したノードの **AUDIO 出力**からドラッグしてつなぐ

> 画像側のノード名は **「画像を読み込む」** です。
> 検索窓は日本語で引けます（`Load Audio` など英語名では出ません）。

音声ファイルも画像と同じ **`/workspace/input/`** に置きます
（UI の `アップロードするファイルを選択` からでも入ります）。

**プロンプトからの参照は `<Audio 1>`**

```
<Picture 1> の人物が <Audio 1> の声で話す。
Use <Picture 1> as the character and <Audio 1> exactly as it is.
```

> テンプレート付属の初期プロンプトも `<Audio 1>` を参照する書き方になっています。

**実機で検証済み（2026-08-20 / H100 80GB）**

画像6枚 + 音声1つ（3秒 wav）で生成が通ることを確認しています。

| 項目 | 結果 |
|------|------|
| 生成時間 | **125秒**（Preview / モデルのコールドロード込み） |
| 出力 | 146KB の MP4 |
| 映像 | h264 / 608×352 / 3.04秒 |
| 音声 | **aac / 32kHz / 3.04秒（音声トラックあり）** |

H3 は映像と音声を同時に生成するモデルなので、**出力 MP4 には音声が入ります。**
リファレンス音声を付けなくても音声トラックは付きます。

---

### プロンプトの書き方（枚数を変えたら必ず読む）

プロンプトの中では **`<Picture 1>` `<Picture 2>` …** で「何枚目の画像か」を指します。
番号は **1始まり**です。

| ノードの並び順 | プロンプトでの呼び名 |
|----------------|----------------------|
| 1つ目の「画像を読み込む」 | `<Picture 1>` |
| 2つ目 | `<Picture 2>` |
| 3つ目 | `<Picture 3>` |
| 1つ目の「Load Audio」 | `<Audio 1>` |

書き方の例:

```
<Picture 1> の人物が振り向いて笑う。背景は <Picture 2> の場所。
カメラはゆっくり寄る。
```

```
Use <Picture 1> as the character reference and <Picture 2> as the background.
```

**⚠ 枚数を減らしたら、プロンプトの `<Picture N>` も必ず直してください。**

テンプレート付属の初期プロンプトは `<Picture 1>` と `<Picture 2>` の**両方**を
参照しています。1枚に減らしたのに `<Picture 2>` が残っていると、
存在しない画像を指すことになり、結果が意図しないものになります。

ターミナルから同時に指定してしまうのが確実です。

```bash
python3 /workspace/make-workflows.py --user yasu --refs 1 --ref-images achan.png \
  --prompt "<Picture 1> の人物が振り向いて笑う。カメラはゆっくり寄る"
```

---

### 0枚にしたい場合

`--refs 0` でリファレンスなしにできます。**実機で動作確認済み**です
（H100 / 145秒で生成完了）。プロンプトだけで生成したいときに使えます。

```bash
python3 /workspace/make-workflows.py --user yasu --refs 0 \
  --prompt "a red sphere slowly rotating on a dark background"
```

UI でやる場合は「画像を読み込む」ノードを2つとも削除してください。
プロンプトから `<Picture 1>` `<Picture 2>` の記述も消します。

---

### コマンド早見表

| やりたいこと | コマンド |
|--------------|----------|
| 1枚 | `--refs 1 --ref-images a.png` |
| 2枚 | `--refs 2 --ref-images a.png b.png` |
| 3枚 | `--refs 3 --ref-images a.png b.png c.png` |
| 枚数だけ変えて画像はUIで選ぶ | `--refs 3` |
| 音声を付ける | `--ref-audios voice.wav` |
| 画像6枚 + 音声1つ | `--refs 6 --ref-images a.png b.png c.png d.png e.png f.png --ref-audios voice.wav` |
| プロンプトも一緒に | `--prompt "..."` |
| 自分用フォルダに出す | `--user yasu` |

すべて `python3 /workspace/make-workflows.py` に付けます。
作り直すと `h3_preview` と `h3_quality` の**両方**が更新されます。

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
