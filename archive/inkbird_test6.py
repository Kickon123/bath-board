"""smartAgent等のデバイス一覧/現在dp値エンドポイントを総当たり探索"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests, json

H = {
    "api-key": "__INKBIRD_API_KEY__",
    "api-secret-key": "__INKBIRD_API_SECRET_KEY__",
    "content-type": "application/json",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": "InkbirdApp/2.1.5 (iPhone; iOS 26.4.2; Scale/3.00)",
}
BASE = "https://us.api-inkbird.com"
GW   = "eba5d6d312122cba07raz1"
SUB  = "eb2bda2a76897bc28bopk9"
UID  = "__TUYA_UID__"
INKUID = "__INKBIRD_UID__"
HOME = 261445727
PID  = "cx7qfwsatomtk5p8"

# 全部入りボディ（不要キーは無視される想定）
BODY = {
    "tuyaUid": UID, "tuyaUId": UID, "uid": INKUID, "homeId": HOME, "home_id": HOME,
    "devId": GW, "dev_id": GW, "deviceId": GW, "gatewayId": GW, "parentId": GW,
    "product_id": PID, "productId": PID, "country_code": "81", "countryCode": "81",
}

PATHS = [
    # device list / sub-device
    ("POST", "/api/smartAgent/device/list"),
    ("POST", "/api/smartAgent/device/get"),
    ("POST", "/api/smartAgent/deviceList"),
    ("POST", "/api/smartAgent/home/device/list"),
    ("POST", "/api/smartAgent/home/devices"),
    ("POST", "/api/smartAgent/sub/device/list"),
    ("POST", "/api/smartAgent/subDevice/list"),
    ("POST", "/api/smartAgent/subDevice/get"),
    ("POST", "/api/smartAgent/gateway/subDevice"),
    ("POST", "/api/smartAgent/gateway/sub/list"),
    ("POST", "/api/smartAgent/device/sub/list"),
    ("POST", "/api/smartAgent/device/children"),
    ("POST", "/api/smartAgent/group/device/list"),
    # current dp / status  ★本命
    ("POST", "/api/smartAgent/dp/get"),
    ("POST", "/api/smartAgent/dp/latest"),
    ("POST", "/api/smartAgent/device/dp"),
    ("POST", "/api/smartAgent/device/dp/get"),
    ("POST", "/api/smartAgent/device/status"),
    ("POST", "/api/smartAgent/device/status/get"),
    ("POST", "/api/smartAgent/status/get"),
    ("POST", "/api/smartAgent/getStatus"),
    ("POST", "/api/smartAgent/device/state"),
    ("POST", "/api/smartAgent/realtime/get"),
    ("POST", "/api/smartAgent/latest/get"),
    ("POST", "/api/smartAgent/now/get"),
    ("POST", "/api/smartAgent/current/get"),
    ("POST", "/api/smartAgent/history/last"),
    ("POST", "/api/smartAgent/history/latest"),
    # inkBird namespace
    ("POST", "/api/inkBird/device/list"),
    ("POST", "/api/inkBird/device/get"),
    ("POST", "/api/inkBird/subDevice/list"),
    ("POST", "/api/inkBird/home/device"),
    ("POST", "/api/inkBird/dp/get"),
    ("POST", "/api/inkBird/device/status"),
    # device namespace
    ("POST", "/api/device/list"),
    ("POST", "/api/device/get"),
    ("POST", "/api/device/dp/get"),
    ("POST", "/api/device/status"),
    ("POST", "/api/device/sub/list"),
    # GET variants
    ("GET", f"/api/smartAgent/device/list?homeId={HOME}&tuyaUId={UID}"),
    ("GET", f"/api/smartAgent/subDevice/list?devId={GW}"),
    ("GET", f"/api/smartAgent/dp/get?devId={GW}"),
    ("GET", f"/api/smartAgent/device/status?devId={GW}"),
    ("GET", f"/api/getSubDevice?devId={GW}&tuyaUId={UID}"),
    ("GET", f"/api/getDevice?homeId={HOME}&tuyaUId={UID}"),
    ("GET", f"/api/getDeviceList?homeId={HOME}&tuyaUId={UID}"),
    ("GET", f"/api/device/sub?devId={GW}"),
]

for method, path in PATHS:
    try:
        if method == "GET":
            r = requests.get(BASE + path, headers=H, timeout=12)
        else:
            r = requests.post(BASE + path, headers=H, json=BODY, timeout=12)
        body = r.text
        # 中身ありそうなものだけ目立たせる
        interesting = r.status_code == 200 and len(r.content) > 30 and '"data":null' not in body and '"data":[]' not in body
        mark = " <<<<<" if interesting else ""
        print(f"{r.status_code} {len(r.content):6}b {method:4} {path}{mark}")
        if interesting:
            print("        " + body[:400])
    except Exception as e:
        print(f"ERR        {method:4} {path}: {e}")
