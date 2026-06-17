"""ゲートウェイのライブdp(=1付近)を詳細調査。全フィールド表示＋エンコード推測"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests, json, time, struct

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
SUB = "eb2bda2a76897bc28bopk9"

def fetch(dev, dp_id, begin):
    body = {
        "dev_id": dev, "product_id": "cx7qfwsatomtk5p8",
        "dateline_begin": begin, "dp_id_list": [dp_id], "dateline_end": now,
        "country_code": "81", "delete_type": 0, "time_interval": 0,
    }
    try:
        r = requests.post(URL, headers=H, json=body, timeout=20)
        if r.status_code == 200:
            return r.json().get("list", [])
    except Exception as e:
        print("err", e)
    return []

def decode(v):
    """色々な解釈を試す"""
    try:
        iv = int(float(v))
    except:
        return ""
    out = []
    # 4バイトに分解
    b = struct.pack(">I", iv & 0xFFFFFFFF)
    out.append("bytes=" + " ".join(str(x) for x in b))
    out.append("hex=" + b.hex())
    # 下位16bit /10 /100
    lo = iv & 0xFFFF
    out.append(f"lo16={lo} /10={lo/10} /100={lo/100}")
    return " | ".join(out)

# 1) ゲートウェイ dp_id=1 の全記録（過去30日）を全フィールド表示
print("="*70)
print("GATEWAY dp_id=1 過去30日 全記録")
recs = fetch(GATEWAY, 1, now - 30*24*3600*1000)
for rec in recs:
    ts = time.strftime("%m/%d %H:%M", time.localtime(int(rec['dateline'])/1000))
    print(f"  {ts}  raw={rec}")
    print(f"        decode: {decode(rec.get('dp_value'))}")

# 2) ゲートウェイの dp_id 1..40, 100..140 を走査（過去48h）
print("\n" + "="*70)
print("GATEWAY dp走査 過去48h（件数>0のみ）")
for dp in list(range(1,41)) + list(range(100,141)) + list(range(200,211)):
    recs = fetch(GATEWAY, dp, now - 48*3600*1000)
    if recs:
        last = recs[-1]
        ts = time.strftime("%m/%d %H:%M", time.localtime(int(last['dateline'])/1000))
        print(f"  dp_id={dp}: {len(recs)}件 最新{ts} val={last.get('dp_value')}  {decode(last.get('dp_value'))}")

# 3) サブセンサーの dp走査（過去1年、件数>0）
print("\n" + "="*70)
print("SUB dp走査 過去1年（件数>0のみ）")
for dp in list(range(0,20)) + list(range(100,115)):
    recs = fetch(SUB, dp, now - 365*24*3600*1000)
    if recs:
        last = recs[-1]
        ts = time.strftime("%m/%d %H:%M", time.localtime(int(last['dateline'])/1000))
        print(f"  dp_id={dp}: {len(recs)}件 最新{ts} val={last.get('dp_value')}  {decode(last.get('dp_value'))}")
