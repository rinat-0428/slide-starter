# 導入手順（管理者向け）

このディレクトリは **Pod にまだ何も無い状態から** ComfyUI + MiniMax H3 を立ち上げるための
ブートストラップ一式です。`workspace/` の中身をそのまま Pod の `/workspace` に置きます。

---

## 前提（2026-08-19 に RunPod コンソールで実機確認済み）

対象アカウント: **Chammi**（Team ID `cm3nq4s8s0002js08gjjilwhx` / owner `rina_t@hwpartners.io`）

| 項目 | 状態 |
|------|------|
| Team | **あり**（Chammi / メンバー3名） |
| クレジット残高 | **$135.73** |
| Pod | **なし**（`/pods` が `/deploy` にリダイレクト） |
| Network Volume | 2つあるが **どちらも US リージョン**（下記） |
| MFA | 未設定 |

### Team メンバー

| メンバー | ロール |
|----------|--------|
| rina_t@hwpartners.io | Admin |
| iamkirkperry@gmail.com | Admin |
| william@elevenzero.com | Dev |

Audit log を見ると 2025-06 に Pod の Start / Stop 履歴がありますが、
その Pod は現存しません（Terminate 済み）。

### 既存の Network Volume は今回は使えません

| 名前 | サイズ | データセンター | H3 に使えるか |
|------|--------|----------------|----------------|
| Kintsugi Workflow (S3) | 200 GB | **US-GA-2** | ✗ |
| Chammi Drive | 300 GB | **US-TX-3** | ✗ |

理由は2つあります。

1. **ライセンス** — H3 は US でのセルフホストがライセンス対象外
2. **構造** — Network Volume はデータセンターに固定され、跨いだ同期もできない

→ **AP-JP-1 に新しく Volume を作る必要があります。**

### 予算の目安

残高 $135.73 に対して:

| 内訳 | 単価 | $135.73 で |
|------|------|------------|
| H100 SXM | $3.29/hr | 約 **41 時間** |
| H200 SXM | $4.59/hr | 約 **29 時間** |
| Network Volume 300GB | $0.07/GB/月 | 約 $21/月 |

セットアップと検証には足りますが、**Stop し忘れると一晩で数十ドル溶けます。**
チーム展開前に Stop 運用を徹底してください。

**残りの準備:**

1. **AP-JP-1 に Network Volume を作成**（300GB 以上）
2. **Pod を作成**（Volume を添付）
3. MFA を有効化（推奨）

---

## 事前に決めること

### 1. リージョンは AP-JP-1（日本・福島）一択

MiniMax H3 の Community License は **US / EU / UK / 韓国でのセルフホスト（ローカル配備）を
ライセンス対象外** としています。制限がかかるのは「会社の所在地」ではなく **「実際に動かす場所」** です。

コンソールで確認したところ、**AP-JP-1 は選択可能**でした。ここで立ててください。
US / EU リージョンで立てるとライセンス違反になります。

### 2. GPU は実質 2択

AP-JP-1 でフィルタした結果、**利用可能なのは以下の2つだけ**でした。
RTX 4090 / L40S / RTX PRO 6000 / B200 などは **すべて Unavailable** です。

| GPU | VRAM | 価格 | 在庫 |
|-----|------|------|------|
| **H100 SXM** | 80GB | $3.29/hr | 1 max・**Low** |
| **H200 SXM** | 141GB / RAM 251GB / 20 vCPU | $4.59/hr | 3 max・**Low** |

H3 は pruned int8 構成なら DiT 19.5GB + TextEncoder 14.6GB + VAE 5.5GB ≒ **40GB** なので、
**H100 (80GB) でも十分動く見込み**です。まず H100 で試して、
720p で詰まるようなら H200 に上げるのが安く済みます。

**ただし両方とも在庫が "Low"、しかも 1〜3 台しかありません。** これが次の判断に直結します。

### 3. ストレージは Network Volume にする（重要）

指示書は「Terminate 禁止・Stop 運用」ですが、**Pod Volume のままだとこの運用は破綻します。**

RunPod は Pod を Stop すると GPU を解放し、他のユーザーがそれを借りられます。
Pod は物理マシンに紐づいたままなので、**再 Start 時にその GPU が埋まっていると起動できません**
（"Zero GPU Pods" 問題）。AP-JP-1 は在庫 Low で 1〜3 台しかないため、**これは頻繁に起きます。**

そうなると復旧手段は「Terminate して別マシンで作り直す」しかなく、
**Pod Volume は Terminate で消えるので、モデルも生成物も全部飛びます。**

**Network Volume を使えばこの問題ごと解決します。**

- Pod ではなく独立したストレージに `/workspace` が載る
- **Stop でも Terminate でも消えない**
- Zero GPU に当たっても、Terminate して別マシンで作り直し、同じ Volume を繋げば元通り
- コンソールで確認済み: **AP-JP-1 で Network Volume を作成できます**

