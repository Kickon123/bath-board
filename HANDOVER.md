# 運用・管理メモ（露天風呂モニター bath_system）

Inkbird 温度センサーの水温を取得し、大浴場・露天風呂の案内板をリアルタイム表示するシステムの運用メモ。

> 🔐 **機密情報（トークン・パスワード・APIキー）はコードにも本ファイルにも実値を載せない。**
> どのサービスに何が必要かの一覧のみ（→ 5章）。実値は社内シークレット管理で別管理。

---

## 1. システム構成

構成・フォルダ・起動方法は [README.md](README.md) を参照。

---

## 2. URL / エンドポイント一覧

### 2-1. Render（本番）
ベース: `https://bath-board.onrender.com`（`deploy_cloud/cloud_server.py`）

**画面**
| URL | 内容 |
|---|---|
| `/` , `/slideshow` | スライドショー（湯畑マップ＋写真カルーセル） |
| `/slideshow64` , `/64` | スライドショー（小型画面向け） |
| `/yubatake` , `/board` | 湯畑 露天風呂 温度マップ |
| `/base-all` , `/all` , `/bath/all` | 湯畑＋大浴場 統合表示 |
| `/bath/yubatake` | 湯畑 温度マップ |
| `/bath/daiyokujo` | 大浴場（男湯・女湯）温度カード |
| `/kanri` | スタッフ管理画面（PIN認証・履歴グラフ） |
| `/static/facility-map/facility-map.html` | 館内マップ（3D フロア表示） |

**API**
| URL | 種別 | 内容 |
|---|---|---|
| `/api/baths` | GET | 最新温度データ JSON |
| `/api/push` | POST | スマホ→Render の温度送信（`X-Token` 必須） |
| `/api/history?id=<n>&n=<件数>` | GET | 湯舟の履歴データ |
| `/api/history/all?n=<件数>` | GET | 全湯舟の履歴データ |

### 2-2. ローカル server.py（方式B）
ベース: `http://localhost:5000`（LAN は `http://<PCのIP>:5000`）

画面は Render と同じ URL 体系。追加 API：

| URL | 種別 | 内容 |
|---|---|---|
| `/api/temp/<bath_id>` | POST | 温度手動上書き |
| `/api/position/<bath_id>` | POST | 案内板上の湯舟位置を保存 |
| `/api/adb/status` | GET | ADB 取得スレッドの状態 |
| `/api/adb/fetch` | POST | 今すぐ手動取得 |
| `/api/bg/status` | GET | 背景画像の有無 |
| `/api/bg/upload` | POST | 背景画像アップロード |

---

## 3. Render デプロイ設定

| 項目 | 値 |
|---|---|
| サービス名 | bath-board |
| 接続リポジトリ | `github.com/catrin48/bath-board` |
| **Root Directory** | **`deploy_cloud`** |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn cloud_server:app --bind 0.0.0.0:$PORT` |
| 自動デプロイ | main への push で自動再デプロイ |

**環境変数（Render ダッシュボード → Environment）**
| 変数 | 必須 | 説明 |
|---|---|---|
| `PUSH_TOKEN` | **必須** | `/api/push` の認証トークン。未設定だと全 push を拒否 |
| `SUPABASE_URL` | 任意 | Supabase の Project URL。未設定時はメモリ内履歴（最大600件）で代替 |
| `SUPABASE_KEY` | 任意 | Supabase の anon key |
| `PORT` | 不要 | Render が自動注入 |

**デプロイ手順**
1. `deploy_cloud/` 配下を更新
2. `git push origin main` → Render が自動ビルド・再デプロイ
3. 確認: `GET https://bath-board.onrender.com/api/baths` が最新 JSON を返すか

> ⚠ `deploy_cloud/static/` と `shared/static/` は**別コピー**（Render の Root Directory が `deploy_cloud/` のため）。
> 案内板HTMLを変更したら**両方を更新**すること。

---

## 4. 認証情報の管理

**機密情報はコードに書かない。実値は社内シークレット管理で別管理。**

| サービス / 用途 | 認証情報の種類 | 設定先 |
|---|---|---|
| Render `/api/push` 認証 | `PUSH_TOKEN` | Render の Environment |
| スマホ→Render 送信 | `config.json` の `cloud.token`（= `PUSH_TOKEN` と同値） | スマホ実機の `~/bath_system/config.json` のみ |
| Inkbird アカウント「花つばき」 | アプリログイン（メール/パスワード） | 社内パスワードマネージャ |
| Supabase（履歴DB・任意） | `SUPABASE_URL` / `SUPABASE_KEY` | Render の Environment |
| GitHub `catrin48/bath-board` | SSHキー or PAT | 各担当者端末 |

**アップロード・公開前チェック**
- [ ] コードに平文のトークン・パスワードが無いか（`__PUSH_TOKEN__` 等のプレースホルダになっているか）
- [ ] `temperatures.json` / `latest.json` / `*.log` 等の実行時生成物を除外済みか
- [ ] 過去に平文コミットしたキーがあれば**ローテーション**（git 履歴にも残るため）

---

## 6. 運用上の技術メモ

- **取得中はスマホを触らない。** Inkbird アプリを前面にして UI ダンプするため、割り込むと「データなし」になる。確認は `GET /api/baths`（非干渉）で行う。
- **スマホ再起動で自己ADBがリセット**される。復旧: PC に USB 接続して `adb tcpip 5555` を一度実行 → `ctl.sh start`。
- **取得間隔は 3 分が最適**（`adb.interval: 180`）。UI 操作 1 周に 1〜2 分かかるため縮めても無意味で発熱のみ増える。常時充電必須。
- **方式A/B の切替は `config.json` の差し替えだけ**（`config.phone.json` ↔ `method_b/config.json`）。座標は解像度依存（BlueStacks は 1920×1080/240dpi 前提）。
- **Inkbird アプリの UI 変更に注意**。リソース ID（`tv_temp` 等）が変わると `adb_reader.py` の抽出が壊れる。アプリ更新時は要確認。
- **取得失敗は前回値を保持して `stale=true`** でマーク（案内板に「最終値」表示）。
- **RTL-SDR 方式**（`rf_reader.py`）は `config` の `rf.enabled` で切替。現在 OFF。手順は `shared/docs/RTL_SDR_SETUP.md`。

### Inkbird クラウド直接取得の調査結果（参考）
UIスクレイピングをやめクラウドAPIから直接取得する方式を2経路調査したが**いずれも未採用**。
- **Tuya 公式 API** → 規約で商用利用禁止（旅館は商用）
- **Inkbird 独自 API**（`us.api-inkbird.com`） → 現在値取得 API が存在せず、履歴の `dp_value` デコード方法も不明

---

## 7. 移行計画

### GitHub（会社 Org へ移行）
現在は個人アカウント `catrin48/bath-board`。会社 Organization への移行手順：
```bash
git clone --mirror git@github.com:catrin48/bath-board.git
cd bath-board.git
git remote set-url --push origin git@github.com:<会社Org>/bath-board.git
git push --mirror
```
⚠ 履歴に過去の平文シークレットが残る場合は移行前にキーをローテーションする。

### Render（会社アカウントへ移管）
現在は個人アカウントでデプロイ。移管後にやること：
- 接続リポジトリを会社 Org の方に向け直す
- `PUSH_TOKEN` を新しい値に再設定
- スマホ側 `config.json` の `cloud.token` を新トークンに更新
- `cloud.url` を新ドメインに更新（独自ドメイン取得時）
