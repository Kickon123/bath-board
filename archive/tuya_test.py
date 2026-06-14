"""Tuya公式Cloud API 接続テスト"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from tuya_connector import TuyaOpenAPI

ACCESS_ID  = "x59ugvdmvexkhkqerk9s"
ACCESS_KEY = "9d05e03f4b0a443f8ee65a8ede48130a"
ENDPOINT   = "https://openapi.tuyaus.com"   # Western America

# 連携済みアカウントのTuya uid（Inkbird backendから入手済み）
TUYA_UID = "az1755672773522595hv"

openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_KEY)
print("== トークン取得（認証テスト） ==")
res = openapi.connect()
print(res)

print("\n== ユーザーのデバイス一覧 (uid=%s) ==" % TUYA_UID)
res = openapi.get(f"/v1.0/users/{TUYA_UID}/devices")
print(res)
