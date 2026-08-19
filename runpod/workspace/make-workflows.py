#!/usr/bin/env python3
"""
ComfyUI 公式の MiniMax H3 テンプレートから
Preview 用 / Quality 用の 2 本のワークフローを生成する。

なぜテンプレートから作るのか:
  H3 のノードは 2026-08-03 に ComfyUI 本体へ入ったばかりで仕様が動く。
  手書き JSON は壊れやすいので、同梱の公式テンプレートを正として、
  そこに用意されたコントロールノードの値だけを差し替える。

重要:
  公式テンプレートは width/height/length/steps を
  ノードのウィジェットではなく「コントロールノードからのリンク」で供給する。
  そのため対象ノードの widgets_values を書き換えても効かない。
  必ず供給元（Resolution Selector / Duration / Lightning LoRA スイッチ）を触ること。

  テンプレートの制御構造:
      Boolean (Enable Lightning LoRA) ─┬→ If/Else Switch (model) → UNet or LoRA
                                       └→ If/Else Switch (Steps) → 4 or 20 steps
      Resolution Selector (Size)  → width / height
      Float (Duration)            → 数式ノード → length（フレーム数）
      Input Text (Prompt)         → prompt

使い方:
    python3 /workspace/make-workflows.py                 # 既定 (user=shared)
    python3 /workspace/make-workflows.py --user yasu
    python3 /workspace/make-workflows.py --list          # テンプレート一覧
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import re
import shutil
import sys
import urllib.request

WS = os.environ.get("WORKSPACE", "/workspace")
COMFY = os.path.join(WS, "comfyui")
OUT_DIR = os.path.join(WS, "workflows")

# megapixels と実解像度の対応（テンプレート同梱の Size Settings Reference より、16:9・multiple=32）
#   0.2 -> 608x352   0.4 -> 864x480   0.7 -> 1152x640   0.9 -> 1280x736
PRESETS = {
    "preview": {
        "lightning": True,    # Lightning LoRA を有効化 → 4 steps
        "megapixels": 0.2,    # 608 x 352
        "duration": 3.0,      # 秒
    },
    "quality": {
        "lightning": False,   # フルモデル → 20 steps
        "megapixels": 0.9,    # 1280 x 736
        "duration": 5.0,
    },
}

# テンプレート側のコントロールノード（タイトルで特定する）
TITLE_LIGHTNING = "Boolean (Enable Lightning LoRA)"
TITLE_RESOLUTION = "Resolution Selector (Size)"
TITLE_DURATION = "Float (Duration)"

SAVE_NODE_TYPES = re.compile(r"(SaveVideo|SaveWEBM|SaveAnimated|VHS_VideoCombine)", re.I)


# ---------------------------------------------------------------------------
# テンプレート探索
# ---------------------------------------------------------------------------
def find_templates() -> list[str]:
    """H3 のローカル用テンプレート JSON を探す。

    置き場所は ComfyUI のバージョンで変わる。v0.33 時点では pip パッケージが
    分割され、実体は comfyui_workflow_templates_json 側にある。
    パッケージ名を決め打ちせず comfyui_workflow_templates* を総当たりする。
    """
    roots: list[str] = []
    for sp in list(sys.path):
        if not os.path.isdir(sp):
            continue
        try:
            entries = os.listdir(sp)
        except OSError:
            continue
        for e in entries:
            if e.startswith("comfyui_workflow_templates"):
                d = os.path.join(sp, e)
                if os.path.isdir(d):
                    roots.append(d)
    roots += [
        os.path.join(COMFY, "web", "templates"),
        os.path.join(COMFY, "custom_nodes"),
        os.path.join(COMFY, "user", "default", "workflows"),
    ]

    hits: list[str] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
            name = os.path.basename(p).lower()
            if "h3" not in name:
                continue
            # api_* は MiniMax のクラウド API を叩くテンプレート。ローカル推論では使わない。
            if name.startswith("api_"):
                continue
            hits.append(p)
    return sorted(set(hits))


def pick_template(templates: list[str], prefer: str) -> str | None:
    order = [prefer, "_r2v", "r2v", "reference", "_i2v", "i2v", "_t2v", "t2v"]
    for key in order:
        for t in templates:
            if key in os.path.basename(t).lower():
                return t
    return templates[0] if templates else None


# ---------------------------------------------------------------------------
# ノード定義（/object_info）からウィジェット名の並びを得る
# ---------------------------------------------------------------------------
def load_object_info() -> dict | None:
    url = f"http://127.0.0.1:{os.environ.get('COMFY_PORT', '8188')}/object_info"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.load(r)
    except Exception:
        return None


def widget_order(object_info: dict | None, node_type: str) -> list[str]:
    if not object_info or node_type not in object_info:
        return []
    spec = object_info[node_type].get("input", {})
    names: list[str] = []
    for group in ("required", "optional"):
        for name, meta in (spec.get(group) or {}).items():
            t = meta[0] if isinstance(meta, (list, tuple)) and meta else meta
            if isinstance(t, (list, dict)):
                names.append(name)
            elif isinstance(t, str) and (
                "COMBO" in t or t in ("INT", "FLOAT", "STRING", "BOOLEAN")
            ):
                names.append(name)
    return names


# ---------------------------------------------------------------------------
# 書き換え
# ---------------------------------------------------------------------------
def patch(workflow: dict, preset: dict, user: str, mode: str,
          object_info: dict | None) -> tuple[list[str], list[str]]:
    changes: list[str] = []
    warnings: list[str] = []
    nodes = workflow.get("nodes", [])
    by_title = {n.get("title"): n for n in nodes if n.get("title")}

    def set_widget(title: str, index: int, value, label: str) -> None:
        n = by_title.get(title)
        if n is None:
            warnings.append(f"  !! コントロールノードが見つかりません: {title!r}（{label} 未設定）")
            return
        wv = n.get("widgets_values")
        if not isinstance(wv, list) or index >= len(wv):
            warnings.append(f"  !! {title!r} の widgets_values が想定と違います: {wv!r}")
            return
        old = wv[index]
        if type(old) is not type(value) and not (
            isinstance(old, (int, float)) and isinstance(value, (int, float))
        ):
            warnings.append(
                f"  !! {title!r}[{index}] の型が違います（{old!r} -> {value!r}）。スキップします")
            return
        if old != value:
            wv[index] = value
            changes.append(f"  {label}: {old} -> {value}   ({title})")

    # Lightning LoRA の ON/OFF がモデル経路と steps を同時に切り替える
    set_widget(TITLE_LIGHTNING, 0, preset["lightning"], "Lightning LoRA")
    # ResolutionSelector = [アスペクト, megapixels, multiple]
    set_widget(TITLE_RESOLUTION, 1, preset["megapixels"], "解像度(megapixels)")
    # Duration(秒) は数式ノード経由でフレーム数になる
    set_widget(TITLE_DURATION, 0, preset["duration"], "長さ(秒)")

    # 保存先。SaveVideo の filename_prefix は通常のウィジェットなので直接書ける。
    # seed は実際に seed / noise_seed を持つノードのタイトルを参照する。
    seed_token = ""
    for n in nodes:
        names = widget_order(object_info, n.get("type", ""))
        for cand in ("seed", "noise_seed"):
            if cand in names:
                seed_token = f"_%{n.get('title') or n.get('type')}.{cand}%"
                break
        if seed_token:
            break
    prefix = f"{user}/{mode}/%date:yyyyMMdd_hhmmss%_{user}_{mode}{seed_token}"

    saved = False
    for n in nodes:
        ntype = n.get("type", "")
        if not SAVE_NODE_TYPES.search(ntype):
            continue
        wv = n.get("widgets_values")
        if not isinstance(wv, list):
            continue
        names = widget_order(object_info, ntype)
        if "filename_prefix" in names:
            i = names.index("filename_prefix")
            if i < len(wv):
                changes.append(f"  保存先: {wv[i]} -> {prefix}   ({ntype})")
                wv[i] = prefix
                saved = True
    if not saved:
        warnings.append("  !! SaveVideo の filename_prefix を設定できませんでした")

    return changes, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("H3_USER", "shared"))
    ap.add_argument("--template")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    templates = find_templates()
    if args.list:
        print("見つかった H3 テンプレート:")
        for t in templates or []:
            print("  ", t)
        if not templates:
            print("   (なし)")
        return 0

    base_path = args.template or pick_template(templates, "_r2v")
    if not base_path or not os.path.isfile(base_path):
        print("[make-workflows:ERROR] MiniMax H3 の公式テンプレートが見つかりませんでした。",
              file=sys.stderr)
        print("  ComfyUI が 0.30.0 以降か確認してください。", file=sys.stderr)
        print("  UI の Workflow > Browse Templates から H3 を開いて Export し、", file=sys.stderr)
        print("  --template で渡すこともできます。", file=sys.stderr)
        return 1

    print(f"[make-workflows] ベーステンプレート: {base_path}")
    with open(base_path, encoding="utf-8") as f:
        base = json.load(f)

    object_info = load_object_info()
    if object_info:
        print("[make-workflows] ComfyUI /object_info からノード定義を取得しました")
    else:
        print("[make-workflows] ⚠ ComfyUI が起動していません。保存先の設定精度が落ちます。")

    os.makedirs(OUT_DIR, exist_ok=True)
    had_warning = False
    for mode, preset in PRESETS.items():
        wf = copy.deepcopy(base)
        changes, warnings = patch(wf, preset, args.user, mode, object_info)
        dest = os.path.join(OUT_DIR, f"h3_{mode}.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(wf, f, ensure_ascii=False, indent=2)

        steps = 4 if preset["lightning"] else 20
        print(f"\n[make-workflows] ✓ {dest}")
        print(f"    {mode}: Lightning LoRA={preset['lightning']} ({steps} steps) / "
              f"{preset['megapixels']} MP / {preset['duration']} 秒")
        for c in changes:
            print(c)
        for w in warnings:
            print(w)
            had_warning = True

    # ComfyUI の Workflows サイドバーからワンクリックで開けるように複製する
    ui_dir = os.path.join(COMFY, "user", "default", "workflows")
    try:
        os.makedirs(ui_dir, exist_ok=True)
        for mode in PRESETS:
            shutil.copyfile(os.path.join(OUT_DIR, f"h3_{mode}.json"),
                            os.path.join(ui_dir, f"h3_{mode}.json"))
        print(f"\n[make-workflows] ✓ ComfyUI のワークフロー一覧にも配置: {ui_dir}")
    except OSError as e:
        print(f"\n[make-workflows] ⚠ ComfyUI 側への配置に失敗: {e}")

    print(f"[make-workflows] 出力先: /workspace/outputs/{args.user}/preview|quality/")
    if had_warning:
        print("[make-workflows] ⚠ 警告があります。UI で該当ノードを確認してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
