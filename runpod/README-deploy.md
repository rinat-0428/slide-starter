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

## 構築済みの環境（2026-08-19 実機構築）

| 項目 | 値 |
|------|-----|
| Pod 名 | `colossal_aqua_mite` |
| Pod ID | `d331tpnh4fx4tu` |
| リージョン | **AP-JP-1**（Network Volume により自動ロック） |
| GPU | **NVIDIA H200 141GB** / $4.59/hr（当初 H100 80GB $3.29/hr で構築、在庫切れで移行） |
| テンプレート | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`（torch 2.8.0 / CUDA 12.8） |
| Network Volume | `h3-shared` / 200GB / AP-JP-1 / ID `aagj8f1j6a` |
| Container disk | 30GB（一時領域） |
| 公開ポート | HTTP `8888`(Jupyter), `8188`(ComfyUI) / TCP `22` |
| 実行コスト | 約 $3.31/hr（GPU + ディスク + Volume） |

**Pod 作成時にテンプレートを PyTorch 2.4.0 から 2.8.0 に変更しています。**
既定の 2.4.0 は 2024 年相当で、ComfyUI 0.30+ / H3 には古いためです。

### スクリプトの配布方法

`runpod/workspace/` はこのリポジトリに入っているので、Pod 側では curl で取得できます。

```bash
cd /workspace && B=https://raw.githubusercontent.com/rinat-0428/slide-starter/main/runpod/workspace && \
for f in setup.sh start-comfyui.sh make-workflows.py record-environment.sh README.md; do
  curl -fsSL -O $B/$f
done; chmod +x *.sh *.py
```

Pod を作り直したときも、この 1 コマンドで復旧できます。

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

### Step 4. 自動起動を設定（実機で設定・検証済み）

Pod の設定 → **Container Start Command** を次に変更します。

```
bash -lc 'mkdir -p /workspace/logs; nohup bash /workspace/start-comfyui.sh >> /workspace/logs/boot.log 2>&1 & exec /start.sh'
```

実機で `PID1: /sbin/docker-init -- /opt/nvidia/nvidia_entrypoint.sh /start.sh` を確認済みです。

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

## 運用ポリシー：Pod は使い捨てにする（2026-08-19 更新）

**Stop / Start をやめて、Terminate / Deploy に切り替えました。** 理由は2つです。

### 1. Stop した Pod は「その物理マシン1台」に紐づく

Start はそのマシンの空きを待つ動作で、データセンター全体の空きを探しません。
AP-JP-1 は H100 が1台、H200 が3台程度しかない小さな DC なので、
Stop 中に取られると Start できなくなります。**実際に1日で2回起きました。**

| | 探す範囲 |
|---|---|
| Stop → Start | **その1台だけ** |
| **Terminate → Deploy** | **AP-JP-1 全体の空き** |

### 2. Terminate してもデータが消えない構成になっている

`/workspace` は Network Volume `h3-shared` 上にあります。
Terminate で消えるのはコンテナだけで、モデル65GB・ワークフロー・生成物は残ります。
**再セットアップは不要**で、Deploy から1〜2分で ComfyUI が自動起動します。

> 元の指示書の「Terminate 禁止」は、データが Pod 側にある前提のルールでした。
> ネットワークボリューム構成にした時点で前提が変わっています。

### 作り直しを3クリックにするテンプレート

毎回テンプレート・ポート・起動コマンドを手入力すると間違えるので、
Pod 設定を **テンプレート `h3-comfyui`** として保存済みです（Private / ID `51dm0pkdia`）。

| 保存済みの内容 | 値 |
|---|---|
| Container image | `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` |
| Container start command | ComfyUI 自動起動 + `exec /start.sh` |
| Container disk | 30GB |
| HTTP ports | `Jupyter:8888` / `ComfyUI:8188` |
| TCP ports | `SSH:22` |

作り直し手順:

0. Pods → ⋮ → **Terminate Pod**
   **確認ダイアログの「Also delete attached network volume (h3-shared)」は
   絶対にチェックしないこと。** 入れると 65GB のモデルと全生成物が消える。
   既定はオフなので、そのまま Terminate Pod を押せばよい。
1. **Deploy** → **Pod template を必ず `h3-comfyui` に変更する**

   既定は **`Runpod Pytorch 2.4.0`** で、これは使わない。
   `Change template` から選び直すこと。忘れると起動コマンドもポート設定も
   入らないため、**ComfyUI が自動起動せず 8188 も開かない**。
   デプロイ自体は成功してしまうので気づきにくい。
   Pod summary に **`Template overrides applied`** が出ていれば正しい。

   > 実際に構築時、テンプレート選択で Community 製の別テンプレート
   > (`smyshnikof/comfyui`) を掴んでしまったことがある。
   > 選んだあとに image 名が
   > `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` になっているか目視すること。

2. Network volume に **`h3-shared`** を選ぶ（リージョンが AP-JP-1 に自動ロック）
3. GPU は **H100 SXM**（$3.29/hr）か **H200 SXM**（$4.59/hr）の空いている方

   在庫はバッジで判断する。**灰色の Unavailable だけが使えない**表示で、
   赤い **Low は「空きが少ない」だけで使える**。ここを誤解しやすい。
   `N max` は 1 Pod に載せられる GPU 枚数で、空き台数ではない。
   表示は数分で変わるので、**Deploy 直前に見ること**。
   （手順の詳細は チーム向け README の「GPU が空いているかを確認する方法」）
4. Deploy

> ボリュームと GPU はテンプレートに含まれません（デプロイ時に選ぶ項目のため）。
> ここだけ毎回選んでください。

### 合わせて守ること

- **まとめて使う** — 起動回数そのものを減らすのが一番効きます
- **URL を配らない** — Pod を作り直すと ID が変わり `https://xxxx-8188.proxy.runpod.net` も変わります。
  チームには「RunPod コンソール → Connect から開く」と伝えてください

