# Method B — PC + BlueStacks（Flaskサーバー）

常時起動の PC 上で BlueStacks（Androidエミュレータ）の Inkbird アプリを操作し、
`server.py`（Flask, :5000）が温度取得と案内板表示の両方を行う構成。

```
[Windows PC]
 server.py (:5000) ──ADB──▶ BlueStacks（Inkbirdアプリ）
   └─ ブラウザで http://localhost:5000 を開いて案内板表示
```

## ファイル
| ファイル | 役割 |
|---|---|
| `server.py` | Flaskサーバー。温度取得ループ + 案内板配信（:5000） |
| `run.sh` | ADB接続 → server.py 起動 |
| `config.json` | 稼働中の設定（BlueStacks用） |
| `config.bluestacks.json` | BlueStacks用設定テンプレート |

※ 温度取得のコア（`adb_reader.py`）と案内板の静的ファイルは `../shared/` を参照する。

## 使い方
```bash
# 依存をインストール
pip install -r requirements.txt

# 設定を用意（テンプレートから・必要に応じて adb.exe のパスを編集）
cp config.bluestacks.json config.json

# 起動
python server.py
# → ブラウザで http://localhost:5000
```

詳細なセットアップは `../shared/docs/SETUP_NEW_PC.md` を参照。
