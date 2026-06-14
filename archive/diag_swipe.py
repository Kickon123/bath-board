"""
横スワイプの動作確認スクリプト
実行: python diag_swipe.py
"""
import subprocess, time, sys, io, json, re, xml.etree.ElementTree as ET
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
LOCAL_DUMP  = BASE_DIR / "window_dump.xml"

cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

def adb(*args, timeout=20):
    exe  = cfg["adb"]["exe"]
    host = cfg["adb"]["host"]
    port = cfg["adb"]["port"]
    if args and args[0] == "connect":
        cmd = [exe] + list(args)
    else:
        cmd = [exe, "-s", f"{host}:{port}"] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr

def dump():
    adb("shell", "uiautomator", "dump", "/sdcard/window_dump.xml")
    time.sleep(1.5)
    LOCAL_DUMP.unlink(missing_ok=True)
    adb("pull", "/sdcard/window_dump.xml", str(LOCAL_DUMP))
    if not LOCAL_DUMP.exists():
        return None
    xml_text = LOCAL_DUMP.read_text(encoding="utf-8", errors="replace")
    try:
        return ET.fromstring(xml_text.strip())
    except:
        return None

def get_temps(root):
    if root is None:
        return []
    temps = [n.get("text","") for n in root.iter("node")
             if n.get("resource-id") == "com.inkbird.inkbirdapp:id/tv_temp"]
    units = [n.get("text","") for n in root.iter("node")
             if n.get("resource-id") == "com.inkbird.inkbirdapp:id/tv_unit"]
    names = [n.get("text","") for n in root.iter("node")
             if n.get("resource-id") == "com.inkbird.inkbirdapp:id/tv_device_name"]
    return list(zip(temps, units, names or (["?"]*len(temps))))

def swipe_left():
    """左スワイプ（次センサーへ）- 速め"""
    adb("shell", "input", "swipe", "900", "800", "100", "800", "250")
    time.sleep(1.2)

def swipe_right():
    """右スワイプ（前センサーへ）"""
    adb("shell", "input", "swipe", "100", "800", "900", "800", "250")
    time.sleep(1.2)

# === 診断開始 ===
print("=== 横スワイプ診断 ===")
print()

# ADB接続
out = adb("connect", f"{cfg['adb']['host']}:{cfg['adb']['port']}")
print(f"接続: {out.strip()}")
print()

# ステップ1: 現在の画面をダンプ
print("--- [1] 現在の画面 ---")
root = dump()
before = get_temps(root)
print(f"  センサー: {before}")

# ステップ2: 左スワイプ
print()
print("--- [2] 左スワイプ実行（次ページへ）---")
swipe_left()
root2 = dump()
after1 = get_temps(root2)
print(f"  センサー: {after1}")

# ステップ3: 変化確認
print()
if before == after1:
    print("[!] スワイプ後も同じ内容 → スワイプが効いていないか、センサーが1件のみ")
    print()
    print("    別のY座標で試します（y=400）...")
    adb("shell", "input", "swipe", "900", "400", "100", "400", "250")
    time.sleep(1.2)
    root3 = dump()
    after2 = get_temps(root3)
    print(f"  センサー（y=400）: {after2}")

    if before != after2:
        print("  [OK] y=400 でスワイプ成功！config.json を更新してください")
    else:
        print()
        print("    y=600 で試します...")
        adb("shell", "input", "swipe", "900", "600", "100", "600", "250")
        time.sleep(1.2)
        root4 = dump()
        after3 = get_temps(root4)
        print(f"  センサー（y=600）: {after3}")
        if before != after3:
            print("  [OK] y=600 でスワイプ成功！")
        else:
            print("  [!] いずれも変化なし → センサーが現在1件のみ登録されている可能性があります")
else:
    print(f"[OK] スワイプ成功！ {before} → {after1}")
    print()
    print("--- [3] さらに左スワイプ ---")
    for i in range(3):
        swipe_left()
        root = dump()
        result = get_temps(root)
        print(f"  スワイプ{i+2}: {result}")
