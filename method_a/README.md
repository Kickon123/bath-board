# Method A — スマホ + Termux（軽量版）

スマホ1台で温度を取得し、Render クラウドへ送信するだけの軽量構成。
Flask は起動せず、案内板の表示はクラウド側（`deploy_cloud/`）に任せる。
現在の本番運用はこちら。

```
[スマホ Termux]                 [Render クラウド]          [モニター]
 run_lite.py ──POST /api/push──▶ cloud_server.py ──▶ ブラウザで案内板表示
 （Inkbird操作で温度取得）        （最新値を保持・配信）
```

## ファイル
| ファイル | 役割 |
|---|---|
| `run_lite.py` | 温度取得 → Render送信のループ（Flaskなし） |
| `ctl.sh` | 起動/停止/状態確認の制御スクリプト |
| `phone_setup.sh` | スマホ初回セットアップ（パッケージ・ADB設定） |
| `config.phone.json` | スマホ用設定テンプレート |

※ 温度取得のコア（`adb_reader.py`）は `../shared/` を参照する。

## 使い方
```bash
# 1) 初回のみ：セットアップ
bash phone_setup.sh

# 2) 設定を有効化（テンプレートをコピー）
cp config.phone.json config.json

# 3) 起動 / 停止 / 状態
bash ctl.sh start
bash ctl.sh status
bash ctl.sh stop
```

詳細は `../shared/docs/PHONE_OPS.md` を参照。
