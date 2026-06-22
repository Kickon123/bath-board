#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# 露天風呂モニター  制御スクリプト (スマホ/Termux用)
#   使い方:
#     bash ~/bath_system/method_a/ctl.sh start     起動（バックグラウンド）
#     bash ~/bath_system/method_a/ctl.sh stop      停止（kill）
#     bash ~/bath_system/method_a/ctl.sh restart   再起動
#     bash ~/bath_system/method_a/ctl.sh status    状態確認（ADB接続・稼働・ポート）
#     bash ~/bath_system/method_a/ctl.sh check     接続確認のみ（自己ADB）
#     bash ~/bath_system/method_a/ctl.sh log       ログを追尾表示（Ctrl+Cで抜ける）
#
#   ※ 短縮エイリアスを入れておくと便利（最下部の説明参照）:
#        b start / b stop / b restart / b status / b log
# ============================================================
set -u

# このスクリプト自身のあるフォルダ（= method_a）を基準にする
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$DIR/server.pid"
LOGFILE="$DIR/server.out"
ADB_TARGET="127.0.0.1:5555"
# 起動するアプリ。軽量版(run_lite.py)は温度取得→Render送信のみ(Flaskなし)。
# 共有コア(adb_reader)は ../shared から、設定は同フォルダの config.json を参照する。
APP="run_lite.py"

# ── 自己ADB接続を確認（必要なら接続）。device状態なら0を返す ──
adb_check() {
  adb connect "$ADB_TARGET" >/dev/null 2>&1
  local state
  state=$(adb -s "$ADB_TARGET" get-state 2>/dev/null)
  if [ "$state" = "device" ]; then
    echo "[OK] 自己ADB接続: $ADB_TARGET"
    return 0
  fi
  echo "[NG] 自己ADB接続に失敗: $ADB_TARGET (state=${state:-なし})"
  echo "     原因: tcpipモードが無効（スマホ再起動でリセット等）。"
  echo "     対処: PCにUSB接続して  adb tcpip 5555  を一度実行 → もう一度 start。"
  return 1
}

# ── サーバープロセスのPIDを返す（PIDファイル優先、無ければ探索）──
server_pid() {
  if [ -f "$PIDFILE" ]; then
    local pid
    pid=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "$pid"; return 0
    fi
  fi
  # PIDファイルが無い/古い場合は実行中プロセスを探す
  pgrep -f "python .*$APP" | head -n1
}

is_running() { [ -n "$(server_pid)" ]; }

# ── 起動 ──────────────────────────────────────────────
start() {
  if is_running; then
    echo "[info] すでに起動しています (PID $(server_pid))。  → status で確認"
    return 0
  fi
  # スリープでCPUを止めないようロック確保
  termux-wake-lock 2>/dev/null

  adb_check || { echo "[中止] ADB未接続のため起動しません。"; exit 1; }

  cd "$DIR" || { echo "[!] $DIR が見つかりません"; exit 1; }
  echo "[起動] $APP をバックグラウンドで開始..."
  nohup python "$APP" >"$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  sleep 2
  if is_running; then
    echo "[OK] 起動しました (PID $(cat "$PIDFILE"))  [$APP]"
    echo "     動作:  温度取得 → Render クラウドへ送信（Flaskなし軽量版）"
    echo "     ログ:    bash $DIR/ctl.sh log"
  else
    echo "[!] 起動に失敗しました。ログを確認してください:"
    tail -n 20 "$LOGFILE" 2>/dev/null
    exit 1
  fi
}

# ── 停止 ──────────────────────────────────────────────
stop() {
  local pid
  pid=$(server_pid)
  if [ -z "$pid" ]; then
    echo "[info] 起動していません。"
    rm -f "$PIDFILE"
    termux-wake-unlock 2>/dev/null
    return 0
  fi
  echo "[停止] PID $pid を終了します..."
  kill "$pid" 2>/dev/null
  # 最大5秒待って、残っていれば強制終了
  for _ in 1 2 3 4 5; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo "[強制終了] kill -9 $pid"
    kill -9 "$pid" 2>/dev/null
  fi
  # 取りこぼし（子プロセス等）も掃除
  pkill -f "python .*$APP" 2>/dev/null
  rm -f "$PIDFILE"
  termux-wake-unlock 2>/dev/null
  echo "[OK] 停止しました。"
}

# ── 状態確認 ──────────────────────────────────────────
status() {
  echo "==== 露天風呂モニター 状態 ===="
  # ADB
  local state
  adb connect "$ADB_TARGET" >/dev/null 2>&1
  state=$(adb -s "$ADB_TARGET" get-state 2>/dev/null)
  if [ "$state" = "device" ]; then
    echo "ADB接続 : OK ($ADB_TARGET)"
  else
    echo "ADB接続 : NG (state=${state:-なし})  ← PCで adb tcpip 5555 が必要かも"
  fi
  # プロセス
  if is_running; then
    echo "稼働     : 取得中 (PID $(server_pid)) [$APP]"
  else
    echo "稼働     : 停止"
  fi
  echo "ログ     : $LOGFILE"
  echo "==============================="
}

# ── ログ追尾 ──────────────────────────────────────────
logs() {
  [ -f "$LOGFILE" ] || { echo "ログがまだありません: $LOGFILE"; exit 0; }
  echo "--- $LOGFILE を追尾（Ctrl+Cで抜ける）---"
  tail -n 40 -f "$LOGFILE"
}

# ── ディスパッチ ──────────────────────────────────────
case "${1:-}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; echo; start ;;
  status)  status ;;
  check)   adb_check ;;
  log|logs) logs ;;
  *)
    echo "使い方: bash ctl.sh {start|stop|restart|status|check|log}"
    exit 1
    ;;
esac
