# bath_system

Inkbird 温度センサーの水温を自動取得し、露天風呂・大浴場の**デジタル案内板**をリアルタイム表示するシステム。

Inkbird は公開 API を持たないため、**ADB で Inkbird アプリの画面を自動操作**して温度をスクレイピングする。

---

## 構成

```
method_a/   スマホ + Termux（現行・本番）
method_b/   PC + BlueStacks（旧方式・予備）
shared/     両方式共通コード（adb_reader.py, rf_reader.py, static/）
deploy_cloud/  Render クラウドサーバー（GitHub から自動デプロイ）
```

## データの流れ

```
[方式A] スマホ Termux
  run_lite.py → adb_reader.py → Inkbird アプリ操作 → POST → Render クラウド → モニター表示

[方式B] PC + BlueStacks
  server.py → adb_reader.py → BlueStacks の Inkbird → Flask(:5000) → ブラウザ表示
```

---

## 方式A（本番）の起動

```bash
# Termux で
bash ~/bath_system/ctl.sh start    # 起動
bash ~/bath_system/ctl.sh status   # 状態確認
bash ~/bath_system/ctl.sh stop     # 停止
```

詳細は [method_a/README.md](method_a/README.md) を参照。

## 方式B の起動

```bash
# venv を使う場合（venv/ が既にあればそのまま使用）
source venv/bin/activate
python method_b/server.py    # → http://localhost:5000

# venv を新規作成する場合
python3 -m venv venv
source venv/bin/activate
pip install -r method_b/requirements.txt
python method_b/server.py
```

詳細は [method_b/README.md](method_b/README.md) を参照。

> `venv/` は `bath_system/` 直下に配置。zip に含める場合は `pip install` 不要で即起動できる。
> 不要なら削除して `pip install -r method_b/requirements.txt` で再生成可。

---

## クラウド（Render）

本番 URL: `https://bath-board.onrender.com`  
デプロイ対象: `deploy_cloud/`（`cloud_server.py` + `static/`）

URL全件・Render設定・秘密鍵管理・障害対応は [HANDOVER.md](HANDOVER.md) を参照。
