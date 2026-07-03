#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# 露天風呂モニター  スマホ(Termux)セットアップ  ＜Method A: 軽量版＞
#   使い方:  bash /sdcard/Download/bath_system/method_a/phone_setup.sh
# ============================================================
echo "=================================================="
echo " 露天風呂モニター セットアップ開始"
echo "=================================================="

echo ""
echo "=== 1/5 パッケージ一覧を更新 ==="
pkg update -y || { echo "[!] pkg update 失敗"; exit 1; }

echo ""
echo "=== 2/5 python と adb(android-tools) を導入 ==="
pkg install -y python android-tools || { echo "[!] pkg install 失敗"; exit 1; }

echo ""
echo "=== 3/5 Python ライブラリ導入 ==="
pip install flask flask-cors requests || { echo "[!] pip install 失敗"; exit 1; }

echo ""
echo "=== 4/5 プロジェクトを ~/bath_system へコピー ==="
if [ ! -d /sdcard/Download/bath_system ]; then
  echo "[!] /sdcard/Download/bath_system が見つかりません。"
  echo "    先に Termux で  termux-setup-storage  を実行して許可したか確認してください。"
  exit 1
fi
mkdir -p ~/bath_system
cp -r /sdcard/Download/bath_system/* ~/bath_system/
echo "    コピー完了: $(ls ~/bath_system | tr '\n' ' ')"

echo ""
echo "=== 5/5 自分自身に ADB 接続 ==="
echo ""
echo "    ★ 事前に PC から USB 接続して以下を実行しておくこと:"
echo "         /home/r/platform-tools/adb tcpip 5555"
echo "      （これをやらないと以下の接続が失敗します）"
echo ""
adb kill-server 2>/dev/null
adb connect 127.0.0.1:5555
echo ""
echo "    ★ スマホ画面に『USBデバッグを許可しますか？』が出たら"
echo "      『このデバイスから常に許可』にチェックして【許可】を押してください。"
echo "      （出ない場合は数秒待ってから次へ）"
echo ""
echo "=================================================="
echo " セットアップ完了！"
echo ""
echo " 次の手順:"
echo "   1) スマホ用の設定を有効化:"
echo "      cp ~/bath_system/method_a/config.phone.json ~/bath_system/method_a/config.json"
echo "   2) 起動:"
echo "      bash ~/bath_system/method_a/ctl.sh start"
echo "=================================================="