### それでも足りない場合

| 案 | 評価 |
|---|---|
| H100用とH200用の Pod を2台止めて置く | **効果が薄い**。特定マシン1台への紐づきが2つできるだけで、GPU を予約はしない |
| インド（AP-IN-1）を第2拠点に | H100 のみ・Low で AP-JP-1 と大差なし。65GB 再取得と月$14 の追加ボリュームが必要 |
| Reserved（予約インスタンス） | 容量を確保できるが 12か月以上の契約。毎日使う本番運用になってから |
| 使う間は落とさない | 確実だが $3〜5/hr。集中作業日はこれが一番安全 |

---

## Zero GPU Pods に実際に遭遇した記録（2026-08-19）

Stop した Pod を Start しようとしたところ、想定どおり
「Your Pod's GPUs are no longer available.」が出ました。**AP-JP-1 の H100 は 1 台しかなく、
Stop 中に他のユーザーに取られたためです。**

このとき RunPod は3つの選択肢を出しますが、**「Automatically migrate your Pod data」を選んではいけません。**

- ネットワークボリュームは**データセンターに固定**される。移行先が AP-JP-1 の外になると
  `h3-shared` が付いてこず、65GB のモデルも生成物も参照できなくなる
- US / EU に移ると **H3 のライセンス違反**になる
- そもそも中身は全部ネットワークボリューム側なので、移行対象の「Pod のデータ」は実質ない

**正しい対処は「Do nothing」を選び、Terminate して同じボリュームで作り直すこと。**
Deploy 画面で `h3-shared` を選べばリージョンは自動で AP-JP-1 にロックされます。

実際の復旧はこうなりました。

1. Deploy 画面で `h3-shared` を選択 → AP-JP-1 に自動ロック
2. 在庫を確認 → H100 は Unavailable、**H200 は Low（空きあり）**
3. H200 + PyTorch 2.8.0 + ポート `8888,8188` + Start command で Deploy
4. **セットアップのやり直しは不要。** 1〜2分で ComfyUI が自動起動し、そのまま生成できた

