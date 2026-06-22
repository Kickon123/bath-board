"""
RTL-SDRドングルでInkbird IBS-P02Rセンサーの電波(433.92MHz)を直接受信して温度取得

仕組み:
  1. rtl_433 を JSON出力モードでサブプロセス起動（プロトコル194 = Inkbird ITH-20R/IBS-P01R系）
  2. 受信パケットの sensor_num を config.json の rf.sensor_map で湯舟IDに対応付け
  3. 一定間隔で temperatures.json を adb_reader と同じ形式で更新
  4. 一定時間受信がないセンサーは前回値を保持して stale マーク

使い方:
  python3 rf_reader.py --discover      # 受信できる全パケットを表示（センサー対応付け調査用）
  python3 rf_reader.py                 # 通常運用（temperatures.json を更新し続ける）
  python3 rf_reader.py --replay f.log  # 保存済みJSONログでテスト（ドングル不要）
"""

import os
import subprocess
import json
import time
import sys
import io
import argparse
import threading
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 実行する method 側のフォルダ（adb_reader.py と同じく BATH_DIR で切り替え）。
# 未設定なら従来どおりこのファイルのあるフォルダを使う（後方互換）。
BASE_DIR    = Path(os.environ.get("BATH_DIR") or Path(__file__).resolve().parent)
CONFIG_PATH = BASE_DIR / "config.json"
TEMPS_PATH  = BASE_DIR / "temperatures.json"
LOG_PATH    = BASE_DIR / "bath_system.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RotatingFileHandler(str(LOG_PATH), maxBytes=1_000_000,
                            backupCount=3, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("bath")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def load_temps() -> dict:
    if not TEMPS_PATH.exists():
        return {}
    with open(TEMPS_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_temps(data: dict):
    with open(TEMPS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── rtl_433 起動 ─────────────────────────────────────
def spawn_rtl433(rf: dict) -> subprocess.Popen:
    cmd = [rf.get("exe", "rtl_433"),
           "-f", rf.get("frequency", "433.92M"),
           "-F", "json"]
    for proto in rf.get("protocols", [194]):
        cmd += ["-R", str(proto)]
    log.info("[RF] 起動: " + " ".join(cmd))
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            text=True, encoding="utf-8", errors="replace")


def packet_stream(rf: dict, replay: str | None):
    """rtl_433（またはリプレイログ）からJSONパケットを1件ずつ生成"""
    if replay:
        with open(replay, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("{"):
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        pass
        return
    while True:
        proc = spawn_rtl433(rf)
        try:
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("{"):
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        pass
        finally:
            proc.kill()
        log.info("[RF] rtl_433 が終了しました。10秒後に再起動します")
        time.sleep(10)


# ── 受信値 → temperatures.json 反映 ──────────────────
def pick_temp(pkt: dict, rf: dict) -> float | None:
    """パケットから水温を取り出す（temperature_C / temperature_2_C のどちらかを設定で選択）"""
    key = rf.get("temp_field", "temperature_C")
    v = pkt.get(key)
    if v is None:  # フォールバック
        v = pkt.get("temperature_C", pkt.get("temperature_2_C"))
    return v

def update_temps(cfg: dict, latest: dict):
    """latest: {sensor_num(str): {"temp","humidity","at"(epoch)}}"""
    rf          = cfg["rf"]
    sensor_map  = rf.get("sensor_map", {})       # {"RFセンサー番号": 湯舟ID}
    gw_num      = str(rf.get("gateway_sensor_num", ""))  # 外気温として扱うセンサー
    stale_after = rf.get("stale_after", 600)

    temps = load_temps()
    now_e = time.time()
    now   = datetime.now().isoformat()
    any_fresh = False

    for snum, r in latest.items():
        fresh = (now_e - r["at"]) <= stale_after
        entry = {"temp": r["temp"], "humidity": r["humidity"],
                 "stale": not fresh,
                 "at": datetime.fromtimestamp(r["at"]).isoformat()}
        if snum == gw_num:
            temps["gateway"] = entry
        elif snum in sensor_map:
            temps[str(sensor_map[snum])] = entry
        if fresh:
            any_fresh = True

    temps["last_attempt"] = now
    temps["online"]       = any_fresh
    if any_fresh:
        temps["last_updated"] = now
    save_temps(temps)


# ── メイン ───────────────────────────────────────────
def run(discover: bool, replay: str | None):
    cfg = load_config()
    rf  = cfg.get("rf", {})
    if not discover and not rf.get("sensor_map"):
        sys.exit("config.json に rf.sensor_map がありません。まず --discover で対応を調べてください")

    latest: dict = {}            # sensor_num → 最新受信値
    last_write = 0.0
    write_interval = rf.get("update_interval", 30)

    # 受信が途絶えても stale/未接続 マークが更新されるよう定期的に書き込む
    def watchdog():
        while True:
            time.sleep(60)
            if latest and time.time() - last_write > rf.get("stale_after", 600):
                log.info("[RF] 受信途絶 → staleマーク更新")
                update_temps(cfg, latest)
    if not discover and not replay:
        threading.Thread(target=watchdog, daemon=True).start()

    log.info("[RF] 受信待機中..." + ("（discoverモード）" if discover else ""))
    for pkt in packet_stream(rf, replay):
        model = str(pkt.get("model", ""))
        if "Inkbird" not in model and "inkbird" not in model:
            if discover:
                log.info(f"[RF][他機種] {json.dumps(pkt, ensure_ascii=False)}")
            continue

        snum = str(pkt.get("sensor_num", pkt.get("channel", pkt.get("id", "?"))))
        temp = pick_temp(pkt, rf)
        hum  = pkt.get("humidity")

        if discover:
            log.info(f"[RF] sensor_num={snum} temp={temp} temp2={pkt.get('temperature_2_C')} "
                     f"hum={hum} batt={pkt.get('battery_ok')} raw={json.dumps(pkt, ensure_ascii=False)}")
            continue

        if temp is None:
            continue
        latest[snum] = {"temp": round(float(temp), 1),
                        "humidity": round(float(hum), 1) if hum is not None else None,
                        "at": time.time()}
        log.info(f"[RF] 受信 sensor_num={snum} → {temp}°C" +
                 (f" / {hum}%" if hum is not None else ""))

        if time.time() - last_write >= write_interval:
            update_temps(cfg, latest)
            last_write = time.time()

    # リプレイ終了時は必ず書き込む
    if replay and latest and not discover:
        update_temps(cfg, latest)
        log.info("[RF] リプレイ完了 → temperatures.json 更新")


def run_loop(cfg: dict):
    """server.py から呼ばれるエントリポイント（adb_reader.run_loop と同形）"""
    run(discover=False, replay=None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true", help="全受信パケットを表示（対応付け調査）")
    ap.add_argument("--replay", help="rtl_433のJSONログを再生してテスト")
    args = ap.parse_args()
    run(args.discover, args.replay)
