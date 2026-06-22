#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# 露天風呂モニター  フルサーバー(Flask)起動スクリプト
#   server.py を起動して案内板(:5000)も自前で配信する。
#   使い方:  bash ~/bath_system/method_b/run.sh
#   ※ 設定は同フォルダの config.json、静的ファイルは ../shared/static を使う。
# ============================================================

# このスクリプト自身のあるフォルダ（= method_b）を基準にする
DIR="$(cd "$(dirname "$0")" && pwd)"

# 端末がスリープでCPUを止めないようロック確保（Termuxのときのみ・無ければ無視）
termux-wake-lock 2>/dev/null

# 自己ADB接続（毎回確認。tcpipが切れていたら要PC再設定）
adb connect 127.0.0.1:5555 >/dev/null 2>&1
STATE=$(adb -s 127.0.0.1:5555 get-state 2>/dev/null)
if [ "$STATE" != "device" ]; then
  echo "[!] ADB接続に失敗しました (127.0.0.1:5555)。"
  echo "    原因: tcpipモードが無効（再起動でリセットされた等）。"
  echo "    対処: PCにUSB接続して  adb tcpip 5555  を一度実行してください。"
  echo "    その後もう一度 run.sh を実行。"
  exit 1
fi
echo "[OK] ADB接続: 127.0.0.1:5555"

cd "$DIR" || exit 1
echo "[起動] http://localhost:5000  をブラウザで開いてください"
python server.py
