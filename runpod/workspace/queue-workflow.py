#!/usr/bin/env python3
"""
ワークフロー（UI 形式 JSON）を ComfyUI の API に投入して生成を実行する。

ブラウザを開かずに動作確認できるので、
セットアップ直後のスモークテストや、Pod 再起動後の疎通確認に使う。

使い方:
    python3 queue-workflow.py --workflow /workspace/workflows/h3_preview.json \\
        --image test_ref.png --prompt "the red sphere slowly rotates"

    # 投入だけして待たない
    python3 queue-workflow.py --workflow ... --no-wait
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HOST = os.environ.get("COMFY_HOST", "127.0.0.1")
PORT = os.environ.get("COMFY_PORT", "8188")
BASE = f"http://{HOST}:{PORT}"

# UI 上だけの飾りで、実行グラフには存在しないノード
NON_EXEC_TYPES = {"Note", "MarkdownNote", "Reroute"}


def api_get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.load(r)


def api_post(path: str, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def widget_names(object_info: dict, node_type: str) -> list[str]:
    """widgets_values の並びに対応する入力名を返す（make-workflows.py と同じ規則）"""
    spec = object_info.get(node_type, {}).get("input", {})
    names: list[str] = []
    for group in ("required", "optional"):
        for name, meta in (spec.get(group) or {}).items():
            t = meta[0] if isinstance(meta, (list, tuple)) and meta else meta
            if isinstance(t, (list, dict)):
                names.append(name)
            elif isinstance(t, str) and t in ("COMBO", "INT", "FLOAT", "STRING", "BOOLEAN"):
                names.append(name)
    return names


def to_api_format(wf: dict, object_info: dict) -> dict:
    """litegraph の UI 形式を /prompt が受け取る API 形式へ変換する。

    UI 形式はノード同士を link id で繋ぐが、API 形式は
    [接続元ノードID, 出力スロット] を直接書く。ここを解決する。
    """
    # link_id -> (origin_node_id, origin_slot)
    links: dict[int, tuple[int, int]] = {}
    for l in wf.get("links", []):
        if isinstance(l, (list, tuple)) and len(l) >= 5:
            links[l[0]] = (l[1], l[2])

    prompt: dict[str, dict] = {}
    for n in wf.get("nodes", []):
        ntype = n.get("type")
        if not ntype or ntype in NON_EXEC_TYPES:
            continue
        # mode 2=muted, 4=bypassed は実行対象外
        if n.get("mode") in (2, 4):
            continue

        inputs: dict = {}

        # 1) リンク接続の入力
        for inp in n.get("inputs") or []:
            link_id = inp.get("link")
            if link_id is None:
                continue
            src = links.get(link_id)
            if src:
                inputs[inp["name"]] = [str(src[0]), src[1]]

        # 2) ウィジェット値
        wv = n.get("widgets_values")
        if isinstance(wv, list):
            names = widget_names(object_info, ntype)
            # リンクで既に埋まっている名前は除く（UI 上でウィジェットが入力に昇格した場合）
            for name, val in zip(names, wv):
                if name not in inputs:
                    inputs[name] = val

        prompt[str(n["id"])] = {"class_type": ntype, "inputs": inputs}

    return prompt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    ap.add_argument("--image", help="ComfyUI の input ディレクトリ内のファイル名")
    ap.add_argument("--prompt", help="生成プロンプト（最初の正のテキスト入力を差し替える）")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--no-wait", action="store_true")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    try:
        object_info = api_get("/object_info")
    except urllib.error.URLError as e:
        sys.exit(f"[queue] ERROR: ComfyUI に接続できません ({BASE}): {e}")

    with open(args.workflow, encoding="utf-8") as f:
        wf = json.load(f)

    prompt = to_api_format(wf, object_info)
    print(f"[queue] {len(prompt)} ノードを API 形式へ変換しました")

    # 差し替え
    for nid, node in prompt.items():
        ct, inp = node["class_type"], node["inputs"]
        if args.image and ct == "LoadImage" and "image" in inp:
            print(f"[queue] LoadImage(node {nid}).image: {inp['image']!r} -> {args.image!r}")
            inp["image"] = args.image
        if args.seed is not None:
            for k in ("noise_seed", "seed"):
                if k in inp and not isinstance(inp[k], list):
                    print(f"[queue] {ct}(node {nid}).{k}: {inp[k]} -> {args.seed}")
                    inp[k] = args.seed
    if args.prompt:
        for nid, node in prompt.items():
            inp = node["inputs"]
            if node["class_type"] == "CLIPTextEncode" and isinstance(inp.get("text"), str):
                print(f"[queue] CLIPTextEncode(node {nid}).text -> {args.prompt!r}")
                inp["text"] = args.prompt
                break

    try:
        res = api_post("/prompt", {"prompt": prompt})
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"[queue] ERROR: /prompt が {e.code} を返しました\n{body[:3000]}")

    pid = res.get("prompt_id")
    print(f"[queue] 投入しました prompt_id={pid}")
    if args.no_wait:
        return 0

    print("[queue] 完了を待っています…")
    t0 = time.time()
    while time.time() - t0 < args.timeout:
        time.sleep(5)
        hist = api_get(f"/history/{pid}")
        if pid not in hist:
            continue
        entry = hist[pid]
        status = entry.get("status", {})
        if status.get("completed"):
            print(f"[queue] ✓ 完了 ({time.time()-t0:.0f} 秒)")
            for nid, out in (entry.get("outputs") or {}).items():
                for key in ("videos", "images", "gifs", "audio"):
                    for f in out.get(key, []) or []:
                        print(f"[queue]   -> {f.get('subfolder','')}/{f.get('filename')}")
            return 0
        if status.get("status_str") == "error":
            print("[queue] ✗ エラーで終了しました")
            print(json.dumps(status, ensure_ascii=False, indent=1)[:3000])
            return 1
    print(f"[queue] ✗ {args.timeout} 秒以内に終わりませんでした")
    return 1


if __name__ == "__main__":
    sys.exit(main())
