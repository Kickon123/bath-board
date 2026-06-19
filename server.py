import json
import threading
import subprocess
import sys
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
TEMPS_PATH  = BASE_DIR / "temperatures.json"
BG_PATH     = BASE_DIR / "static" / "bg.png"
PDF_PATH    = BASE_DIR / "湯畑レイアウト.pdf"


# ── ユーティリティ ────────────────────────────────────
def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_temps():
    if not TEMPS_PATH.exists():
        return {}
    with open(TEMPS_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_temps(data):
    with open(TEMPS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── API エンドポイント ────────────────────────────────
@app.route("/")
@app.route("/slideshow")
def slideshow():
    return send_from_directory("static", "slideshow.html")

@app.route("/slideshow64")
@app.route("/64")
def slideshow64():
    return send_from_directory("static", "slideshow64.html")

@app.route("/yubatake")
def yubatake():
    return send_from_directory("static", "base7-flat.html")

@app.route("/base-all")
@app.route("/all")
def base_all():
    return send_from_directory("static", "base-all.html")

@app.route("/bath/yubatake")
def bath_yubatake():
    return send_from_directory("static", "base7-flat.html")

@app.route("/bath/daiyokujo")
def bath_daiyokujo():
    return send_from_directory("static", "daiyokujo.html")

@app.route("/bath/all")
def bath_all():
    return send_from_directory("static", "base-all.html")


@app.route("/api/baths")
def api_baths():
    cfg   = load_config()
    temps = load_temps()
    baths = []
    for b in cfg["baths"]:
        entry = temps.get(str(b["id"]))
        # entry は数値（手動入力）またはdict（ADB取得）の両方に対応
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
        baths.append({**b, "temp": temp, "humidity": humidity, "stale": stale, "at": at})

    # ゲートウェイ（外気温）
    gateway      = temps.get("gateway")       # {"temp": X, "humidity": Y} or None
    last_updated = temps.get("last_updated")  # 最後に成功した取得時刻
    last_attempt = temps.get("last_attempt")  # 最後に試行した時刻
    online       = temps.get("online", True)  # 直近の取得が成功したか

    return jsonify({
        "baths": baths, "gateway": gateway,
        "last_updated": last_updated, "last_attempt": last_attempt,
        "online": online,
    })

@app.route("/api/temp/<int:bath_id>", methods=["POST"])
def api_set_temp(bath_id):
    body  = request.get_json()
    temp  = body.get("temp")
    temps = load_temps()
    if temp is None:
        temps.pop(str(bath_id), None)
    else:
        temps[str(bath_id)] = temp
    save_temps(temps)
    return jsonify({"ok": True})

@app.route("/api/position/<int:bath_id>", methods=["POST"])
def api_set_position(bath_id):
    body = request.get_json()
    cfg  = load_config()
    for b in cfg["baths"]:
        if b["id"] == bath_id:
            b["left"] = round(body["left"], 2)
            b["top"]  = round(body["top"],  2)
            break
    save_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/adb/status")
def api_adb_status():
    cfg = load_config()
    return jsonify({
        "enabled":  cfg["adb"].get("enabled", False),
        "interval": cfg["adb"].get("interval", 30),
        "running":  _adb_thread is not None and _adb_thread.is_alive(),
    })

@app.route("/api/adb/fetch", methods=["POST"])
def api_adb_fetch():
    """手動で今すぐ取得"""
    def _run():
        from adb_reader import run_once, load_config as lc
        run_once(lc())
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "message": "取得開始しました"})

@app.route("/api/bg/status")
def api_bg_status():
    return jsonify({"exists": BG_PATH.exists()})

@app.route("/api/bg/upload", methods=["POST"])
def api_bg_upload():
    if "photo" not in request.files:
        return jsonify({"error": "ファイルがありません"}), 400
    file = request.files["photo"]
    tmp  = BASE_DIR / "static" / "_upload_tmp.jpg"
    file.save(str(tmp))
    try:
        cmd = [sys.executable, str(BASE_DIR / "convert_photo.py"), str(tmp)]
        subprocess.run(cmd, check=True, capture_output=True, cwd=str(BASE_DIR))
        tmp.unlink(missing_ok=True)
        return jsonify({"ok": True, "bg": "/static/bg.jpg"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr.decode("utf-8", errors="replace")}), 500


# ── ADB バックグラウンドスレッド ──────────────────────
_adb_thread: threading.Thread | None = None

def start_adb_loop():
    global _adb_thread
    cfg = load_config()
    # RF（RTL-SDR直接受信）が有効ならADBの代わりにそちらを使う
    if cfg.get("rf", {}).get("enabled", False):
        from rf_reader import run_loop
        print("[RF] RTL-SDR受信開始（rtl_433）")
        _adb_thread = threading.Thread(target=run_loop, args=(cfg,), daemon=True)
        _adb_thread.start()
        return
    from adb_reader import run_loop, load_config as lc
    cfg = lc()
    if not cfg["adb"].get("enabled", False):
        print("[ADB] 無効 (config.json の adb.enabled を true に)")
        return
    print(f"[ADB] バックグラウンド取得開始（{cfg['adb']['interval']}秒ごと）")
    _adb_thread = threading.Thread(target=run_loop, args=(cfg,), daemon=True)
    _adb_thread.start()


# ── 起動 ─────────────────────────────────────────────
def auto_convert_pdf():
    """起動時にPDFが存在すれば自動で背景画像に変換"""
    if PDF_PATH.exists() and not BG_PATH.exists():
        print("[PDF] 背景画像を生成中...")
        try:
            import fitz
            doc  = fitz.open(str(PDF_PATH))
            pix  = doc[0].get_pixmap(matrix=fitz.Matrix(3, 3))
            BG_PATH.parent.mkdir(exist_ok=True)
            pix.save(str(BG_PATH))
            print(f"[PDF] 変換完了: {BG_PATH.name}")
        except Exception as e:
            print(f"[PDF] 変換失敗: {e}")

if __name__ == "__main__":
    print("露天風呂モニター起動中...")
    print("ブラウザで http://localhost:5000 を開いてください")
    auto_convert_pdf()
    start_adb_loop()
    app.run(host="0.0.0.0", port=5000, debug=False)
