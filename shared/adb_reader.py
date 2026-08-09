"""
Inkbirdアプリから温度を自動取得（BlueStacks + ADB）

仕組み:
  1. BlueStacksにADB接続
  2. Inkbirdアプリの画面をリスト先頭にスクロール
  3. UIダンプ取得 → 温度抽出
  4. スクロールしながら全センサーを収集
  5. config.json の sensor_index に従い temperatures.json を更新
"""

import os
import subprocess
import xml.etree.ElementTree as ET
import json
import time
import re
import sys
import io
import requests
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Windows で日本語・特殊文字を正しく出力する
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 実行する method 側のフォルダ（config.json / temperatures.json / ログの置き場所）。
# 各 method のランチャー（run_lite.py / server.py）が環境変数 BATH_DIR を設定する。
# 未設定なら従来どおりこのファイルのあるフォルダを使う（後方互換）。
BASE_DIR    = Path(os.environ.get("BATH_DIR") or Path(__file__).resolve().parent)
CONFIG_PATH = BASE_DIR / "config.json"
TEMPS_PATH  = BASE_DIR / "temperatures.json"
LOG_PATH    = BASE_DIR / "bath_system.log"

# ── ログ設定 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # 1MB×3世代でローテーション（無限肥大を防止）
        RotatingFileHandler(str(LOG_PATH), maxBytes=1_000_000,
                            backupCount=3, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("bath")


# ── 設定読み込み ──────────────────────────────────────
def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── ADB コマンド実行 ──────────────────────────────────
def adb(cfg: dict, *args, timeout=20) -> tuple[str, int]:
    exe  = cfg["adb"].get("exe", "adb")
    # serial を指定すれば USB実機（-s <serial>）。未指定なら host:port（BlueStacks/ワイヤレス）
    serial = cfg["adb"].get("serial")
    host = cfg["adb"]["host"]
    port = cfg["adb"]["port"]
    target = serial if serial else f"{host}:{port}"
    # connect コマンド以外は -s でターゲットを明示指定
    if args and args[0] == "connect":
        cmd = [exe] + list(args)
    else:
        cmd = [exe, "-s", target] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1
    except FileNotFoundError:
        return f"ADB not found: {exe}", 1


# ── ADB 接続 ──────────────────────────────────────────
def connect(cfg: dict) -> bool:
    serial = cfg["adb"].get("serial")
    if serial:
        # USB実機: connect は不要。デバイスが device 状態かだけ確認する
        out, _ = adb(cfg, "get-state")
        ok = out.strip() == "device"
        if ok:
            log.info(f"  [OK] ADB接続(USB): {serial}")
        else:
            log.info(f"  [NG] ADB未接続(USB): {serial} → {out.strip()}")
        return ok
    host = cfg["adb"]["host"]
    port = cfg["adb"]["port"]
    out, _ = adb(cfg, "connect", f"{host}:{port}")
    ok = "connected" in out or "already connected" in out
    if ok:
        log.info(f"  [OK] ADB接続: {host}:{port}")
    else:
        log.info(f"  [NG] ADB接続失敗: {out.strip()}")
    return ok


# ── UIダンプ取得 ──────────────────────────────────────
LOCAL_DUMP = BASE_DIR / "window_dump.xml"

def dump_ui(cfg: dict, retries: int = 3) -> ET.Element | None:
    """UIダンプ取得。アニメーション中は uiautomator dump が失敗して
    空ファイルになることがあるため、リトライする。"""
    exe    = cfg["adb"].get("exe", "adb")
    serial = cfg["adb"].get("serial")
    host   = cfg["adb"]["host"]
    port   = cfg["adb"]["port"]
    target = serial if serial else f"{host}:{port}"

    for attempt in range(retries):
        if attempt > 0:
            time.sleep(2)  # アニメーション終了を待ってから再試行

        # 1) 端末内でダンプ生成
        out, code = adb(cfg, "shell", "uiautomator", "dump", "/sdcard/window_dump.xml")
        time.sleep(1.5)  # ダンプ完了を待つ
        if "dumped" not in out.lower():
            log.info(f"  [!] uiautomator dump 失敗 (試行{attempt+1}/{retries}): {out.strip()[:80]}")
            continue

        # 2) exec-out cat でファイル内容を直接取得（adb pull はBlueStacksで失敗するため）
        cmd = [exe, "-s", target, "exec-out", "cat", "/sdcard/window_dump.xml"]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=20)
            xml_bytes = r.stdout
        except subprocess.TimeoutExpired:
            log.info("  [!] exec-out タイムアウト")
            continue
        except FileNotFoundError:
            log.info(f"  [!] ADB not found: {exe}")
            return None

        if not xml_bytes.strip():
            log.info(f"  [!] exec-out 結果が空 (試行{attempt+1}/{retries})")
            continue

        # ローカルにも保存（デバッグ用）
        LOCAL_DUMP.write_bytes(xml_bytes)

        # 3) XML解析
        try:
            xml_text = xml_bytes.decode("utf-8", errors="replace")
            return ET.fromstring(xml_text.strip())
        except ET.ParseError as e:
            log.info(f"  [!] XML解析エラー: {e}")
            continue

    return None