GPU が H100 → H200 に変わっても、`/workspace` は同一なのでそのまま動きます。

---

## 実機で判明した仕様（重要）

構築中に踏んだ落とし穴です。次に触る人が同じ所で止まらないよう残します。

### 1. パラメータはコントロールノードから供給されている

公式テンプレートは `width` / `height` / `length` / `steps` を、
**対象ノードのウィジェットではなく専用のコントロールノードからのリンク**で供給します。

```
Boolean (Enable Lightning LoRA) ─┬→ If/Else Switch (model) → UNet か LoRA 経路
                                 └→ If/Else Switch (Steps) → 4 か 20
Resolution Selector (Size)       → width / height
Float (Duration)                 → 数式ノード → length（フレーム数）
Input Text (Prompt)              → prompt
```

**生成ノード側の数値を書き換えても一切効きません。** 必ず上記を触ること。
`make-workflows.py` はノードのタイトルでこれらを特定して書き換えます。

megapixels と解像度の対応（16:9 / multiple=32、テンプレート同梱の表より）:

| megapixels | 解像度 |
|---|---|
| 0.2 | 608 × 352 |
| 0.4 | 864 × 480 |
| 0.7 | 1152 × 640 |
| 0.9 | 1280 × 736 |

### 2. Turbo (Lightning) LoRA が必須

公式テンプレートは LoRA ノードを含むため、ファイルが無いと
`lora_name: not in []` で検証落ちします。`setup.sh` が3本取得します。

| ファイル | 用途 |
|---|---|
| `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | r2v（今回のメイン） |
| `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors` | fl2v |
| `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | fl2v |

既定では **Lightning LoRA は OFF**（= 20 steps のフルモデル）です。
Preview 用に `make-workflows.py` が ON（4 steps）に切り替えます。

### 3. ファイル名のトークンは使えない

- `%date:...%` は v0.33 の SaveVideo では展開されない
- `%ノード名.ウィジェット%` はフロントエンド専用で API 経由では解決されない

そのため prefix はプレーンにし、日時と seed が必要な場合は
`queue-workflow.py` が投入時に実値を埋めます。

### 4. ComfyUI のバージョンとテンプレートの置き場所

- 実機は **ComfyUI v0.33.0**
- テンプレートの実体は `comfyui_workflow_templates_json`（`_json` 付き）にある
  （`comfyui_workflow_templates` は空のシムになっている）
- `api_minimax_h3_*.json` は **MiniMax のクラウド API を叩く**テンプレート。
  ローカル推論では使わない（`make-workflows.py` が除外する）
- `/object_info` では COMBO が文字列 `"COMBO"` で返り、
  `SaveVideo.codec` は `COMFY_DYNAMICCOMBO_V3` という派生型

### 5. 実測値（H100 80GB / AP-JP-1）

| | Preview | Quality |
|---|---|---|
| 設定 | Lightning ON / 4 steps / 608×352 / 3秒 | Full / 20 steps / 1280×736 / 5秒 |
| 生成時間 | **約5秒**（VRAM常駐時） | 約8分 |
| VRAM | 約42GB | 約42GB |

初回はモデルのVRAMロードで数分かかります。

---

## ブラウザから ComfyUI が開けない場合

RunPod のプロキシ（`https://<podid>-8188.proxy.runpod.net`）は正常でも、
ブラウザによっては開けないことがあります。まず外部から確認してください。

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://<podid>-8188.proxy.runpod.net/
```

200 が返るならプロキシは正常です。別ブラウザ、またはシークレットウィンドウを試してください。

ブラウザを使わずに生成テストしたい場合は `queue-workflow.py` を使います。

```bash
python3 /workspace/queue-workflow.py --workflow /workspace/workflows/h3_preview.json --image test_ref.png --prompt "..."
```

UI 形式のワークフローを API 形式へ変換して `/prompt` に投げるので、
Pod 再作成後の疎通確認にもそのまま使えます。

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
