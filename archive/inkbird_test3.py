"""ゲートウェイのサブデバイス（個別センサー）一覧を取得"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests, json

H = {
    "api-key": "8V073Jrc4H",
    "api-secret-key": "9HbzOuNhQlkESVW7PqxQ",
    "content-type": "application/json",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": "InkbirdApp/2.1.5 (iPhone; iOS 26.4.2; Scale/3.00)",
}
BASE = "https://us.api-inkbird.com"
GATEWAY = "eba5d6d312122cba07raz1"
TUYA_UID = "az1755672773522595hv"
HOME_ID = 261445727

def try_call(name, method, path, body=None):
    print(f"\n[{name}] {method} {path}")
    try:
        if method == "GET":
            r = requests.get(BASE + path, headers=H, timeout=15)
        else:
            r = requests.post(BASE + path, headers=H, json=body, timeout=15)
        print(f"  Status: {r.status_code} / {len(r.content)}b")
        if r.status_code == 200:
            try:
                print("  " + json.dumps(r.json(), ensure_ascii=False)[:500])
            except:
                print("  " + r.text[:200])
        elif r.status_code != 404:
            print("  " + r.text[:150])
    except Exception as e:
        print(f"  Error: {e}")

# 推測：サブデバイス取得API
try_call("subDevice", "POST", "/api/subDevice/get", {"gatewayId": GATEWAY})
try_call("childDevice", "POST", "/api/childDevice/list", {"deviceId": GATEWAY})
try_call("inkBird/subDevice", "POST", "/api/inkBird/subDevice", {"deviceId": GATEWAY, "tuyaUid": TUYA_UID})
try_call("inkBird/subDevice/v2", "POST", "/api/inkBird/subDevice/v2", {"deviceId": GATEWAY})
try_call("inkBird/getSubDevice", "POST", "/api/inkBird/getSubDevice", {"deviceId": GATEWAY})
try_call("device/sub/list", "POST", "/api/device/sub/list", {"deviceId": GATEWAY})
try_call("smartAgent/subDevice", "POST", "/api/smartAgent/subDevice", {"deviceId": GATEWAY})
try_call("smartAgent/getSubDevice", "POST", "/api/smartAgent/getSubDevice", {"deviceId": GATEWAY})
try_call("smartAgent/device/sub", "POST", "/api/smartAgent/device/sub", {"deviceId": GATEWAY})
try_call("smartAgent/device/children", "POST", "/api/smartAgent/device/children", {"parentId": GATEWAY})
try_call("inkBird/allDevice", "POST", "/api/inkBird/allDevice", {"homeId": HOME_ID, "tuyaUid": TUYA_UID})
try_call("inkBird/device/get", "POST", "/api/inkBird/device/get", {"homeId": HOME_ID, "tuyaUid": TUYA_UID})
try_call("inkBird/device/list", "POST", "/api/inkBird/device/list", {"homeId": HOME_ID, "tuyaUid": TUYA_UID})
try_call("inkBird/home/device", "POST", "/api/inkBird/home/device", {"homeId": HOME_ID})

# GET系
try_call("subDevice_GET", "GET", f"/api/subDevice/get?gatewayId={GATEWAY}")
try_call("inkBird/home_GET", "GET", f"/api/inkBird/home?homeId={HOME_ID}")
try_call("home/devices_GET", "GET", f"/api/home/devices?homeId={HOME_ID}")
