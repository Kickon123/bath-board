"""
クラウド中継サーバー（受信 → 保持 → 配信 → 案内板表示）

役割:
  - スマホ(adb_reader)が温度を取得するたびに POST /api/push でここへ送信
  - 最新値を latest.json に保持
  - 別モニターのブラウザは GET / （案内板HTML）を開き、5秒ごとに /api/baths を読む

ローカル試験:   python3 cloud_server.py    → http://<このPCのIP>:8000/
クラウド配備:   Render等にこのファイル + static/ を置く（gunicorn cloud_server:app）
"""
import json
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_DIR = Path(__file__).parent
STORE    = BASE_DIR / "latest.json"
# なりすまし防止の共有トークン（config.phone.json の cloud.token と一致させる）
SECRET   = os.environ.get("PUSH_TOKEN", "bath-secret-2026")


@app.post("/api/push")
def api_push():
    if request.headers.get("X-Token") != SECRET:
        return jsonify(error="forbidden"), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="no json"), 400
    STORE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return jsonify(ok=True)


@app.get("/api/baths")
def api_baths():
    if STORE.exists():
        return app.response_class(STORE.read_text(encoding="utf-8"),
                                  mimetype="application/json")
    return jsonify(baths=[], gateway=None, online=False)


@app.get("/")
@app.get("/board")
def board():
    # 既存の案内板HTMLをそのまま配信（/api/baths を5秒ごとに読む作りになっている）
    return send_from_directory("static", "base7-flat.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"クラウド中継サーバー起動: http://0.0.0.0:{port}/")
    app.run(host="0.0.0.0", port=port)
