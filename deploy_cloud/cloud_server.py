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
import time
from collections import deque
from pathlib import Path

import requests as req
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_DIR = Path(__file__).parent
STORE    = BASE_DIR / "latest.json"
NAME_ID_MAP = BASE_DIR / "name_id_map.json"   # センサー名→id の自動採番テーブル（永続化）
BATH_CONFIG = BASE_DIR / "bath-config.json"   # スマホが取得する『温度取得対象リスト』（同梱・フォールバック用）
# 通常は GitHub の raw を直接読む → CMS公開で再デプロイ不要・数十秒で反映
BATH_CONFIG_URL = os.environ.get(
    "BATH_CONFIG_URL",
    "https://raw.githubusercontent.com/Kickon123/bath-board/main/deploy_cloud/bath-config.json")
_bc_cache = {"t": 0.0, "body": None}

SECRET    = os.environ.get("PUSH_TOKEN")
SUPA_URL  = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPA_KEY  = os.environ.get("SUPABASE_KEY", "")

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
def _load_name_id_map() -> dict:
    """センサー名→id の対応表。無ければ、現行 bath-config.json の
    sensor_name/name→id を初期値として作る（＝既存の案内板テンプレ(SPOTS)の
    id とズレないようにするための種まき）。以後は初めて見る名前にだけ、
    使われていない最小の空き番号を新規採番する。"""
    if NAME_ID_MAP.exists():
        try:
            return json.loads(NAME_ID_MAP.read_text(encoding="utf-8"))
        except Exception:
            pass
    seed = {}
    if BATH_CONFIG.exists():
        try:
            cur = json.loads(BATH_CONFIG.read_text(encoding="utf-8"))
            for b in cur.get("baths", []):
                key = (b.get("sensor_name") or b.get("name") or "").strip()
                if key and isinstance(b.get("id"), int):
                    seed[key] = b["id"]
        except Exception:
            pass
    _save_name_id_map(seed)
    return seed


def _save_name_id_map(m: dict):
    NAME_ID_MAP.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


def _id_for_name(m: dict, name: str) -> int:
    """名前に対応するidを返す。未登録なら、使われていない最小の番号を新規採番する。"""
    name = name.strip()
    if name in m:
        return m[name]
    used = set(m.values())
    nid = 1
    while nid in used:
        nid += 1
    m[name] = nid
    return nid


def _sensors_payload_to_baths(sensors: list) -> list:
    """新方式(名前ベース)の {"sensors": [{"name","temp",...}]} を、
    旧方式と同じ {"baths": [{"id","name","temp",...}]} 形へ変換する
    （id は初見の名前ごとに自動採番・永続化）。"""
    m = _load_name_id_map()
    baths = []
    changed = False
    for s in sensors:
        name = str(s.get("name", "")).strip()
        if not name:
            continue
        if name not in m:
            changed = True
        bid = _id_for_name(m, name)
        baths.append({
            "id": bid, "name": name, "device": "湯畑",
            "temp": s.get("temp"), "humidity": s.get("humidity"),
            "stale": s.get("stale", False), "at": s.get("at"),
        })
    if changed:
        _save_name_id_map(m)
    return baths


@app.post("/api/push")
def api_push():
    if not SECRET or request.headers.get("X-Token") != SECRET:
        return jsonify(error="forbidden"), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="no json"), 400
    # 新方式（名前ベース、"sensors"配列）が来たら、旧方式と同じ"baths"形へ変換して保存する。
    # 旧方式（"baths"配列、idはスマホ側で決め打ち）を送ってくる古いスマホとも
    # そのまま互換動作する（どちらの形式でも受理できる）。
    if isinstance(data.get("sensors"), list):
        data = {**data, "baths": _sensors_payload_to_baths(data["sensors"])}
        data.pop("sensors", None)
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


@app.get("/api/bath-config")
def api_bath_config():
    """スマホ(run_lite.py)が毎サイクル取得する『温度取得対象リスト』。
    GitHub の raw を直接読む（60秒キャッシュ）ので、CMSの公開で bath-config.json が
    変わると再デプロイ無しで数十秒後に反映される。取得失敗時は同梱ファイルにフォールバック。"""
    now = time.time()
    if _bc_cache["body"] is not None and now - _bc_cache["t"] < 60:
        return app.response_class(_bc_cache["body"], mimetype="application/json")
    try:
        r = req.get(BATH_CONFIG_URL, timeout=8)
        if r.status_code == 200 and isinstance(r.json().get("baths"), list):
            _bc_cache["body"] = r.text
            _bc_cache["t"] = now
            return app.response_class(r.text, mimetype="application/json")
    except Exception:
        pass
    if BATH_CONFIG.exists():
        return app.response_class(BATH_CONFIG.read_text(encoding="utf-8"),
                                  mimetype="application/json")
    return jsonify(baths=[])



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
    # allcutと同じファイル。大浴場パネルはJS側でパスを見て自動的に非表示にする
    return send_from_directory("static", "base-all-cut.html")

@app.get("/bath/yubatake")
def bath_yubatake():
    return send_from_directory("static", "base-all-cut.html")

@app.get("/bath/daiyokujo")
def bath_daiyokujo():
    return send_from_directory("static", "daiyokujo.html")

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


import re as _re
_SCREEN_SLUG_RE = _re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")

@app.get("/s/<slug>")
def custom_screen(slug):
    """CMSで追加した画面。static/screens/<slug>.html を配信（背景は /static/screens/<slug>.png）。"""
    if not _SCREEN_SLUG_RE.match(slug or ""):
        return "not found", 404
    f = BASE_DIR / "static" / "screens" / f"{slug}.html"
    if not f.is_file():
        return "not found", 404
    return send_from_directory(str(BASE_DIR / "static" / "screens"), f"{slug}.html")



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"クラウド中継サーバー起動: http://0.0.0.0:{port}/")
    app.run(host="0.0.0.0", port=port)
