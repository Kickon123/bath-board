"""history/get の product_id 依存性テスト:
- product_id を省略/空にした場合
- dp_id_list を複数まとめて送った場合
で応答が変わるか確認する"""
import sys, io, time, json
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

H = {
    "api-key": "__INKBIRD_API_KEY__",
    "api-secret-key": "__INKBIRD_API_SECRET_KEY__",
    "content-type": "application/json",
    "accept": "*/*",
    "user-agent": "InkbirdApp/2.1.5 (iPhone; iOS 26.4.2; Scale/3.00)",
}
URL = "https://us.api-inkbird.com/api/smartAgent/history/get"
now = int(time.time() * 1000)
SUB = "eb2bda2a76897bc28bopk9"
GW  = "eba5d6d312122cba07raz1"

def call(label, body):
    try:
        r = requests.post(URL, headers=H, json=body, timeout=15)
        txt = r.text[:400]
        print(f"[{label}] {r.status_code} {len(r.content)}b")
        if r.status_code == 200:
            data = r.json()
            lst = data.get("list", [])
            print(f"  件数={len(lst)}")
            for rec in lst[-5:]:
                ts = time.strftime("%m/%d %H:%M", time.localtime(int(rec["dateline"])/1000))
                print(f"    {ts} {rec}")
        else:
            print("  " + txt)
    except Exception as e:
        print(f"[{label}] Error: {e}")

base = {"dev_id": SUB, "dateline_begin": now - 7*24*3600*1000,
        "dateline_end": now, "country_code": "81", "delete_type": 0,
        "time_interval": 0}

# 1. product_id なし + 複数dp
call("SUB pid省略 dp1-20", {**base, "dp_id_list": list(range(1, 21))})
# 2. product_id 空文字
call("SUB pid空 dp1-20", {**base, "product_id": "", "dp_id_list": list(range(1, 21))})
# 3. dp_id_list 空（全dp返す?）
call("SUB pid省略 dp空list", {**base, "dp_id_list": []})
# 4. dp_id_list 省略
b4 = dict(base); b4.pop("time_interval")
call("SUB dp_id_list省略", {**base})
# 5. time_interval=60 (集計モード?)
call("SUB interval=60 dp1-20", {**base, "dp_id_list": list(range(1, 21)), "time_interval": 60})
# 6. GW でも pid省略 全dp
call("GW pid省略 dp空list", {**base, "dev_id": GW, "dp_id_list": []})
