# スマホ運用 クイックリファレンス

## 通常の起動・停止

| やること | コマンド |
|---|---|
| 起動 | `bash ~/bath_system/ctl.sh start` |
| 停止 | `bash ~/bath_system/ctl.sh stop` |
| 再起動 | `bash ~/bath_system/ctl.sh restart` |
| 状態確認 | `bash ~/bath_system/ctl.sh status` |
| ログ確認 | `bash ~/bath_system/ctl.sh log` |

エイリアスを登録すると短縮できる:
```bash
alias b="bash ~/bath_system/ctl.sh"
# → b start / b stop / b status / b log
```

---

## スマホ再起動後

Termux を開いてこの 2 行を打てば OK（PC 不要）:

```bash
adb tcpip 5555
bash ~/bath_system/ctl.sh start
```

> それでも `[NG] 自己ADB接続に失敗` が出たら → PC に USB 接続して `adb tcpip 5555` を実行 → USB を抜いて再度 `start`

---

## 動作確認

スマホを触らず Render API で確認する（取得中に割り込まないこと）:

```
https://bath-board.onrender.com/api/baths
```

`stale: false` かつ温度が更新されていれば正常。

---

## よくあるトラブル

| 症状 | 原因 | 対処 |
|---|---|---|
| `[NG] 自己ADB接続に失敗` | 再起動で tcpip モードがリセット | `adb tcpip 5555` → `ctl.sh start` |
| 「湯畑が見つからず データなし」 | 取得中に画面を触った／別アプリが前面 | `ctl.sh restart` で仕切り直し |
| Render の値が古い | スマホがスリープ or プロセスが落ちた | `ctl.sh status` → 停止なら `start` |
| 温度が両方 `stale: true` | ADB は繋がっているが Inkbird アプリが落ちた | Inkbird アプリを起動 → `ctl.sh restart` |

---

## PC から操作する場合（ADB 経由）

```bash
# スマホのTermuxでコマンドを実行
BASE=/data/data/com.termux/files
/home/r/platform-tools/adb shell "run-as com.termux env HOME=$BASE/home TMPDIR=$BASE/usr/tmp PREFIX=$BASE/usr PATH=$BASE/usr/bin $BASE/usr/bin/bash $BASE/home/bath_system/ctl.sh start"
```
