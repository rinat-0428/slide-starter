#!/usr/bin/env bash
# =============================================================================
# RunPod + ComfyUI + MiniMax H3  一括セットアップ
#
# 使い方（Pod の Web Terminal で1回だけ実行）:
#   bash /workspace/setup.sh
#
# 冪等: 何度実行しても壊れない（既にあるものはスキップ）
# すべて /workspace 配下に置くので Pod を Stop → Start しても残る
# =============================================================================
set -euo pipefail

WS=/workspace
COMFY="$WS/comfyui"
VENV="$WS/venv"
MODELS="$WS/models/h3"
LOGS="$WS/logs"

# ダウンロードする H3 のバリアント
#   ref2va = リファレンス画像/動画/音声 → 動画（今回のメイン用途）
#   fl2va  = テキスト→動画 / 最初と最後のフレーム指定
# 片方だけで良ければ H3_VARIANTS="ref2va" のように環境変数で上書き
H3_VARIANTS="${H3_VARIANTS:-ref2va fl2va}"

# 量子化バリアント。VRAM が潤沢なら int8_convrot / bf16 に変更可
#   pruned_int8_convrot = 19.5GB（省メモリ・推奨）
#   int8_convrot        = 31.7GB
#   bf16                = 61.7GB（フル品質）
H3_DIT_QUANT="${H3_DIT_QUANT:-pruned_int8_convrot}"
#   nvfp4_awq    = 14.6GB（推奨・どの GPU でも動く）
#   int8_convrot = 25.3GB
#   bf16         = 48.0GB
H3_TE_QUANT="${H3_TE_QUANT:-nvfp4_awq}"

