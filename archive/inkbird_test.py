"""Inkbird API テスト（直近1分間の温度取得）"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests, json, time

H = {
    "api-key": "8V073Jrc4H",
    "api-secret-key": "9HbzOuNhQlkESVW7PqxQ",
    "content-type": "application/json",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": "InkbirdApp/2.1.5 (iPhone; iOS 26.4.2; Scale/3.00)",
    "accept-language": "ja-JP;q=1, en-JP;q=0.9",
}

URL = "https://us.api-inkbird.com/api/smartAgent/history/get"

# 直近24時間
now = int(time.time() * 1000)
DEVICES = [
    ("eb2bda2a76897bc28bopk9", "個別センサー"),
    ("eba5d6d312122cba07raz1", "ゲートウェイ"),
]

for dev_id, label in DEVICES:
    print(f"\n=== {label}: {dev_id} ===")
    body = {
        "dev_id": dev_id,
        "product_id": "cx7qfwsatomtk5p8",
        "dateline_begin": now - 24 * 3600 * 1000,  # 24時間前
        "dp_id_list": [0],
        "dateline_end": now,
        "country_code": "81",
        "delete_type": 0,
        "time_interval": 0,
    }
    for attempt in range(3):
        try:
            t0 = time.time()
            r = requests.post(URL, headers=H, json=body, timeout=30)
            elapsed = time.time() - t0
            print(f"試行{attempt+1}: Status={r.status_code} / {elapsed:.1f}秒 / {len(r.content)}bytes")
            if r.status_code == 200:
                data = r.json()
                if "list" in data:
                    n = len(data["list"])
                    print(f"  → 件数: {n}")
                    if n > 0:
                        last = data["list"][-1]
                        ts = int(last['dateline']) / 1000
                        dt = time.strftime("%H:%M:%S", time.localtime(ts))
                        print(f"  → 最新: {dt}  dp_value={last['dp_value']}")
                else:
                    print(f"  → {json.dumps(data, ensure_ascii=False)[:200]}")
                break
            elif r.status_code in (502, 504):
                print(f"  サーバーエラー、リトライ...")
                time.sleep(3)
            else:
                print(f"  本文: {r.text[:200]}")
                break
        except requests.exceptions.Timeout:
            print(f"試行{attempt+1}: タイムアウト")
            time.sleep(3)
        except Exception as e:
            print(f"試行{attempt+1}: エラー {e}")
            break
