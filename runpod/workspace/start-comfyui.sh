#!/usr/bin/env bash
# =============================================================================
# ComfyUI 起動スクリプト（Pod 起動時に自動実行される想定）
#
# RunPod の Pod 設定 → Container Start Command に以下を設定:
#   bash -lc 'mkdir -p /workspace/logs; nohup bash /workspace/start-comfyui.sh >> /workspace/logs/boot.log 2>&1 & exec /start.sh'
#
# 手動で起動する場合:
#   bash /workspace/start-comfyui.sh
# =============================================================================
set -uo pipefail

WS=/workspace
COMFY="$WS/comfyui"
VENV="$WS/venv"
LOGS="$WS/logs"
PORT="${COMFY_PORT:-8188}"

mkdir -p "$LOGS"
LOG="$LOGS/comfyui_$(date +%Y%m%d_%H%M%S).log"

log()  { echo -e "\033[1;36m[start]\033[0m $*" | tee -a "$LOG"; }
warn() { echo -e "\033[1;33m[start:WARN]\033[0m $*" | tee -a "$LOG"; }
die()  { echo -e "\033[1;31m[start:ERROR]\033[0m $*" | tee -a "$LOG" >&2; exit 1; }

log "=============================================="
log " ComfyUI 起動  $(date '+%Y-%m-%d %H:%M:%S %Z')"
log " ログ: $LOG"
log "=============================================="

# -----------------------------------------------------------------------------
# 起動前チェック（不足があればここで明確に落とす）
# -----------------------------------------------------------------------------
log "--- 起動前チェック ---"

[ -d "$WS" ]            || die "/workspace がありません。永続ボリュームが未マウントです。"
[ -d "$COMFY" ]         || die "ComfyUI が未インストールです。先に 'bash /workspace/setup.sh' を実行してください。"
[ -d "$VENV" ]          || die "venv がありません。先に 'bash /workspace/setup.sh' を実行してください。"

# shellcheck disable=SC1091
source "$VENV/bin/activate"
export HF_HOME="$WS/.cache/huggingface"
export PIP_CACHE_DIR="$WS/.cache/pip"

# GPU / CUDA
if ! nvidia-smi >/dev/null 2>&1; then
  die "GPU が見えません（nvidia-smi 失敗）。Pod の GPU 割り当てを確認してください。"
fi
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader | sed 's/^/       GPU: /' | tee -a "$LOG"

python - <<'PY' | tee -a "$LOG"
import sys
try:
    import torch
except ImportError:
    sys.exit("[start:ERROR] torch が import できません")
if not torch.cuda.is_available():
    sys.exit("[start:ERROR] torch.cuda.is_available() == False")
print(f"       torch {torch.__version__} / CUDA {torch.version.cuda} / GPU {torch.cuda.get_device_name(0)}")
PY
[ "${PIPESTATUS[0]}" -eq 0 ] || die "CUDA チェックに失敗しました"

# モデル存在チェック
MODELS="$WS/models/h3"
MISSING=0
check_model() {
  local dir="$1" pattern="$2" label="$3"
  if compgen -G "$MODELS/$dir/$pattern" > /dev/null; then
    local f; f=$(ls -S "$MODELS/$dir/"$pattern | head -1)
    log "  ✓ $label: $(basename "$f") ($(du -h "$f" | cut -f1))"
  else
    warn "  ✗ $label が見つかりません: $MODELS/$dir/$pattern"
    MISSING=1
  fi
}
log "--- モデルチェック ---"
check_model diffusion_models "minimax_h3_*.safetensors" "H3 diffusion model"
check_model text_encoders    "qwen3vl*.safetensors"     "text encoder"
check_model vae              "minimax_h3_video_vae*"    "video VAE"
check_model vae              "minimax_h3_audio_vae*"    "audio VAE"
[ "$MISSING" -eq 1 ] && warn "モデルが不足しています。'bash /workspace/setup.sh' を再実行してください。（起動は続行します）"

# ワークフローチェック
log "--- ワークフローチェック ---"
for wf in h3_preview.json h3_quality.json; do
  if [ -f "$WS/workflows/$wf" ]; then
    log "  ✓ $wf"
  else
    warn "  ✗ $WS/workflows/$wf がありません（README の手順でロードしてください）"
  fi
done

# 出力ディレクトリ
mkdir -p "$WS/outputs" "$WS/input"
log "--- ディスク使用量 ---"
du -sh "$WS"/* 2>/dev/null | sed 's/^/       /' | tee -a "$LOG"

# 既に起動していないか
if pgrep -f "comfyui/main.py" >/dev/null 2>&1; then
  warn "ComfyUI は既に起動しています（PID: $(pgrep -f 'comfyui/main.py' | tr '\n' ' ')）"
  warn "再起動する場合: pkill -f comfyui/main.py"
  exit 0
fi

# -----------------------------------------------------------------------------
# 起動
# -----------------------------------------------------------------------------
log "--- ComfyUI 起動 (port $PORT) ---"
log "RunPod の HTTP Service で Port $PORT を開くとアクセスできます"

cd "$COMFY"
python "$COMFY/main.py" \
  --listen 0.0.0.0 \
  --port "$PORT" \
  --output-directory "$WS/outputs" \
  --input-directory "$WS/input" \
  --extra-model-paths-config "$COMFY/extra_model_paths.yaml" \
  2>&1 | tee -a "$LOG"
