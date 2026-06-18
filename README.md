# 露天風呂モニター（bath_system）

Inkbird 温度センサーの水温・湿度を自動取得し、大浴場／露天風呂の **デジタル案内板** に表示するシステム。
花つばきの「湯畑」「大浴場（男）」の各湯舟を対象にしている。

```
Inkbird センサー → Inkbird アプリ → (ADB で UI自動取得) → temperatures.json
   → Flask 案内板(:5000) もしくは Render クラウドへ送信 → ブラウザ/モニターで表示
```

Inkbird は公開 API を提供していないため、**Inkbird アプリの画面を ADB(`uiautomator dump` + `input tap`)で自動操作してスクレイピング**する方式をとっている。
アプリを動かす場所によって 2 つの方式がある（下記）。

---

## 取得方式は 2 通り

| | 方式A: Android スマホ + Termux | 方式B: PC + Android エミュレーター(BlueStacks) |
|---|---|---|
| 状態 | **現行・本番** | 旧方式 / 代替・予備 |
| Inkbird アプリの実行場所 | スマホ実機 | PC 上の BlueStacks |
| Python の実行場所 | スマホの Termux | PC |
| 使う設定ファイル | `config.phone.json` → `config.json` | `archive/config.bluestacks.json` → `config.json` |
| 起動 | `run_lite.py`（Flask なし・軽量） | `server.py`（Flask :5000 + 取得ループ） |
| 案内板の表示元 | Render クラウド | PC の Flask(:5000) |
| 常時稼働させるもの | スマホ（充電しっぱなし） | PC + BlueStacks |
| 詳細手順 | 下記「方式A」 | [docs/SETUP_NEW_PC.md](docs/SETUP_NEW_PC.md) |

> どちらの方式でも、ADB 操作するコードは同じ `adb_reader.py`。解像度・座標・ADB 接続先だけが
> `config.json` で切り替わる。**運用したい方式の設定ファイルを `config.json` にコピーして使う**のが基本。

---

## 方式A: Android スマホ + Termux（本番）

スマホ 1 台で「Inkbird アプリ」「Termux（Python）」を同居させ、**スマホが自分自身に ADB 接続**して
自分の画面の Inkbird を読み取る。取得結果は Render クラウドへ送り、案内板はクラウド側で配信する。
（スマホでは Flask 案内板は動かさず、負荷を最小化した軽量版 `run_lite.py` を使う。）

```
[スマホ] Termux: run_lite.py
    └ adb connect 127.0.0.1:5555 (自己ADB)
    └ Inkbird アプリを UI自動操作して温度取得 → temperatures.json
    └ 整形 JSON を POST → https://bath-board.onrender.com/api/push
[Render] cloud_server.py: /api/push で受信・保持 → 案内板 HTML を配信
[別モニター] ブラウザで Render の URL を開く（5秒ごとに /api/baths を取得）
```

