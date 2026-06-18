"""
クラウド中継サーバー（受信 → 保持 → 配信 → 案内板表示）

役割:
  - スマホ(adb_reader)が温度を取得するたびに POST /api/push でここへ送信
  - 最新値を latest.json に保持
  - 履歴を history.json に蓄積（最大 600 件 ≒ 約 30 時間）
  - 別モニターのブラウザは GET / （案内板HTML）を開き、5秒ごとに /api/baths を読む

ローカル試験:   python3 cloud_server.py    → http://<このPCのIP>:8000/
クラウド配備:   Render等にこのファイル + static/ を置く（gunicorn cloud_server:app）
"""
import json
import os
from collections import deque
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_DIR     = Path(__file__).parent
STORE        = BASE_DIR / "latest.json"
HISTORY_FILE = BASE_DIR / "history.json"
HISTORY_MAX  = 600  # 3分間隔で約30時間分

# なりすまし防止の共有トークン。実値はコードに書かず、環境変数 PUSH_TOKEN で必ず設定する
# （会社のシークレット管理から注入）。スマホ側 config.json の cloud.token と一致させること。
# 未設定時は安全側に倒して全 push を拒否する。
SECRET = os.environ.get("PUSH_TOKEN")

# 起動時に既存の履歴を読み込む
_history: deque = deque(maxlen=HISTORY_MAX)
if HISTORY_FILE.exists():
    try:
        saved = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        _history.extend(saved[-HISTORY_MAX:])
    except Exception:
        pass


@app.post("/api/push")
def api_push():
    if not SECRET or request.headers.get("X-Token") != SECRET:
        return jsonify(error="forbidden"), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="no json"), 400
    STORE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    # 履歴に追記
    _history.append(data)
    HISTORY_FILE.write_text(json.dumps(list(_history), ensure_ascii=False), encoding="utf-8")
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
    指定した湯舟IDの過去データを返す（古い順）。
    GET /api/history?id=1&n=100
    """
    bath_id = request.args.get("id", type=int)
    n       = request.args.get("n", 100, type=int)

    result = []
    for snap in list(_history):
        ts = snap.get("last_updated")
        if not ts:
            continue
        if bath_id is not None:
            bath = next((b for b in snap.get("baths", []) if b.get("id") == bath_id), None)
            if bath:
                result.append({
                    "at":    ts,
                    "temp":  bath.get("temp"),
                    "stale": bath.get("stale", False),
                })
        else:
            result.append({
                "at":    ts,
                "baths": [{"id": b["id"], "temp": b.get("temp"), "stale": b.get("stale", False)}
                          for b in snap.get("baths", [])],
            })

    # 最新 n 件を古い順で返す
    return jsonify(result[-n:])


@app.get("/")
@app.get("/slideshow")
def slideshow():
    # スライドショー案内板 7:3（左:温度マップ(base7-flat) / 右:案内画像）
    return send_from_directory("static", "slideshow.html")


@app.get("/slideshow64")
@app.get("/64")
def slideshow64():
    # スライドショー案内板 6:4 版（右の案内画像を拡大）
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


@app.get("/staff")
def staff():
    # 従業員向けステータスモニター（スマホ縦画面）
    return send_from_directory("static", "staff.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"クラウド中継サーバー起動: http://0.0.0.0:{port}/")
    app.run(host="0.0.0.0", port=port)
