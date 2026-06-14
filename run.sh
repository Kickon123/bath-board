#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# 露天風呂モニター  起動スクリプト (スマホ/Termux用)
#   使い方:  bash ~/bath_system/run.sh
# ============================================================

# 端末がスリープでCPUを止めないようロック確保（termux-api不要の簡易版）
termux-wake-lock 2>/dev/null

# 自己ADB接続（毎回確認。tcpipが切れていたら要PC再設定）
adb connect 127.0.0.1:5555 >/dev/null 2>&1
STATE=$(adb -s 127.0.0.1:5555 get-state 2>/dev/null)
if [ "$STATE" != "device" ]; then
  echo "[!] スマホ自身へのADB接続に失敗しました。"
  echo "    原因: tcpipモードが無効（再起動でリセットされた等）。"
  echo "    対処: PCにUSB接続して  adb tcpip 5555  を一度実行してください。"
  echo "    その後もう一度 run.sh を実行。"
  exit 1
fi
echo "[OK] 自己ADB接続: 127.0.0.1:5555"

cd ~/bath_system || exit 1
echo "[起動] http://localhost:5000  をスマホのブラウザで開いてください"
python server.py