# ── センサーデータを座標付きで抽出 ──────────────────────
def extract_sensors_with_bounds(root: ET.Element) -> list[dict]:
    """
    画面上の全センサーデータを { temp, humidity, device_name, y_center } の形で返す
    温度(°C)と湿度(%)をペアにまとめる
    """
    temp_nodes = [n for n in root.iter("node")
                  if n.get("resource-id") == "com.inkbird.inkbirdapp:id/tv_temp"]
    unit_nodes = [n for n in root.iter("node")
                  if n.get("resource-id") == "com.inkbird.inkbirdapp:id/tv_unit"]
    name_nodes = [n for n in root.iter("node")
                  if n.get("resource-id") == "com.inkbird.inkbirdapp:id/tv_device_name"]

    # デバイス名（ページに1つ）
    device_name = name_nodes[0].get("text", "") if name_nodes else ""

    # (値, 単位, y座標) のリストを作る
    readings = []
    for t_node, u_node in zip(temp_nodes, unit_nodes):
        try:
            val  = float(t_node.get("text", ""))
            unit = u_node.get("text", "")
        except ValueError:
            continue
        bounds   = t_node.get("bounds", "")
        nums     = re.findall(r"\d+", bounds)
        y_center = (int(nums[1]) + int(nums[3])) // 2 if len(nums) >= 4 else 0
        readings.append({"val": val, "unit": unit, "y": y_center})

    # 温度→湿度 のペアにまとめる（順番で対応）
    results = []
    i = 0
    while i < len(readings):
        r = readings[i]
        if r["unit"] == "°C":
            sensor = {"temp": r["val"], "humidity": None,
                      "y": r["y"], "device_name": device_name}
            # 次が湿度(%)なら対応付け
            if i + 1 < len(readings) and readings[i+1]["unit"] == "%":
                sensor["humidity"] = readings[i+1]["val"]
                i += 2
            else:
                i += 1
            results.append(sensor)
        else:
            i += 1

    return results


# ── スワイプ操作 ──────────────────────────────────────
def scroll(cfg: dict, direction: str = "up"):
    """
    up  = 左スワイプ（次のセンサーページへ）
    top = 右スワイプ（前のセンサーページへ）
    y=200 の RecyclerView外エリアでスワイプすることで ViewPager を正しく操作できる
    """
    key      = "scroll_swipe" if direction == "up" else "scroll_top"
    coords   = cfg["adb"][key]
    duration = cfg["adb"].get("swipe_duration_ms", 400)
    wait     = cfg["adb"].get("swipe_wait_ms", 1500) / 1000

    adb(cfg, "shell", "input", "swipe",
        str(coords[0]), str(coords[1]),
        str(coords[2]), str(coords[3]),
        str(duration))
    time.sleep(wait)


# ── ページインジケーター取得 ──────────────────────────
def get_indicator_tabs(root: ET.Element) -> list:
    """
    indicator_home 内のタブ座標リストを返す
    戻り値: [(cx, cy, label), ...] label は dot が "" 、数字ページが "1","3" 等
    """
    tabs = []
    for node in root.iter("node"):
        if node.get("resource-id") == "com.inkbird.inkbirdapp:id/indicator_home":
            for child in node:
                bounds = child.get("bounds", "")
                nums = re.findall(r"\d+", bounds)
                if len(nums) >= 4:
                    cx = (int(nums[0]) + int(nums[2])) // 2
                    cy = (int(nums[1]) + int(nums[3])) // 2
                    label = child.get("text", "")
                    tabs.append((cx, cy, label))
            break
    return tabs


