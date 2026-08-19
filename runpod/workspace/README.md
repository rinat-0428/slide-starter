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

### Preview（速い・ラフ確認用）

1. ComfyUI の **Workflow → Open** から `/workspace/workflows/h3_preview.json` を読み込む
2. **Load Image** ノードにリファレンス画像をセット
3. **Prompt** に作りたい映像の説明を入れる
4. **Queue Prompt** を押す
5. 生成が終わると画面に動画が出る

### Quality（遅い・本番用）

手順は同じで、読み込むファイルが `/workspace/workflows/h3_quality.json` になるだけです。

### Preview と Quality の使い分け

| | Preview 🐇 | Quality 🐢 |
|---|---|---|
| 速さ | 速い | 遅い |
| 用途 | 構図・動きのラフ確認 | 最終版 |
| steps | 8 | 20 |
| 解像度 | 640×384 | 1280×720 |
| 長さ | 約2.5秒 | 約5秒 |

**まず Preview で試して、良さそうなら同じ prompt / seed で Quality。** これが一番速く仕上がります。

---

## 3. 保存先

生成した動画はここに入ります。

```
/workspace/outputs/<あなたの名前>/preview/
/workspace/outputs/<あなたの名前>/quality/
```

ファイル名の形式:

```
20260818_142233_yasu_quality_123456.mp4
 └日付   └時刻  └ユーザー └モード  └seed
```

### 自分専用のフォルダにするには

ワークフローを読み込んだあと、**Save Video** ノードの `filename_prefix` を見てください。

```
shared/preview/%date:yyyyMMdd_hhmmss%_shared_preview_%KSampler.seed%
└──┬──┘        
   ここの shared を自分の名前に変える（3か所）
```

またはターミナルで一発で作れます:

```bash
python3 /workspace/make-workflows.py --user yasu
```

> **他の人の output フォルダは触らないでください。**

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

## 5. 困ったときは

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

## 6. フォルダ構成

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

## 7. 管理者向けメモ

- 初回セットアップ: `bash /workspace/setup.sh`
- 自動起動の設定: Pod の **Container Start Command** に
  ``bash -lc 'mkdir -p /workspace/logs; nohup bash /workspace/start-comfyui.sh >> /workspace/logs/boot.log 2>&1 & exec /start.sh'``
  （`exec /start.sh` を残すのは、SSH / JupyterLab を殺さないため）
- 環境情報の更新: `bash /workspace/record-environment.sh`
- ComfyUI は **0.30.0 以降** が必要（H3 ネイティブ対応は PR #15224 / 2026-08-03 merge）
- モデル配布元: [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)
- ライセンス: MiniMax H3 Community License。**US / EU / UK / 韓国のリージョンでのセルフホストは対象外**。
  Pod は日本リージョン（AP-JP-1 など）で立てること。