| 項目 | 推奨 |
|------|------|
| サイズ | **300GB 以上**（モデル約60GB + 生成物） |
| 料金 | $0.07/GB/月 → 300GB で **約 $21/月** |
| 注意 | **Pod 作成時にしかアタッチできません**（後付け不可） |
| 注意 | サイズは後から増やせるが**減らせません** |
| 注意 | データセンターを跨いで同期はされません |

> チーム向けの「Terminate するな」というルールは README にそのまま残してあります。
> Network Volume があれば管理者は復旧できますが、
> **メンバーが気軽に Terminate を押す状況は作らない方が安全**なためです。

### 4. その他

| 項目 | 推奨 |
|------|------|
| クラウド種別 | **Secure Cloud**（Community Cloud より安定） |
| テンプレート | RunPod 公式の **PyTorch**（torch 同梱のものを選ぶ） |
| 公開ポート | **8188**（HTTP Service） |
| Team 権限 | メンバーに **Start / Stop** を許可。Terminate は可能なら管理者のみ |

> 生成時間の目安（launch-day レポート、環境依存）:
> RTX 3060 12GB で 864×480 / 124frames / 20steps が約9分、
> RTX 4090 Laptop 16GB で 960×540 / 5秒 が約182秒。
> H100 / H200 ならこれより大幅に速い見込みですが、**実測は要検証**です。

---

## 導入手順

### Step 1. Network Volume を作る

先に Volume を作ります（Pod 作成時にしかアタッチできないため）。

1. コンソール左の **Storage** → **Create Network Volume**
2. Data center: **Japan / AP-JP-1**
3. サイズ: **300GB 以上**
4. 名前: 例 `h3-shared`

### Step 1b. Pod を作る

- **Network volume**: Step 1 で作ったものを選択（`/workspace` にマウントされます）
- リージョン: **AP-JP-1**
- クラウド: **Secure Cloud**
- GPU: **H100 SXM**（足りなければ H200 SXM）
- テンプレート: PyTorch
- Expose HTTP Ports: `8188`

### Step 2. このディレクトリを Pod に送る

Pod の Web Terminal から取得するのが一番速いです。

```bash
cd /workspace && curl -fsSL -O https://raw.githubusercontent.com/<repo>/main/runpod/workspace/setup.sh
```

リポジトリを公開したくない場合は、Web Terminal で直接貼り付けるか、
`runpodctl send` でローカルから転送します。

```bash
runpodctl send runpod/workspace
```

`workspace/` の 5ファイルが `/workspace` 直下に並んでいれば OK です。

```
/workspace/setup.sh
/workspace/start-comfyui.sh
/workspace/make-workflows.py
/workspace/record-environment.sh
/workspace/README.md
```

### Step 3. セットアップを実行

```bash
bash /workspace/setup.sh
```

やっていること:

1. GPU / CUDA / ディスク容量のチェック
2. `/workspace` 配下にディレクトリを作成
3. `/workspace/venv` に Python 環境（コンテナの torch を再利用）
4. ComfyUI を clone + 依存インストール + **0.30.0 以降かを検証**
5. `extra_model_paths.yaml` を書いてモデル置き場を `/workspace/models/h3` に向ける
6. HuggingFace から H3 のモデルを取得（**ファイル名は決め打ちせず、リポジトリの一覧から正規表現で探す**）
7. 公式テンプレートから Preview / Quality ワークフローを生成
8. `ENVIRONMENT.md` を自動生成

40〜60GB のダウンロードがあるので、初回は時間がかかります。
冪等なので、途中で切れたら再実行してください。

環境変数で構成を変えられます。

```bash
H3_VARIANTS="ref2va" H3_DIT_QUANT="int8_convrot" bash /workspace/setup.sh
```

| 変数 | 既定 | 意味 |
|------|------|------|
| `H3_VARIANTS` | `ref2va fl2va` | ref2va=リファレンス画像→動画 / fl2va=T2V・最初と最後のフレーム |
| `H3_DIT_QUANT` | `pruned_int8_convrot` (19.5GB) | `int8_convrot` (31.7GB) / `bf16` (61.7GB) |
| `H3_TE_QUANT` | `nvfp4_awq` (14.6GB) | `int8_convrot` (25.3GB) / `bf16` (48.0GB) |

### Step 4. 自動起動を設定

Pod の設定 → **Container Start Command** を次に変更します。

```
bash -lc 'mkdir -p /workspace/logs; nohup bash /workspace/start-comfyui.sh >> /workspace/logs/boot.log 2>&1 & exec /start.sh'
```

**`exec /start.sh` を必ず残してください。** これはテンプレート本来の
エントリポイント（sshd / JupyterLab / RunPod agent）です。ここを消して
ComfyUI だけを起動する形にすると、**ComfyUI が落ちたときに Pod へ入る手段が無くなります。**

