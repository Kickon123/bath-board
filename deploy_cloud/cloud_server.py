"""
クラウド中継サーバー（受信 → 保持 → 配信 → 案内板表示）

役割:
  - スマホ(adb_reader)が温度を取得するたびに POST /api/push でここへ送信
  - 最新値を latest.json に保持
  - 履歴を Supabase (PostgreSQL) に永続保存
  - 別モニターのブラウザは GET / （案内板HTML）を開き、5秒ごとに /api/baths を読む

ローカル試験:   python3 cloud_server.py    → http://<このPCのIP>:8000/
クラウド配備:   Render等にこのファイル + static/ を置く（gunicorn cloud_server:app）
"""
import json
import os
from collections import deque
from pathlib import Path

import requests as req
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_DIR = Path(__file__).parent
STORE    = BASE_DIR / "latest.json"

SECRET    = os.environ.get("PUSH_TOKEN")
SUPA_URL  = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPA_KEY  = os.environ.get("SUPABASE_KEY", "")
CMS_PASSWORD = os.environ.get("CMS_PASSWORD", "")

# CMSで未設定の場合に使うデフォルト値（現状ハードコードされている値と同じ）
DEFAULT_CONFIG = {
    "color": {
        "temp_threshold": 28, "temp_max": 40,
        "hue_blue": 210, "sat_blue": 85,
        "hue_warm_start": 28, "hue_warm_end": 55, "sat_warm": 92,
        "grad_light": 50,
    },
    "pin_scale": 0.93,
    "spots": [
        {"id": 1, "name": "高温の湯", "u": 0.188, "v": 0.578},
        {"id": 2, "name": "中温の湯", "u": 0.318, "v": 0.540},
        {"id": 3, "name": "低温の湯", "u": 0.439, "v": 0.492},
        {"id": 6, "name": "立湯", "u": 0.643, "v": 0.455, "lg": True},
        {"id": 5, "name": "座湯", "u": 0.624, "v": 0.780, "lg": True},
    ],
    "ticker_text": "湯あみ着はエレベーター横のカゴまでお持ちください",
    "slideshow": {
        "bath_url": "/allcut?nodaiyu",
        "images": [
            "ChatGPT Image May 15, 2026, 08_26_50 PM.png",
            "ChatGPT Image May 23, 2026, 11_16_35 PM.png",
            "ChatGPT Image May 23, 2026, 11_26_28 PM.png",
        ],
    },
    "bath_screens": [
        {"label": "湯畑（配色版）", "url": "/allcut"},
        {"label": "湯畑（大浴場なし）", "url": "/allcut?nodaiyu"},
        {"label": "露天風呂メイン", "url": "/rotenburo"},
        {"label": "湯畑（旧レイアウト）", "url": "/yubatake"},
    ],
}

# Supabase 未設定時のフォールバック用（メモリ内履歴）
HISTORY_MAX = 600
_history: deque = deque(maxlen=HISTORY_MAX)


# ── Supabase ヘルパー ───────────────────────────────
def _supa_ok():
    return bool(SUPA_URL and SUPA_KEY)

def _supa_headers():
    return {
        "apikey":        SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
        "Content-Type":  "application/json",
    }

def supa_insert(push_data):
    if not _supa_ok():
        return
    ts = push_data.get("last_updated") or ""
    # タイムゾーン情報がない場合はJST(+09:00)として扱う
    if ts and "+" not in ts and "Z" not in ts:
        ts = ts + "+09:00"
    rows = [
        {
            "recorded_at": ts,
            "bath_id":     b["id"],
            "bath_name":   b.get("name"),
            "temp":        b.get("temp"),
            "stale":       b.get("stale", False),
        }
        for b in push_data.get("baths", [])
        if b.get("temp") is not None
    ]
    if not rows:
        return
    try:
        req.post(
            f"{SUPA_URL}/rest/v1/temperatures",
            headers={**_supa_headers(), "Prefer": "return=minimal"},
            json=rows,
            timeout=5,
        )
    except Exception:
        pass

def supa_query_bath(bath_id, n=100):
    """指定湯舟の過去データを古い順で返す。"""
    if not _supa_ok():
        return None
    try:
        res = req.get(
            f"{SUPA_URL}/rest/v1/temperatures",
            headers=_supa_headers(),
            params={
                "bath_id": f"eq.{bath_id}",
                "order":   "recorded_at.desc",
                "limit":   n,
                "select":  "recorded_at,temp,stale",
            },
            timeout=5,
        )
        rows = res.json()
        # 古い順に並べ直して at キーに統一
        return [{"at": r["recorded_at"], "temp": r["temp"], "stale": r["stale"]}
                for r in reversed(rows)]
    except Exception:
        return None

def supa_query_all(n=300):
    """全湯舟の過去データを古い順で返す。"""
    if not _supa_ok():
        return None
    try:
        res = req.get(
            f"{SUPA_URL}/rest/v1/temperatures",
            headers=_supa_headers(),
            params={
                "order":  "recorded_at.desc",
                "limit":  n,
                "select": "recorded_at,bath_id,bath_name,temp,stale",
            },
            timeout=5,
        )
        rows = res.json()
        return [{"at": r["recorded_at"], "bath_id": r["bath_id"],
                 "bath_name": r["bath_name"], "temp": r["temp"], "stale": r["stale"]}
                for r in reversed(rows)]
    except Exception:
        return None


