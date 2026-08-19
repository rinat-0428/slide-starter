#!/usr/bin/env bash
# /workspace/ENVIRONMENT.md を実際の環境から自動生成する
# 構成を変えたら再実行すること: bash /workspace/record-environment.sh
set -uo pipefail

WS=/workspace
COMFY="$WS/comfyui"
VENV="$WS/venv"
OUT="$WS/ENVIRONMENT.md"

[ -d "$VENV" ] && source "$VENV/bin/activate" 2>/dev/null || true

gpu=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1 || echo "N/A")
driver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || echo "N/A")
comfy_commit=$(git -C "$COMFY" rev-parse HEAD 2>/dev/null || echo "N/A")
comfy_tag=$(git -C "$COMFY" describe --tags --abbrev=0 2>/dev/null || echo "N/A")
comfy_date=$(git -C "$COMFY" log -1 --format=%cI 2>/dev/null || echo "N/A")
pyver=$(python3 -V 2>&1 | awk '{print $2}')
torchver=$(python3 -c "import torch;print(torch.__version__)" 2>/dev/null || echo "N/A")
cudaver=$(python3 -c "import torch;print(torch.version.cuda)" 2>/dev/null || echo "N/A")
nvcc=$(nvcc --version 2>/dev/null | grep release | sed 's/.*release //' || echo "N/A")

{
cat <<MD
# ENVIRONMENT.md

このファイルは \`bash /workspace/record-environment.sh\` で自動生成されます。
手で書き換えず、構成を変えたら再実行してください。

- 生成日時: $(date '+%Y-%m-%d %H:%M:%S %Z')
- RunPod Pod ID: ${RUNPOD_POD_ID:-N/A}
- RunPod DC: ${RUNPOD_DC_ID:-N/A}

## ハードウェア

| 項目 | 値 |
|------|-----|
| GPU | $gpu |
| NVIDIA Driver | $driver |
| CUDA (nvcc) | $nvcc |

## ソフトウェア

| 項目 | 値 |
|------|-----|
| ComfyUI tag | $comfy_tag |
| ComfyUI commit | $comfy_commit |
| ComfyUI commit date | $comfy_date |
| Python | $pyver |
| PyTorch | $torchver |
| PyTorch CUDA | $cudaver |

## モデル

| ファイル | 配置 | サイズ |
|----------|------|--------|
MD

for d in diffusion_models text_encoders vae loras; do
  for f in "$WS/models/h3/$d"/*; do
    [ -e "$f" ] || continue
    echo "| $(basename "$f") | models/h3/$d/ | $(du -h "$f" | cut -f1) |"
  done
done

cat <<MD

配布元: [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)
（オリジナル: [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3)）
ライセンス: MiniMax H3 Community License Agreement

## custom nodes

MD

if compgen -G "$COMFY/custom_nodes/*/" > /dev/null; then
  echo "| ノード | commit |"
  echo "|--------|--------|"
  for d in "$COMFY"/custom_nodes/*/; do
    [ -d "$d" ] || continue
    c=$(git -C "$d" rev-parse --short HEAD 2>/dev/null || echo "-")
    echo "| $(basename "$d") | $c |"
  done
else
  echo "なし（MiniMax H3 は ComfyUI 本体のネイティブノードを使用）"
fi

cat <<MD

## 主要依存ライブラリ

\`\`\`
$(pip list 2>/dev/null | grep -iE "^(torch|torchvision|torchaudio|transformers|diffusers|accelerate|safetensors|numpy|pillow|huggingface|einops|sageattention|comfyui)" || echo "N/A")
\`\`\`

## ワークフロー

| ファイル | steps | 用途 |
|----------|-------|------|
| workflows/h3_preview.json | 8 | 構図・動きのラフ確認 |
| workflows/h3_quality.json | 20 | 本番生成 |

## 動作確認

| 項目 | 状態 | 確認日 |
|------|------|--------|
| ComfyUI 起動 | 未確認 | |
| H3 モデルロード | 未確認 | |
| Reference image + Prompt で生成 | 未確認 | |
| Preview workflow | 未確認 | |
| Quality workflow | 未確認 | |
| Stop → Start 後もモデルが残る | 未確認 | |
| Stop → Start 後も outputs が残る | 未確認 | |

※ 確認できたら「未確認」を「OK」に書き換えてください（このセクションのみ手動更新）
MD
} > "$OUT"

echo "[record-environment] ✓ $OUT を生成しました"
