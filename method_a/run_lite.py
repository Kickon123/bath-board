"""
軽量版ランナー（Flaskなし）

役割:
  温度を取得して Render クラウドへ送るだけ。スマホの負荷を最小にするため
  Flask(:5000) は起動しない。案内板表示はクラウド側(Render)に任せる。

  - server.py / adb_reader.py は変更せず再利用する
  - server.py の /api/baths が作っていた整形JSONを、ここでHTTPを介さず直接組み立てる
  - 取得ごとに Render の /api/push へ POST する

使い方:
  python run_lite.py          # ループ実行（interval秒ごと）
  python run_lite.py --once   # 1回だけ取得して送信
"""
import os
import sys
import time
import json
import requests
import logging
from pathlib import Path
from datetime import datetime

# 設定 / temperatures.json / ログはこの method_a フォルダに置く（adb_reader が参照）
_HERE = Path(__file__).resolve().parent
os.environ.setdefault("BATH_DIR", str(_HERE))
# 共有コア（adb_reader）を import できるようにする
sys.path.insert(0, str(_HERE.parent / "shared"))

from adb_reader import load_config, run_once, load_temps, log


# ── /api/baths と同じ整形JSONをHTTP無しで組み立てる ──────
def build_payload(cfg: dict) -> dict:
    """server.py の api_baths と同一フォーマットの案内板用JSONを返す。"""
    temps = load_temps()
    baths = []
    for b in cfg["baths"]:
        entry = temps.get(str(b["id"]))
        if isinstance(entry, dict):
            temp     = entry.get("temp")
            humidity = entry.get("humidity")
            stale    = entry.get("stale", False)
            at       = entry.get("at")
        else:
            temp     = entry
            humidity = None
            stale    = False
            at       = None
        baths.append({**b, "temp": temp, "humidity": humidity,
                      "stale": stale, "at": at})

    return {
        "baths":        baths,
        "gateway":      temps.get("gateway"),
        "last_updated": temps.get("last_updated"),
        "last_attempt": temps.get("last_attempt"),
        "online":       temps.get("online", True),
    }


# ── Render へ直接送信 ─────────────────────────────────
def push_to_cloud(cfg: dict):
    c   = cfg.get("cloud", {})
    url = c.get("url")
    if not url:
        return  # cloud.url 未設定なら送信しない（ローカル運用）
    payload = build_payload(cfg)
    try:
        r = requests.post(url.rstrip("/") + "/api/push", json=payload,
                          headers={"X-Token": c.get("token", "")}, timeout=15)
        log.info(f"  [クラウド送信] {r.status_code} → {url}")
    except Exception as e:
        log.info(f"  [クラウド送信失敗] {e}")


# ── ループ ────────────────────────────────────────────
def run_loop(cfg: dict):
    interval = cfg["adb"].get("interval", 180)
    while True:
        try:
            log.info(f"【取得開始】次回は {interval}秒後")
            run_once(cfg)          # Inkbird操作で取得 → temperatures.json 更新
            push_to_cloud(cfg)     # 整形JSONを Render へ送信
        except Exception as e:
            log.info(f"[!] エラー: {e}")
        log.info(f"【待機中】{interval}秒後に次の取得を開始します")
        time.sleep(interval)


if __name__ == "__main__":
    cfg = load_config()
    if not cfg["adb"].get("enabled", True):
        print("ADBが無効です (config.json の adb.enabled を true に)")
        sys.exit(1)

    if "--once" in sys.argv:
        print("=== 軽量版: 1回取得して送信 ===")
        run_once(cfg)
        push_to_cloud(cfg)
    else:
        print("=== 軽量版: 取得→Render送信ループ開始（Flaskなし / Ctrl+Cで停止）===")
        run_loop(cfg)
