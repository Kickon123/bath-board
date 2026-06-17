"""Inkbird API - dp_idと期間を変えて温度データを探す"""
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
DEVICES = ["eb2bda2a76897bc28bopk9", "eba5d6d312122cba07raz1"]

# パターン1: 全期間（過去1年）で各種dp_idを試す
periods = [
    ("過去1時間", now - 3600*1000),
    ("過去24時間", now - 24*3600*1000),
    ("過去7日", now - 7*24*3600*1000),
    ("過去30日", now - 30*24*3600*1000),
    ("過去1年", now - 365*24*3600*1000),
]

for dev in DEVICES:
    print(f"\n{'='*60}\nデバイス: {dev}\n{'='*60}")
    for plabel, pbegin in periods:
        for dp_id in [0, 1, 2]:
            body = {
                "dev_id": dev,
                "product_id": "cx7qfwsatomtk5p8",
                "dateline_begin": pbegin,
                "dp_id_list": [dp_id],
                "dateline_end": now,
                "country_code": "81",
                "delete_type": 0,
                "time_interval": 0,
            }
            try:
                r = requests.post(URL, headers=H, json=body, timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    n = len(data.get("list", []))
                    if n > 0:
                        last = data["list"][-1]
                        ts = int(last['dateline']) / 1000
                        dt = time.strftime("%m/%d %H:%M", time.localtime(ts))
                        print(f"  {plabel} dp_id={dp_id}: {n}件 / 最新 {dt} dp_value={last['dp_value']}")
            except Exception as e:
                print(f"  {plabel} dp_id={dp_id}: エラー")
