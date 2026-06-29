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

再起動すると adb の tcpip モードがリセットされるので、再有効化が必要。
方法は **A（スマホだけ）** と **B（PCから）** の 2 つ。
**この環境では A が使えないため、通常は B を使う。**

### 方法A：Termux だけで実行（※この環境では使用不可）

Termux を開いて 2 行を打つだけだが、現状この端末では
`[NG] 自己ADB接続に失敗` となり起動できないため使わない。
（参考のみ）

```bash
adb tcpip 5555
bash ~/bath_system/ctl.sh start
```

### 方法B：PC から USB 経由で起動 ← 【通常はこちら】

スマホを USB ケーブルで PC につないでから、PC のターミナルで実行する。

#### 事前準備（毎回ではなく初回のみ）
- スマホとPCを **USBケーブル** で接続
- スマホ側で「USBデバッグ」がON（設定→開発者向けオプション）
- 初回接続時はスマホに「このPCを許可しますか？」が出る → **許可**（「常に許可」推奨）

#### 環境メモ（このPCで確認済みの値）
| 項目 | 値 |
|---|---|
| adb のパス | `/home/r/platform-tools/adb` |
| 端末シリアル | `RF8N11NCL0N`（機種 SC-02M） |
| スマホ Wi-Fi IP（例） | `192.168.2.48`（DHCPで変わり得る。手順3で都度確認） |
| TCP ポート | `5555` |

#### 手順（コピペ用）

```bash
# ── 0) adb の場所を変数に入れておく（以降 $ADB で使う）──
ADB=/home/r/platform-tools/adb

# ── 1) USB 実機が見えるか確認 ──
#   "RF8N11NCL0N   device" と出れば OK
#   "unauthorized" → スマホ画面のUSBデバッグ許可ダイアログを「許可」
#   "List of devices attached" だけで空 → ケーブル/ポート/デバッグ設定を確認
$ADB devices

# ── 2) スマホの adb を TCP モード(5555)で起動する ★ここが「PCからadbを起動」 ──
#   "restarting in TCP mode port: 5555" と出れば成功
$ADB -s RF8N11NCL0N tcpip 5555

# ── 3) スマホの Wi-Fi IP と待受ポートを確認 ──
$ADB -s RF8N11NCL0N shell ip -f inet addr show wlan0 | grep -o 'inet [0-9.]*'   # 例: inet 192.168.2.48
$ADB -s RF8N11NCL0N shell getprop service.adb.tcp.port                           # → 5555 なら待受OK

# ── 4) スマホ上の bath_system を PC から起動する（run-as で Termux 環境に入る）──
BASE=/data/data/com.termux/files
$ADB -s RF8N11NCL0N shell "run-as com.termux env HOME=$BASE/home TMPDIR=$BASE/usr/tmp PREFIX=$BASE/usr PATH=$BASE/usr/bin $BASE/usr/bin/bash $BASE/home/bath_system/ctl.sh start"
```

> **注意:** 手順2の `tcpip 5555` の直後に、USB の `$ADB devices` から端末が一瞬消えることがある
> （adbd の再起動／ケーブルの接触で発生）。その場合は次の「USBが切れたとき」を使う。

#### USBが切れたとき（無線で接続して操作する）

USB を抜いた／消えた後でも、同じ Wi-Fi 上なら IP 指定で接続して操作できる。
（IP は手順3で確認した値。以下は例 `192.168.2.48`）

```bash
ADB=/home/r/platform-tools/adb

# 無線で接続（"connected to ..." と出ればOK）
$ADB connect 192.168.2.48:5555

# 以降は -s をこの IP:ポートに変えて同じコマンドを使う
BASE=/data/data/com.termux/files
$ADB -s 192.168.2.48:5555 shell "run-as com.termux env HOME=$BASE/home TMPDIR=$BASE/usr/tmp PREFIX=$BASE/usr PATH=$BASE/usr/bin $BASE/usr/bin/bash $BASE/home/bath_system/ctl.sh start"
```

#### 起動以外の操作（PCから）

`ctl.sh` の引数を `start` から変えるだけ。`-s` のターゲットは USB なら `RF8N11NCL0N`、無線なら `192.168.2.48:5555`。

```bash
ADB=/home/r/platform-tools/adb
BASE=/data/data/com.termux/files
TARGET=RF8N11NCL0N            # 無線のときは 192.168.2.48:5555 に変える

run() { $ADB -s "$TARGET" shell "run-as com.termux env HOME=$BASE/home TMPDIR=$BASE/usr/tmp PREFIX=$BASE/usr PATH=$BASE/usr/bin $BASE/usr/bin/bash $BASE/home/bath_system/ctl.sh $1"; }

run start      # 起動
run stop       # 停止
run restart    # 再起動
run status     # 状態確認
run log        # ログ確認
```

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
| `[NG] 自己ADB接続に失敗` | 再起動で tcpip モードがリセット | 方法B の手順2 `tcpip 5555` をやり直す |
| `device 'RF8N11NCL0N' not found` | tcpip 後にUSBが切れた／ケーブル抜け | 「USBが切れたとき」の無線接続で操作、またはケーブル挿し直し→手順1から |
| `unauthorized` | PCがスマホに未許可 | スマホ画面の許可ダイアログを「許可」 |
| 「湯畑が見つからず データなし」 | 取得中に画面を触った／別アプリが前面 | `run restart` で仕切り直し |
| Render の値が古い | スマホがスリープ or プロセスが落ちた | `run status` → 停止なら `run start` |
| 温度が両方 `stale: true` | ADB は繋がっているが Inkbird アプリが落ちた | Inkbird アプリを起動 → `run restart` |