log() { echo -e "\033[1;36m[setup]\033[0m $*"; }
die() { echo -e "\033[1;31m[setup:ERROR]\033[0m $*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# 0. 前提チェック
# -----------------------------------------------------------------------------
log "前提チェック"
[ -d "$WS" ] || die "/workspace が存在しません。Pod に永続ボリュームがマウントされているか確認してください。"
command -v git >/dev/null || die "git がありません"
command -v python3 >/dev/null || die "python3 がありません"
nvidia-smi >/dev/null 2>&1 || die "GPU が見えません（nvidia-smi 失敗）"

log "GPU:"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | sed 's/^/       /'

AVAIL_GB=$(df -BG "$WS" | awk 'NR==2{gsub("G","",$4); print $4}')
log "/workspace 空き容量: ${AVAIL_GB}GB"
[ "$AVAIL_GB" -lt 120 ] && log "⚠ 空きが少なめです。モデルだけで 40〜80GB 使います（推奨 200GB 以上）"

# -----------------------------------------------------------------------------
# 1. ディレクトリ
# -----------------------------------------------------------------------------
log "ディレクトリ作成"
mkdir -p "$MODELS"/{diffusion_models,text_encoders,vae,loras} \
         "$WS"/workflows "$WS"/outputs "$WS"/input "$LOGS" \
         "$WS"/.cache/huggingface "$WS"/.cache/pip

# HuggingFace / pip のキャッシュも永続領域へ（コンテナ一時領域を使わない）
export HF_HOME="$WS/.cache/huggingface"
export PIP_CACHE_DIR="$WS/.cache/pip"

# -----------------------------------------------------------------------------
# 2. Python 仮想環境（/workspace 側に置いて再起動後も残す）
# -----------------------------------------------------------------------------
if [ ! -d "$VENV" ]; then
  log "venv 作成（コンテナの torch を再利用するため --system-site-packages）"
  python3 -m venv --system-site-packages "$VENV"
else
  log "venv は既にあります: $VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip -q

python - <<'PY'
import sys
try:
    import torch
    print(f"[setup] torch {torch.__version__} / CUDA {torch.version.cuda} / available={torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        sys.exit("[setup:ERROR] torch から GPU が見えません")
except ImportError:
    sys.exit("[setup:ERROR] torch が入っていません。RunPod の PyTorch テンプレートで Pod を作り直してください。")
PY

# -----------------------------------------------------------------------------
# 3. ComfyUI
# -----------------------------------------------------------------------------
if [ ! -d "$COMFY/.git" ]; then
  log "ComfyUI を clone"
  git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY"
else
  log "ComfyUI を更新"
  git -C "$COMFY" pull --ff-only || log "⚠ pull 失敗（ローカル変更あり？）スキップします"
fi

log "ComfyUI の依存関係をインストール"
pip install -r "$COMFY/requirements.txt" -q

# MiniMax H3 のネイティブ対応は ComfyUI 0.30.0 以降（PR #15224, 2026-08-03 merge）
COMFY_VER=$(git -C "$COMFY" describe --tags --abbrev=0 2>/dev/null || echo "unknown")
log "ComfyUI version: $COMFY_VER ($(git -C "$COMFY" rev-parse --short HEAD))"
python - "$COMFY_VER" <<'PY'
import re, sys
v = sys.argv[1].lstrip("v")
m = re.match(r"(\d+)\.(\d+)\.(\d+)", v)
if not m:
    print("[setup] ⚠ バージョンを判定できませんでした。0.30.0 以降か手動で確認してください。")
else:
    if tuple(map(int, m.groups())) < (0, 30, 0):
        sys.exit("[setup:ERROR] ComfyUI が 0.30.0 未満です。MiniMax H3 のネイティブノードが入っていません。")
    print("[setup] ✓ ComfyUI は H3 対応バージョンです")
PY

# -----------------------------------------------------------------------------
# 4. モデルの置き場所を /workspace/models/h3 に向ける
# -----------------------------------------------------------------------------
log "extra_model_paths.yaml を書き出し"
cat > "$COMFY/extra_model_paths.yaml" <<YAML
# 自動生成: /workspace/setup.sh
# モデル本体はコンテナ一時領域ではなく永続領域 /workspace/models/h3 に置く
h3:
  base_path: $MODELS
  diffusion_models: diffusion_models
  text_encoders: text_encoders
  vae: vae
  loras: loras
YAML

# -----------------------------------------------------------------------------
# 5. モデルのダウンロード
# -----------------------------------------------------------------------------
log "HuggingFace CLI を用意"
pip install -q -U "huggingface_hub[cli,hf_transfer]"
export HF_HUB_ENABLE_HF_TRANSFER=1

log "MiniMax H3 のモデルを取得（Comfy-Org/MiniMax-H3）"
log "  DiT quant: $H3_DIT_QUANT / TextEncoder quant: $H3_TE_QUANT / variants: $H3_VARIANTS"

# リポジトリ内のディレクトリ構成は変わりうるので、
# ファイル一覧を取得して正規表現で拾う（決め打ちしない）
python - <<PY
import os, re, sys, shutil
from huggingface_hub import list_repo_files, hf_hub_download

REPO      = "Comfy-Org/MiniMax-H3"
MODELS    = "$MODELS"
VARIANTS  = "$H3_VARIANTS".split()
DIT_QUANT = "$H3_DIT_QUANT"
TE_QUANT  = "$H3_TE_QUANT"

try:
    files = list_repo_files(REPO)
except Exception as e:
    sys.exit(f"[setup:ERROR] {REPO} のファイル一覧取得に失敗: {e}\n"
             f"  ライセンス同意が必要な場合は 'hf auth login' を実行してください。")

def pick(pattern, label, required=True):
    """正規表現に一致するファイルを1つ選ぶ（複数ならパスが短いものを優先）"""
    hits = [f for f in files if re.search(pattern, f) and f.endswith(".safetensors")]
    if not hits:
        msg = f"[setup] {'ERROR' if required else 'WARN'}: {label} が見つかりません (pattern={pattern})"
        if required:
            sys.exit(msg + "\n  リポジトリのファイル一覧:\n    " + "\n    ".join(sorted(files)[:60]))
        print(msg); return None
    return sorted(hits, key=len)[0]

targets = []
for v in VARIANTS:
    f = pick(rf"minimax_h3_{v}_{DIT_QUANT}\b", f"diffusion model ({v}/{DIT_QUANT})")
    targets.append((f, "diffusion_models"))
targets.append((pick(rf"qwen3vl.*minimax_h3.*{TE_QUANT}", f"text encoder ({TE_QUANT})"), "text_encoders"))
targets.append((pick(r"minimax_h3_video_vae", "video VAE"), "vae"))
targets.append((pick(r"minimax_h3_audio_vae", "audio VAE"), "vae"))

for repo_file, subdir in targets:
    if not repo_file:
        continue
    dest_dir = os.path.join(MODELS, subdir)
    dest = os.path.join(dest_dir, os.path.basename(repo_file))
    if os.path.exists(dest):
        print(f"[setup] skip (already exists): {subdir}/{os.path.basename(repo_file)}")
        continue
    print(f"[setup] downloading {repo_file} -> {subdir}/")
    os.makedirs(dest_dir, exist_ok=True)
    # local_dir を指定して配置先へ直接ダウンロードする。
    # キャッシュ経由でコピーすると同じボリューム上に二重に置かれ、約60GB 無駄になる。
    p = hf_hub_download(repo_id=REPO, filename=repo_file, local_dir=dest_dir)
    # リポジトリ内がサブフォルダ構成の場合、その階層ごと作られるので平らに直す
    p = os.path.realpath(p)
    if os.path.realpath(p) != os.path.realpath(dest):
        shutil.move(p, dest)
        # 空になったサブフォルダを掃除
        d = os.path.dirname(p)
        while os.path.realpath(d) != os.path.realpath(dest_dir):
            try:
                os.rmdir(d)
            except OSError:
                break
            d = os.path.dirname(d)
    print(f"[setup] ✓ {dest} ({os.path.getsize(dest)/1e9:.1f} GB)")
PY

# -----------------------------------------------------------------------------
# 6. ワークフロー生成
# -----------------------------------------------------------------------------
log "Preview / Quality ワークフローを生成"
python "$WS/make-workflows.py" || log "⚠ ワークフロー自動生成に失敗しました。README の『手動でのワークフロー作成』を参照してください。"

# -----------------------------------------------------------------------------
# 7. 環境情報の記録
# -----------------------------------------------------------------------------
log "ENVIRONMENT.md を生成"
bash "$WS/record-environment.sh" || true

chmod +x "$WS"/*.sh 2>/dev/null || true

log "✅ セットアップ完了"
log ""
log "次にやること:"
log "  1) RunPod の Pod 設定 → Container Start Command を次に変更（再起動時に自動起動）:"
log "       bash -lc 'mkdir -p /workspace/logs; nohup bash /workspace/start-comfyui.sh >> /workspace/logs/boot.log 2>&1 & exec /start.sh'"
log "  2) いま起動して試す:  bash /workspace/start-comfyui.sh"
log "  3) HTTP Service (Port 8188) の URL をブラウザで開く"
