"""直近のゲートウェイdp_id=1記録を全部取得し、温度26.6/24.3/39.6/37.5との対応を探す"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests, json, time

H = {
    "api-key": "__INKBIRD_API_KEY__",
    "api-secret-key": "__INKBIRD_API_SECRET_KEY__",
    "content-type": "application/json",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": "InkbirdApp/2.1.5 (iPhone; iOS 26.4.2; Scale/3.00)",
}
URL = "https://us.api-inkbird.com/api/smartAgent/history/get"
now = int(time.time() * 1000)
GATEWAY = "eba5d6d312122cba07raz1"

def fetch(dev, dp_id, hours):
    body = {"dev_id": dev, "product_id": "cx7qfwsatomtk5p8",
            "dateline_begin": now - hours*3600*1000, "dp_id_list": [dp_id],
            "dateline_end": now, "country_code": "81", "delete_type": 0, "time_interval": 0}
    r = requests.post(URL, headers=H, json=body, timeout=20)
    return r.json().get("list", []) if r.status_code == 200 else []

def analyze(v):
    iv = int(float(v))
    s = str(iv)
    # 各種の桁分割を表示
    groups = []
    # 末尾4桁 / 末尾3桁
    groups.append(f"末尾4={iv%10000} (/10={iv%10000/10})")
    groups.append(f"末尾3={iv%1000} (/10={iv%1000/10})")
    # 上位を削った中間など
    return f"{iv}  " + " | ".join(groups)

print("GATEWAY dp_id=1 直近3時間 全記録:")
recs = fetch(GATEWAY, 1, 3)
for rec in recs:
    ts = time.strftime("%H:%M:%S", time.localtime(int(rec['dateline'])/1000))
    print(f"  {ts}  {analyze(rec['dp_value'])}")

print("\nGATEWAY dp_id=1 直近30日 全記録:")
recs = fetch(GATEWAY, 1, 24*30)
for rec in recs:
    ts = time.strftime("%m/%d %H:%M:%S", time.localtime(int(rec['dateline'])/1000))
    print(f"  {ts}  {analyze(rec['dp_value'])}")

# 探したい温度*10
print("\n探索対象 temp*10:", [266,243,396,375])