# ゲートウェイと判定するデバイス名キーワード
GATEWAY_KEYWORDS = ["IBS-M2", "IBS-M1", "GATEWAY"]

def is_gateway_device(device_name: str) -> bool:
    upper = device_name.upper()
    return any(kw in upper for kw in GATEWAY_KEYWORDS)


# ── 全センサー温度収集 ────────────────────────────────
def _norm_name(s: str) -> str:
    """デバイス名比較用の正規化。全角/半角カッコ・空白の違いを吸収する。
    例: 「大浴場（男）」「大浴場 (男)」「大浴場(男)」を同一視する。"""
    if not s:
        return ""
    table = str.maketrans("（）　", "() ")
    return s.translate(table).replace(" ", "").strip()


def find_device_coords(cfg: dict, device_name: str) -> tuple[int, int] | None:
    """UIダンプからデバイス名のテキストを探してタップ座標を返す。
    全角/半角カッコの違いは無視して照合する（B案）。"""
    root = dump_ui(cfg)
    if root is None:
        return None
    target = _norm_name(device_name)
    for node in root.iter("node"):
        if _norm_name(node.get("text", "")) == target:
            bounds = node.get("bounds", "")
            nums = re.findall(r"\d+", bounds)
            if len(nums) >= 4:
                cx = (int(nums[0]) + int(nums[2])) // 2
                cy = (int(nums[1]) + int(nums[3])) // 2
                return cx, cy
    return None


def scroll_device_list(cfg: dict):
    """ホーム画面のデバイス一覧(RecyclerView)を下にスクロールする。
    デバイス数が増えて一覧が画面に収まらない場合、下側の項目
    （例: 大浴場）を見つけるために使う。"""
    coords   = cfg["adb"].get("device_list_scroll", [360, 1300, 360, 700])
    duration = cfg["adb"].get("swipe_duration_ms", 300)
    adb(cfg, "shell", "input", "swipe",
        str(coords[0]), str(coords[1]), str(coords[2]), str(coords[3]), str(duration))
    time.sleep(1.5)


def _force_start(cfg: dict, pkg: str, app_wait: int):
    """force-stop → ランチャー起動（フォールバック用）"""
    adb(cfg, "shell", "am", "force-stop", pkg)
    time.sleep(2)
    adb(cfg, "shell", "monkey", "-p", pkg, "-c",
        "android.intent.category.LAUNCHER", "1")
    time.sleep(app_wait)


def refresh_device_view(cfg: dict, device_name: str | None = None):
    """
    Inkbirdのホーム一覧から指定デバイスをタップしてデバイス画面を開く。

    まずバックキーでホーム一覧への遷移を試みる。
    デバイス名が見つからなければ force-stop → 再起動にフォールバック。

    単体センサー機器（パントリー等、タブなしの1画面のみ）は、複数センサーを
    束ねるハブ機器（湯畑・大浴場等）よりも画面が単純で読み込みが速いため、
    adb.single_sensor_wait（既定2秒）を使って待ち時間を短縮する。
    ハブ機器は従来通り adb.page_refresh_wait（既定4秒）を使う。
    """
    ui       = cfg["adb"].get("ui", {})
    target   = device_name or ui.get("device_name", "湯畑")
    single_sensor_devices = {_norm_name(n) for n in cfg["adb"].get("single_sensor_devices", [])}
    is_single = _norm_name(target) in single_sensor_devices
    wait     = cfg["adb"].get("single_sensor_wait", 2) if is_single \
               else cfg["adb"].get("page_refresh_wait", 4)
    app_wait = cfg["adb"].get("app_launch_wait", 9)
    pkg      = cfg["adb"].get("inkbird_package", "com.inkbird.inkbirdapp")

    # ① バックキーでホーム一覧へ戻ることを試みる
    log.info(f"  [バック遷移] バックキーでホームへ戻る試み")
    adb(cfg, "shell", "input", "keyevent", "4")
    time.sleep(2)
    coords = find_device_coords(cfg, target)
    if coords is None:
        # ホーム一覧に戻れていない → force-stop にフォールバック
        log.info(f"  [フォールバック] 「{target}」が見つからず → force-stop → 再起動")
        _force_start(cfg, pkg, app_wait)

    # ② デバイス名がホーム一覧に現れるまでリトライしてタップ
    #    見つからない場合は一覧を下にスクロールしてから再検索する
    #   （デバイス数が多く画面に収まらない場合、下側の項目は初期表示では見えないため）
    log.info(f"  「{target}」を検索中...")
    coords = None
    for attempt in range(6):
        coords = find_device_coords(cfg, target)
        if coords:
            break
        if attempt == 2:
            log.info(f"  「{target}」が見つからないため一覧をスクロール...")
            scroll_device_list(cfg)
        time.sleep(2)

    if coords:
        log.info(f"  「{target}」発見: x={coords[0]}, y={coords[1]}")
        adb(cfg, "shell", "input", "tap", str(coords[0]), str(coords[1]))
    else:
        device_x = ui.get("device_tap_x", 188)
        device_y = ui.get("device_tap_y", 1120)
        log.info(f"  「{target}」が見つからず、デフォルト座標を使用: ({device_x},{device_y})")
        adb(cfg, "shell", "input", "tap", str(device_x), str(device_y))

    log.info(f"  データ読み込み待ち {wait}秒...")
    time.sleep(wait)


