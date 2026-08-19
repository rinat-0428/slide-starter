#!/usr/bin/env python3
"""
ComfyUI 公式の MiniMax H3 テンプレートをベースに、
Preview 用 / Quality 用の 2 本のワークフローを生成する。

なぜテンプレートから作るのか:
  H3 のノードは 2026-08-03 に ComfyUI 本体へ入ったばかりで、
  ノード名や入力の仕様が変わりうる。手書きの JSON は壊れやすいので、
  インストール済み ComfyUI に同梱された公式テンプレートを正として、
  必要な値（steps / 解像度 / フレーム数 / 保存先）だけを書き換える。

使い方:
    python3 /workspace/make-workflows.py                 # 既定 (user=shared)
    python3 /workspace/make-workflows.py --user yasu     # 保存先をユーザー別に
    python3 /workspace/make-workflows.py --list          # 見つかったテンプレート一覧
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import os
import re
import sys
import urllib.request

WS = os.environ.get("WORKSPACE", "/workspace")
COMFY = os.path.join(WS, "comfyui")
OUT_DIR = os.path.join(WS, "workflows")

# Preview = 速さ優先 / Quality = 品質優先
PRESETS = {
    "preview": {
        "steps": 8,
        "width": 640,
        "height": 384,
        "length": 61,       # ≒ 2.5秒 @24fps
    },
    "quality": {
        "steps": 20,        # 公式ベースラインが 20 steps
        "width": 1280,
        "height": 720,
        "length": 121,      # ≒ 5秒 @24fps
    },
}

# 書き換え対象のウィジェット名（ノード実装によって名前が揺れるので候補を列挙）
WIDGET_ALIASES = {
    "steps":  ["steps"],
    "width":  ["width"],
    "height": ["height"],
    "length": ["length", "num_frames", "frames", "video_frames"],
}

SAVE_NODE_TYPES = re.compile(r"(SaveVideo|SaveWEBM|SaveAnimated|VHS_VideoCombine|SaveAudio)", re.I)
SAMPLER_NODE_TYPES = re.compile(r"Sampler", re.I)


# ---------------------------------------------------------------------------
# 1. 公式テンプレートを探す
# ---------------------------------------------------------------------------
def find_templates() -> list[str]:
    roots = []
    # pip パッケージ comfyui-workflow-templates
    try:
        import comfyui_workflow_templates as t
        roots.append(os.path.dirname(t.__file__))
    except ImportError:
        pass
    # フロントエンドに同梱されるパターン
    roots += [
        os.path.join(COMFY, "web", "templates"),
        os.path.join(COMFY, "custom_nodes"),
        os.path.join(COMFY, "user", "default", "workflows"),
    ]
    for sp in sys.path:
        cand = os.path.join(sp, "comfyui_workflow_templates")
        if os.path.isdir(cand):
            roots.append(cand)

    hits: list[str] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
            name = os.path.basename(p).lower()
            if ("minimax" in name or "_h3" in name or name.startswith("h3")) and "h3" in name:
                hits.append(p)
    return sorted(set(hits))


def pick_template(templates: list[str], prefer: str) -> str | None:
    """prefer: 'ref2va'(リファレンス画像→動画) を優先し、無ければ i2v/t2v"""
    order = [prefer, "ref2va", "r2v", "reference", "i2v", "image_to_video", "fl2va", "t2v"]
    for key in order:
        for t in templates:
            if key in os.path.basename(t).lower():
                return t
    return templates[0] if templates else None


# ---------------------------------------------------------------------------
# 2. ノードのウィジェット名を解決する
#    ComfyUI の /object_info から「入力の順番」を取れると正確に書き換えられる
# ---------------------------------------------------------------------------
def load_object_info() -> dict | None:
    url = f"http://127.0.0.1:{os.environ.get('COMFY_PORT', '8188')}/object_info"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.load(r)
    except Exception:
        return None


def widget_order(object_info: dict | None, node_type: str) -> list[str]:
    """そのノードの widgets_values に対応する入力名を順番に返す"""
    if not object_info or node_type not in object_info:
        return []
    spec = object_info[node_type].get("input", {})
    names: list[str] = []
    for group in ("required", "optional"):
        for name, meta in (spec.get(group) or {}).items():
            # リンク接続専用（MODEL/LATENT等）はウィジェットにならない
            t = meta[0] if isinstance(meta, (list, tuple)) and meta else meta
            if isinstance(t, list):          # COMBO
                names.append(name)
            elif isinstance(t, str) and t in ("INT", "FLOAT", "STRING", "BOOLEAN"):
                names.append(name)
    return names


# ---------------------------------------------------------------------------
# 3. 書き換え
# ---------------------------------------------------------------------------
def patch(workflow: dict, preset: dict, user: str, mode: str, object_info: dict | None) -> list[str]:
    changes: list[str] = []
    nodes = workflow.get("nodes", [])

    # 保存先: /workspace/outputs/<user>/<mode>/YYYYMMDD_HHMMSS_<user>_<mode>_<seed>
    # ComfyUI の filename_prefix は %date:...% と %NodeTitle.widget% を展開できる
    sampler_title = None
    for n in nodes:
        if SAMPLER_NODE_TYPES.search(n.get("type", "")):
            sampler_title = n.get("title") or n.get("type")
            break
    seed_token = f"_%{sampler_title}.seed%" if sampler_title else ""
    prefix = f"{user}/{mode}/%date:yyyyMMdd_hhmmss%_{user}_{mode}{seed_token}"

    for n in nodes:
        ntype = n.get("type", "")
        wv = n.get("widgets_values")
        if not isinstance(wv, list):
            continue
        names = widget_order(object_info, ntype)

        def set_by_name(keys: list[str], value) -> bool:
            for k in keys:
                if k in names:
                    i = names.index(k)
                    if i < len(wv):
                        old = wv[i]
                        if old != value:
                            wv[i] = value
                            changes.append(f"  {ntype}.{k}: {old} -> {value}")
                        return True
            return False

        # 保存ノード
        if SAVE_NODE_TYPES.search(ntype):
            if not set_by_name(["filename_prefix"], prefix):
                # スキーマが無い場合: パスっぽい文字列ウィジェットを差し替える
                for i, v in enumerate(wv):
                    if isinstance(v, str) and ("/" in v or v.lower() in ("comfyui", "video")):
                        changes.append(f"  {ntype}[{i}] (推定 filename_prefix): {v!r} -> {prefix!r}")
                        wv[i] = prefix
                        break
            continue

        # サンプラー・解像度・長さ
        if names:
            set_by_name(WIDGET_ALIASES["steps"], preset["steps"])
            set_by_name(WIDGET_ALIASES["width"], preset["width"])
            set_by_name(WIDGET_ALIASES["height"], preset["height"])
            set_by_name(WIDGET_ALIASES["length"], preset["length"])

    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("H3_USER", "shared"),
                    help="出力先フォルダ名 (例: yasu)")
    ap.add_argument("--template", help="ベースにするテンプレート JSON のパス（省略時は自動検出）")
    ap.add_argument("--list", action="store_true", help="見つかったテンプレートを表示して終了")
    args = ap.parse_args()

    templates = find_templates()
    if args.list:
        print("見つかった H3 テンプレート:")
        for t in templates or []:
            print("  ", t)
        if not templates:
            print("   (なし)")
        return 0

    base_path = args.template or pick_template(templates, "ref2va")
    if not base_path or not os.path.isfile(base_path):
        print("[make-workflows:ERROR] MiniMax H3 の公式テンプレートが見つかりませんでした。", file=sys.stderr)
        print("  ComfyUI が 0.30.0 以降か確認してください。", file=sys.stderr)
        print("  UI の Workflow > Browse Templates から H3 のテンプレートを開き、", file=sys.stderr)
        print("  Export して --template で渡すこともできます。", file=sys.stderr)
        return 1

    print(f"[make-workflows] ベーステンプレート: {base_path}")
    with open(base_path, encoding="utf-8") as f:
        base = json.load(f)

    object_info = load_object_info()
    if object_info:
        print("[make-workflows] ComfyUI /object_info からノード定義を取得しました（正確な書き換え）")
    else:
        print("[make-workflows] ⚠ ComfyUI が起動していないため推定で書き換えます。")
        print("[make-workflows]   起動後にもう一度実行すると精度が上がります。")

    os.makedirs(OUT_DIR, exist_ok=True)
    for mode, preset in PRESETS.items():
        wf = copy.deepcopy(base)
        changes = patch(wf, preset, args.user, mode, object_info)
        dest = os.path.join(OUT_DIR, f"h3_{mode}.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(wf, f, ensure_ascii=False, indent=2)
        print(f"[make-workflows] ✓ {dest}  ({mode}: {preset['steps']} steps, "
              f"{preset['width']}x{preset['height']}, {preset['length']} frames)")
        for c in changes:
            print(c)
        if not changes:
            print("  ⚠ 何も書き換えられませんでした。UI で steps / 解像度 / 保存先を手動確認してください。")

    print("\n[make-workflows] 完了。ComfyUI の Workflow > Open から読み込んでください。")
    print(f"[make-workflows] 出力先: /workspace/outputs/{args.user}/preview|quality/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