> 使っているテンプレートのエントリポイントが `/start.sh` でない場合があります。
> Pod 作成後に確認してから設定してください。
>
> ```bash
> cat /proc/1/cmdline | tr '\0' ' '; echo
> ```
>
> ```bash
> ls -la /start.sh /entrypoint.sh 2>/dev/null
> ```

`/workspace` は永続、コンテナは毎回作り直されるので、
「起動コマンドは Pod 設定側 / 中身は /workspace 側」という分担にしています。

### Step 5. 動作確認

```bash
bash /workspace/start-comfyui.sh
```

起動前チェックが走り、GPU・CUDA・モデル4種・ワークフローの有無をログに出します。
不足があればその場で分かります。

`Connect → HTTP Service [Port 8188]` を開いて ComfyUI が出れば成功です。

ComfyUI が起動した状態でワークフローを作り直すと、
`/object_info` からノード定義を取れるので **書き換えが正確になります**。

```bash
python3 /workspace/make-workflows.py --user yasu
```

### Step 6. 永続性の検証（完了条件）

1. Preview / Quality をそれぞれ1本生成する
2. Pod を **Stop**
3. Pod を **Start**
4. 以下が残っていることを確認する

```bash
ls -lh /workspace/models/h3/diffusion_models/
ls -lh /workspace/workflows/
ls -lhR /workspace/outputs/
```

5. 両ワークフローを再テストする
6. `ENVIRONMENT.md` の「動作確認」表を OK に更新する

```bash
bash /workspace/record-environment.sh
```

---

## 注意点 / 既知のリスク

### ワークフロー生成は「公式テンプレートの書き換え」方式

H3 のノードは 2026-08-03 に本体マージされたばかりで、ノード名・入力仕様が変わりえます。
JSON を手書きすると読み込めない事故が起きるので、
**ComfyUI 同梱の公式テンプレートを正として steps / 解像度 / フレーム数 / 保存先だけを差し替える**
方式にしています。

- ComfyUI 起動中に実行すると `/object_info` から正確に書き換わります
- 起動していない場合は推定で書き換え、**書き換えた内容を全部ログに出します**
- テンプレートが見つからない場合はエラーになるので、
  UI の `Workflow → Browse Templates` から H3 を開いて Export し、
  `--template` で渡してください

生成後は **UI で steps と保存先を目視確認** してください。

### seed のファイル名埋め込み

`%KSampler.seed%` はサンプラーノードの **タイトル** を参照します。
スクリプトは実際のノードタイトルを読んで組み立てますが、
UI でノード名を変えると壊れます。その場合はファイル名から seed が消えるだけで、生成自体は動きます。

### Prompt Rewriter

指示書どおり **今回は入れていません**。H3 本体の必須依存にしない方針です。
必要になったら、ComfyUI の custom node か外部 LLM を後付けする形で追加できます。

### Idle Stop

RunPod 側の自動 Stop は、生成中ジョブを落とすリスクがあるため **今回は設定していません**。
運用が回り始めてから、実際の生成時間を見て閾値を決めるのが安全です。
当面は README の「終わったら Stop」の周知で対応します。

---

## 出典

- [MiniMax H3 オープンソース化（公式）](https://www.minimax.io/news/minimax-h3-open-source)
- [MiniMaxAI/MiniMax-H3（HuggingFace）](https://huggingface.co/MiniMaxAI/MiniMax-H3)
- [Comfy-Org/MiniMax-H3（ComfyUI 向け再パッケージ）](https://huggingface.co/Comfy-Org/MiniMax-H3)
- [MiniMax H3 in ComfyUI（ComfyUI Wiki）](https://comfyui-wiki.com/en/tutorial/advanced/video/minimax/minimax-h3)
- [H3 Open Weights + ComfyUI 対応（ComfyUI Wiki, 2026-08-03）](https://comfyui-wiki.com/en/news/2026-08-03-minimax-h3-open-weights-comfyui)
- [ライセンスの地域制限について](https://explainx.ai/blog/minimax-h3-open-video-model-hailuo-july-2026)
- [RunPod AP-JP-1 福島リージョン](https://www.runpod.io/blog/runpod-apac-launch-fukushima)
- [ローカル実行のハードウェア要件](https://kingy.ai/ai/ai-guides/minimax-h3-comfyui-local-guide/)
- [RunPod ストレージの種類と永続性](https://docs.runpod.io/pods/storage/types)
- [Zero GPU Pods 問題（再 Start できない件）](https://docs.runpod.io/pods/troubleshooting/zero-gpus)
- [Network Volume の作成と料金](https://docs.runpod.io/pods/storage/create-network-volumes)

GPU の在庫・価格・リージョンは 2026-08-19 に RunPod コンソールで直接確認した値です。
変動するので、Pod 作成前にコンソールで再確認してください。