def find_sensor_tabs(root: ET.Element) -> list[tuple[int, int]]:
    """デバイス画面 上部の clickable な番号タブ(1,3,4,5,6...)の中心座標を左から順に返す"""
    tabs = []
    for n in root.iter("node"):
        if n.get("clickable") == "true" and n.get("text", "").strip().isdigit():
            nums = re.findall(r"\d+", n.get("bounds", ""))
            if len(nums) >= 4:
                y = (int(nums[1]) + int(nums[3])) // 2
                if y < 200:   # 画面上部のタブのみ
                    x = (int(nums[0]) + int(nums[2])) // 2
                    tabs.append((x, y))
    tabs.sort()
    return tabs


def collect_device_temperatures(cfg: dict, device_name: str) -> dict:
    """
    1つのInkbirdデバイスのセンサーを全タブ巡回して収集する。
    戻り値: {"sensors": {センサー名: {temp,humidity}}, "gateway": {temp,humidity}|None}

    config の adb.single_sensor_devices に列挙された機器（パントリーの単体
    温湿度計など）は、タブ探索・タップを一切行わず選択直後の画面だけを読む。
    画面内の表示名は"IBS-M2"等の型番になり全台共通でゲートウェイ扱いされて
    しまうため、device_name（呼び出し元が指定した機器名）をキーに記録する。
    """
    refresh_device_view(cfg, device_name)

    collected: dict = {}
    gateway: dict | None = None
    tab_wait = cfg["adb"].get("tab_wait", 4)
    single_sensor_devices = set(cfg["adb"].get("single_sensor_devices", []))
    single_sensor = _norm_name(device_name) in {_norm_name(n) for n in single_sensor_devices}

    def read_current(label: str, root_override=None):
        nonlocal gateway
        r = root_override if root_override is not None else dump_ui(cfg)
        if r is None:
            log.info(f"    {label}: UIダンプ失敗")
            return
        visible = extract_sensors_with_bounds(r)
        if not visible:
            log.info(f"    {label}: データなし")
            return
        s = visible[0]
        dev = s.get("device_name", "")
        if single_sensor:
            collected[device_name] = s
            log.info(f"    {label}: [{device_name}] {s['temp']}°C" +
                     (f" / {s['humidity']}%" if s.get("humidity") is not None else ""))
        elif is_gateway_device(dev):
            gateway = {"temp": s["temp"], "humidity": s.get("humidity")}
            log.info(f"    {label}: [{dev}] {s['temp']}°C → 外気温")
        elif dev and dev not in collected:
            collected[dev] = s
            log.info(f"    {label}: [{dev}] {s['temp']}°C" +
                     (f" / {s['humidity']}%" if s.get("humidity") is not None else ""))

    if single_sensor:
        # 単体センサー機器: タブ探索・タップは一切行わず初期画面だけ読む
        log.info(f"  単体センサー機器のためタブ操作なし")
        read_current("初期画面")
    else:
        root = dump_ui(cfg)
        tabs = find_sensor_tabs(root) if root is not None else []
        log.info(f"  検出タブ数: {len(tabs)} {tabs}")
        read_current("初期画面", root_override=root)
        for i, (x, y) in enumerate(tabs):
            adb(cfg, "shell", "input", "tap", str(x), str(y))
            time.sleep(tab_wait)
            read_current(f"タブ{i+1}")

    log.info(f"  [{device_name}] 取得完了: センサー={list(collected.keys())} / ゲートウェイ={'あり' if gateway else 'なし'}")
    return {"sensors": collected, "gateway": gateway}