def supa_get_config():
    """CMSの表示設定を取得。未保存 or Supabase未設定ならNoneを返す。"""
    if not _supa_ok():
        return None
    try:
        res = req.get(
            f"{SUPA_URL}/rest/v1/site_config",
            headers=_supa_headers(),
            params={"select": "config", "order": "updated_at.desc", "limit": 1},
            timeout=5,
        )
        rows = res.json()
        return rows[0]["config"] if rows else None
    except Exception:
        return None


def supa_save_config(config):
    """CMSの表示設定を保存（既存行を全削除して1行だけ挿入）。"""
    if not _supa_ok():
        return False
    try:
        req.delete(
            f"{SUPA_URL}/rest/v1/site_config",
            headers=_supa_headers(),
            params={"id": "gte.0"},
            timeout=5,
        )
        res = req.post(
            f"{SUPA_URL}/rest/v1/site_config",
            headers={**_supa_headers(), "Prefer": "return=minimal"},
            json={"config": config},
            timeout=5,
        )
        return res.ok
    except Exception:
        return False


# ── エンドポイント ──────────────────────────────────
@app.post("/api/push")
def api_push():
    if not SECRET or request.headers.get("X-Token") != SECRET:
        return jsonify(error="forbidden"), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="no json"), 400
    STORE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    supa_insert(data)
    _history.append(data)
    return jsonify(ok=True)


@app.get("/api/baths")
def api_baths():
    if STORE.exists():
        return app.response_class(STORE.read_text(encoding="utf-8"),
                                  mimetype="application/json")
    return jsonify(baths=[], gateway=None, online=False)


@app.get("/api/config")
def api_config_get():
    """案内板の表示設定（配色・テロップ・ピン位置など）。CMSで編集する。"""
    config = supa_get_config()
    return jsonify(config or DEFAULT_CONFIG)


@app.post("/api/config")
def api_config_set():
    if not CMS_PASSWORD or request.headers.get("X-Token") != CMS_PASSWORD:
        return jsonify(error="forbidden"), 403
    config = request.get_json(silent=True)
    if config is None:
        return jsonify(error="no json"), 400
    if not supa_save_config(config):
        return jsonify(error="save failed（Supabaseのsite_configテーブルを確認してください）"), 500
    return jsonify(ok=True)


@app.get("/api/images")
def api_images():
    """静止画スライドショーで選べる画像一覧（static直下のpng/jpg/webp）。"""
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    names = sorted(
        p.name for p in (BASE_DIR / "static").iterdir()
        if p.is_file() and p.suffix.lower() in exts
    )
    return jsonify(images=names)


@app.get("/api/history")
def api_history():
    """
    指定湯舟の過去データ（古い順）。
    GET /api/history?id=1&n=100
    """
    bath_id = request.args.get("id", type=int)
    n       = request.args.get("n", 100, type=int)

    # Supabase から取得
    if _supa_ok() and bath_id is not None:
        result = supa_query_bath(bath_id, n)
        if result is not None:
            return jsonify(result)

    # フォールバック：メモリ内履歴
    result = []
    for snap in list(_history):
        ts = snap.get("last_updated")
        if not ts:
            continue
        if bath_id is not None:
            bath = next((b for b in snap.get("baths", []) if b.get("id") == bath_id), None)
            if bath:
                result.append({"at": ts, "temp": bath.get("temp"), "stale": bath.get("stale", False)})
        else:
            result.append({"at": ts, "baths": snap.get("baths", [])})
    return jsonify(result[-n:])


@app.get("/api/history/all")
def api_history_all():
    """
    全湯舟の過去データ（古い順）。全体グラフ用。
    GET /api/history/all?n=300
    """
    n = request.args.get("n", 300, type=int)

    if _supa_ok():
        result = supa_query_all(n)
        if result is not None:
            return jsonify(result)

    # フォールバック：メモリ内履歴を展開
    result = []
    for snap in list(_history)[-n:]:
        ts = snap.get("last_updated")
        for b in snap.get("baths", []):
            result.append({
                "at": ts, "bath_id": b.get("id"), "bath_name": b.get("name"),
                "temp": b.get("temp"), "stale": b.get("stale", False),
            })
    return jsonify(result)


@app.get("/")
@app.get("/slideshow")
def slideshow():
    return send_from_directory("static", "slideshow.html")

@app.get("/slideshow64")
@app.get("/64")
def slideshow64():
    return send_from_directory("static", "slideshow64.html")

@app.get("/yubatake")
@app.get("/board")
def board():
    return send_from_directory("static", "yubatake.html")

@app.get("/base-all")
@app.get("/all")
def board_all():
    return send_from_directory("static", "base-all.html")

@app.get("/bath/yubatake")
def bath_yubatake():
    return send_from_directory("static", "yubatake.html")

@app.get("/bath/daiyokujo")
def bath_daiyokujo():
    return send_from_directory("static", "daiyokujo.html")

@app.get("/bath/all")
def bath_all():
    return send_from_directory("static", "base-all.html")

@app.get("/all75")
@app.get("/base-all-75")
def board_all_75():
    return send_from_directory("static", "base-all-75.html")

@app.get("/allcut")
@app.get("/base-all-cut")
def board_all_cut():
    return send_from_directory("static", "base-all-cut.html")

@app.get("/rotenburo")
def rotenburo():
    return send_from_directory("static", "rotenburo.html")

@app.get("/kanri")
def kanri():
    return send_from_directory("static", "staff.html")

@app.get("/kanri-settings")
def kanri_settings():
    return send_from_directory("static", "settings.html")



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"クラウド中継サーバー起動: http://0.0.0.0:{port}/")
    app.run(host="0.0.0.0", port=port)
