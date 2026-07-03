# スマホ運用 クイックリファレンス

## 通常の起動・停止（Termux で直接操作する場合）

`b` エイリアス（`~/.bashrc` に登録済み）で短縮できる:

| やること | コマンド |
|---|---|
| 起動 | `b start` |
| 停止 | `b stop` |
| 再起動 | `b restart` |
| 状態確認 | `b status` |
| ADB接続確認 | `b check` |
| ログ追尾 | `b log` |

---

## スマホ再起動後 ← 【USB ケーブルで PC につないで実施】

再起動すると ADB の TCP モードがリセットされる。
**PC から USB 経由で以下の 2 コマンドを実行する。**

```bash
# 1) TCP モードを有効化
/home/r/platform-tools/adb tcpip 5555

# 2) bath_system を起動
/home/r/platform-tools/adb shell 'run-as com.termux env HOME=/data/data/com.termux/files/home TMPDIR=/data/data/com.termux/files/usr/tmp PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin /data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/bath_system/ctl.sh start'
```

> USB を挿したまま 2 コマンドを続けて打つだけで OK。

---

## PC から他の操作をする場合

```bash
# start の部分を変えるだけ
/home/r/platform-tools/adb shell 'run-as com.termux env HOME=/data/data/com.termux/files/home TMPDIR=/data/data/com.termux/files/usr/tmp PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin /data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/bath_system/ctl.sh stop'

/home/r/platform-tools/adb shell 'run-as com.termux env HOME=/data/data/com.termux/files/home TMPDIR=/data/data/com.termux/files/usr/tmp PREFIX=/data/data/com.termux/files/usr PATH=/data/data/com.termux/files/usr/bin /data/data/com.termux/files/usr/bin/bash /data/data/com.termux/files/home/bath_system/ctl.sh status'
```

---

## 動作確認

Render API で確認する（取得中に割り込まないこと）:

```
https://bath-board.onrender.com/api/baths
```

`stale: false` かつ温度が更新されていれば正常。

---

## よくあるトラブル

| 症状 | 原因 | 対処 |
|---|---|---|
| `[NG] 自己ADB接続に失敗` | 再起動で TCP モードがリセット | USB 接続して `adb tcpip 5555` → 手順2を実行 |
| `unauthorized` | PC がスマホに未許可 | スマホ画面の許可ダイアログを「許可」 |
| `no devices/emulators found` | USB ケーブルが抜けている | ケーブルを挿し直して `adb devices` で確認 |
| 「湯畑が見つからず データなし」 | 取得中に画面を触った／別アプリが前面 | `ctl.sh restart` で仕切り直し |
| Render の値が古い | スマホがスリープ or プロセスが落ちた | `ctl.sh status` → 停止なら `start` |
| 温度が両方 `stale: true` | ADB は繋がっているが Inkbird アプリが落ちた | Inkbird アプリを起動 → `ctl.sh restart` |