### 必要なもの
- Android スマホ（充電しながら常時稼働できるもの）
- [Termux](https://f-droid.org/packages/com.termux/)（F-Droid 版推奨）
- Inkbird アプリ（Play ストア）に **Inkbird アカウント「花つばき」でログイン**し、
  ホームに「湯畑」「大浴場（男）」がオンライン表示される状態
- 初回のみ：PC（USB 接続して `adb tcpip 5555` を一度実行するため）

### セットアップ
1. プロジェクト一式をスマホの `/sdcard/Download/bath_system/` に置く
   （PC から `adb push` か MTP で転送）。
2. Termux でストレージ許可：`termux-setup-storage`
3. セットアップスクリプトを実行（python / android-tools / flask 等を導入し `~/bath_system` へコピー）:
   ```bash
   bash /sdcard/Download/bath_system/phone_setup.sh
   ```
4. `config.phone.json` を `config.json` として配置（スマホ用の座標・解像度・Render 送信先が入っている）:
   ```bash
   cp ~/bath_system/config.phone.json ~/bath_system/config.json
   ```
5. **自己 ADB の有効化（初回・スマホ再起動後に必要）**
   スマホを PC に USB 接続し、PC 側で一度だけ:
   ```bash
   adb tcpip 5555
   ```
   スマホに「USB デバッグを許可しますか？」が出たら **「常に許可」**。

### 起動・運用（`ctl.sh`）
バックグラウンド起動・停止・状態確認は `ctl.sh` で行う:
```bash
bash ~/bath_system/ctl.sh start     # 起動（nohup + PIDファイル）
bash ~/bath_system/ctl.sh stop      # 停止
bash ~/bath_system/ctl.sh restart   # 再起動
bash ~/bath_system/ctl.sh status    # ADB接続・稼働・ログの状態確認
bash ~/bath_system/ctl.sh check     # 自己ADB接続だけ確認
bash ~/bath_system/ctl.sh log       # ログ追尾（Ctrl+Cで抜ける）
```
エイリアス登録しておくと便利:
```bash
alias b="bash ~/bath_system/ctl.sh"   # 以後 b start / b stop / b status
```
`ctl.sh` が起動するのは `APP="run_lite.py"`（温度取得→Render 送信のみ）。
スマホでも案内板（:5000）を出したい場合は `ctl.sh` の `APP=server.py` に変更するか `run.sh` を使う。

### 動作確認
スマホを **触らずに** Render 側で確認する（後述の「ハマりどころ」参照）:
```
GET https://bath-board.onrender.com/api/baths
```

### 注意（ハマりどころ）
- **取得中はスマホを触らない／PC から割り込まない。** 温度取得は Inkbird を前面にして UI ダンプするため、
  途中で別アプリを開いたり PC から `am start`・`screencap`・`uiautomator dump` を打つと
  「湯畑が見つからず データなし」になる。確認は上記 Render API（非干渉）で行う。
- **スマホ再起動で tcpip モードがリセットされる。** 再起動後は Termux を開いて以下を実行すれば OK（PC 不要）:
  ```bash
  adb tcpip 5555
  bash ~/bath_system/ctl.sh start
  ```
  それでも繋がらない場合は PC に USB 接続して `adb tcpip 5555` を実行してから `ctl.sh start`。
- **取得間隔は 3 分（`adb.interval: 180`）が最適。** 水温は分単位でしか変化せず、UI 操作 1 周に
  1〜2 分かかるため、間隔を縮めても更新は速くならず発熱・電池消費だけ増える。常時充電が前提。
- スリープで CPU が止まらないよう `ctl.sh`/`run.sh` が `termux-wake-lock` を確保している。

---

## 方式B: PC + Android エミュレーター（BlueStacks）

PC に BlueStacks（Android エミュレーター）を入れて Inkbird アプリを動かし、PC の Python が
`adb.exe` 経由で BlueStacks を操作して温度を取得する。案内板も PC の Flask(:5000) が配信する。

```
ブラウザ → Flask(server.py :5000) → adb_reader.py → adb.exe → BlueStacks → Inkbird アプリ
```

### 必要なもの
- Windows PC（常時起動）
- Python 3.12 / SDK Platform Tools（`adb.exe`）/ BlueStacks 5
- BlueStacks 内に Inkbird アプリ（「花つばき」でログイン）
- （任意）cloudflared … 外出先からも見たい場合

### セットアップ要点
1. `pip install -r requirements.txt`
2. `archive/config.bluestacks.json` を `config.json` にコピー（**BlueStacks 用の座標が入っている**）。
3. `config.json` の `adb.exe` を自分の PC の `adb.exe` パスに修正。
4. BlueStacks 設定で **ADB を ON**（接続先 `127.0.0.1:5555`）。
5. **BlueStacks の解像度を 1920×1080 / 240dpi に設定**（座標がこの解像度前提。違うと全ページ「データなし」）。
6. 起動:
   ```powershell
   python server.py        # http://localhost:5000
   ```
   LAN 内の他端末からは `http://<PCのIP>:5000`、外部公開は `cloudflared tunnel --url http://localhost:5000`。

> 完全な手順・トラブルシュートは **[docs/SETUP_NEW_PC.md](docs/SETUP_NEW_PC.md)** を参照。

---

## クラウド配信（Render）

`deploy_cloud/cloud_server.py` はスマホ（方式A）から温度を受信して案内板を配信する中継サーバー。
本番は Render にデプロイ済み（`https://bath-board.onrender.com`）。

- `POST /api/push`（`X-Token` 必須）… スマホが温度を送る。`latest.json` に保持。
- `GET /api/baths` … 案内板が 5 秒ごとに読む最新値。
- `GET /`（`/board`）… 案内板 HTML。

デプロイ用ファイルは [deploy_cloud/](deploy_cloud/)（`cloud_server.py` + `static/` + `Procfile` + `requirements.txt`、`gunicorn cloud_server:app`）。

---

## ファイル構成

| パス | 役割 |
|---|---|
| `adb_reader.py` | **核**。ADB で Inkbird アプリを UI 自動操作し温度取得 → `temperatures.json` 更新 |
| `run_lite.py` | 方式A 用の軽量ランナー（Flask なし。取得 → Render 送信） |
| `server.py` | 方式B / 案内板用の Flask サーバー（:5000、取得ループも内蔵） |
| `deploy_cloud/cloud_server.py` | Render 中継サーバー（受信 → 保持 → 案内板配信）。**Render はこれを使用**（cloud_server はこの1本に一本化） |
| `rf_reader.py` | RTL-SDR で 433MHz を直接受信する代替取得（`config.json` の `rf.enabled` で切替・現在 OFF） |
| `config.json` | 実行時に使う設定（方式に応じて下記からコピーする） |
| `config.phone.json` | 方式A（スマホ）用テンプレート |
| `archive/config.bluestacks.json` | 方式B（BlueStacks）用テンプレート |
| `ctl.sh` / `run.sh` / `phone_setup.sh` | スマホ(Termux)用 制御・起動・セットアップ |
| `static/` | 案内板 HTML/CSS/JS・背景画像（`base7-flat.html` がメイン案内板） |
| `deploy_cloud/` | Render デプロイ一式 |
| `docs/` | 方式B 手順（`SETUP_NEW_PC.md`）、RTL-SDR 手順、作業ログ、湯畑レイアウト PDF |
| `archive/` | 実験コード・テストログ・古い設定（運用には不要） |
| `temperatures.json` / `latest.json` / `bath_system.log` / `window_dump.xml` | **実行時に自動生成**（消してよい） |

### 設定（`config.json` 共通）
- `adb` … 接続先・取得間隔・スワイプ／タップ座標・対象デバイス（`devices`）
- `baths` … 湯舟の定義（`id` / `name` / `sensor_name` / 案内板上の位置 `left,top` / 目標温度 `target`）
- `cloud` … Render の `url` と `token`（方式A のみ）
- `rf` … RTL-SDR 直接受信の設定（既定 OFF）

> センサー名（`sensor_name`）で湯舟を識別する。取得できなかった湯舟は前回値を保持し `stale=true`
> としてマークされ、案内板側で「未接続・最終値」表示になる。
