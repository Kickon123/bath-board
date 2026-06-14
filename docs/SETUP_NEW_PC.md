# 露天風呂モニター — 別PC(BlueStacks方式)への移植 & Web表示 手順

このフォルダをUSBで新PCにコピーして動かすための完全手順。
方式: **BlueStacks(エミュレータ) + ADB で Inkbirdアプリ画面をスクレイピング**。

```
ブラウザ → Flask(server.py) → adb_reader.py → ADB → BlueStacks → Inkbirdアプリ → クラウド
```

---

## ★最重要の注意（先に読む）

現在の `config.json` は**スマホ(USB実機)用に書き換わっています**（serial・720×1560座標）。
**BlueStacks方式の新PCでは、`config.bluestacks.json` を `config.json` に上書きコピーして使うこと。**

```
新PCで:  config.bluestacks.json  →  config.json  にリネーム/コピー
```

---

## 1. 新PCにインストールするツール（3つ）

| ツール | 入手先 | 用途 |
|---|---|---|
| **Python 3.12**（推奨） | https://www.python.org/downloads/ | server.py を動かす |
| **SDK Platform Tools** | https://developer.android.com/tools/releases/platform-tools | adb.exe（BlueStacks操作） |
| **BlueStacks 5** | https://www.bluestacks.com/ | Inkbirdアプリを動かすエミュレータ |

（任意：インターネット公開する場合のみ）
| **cloudflared** | https://github.com/cloudflare/cloudflared/releases | 外出先からも見るためのトンネル |

---

## 2. USBに入れて持っていく必要ファイル

**フォルダごと持っていってOK**だが、最低限これがあれば動く：

必須:
- `server.py`
- `adb_reader.py`
- `config.bluestacks.json` ← 新PCで `config.json` にする
- `requirements.txt`
- `static/`（フォルダごと。`chatgpt-flat.html` `app.js` `style.css` `bg.png` が必須）

任意（あると便利）:
- `湯畑レイアウト.pdf`（`static/bg.png` が無い時の背景生成元。bg.pngがあれば不要）
- `convert_photo.py` `convert_pdf.py`（写真アップロード/PDF変換機能を使うなら）
- `start_server.bat`（起動バッチ。中のパスは新PCに合わせて要修正）

**要らない**（容量節約に消してよい）:
- `*_test.py` `inkbird_test*.py` `tuya_test.py`（実験コード）
- `test_result*.txt` `test_now.txt`（実験ログ）
- `phone_setup.sh` `run.sh` `config.phone.json`（スマホ専用。BlueStacksでは使わない）
- `bath_system.log*` `server_stdout.log` `startup.log` `__pycache__`（ログ/キャッシュ）
- ルートの作業用画像（`60.png` `gem.png` `gg.png` `map.png` 等）

---

## 3. 新PCでのインストール手順

### 3-1. Python
1. python.org からインストーラをDL → 実行
2. ⚠️ **最初の画面で「Add python.exe to PATH」に必ずチェック** → Install Now
3. 確認（PowerShellで）: `python --version` が出ればOK

### 3-2. Pythonライブラリ
フォルダ内でPowerShellを開いて:
```powershell
pip install -r requirements.txt
```
（flask / flask-cors / requests / PyMuPDF / opencv-python / numpy が入る）

### 3-3. ADB (Platform Tools)
1. zipをDL → 任意の場所に解凍（例 `C:\platform-tools\`）
2. `config.json`(=元config.bluestacks.json) の `adb.exe` を新PCのパスに修正:
   ```json
   "exe": "C:\\platform-tools\\adb.exe",
   ```

### 3-4. BlueStacks + Inkbird
1. BlueStacks 5 をインストール
2. 設定 → 詳細設定 → **Android Debug Bridge (ADB) を ON**（接続先 127.0.0.1:5555 を確認。違うポートなら config.json の `port` を合わせる）
3. BlueStacks内に **Inkbird アプリ**をインストール（Playストア）
4. **Inkbirdアカウント「花つばき」でログイン** → ホームに「湯畑」が"オンライン"で出ればOK
5. ⚠️ **BlueStacksの解像度を 1920×1080 / 240dpi に設定**
   （config.bluestacks.json の座標はこの解像度用。違う解像度だと全ページ「データなし」になる）

---

## 4. 起動 & Web表示

### 起動
```powershell
# 1) BlueStacksを起動し、Inkbirdアプリを開いてデバイス一覧を表示させておく
# 2) サーバー起動
python server.py
```
server.py は `0.0.0.0:5000` で待ち受けるので、最初から**LAN内の他端末から見られる**。

### (A) 同じWiFi/LAN内で見る（追加設定ほぼ不要）
1. 新PCのIPアドレスを確認（PowerShell）:
   ```powershell
   ipconfig   # Wi-Fi の IPv4 アドレス、例 192.168.1.50
   ```
2. 他のスマホ/タブレット/PCのブラウザで:
   ```
   http://192.168.1.50:5000
   ```
3. 繋がらない時は Windowsファイアウォールで python の受信を許可（初回起動時のダイアログで「許可」）。

### (B) 外出先からインターネットで見る（cloudflared が楽）
1. cloudflared.exe をDL
2. server.py を起動した状態で:
   ```powershell
   cloudflared tunnel --url http://localhost:5000
   ```
3. 表示される `https://xxxx.trycloudflare.com` のURLでどこからでも閲覧可（無料・アカウント不要のクイックトンネル）。
   ※URLは起動ごとに変わる。固定したい場合はCloudflareアカウントで名前付きトンネルを設定。

---

## 5. トラブルシュート

| 症状 | 対処 |
|---|---|
| `python` が見つからない | PATH追加し忘れ。Pythonを「Modify→Add to PATH」で入れ直し |
| `ADB接続失敗 (10061)` | BlueStacks未起動 / ADB無効 / ポート違い。3-4を確認 |
| 全ページ「データなし」 | BlueStacks解像度が1920×1080でない（3-4の5）。または Inkbird がデバイス一覧に居ない |
| `import fitz` エラー | `pip install PyMuPDF` |
| LANで繋がらない | Windowsファイアウォールで python の受信許可 |

---

## 補足
- この方式はBlueStacks起動・解像度・アプリUIに依存し壊れやすい。PC常時起動も必要。
- スマホ単体運用版（Termux）やクラウド配信版は別途検討（メモ参照）。