def collect_all_temperatures(cfg: dict) -> dict:
    """
    config の adb.devices リストに定義された全Inkbirdデバイスを順に巡回して
    センサー温度を収集する。
    devices が未定義の場合は ui.device_name の1台のみ取得（後方互換）。
    戻り値: {"sensors": {センサー名: {temp,humidity}}, "gateway": {temp,humidity}|None}
    """
    devices = cfg["adb"].get("devices") or [cfg["adb"]["ui"].get("device_name", "湯畑")]
    all_sensors: dict = {}
    all_gateway: dict | None = None

    for dev_name in devices:
        log.info(f"=== デバイス「{dev_name}」取得開始 ===")
        result = collect_device_temperatures(cfg, dev_name)
        all_sensors.update(result["sensors"])
        if result["gateway"] and all_gateway is None:
            all_gateway = result["gateway"]

    log.info(f"  全デバイス取得完了: センサー={list(all_sensors.keys())}")
    return {"sensors": all_sensors, "gateway": all_gateway}


# ── temperatures.json 更新 ────────────────────────────
def load_temps() -> dict:
    if not TEMPS_PATH.exists():
        return {}
    with open(TEMPS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_temps(data: dict):
    with open(TEMPS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def mark_offline(reason: str = ""):
    """
    通信失敗時：前回取得した温度をそのまま保持し、online=false だけ記録する。
    last_updated（最後に成功した時刻）は変更しない＝Web側で「最終取得 HH:MM」を出せる。
    """
    temps = load_temps()
    temps["online"]       = False
    temps["last_attempt"] = datetime.now().isoformat()
    save_temps(temps)
    log.info(f"  [オフライン記録] 前回の温度を保持（理由: {reason or '不明'}）")


def update_temps(cfg: dict, sensors: dict,
                 gateway: dict | None = None) -> int:
    """
    sensor_name（センサー名）で湯舟を識別して temperatures.json を書き換える。
    取得できなかった湯舟は「前回値を保持して stale=True」にし、
    Web側でその湯舟だけ未接続マーク＋最終値表示にする。
    """
    prev: dict = load_temps()   # 個別保持のための前回値
    now = datetime.now().isoformat()
    temps: dict = {}
    matched = 0
    for bath in cfg["baths"]:
        sname = bath.get("sensor_name", bath["name"])
        s = sensors.get(sname)
        bid = str(bath["id"])
        if s is None:
            # 個別取得失敗 → 前回値・最終取得時刻を引き継ぎ、その湯舟だけ未接続(stale)
            p = prev.get(bid) if isinstance(prev.get(bid), dict) else {}
            temps[bid] = {
                "temp":     p.get("temp"),
                "humidity": p.get("humidity"),
                "stale":    True,
                "at":       p.get("at"),   # 最後に取得できた時刻を保持
            }
        else:
            temps[bid] = {
                "temp":     s["temp"],
                "humidity": s.get("humidity"),
                "stale":    False,
                "at":       now,           # 今回取得できた時刻
            }
            matched += 1
    # ゲートウェイ（外気温）も同様に個別保持
    if gateway is not None:
        temps["gateway"] = {"temp": gateway.get("temp"),
                            "humidity": gateway.get("humidity"), "stale": False, "at": now}
    else:
        pg = prev.get("gateway") if isinstance(prev.get("gateway"), dict) else {}
        temps["gateway"] = {"temp": pg.get("temp"),
                            "humidity": pg.get("humidity"), "stale": True, "at": pg.get("at")}
    temps["last_updated"] = now
    temps["last_attempt"] = now
    temps["online"]       = True
    save_temps(temps)
    return matched


# ── メイン実行 ────────────────────────────────────────
def run_once(cfg: dict, retries: int = 4) -> bool:
    """
    1回分の取得・更新処理。センサー0件の場合は retries 回リトライする。
    """
    if not connect(cfg):
        mark_offline("ADB接続失敗")
        log.info("=" * 50)
        log.info("【通信失敗】ADB未接続 → 前回の温度を表示し続けます（未接続マーク）")
        log.info("=" * 50)
        return False

    sensor_temps: list = []
    gateway = None

    for attempt in range(retries + 1):
        if attempt > 0:
            log.info(f"[リトライ {attempt}/{retries}] センサーが見つからなかったため再試行...")
            time.sleep(3)

        log.info("センサーデータ収集中...")
        result = collect_all_temperatures(cfg)
        sensor_temps = result["sensors"]
        gateway      = result["gateway"]

        # 1つでも取得できれば成功とみなす
        n_ok = sum(1 for s in sensor_temps if s is not None)
        if n_ok > 0:
            break

        log.info(f"[!] 水温データなし（試行 {attempt + 1}/{retries + 1}）")

    # 1件も取得できなかった＝通信失敗とみなし、前回値を保持して未接続マーク
    if not sensor_temps:
        mark_offline("センサーデータ取得失敗")
        log.info("=" * 50)
        log.info("【通信失敗】データ取得0件 → 前回の温度を表示し続けます（未接続マーク）")
        log.info("=" * 50)
        return False

    matched = update_temps(cfg, sensor_temps, gateway)
    saved = load_temps()  # 保持された前回値を表示するため読み戻す

    log.info("=" * 50)
    log.info(f"【データ取得完了】")
    if gateway:
        h = f" / 湿度 {gateway['humidity']}%" if gateway.get("humidity") is not None else ""
        log.info(f"  外気温（加賀市）: {gateway['temp']}°C{h}")
    else:
        log.info("  外気温（加賀市）: -- ℃（3周内に取得できず → 未接続）")
    for bath in cfg["baths"]:
        sname = bath.get("sensor_name", bath["name"])
        s = sensor_temps.get(sname)
        if s is not None:
            h = f" / 湿度 {s['humidity']}%" if s.get("humidity") is not None else ""
            log.info(f"  {bath['name']} ({sname}): {s['temp']}°C{h}")
        else:
            # 3周とも取れず → 前回値を保持して未接続(stale)
            kept = saved.get(str(bath["id"]), {})
            kt = kept.get("temp")
            kt_str = f"{kt}°C(前回値)" if kt is not None else "-- ℃"
            log.info(f"  {bath['name']} ({sname}): {kt_str} ← 3周内に取得できず・未接続(stale)")
    log.info(f"  → temperatures.json 更新（取得{matched}箇所 / 未接続{len(cfg['baths'])-matched}箇所）")
    log.info("=" * 50)

    return matched > 0


def push_to_cloud(cfg: dict):
    """取得結果(temperatures.json)をクラウドサーバーへ送信する"""
    c = cfg.get("cloud", {})
    url = c.get("url")
    if not url:
        return  # cloud.url 未設定なら送信しない（ローカル運用）
    # 自分のローカルAPI(/api/baths)から案内板用の完成形JSONを取得して転送する
    local_api = c.get("local_api", "http://127.0.0.1:5000/api/baths")
    try:
        payload = requests.get(local_api, timeout=10).json()
        r = requests.post(url.rstrip("/") + "/api/push", json=payload,
                          headers={"X-Token": c.get("token", "")}, timeout=15)
        log.info(f"  [クラウド送信] {r.status_code} → {url}")
    except Exception as e:
        log.info(f"  [クラウド送信失敗] {e}")


def run_loop(cfg: dict):
    """バックグラウンドループ（server.pyから呼ぶ）"""
    interval = cfg["adb"].get("interval", 30)
    while True:
        try:
            log.info(f"【取得開始】次回は {interval}秒後")
            run_once(cfg)
            push_to_cloud(cfg)
        except Exception as e:
            log.info(f"[!] エラー: {e}")
        log.info(f"【待機中】{interval}秒後に次の取得を開始します")
        time.sleep(interval)


# ── スタンドアロン実行 ────────────────────────────────
if __name__ == "__main__":
    import sys
    cfg = load_config()

    if not cfg["adb"].get("enabled", True):
        print("ADBが無効です (config.json の adb.enabled を true に)")
        sys.exit(1)

    if "--loop" in sys.argv:
        print("=== ADB自動取得 開始（Ctrl+Cで停止）===")
        run_loop(cfg)
    else:
        print("=== ADB温度取得（1回）===")
        ok = run_once(cfg)
        sys.exit(0 if ok else 1)
