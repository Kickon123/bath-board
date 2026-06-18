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
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_DIR = Path(__file__).parent
STORE    = BASE_DIR / "latest.json"

SECRET     = os.environ.get("PUSH_TOKEN")
SUPA_URL   = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPA_KEY   = os.environ.get("SUPABASE_KEY", "")
STAFF_PIN  = os.environ.get("STAFF_PIN", "")

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

@app.get("/base7")
@app.get("/board")
def board():
    return send_from_directory("static", "base7-flat.html")

@app.get("/base-all")
@app.get("/all")
def board_all():
    return send_from_directory("static", "base-all.html")

@app.get("/bath/yubatake")
def bath_yubatake():
    return send_from_directory("static", "base7-flat.html")

@app.get("/bath/daiyokujo")
def bath_daiyokujo():
    return send_from_directory("static", "daiyokujo.html")

@app.get("/bath/all")
def bath_all():
    return send_from_directory("static", "base-all.html")

_LOGIN_HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>スタッフ認証</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
  min-height:100dvh;background:#f4f6f9;}}
.box{{background:#fff;padding:36px 28px;border-radius:16px;
  box-shadow:0 2px 16px rgba(0,0,0,.08);text-align:center;width:280px;}}
h2{{font-size:1rem;font-weight:700;color:#1e293b;margin-bottom:24px;}}
input{{width:100%;padding:14px;font-size:1.5rem;border:1.5px solid #e2e8f0;
  border-radius:10px;text-align:center;letter-spacing:.3em;outline:none;}}
input:focus{{border-color:#3b82f6;}}
button{{margin-top:14px;width:100%;padding:13px;background:#3b82f6;color:#fff;
  border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer;}}
.err{{color:#ef4444;font-size:.82rem;margin-top:10px;min-height:1.2em;}}
</style></head>
<body><div class="box">
<h2>スタッフ専用</h2>
<form method="post" action="/staff-login">
<input type="password" name="pin" placeholder="PIN" autofocus inputmode="numeric">
<button type="submit">ログイン</button>
</form>
<div class="err">{err}</div>
</div></body></html>"""

@app.get("/staff")
def staff():
    if STAFF_PIN and request.cookies.get("staff_auth") != STAFF_PIN:
        return _LOGIN_HTML.format(err=""), 401
    return send_from_directory("static", "staff.html")

@app.post("/staff-login")
def staff_login():
    if request.form.get("pin", "") == STAFF_PIN:
        resp = make_response(redirect("/staff"))
        resp.set_cookie("staff_auth", STAFF_PIN, max_age=60*60*24*30,
                        httponly=True, samesite="Lax")
        return resp
    return _LOGIN_HTML.format(err="PINが違います"), 401


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"クラウド中継サーバー起動: http://0.0.0.0:{port}/")
    app.run(host="0.0.0.0", port=port)
