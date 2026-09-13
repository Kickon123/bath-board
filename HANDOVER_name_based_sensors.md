# 引き継ぎ: 温度センサーの「名前ベース方式」への移行（未マージ・未デプロイ）

作業日: 2026-09-13　ブランチ: `feature/name-based-sensors`（bath_system・yubatake_cms 両方）
状態: **コード実装済み・両GitHubアカウントにpush済み。まだ main には未マージ、本番デプロイもしていない。**

別セッションでこの続きを見る場合は、まずこのファイルを読んでから着手してください。

---

## 1. GitHubに関すること（前提として必ず把握すること）

このプロジェクトは **GitHubアカウントが2つに分かれて存在**しています（過去のアカウント移行が中途半端に終わったため）。

| 用途 | 本物（現行・本番） | 使われていない残骸 |
|---|---|---|
| bath-board（案内板） | `Kickon123/bath-board` | `catrin48/bath-board`（2026-08-29で更新停止） |
| yubatake-cms（CMS） | `Kickon123/yubatake-cms` | `catrin48/yubatake-cms` |
| CMS実機のRenderサービス | `yubatake-cms-5ea4.onrender.com`（`Kickon123/yubatake-cms` から自動デプロイ、確認済み） | `yubatake-cms.onrender.com`（`catrin48` 側から自動デプロイ） |
| bath-board実機のRenderサービス | `bath-board-1az8.onrender.com` | `bath-board.onrender.com`（旧） |

- ローカルの `git remote` は両リポジトリとも `origin`=catrin48、`kickon`=Kickon123 の2本立て。
- **今回の作業は両方のリモートに push 済み**（`feature/name-based-sensors` ブランチとして）。main には未マージなので、どちらのRenderサービスにも自動デプロイされていない（Renderは `main` を見ている）。
- 詳しい経緯は同フォルダの `HANDOVER.md` と、`yubatake_cms/ISSUE_deploy_not_reflected.md` ／ `yubatake_cms/ISSUE_multiple_repos_render.md` を参照。
- CMS画面右上に build 表示（`build: <repo>@<branch> #<commit>`）があるので、実際にどのコミットが動いているかはそこで確認できる。

## 2. 今回の問題（なぜこの変更をしたか）

### 元の設計とその欠陥

```
CMS（yubatake-cms）が「探すべきセンサー名」を bath-config.json に事前に書く
        ↓
スマホ(Termux上の run_lite.py)が bath-config.json を取得
        ↓
Inkbirdアプリの画面を読み、bath-config.json の sensor_name(またはname)と
「完全一致」するものだけを温度データとして採用
        ↓
一致しなければ、そのセンサーは「前回値のまま stale=True」で止まる
```

**問題点**: CMSでピンの表示名を変えたり、Inkbird側の名前とCMS側の名前が少しでもズレる（全角半角・空白・表記ゆれ等）と、**そのセンサーの温度取得が黙って止まる**。ユーザー（依頼者）はこれを「本末転倒」と判断し、以下の方式への変更を提案した。

### 提案された新方式

```
スマホが Inkbird アプリで見えているセンサーを、名前が何であれ無条件に全部アップロード
        ↓
クラウド(cloud_server.py)が受け取り、初めて見る名前には自動でidを採番して保存
        ↓
CMSは「実際に届いている全センサー」をそのまま一覧表示し、
画面ごとに「表示/非表示」を選ぶだけ（一致確認という概念自体が無くなる）
```

事前登録・名前の一致確認が丸ごと不要になり、「表示名を変えたら温度が止まった」という事故が原理的に起きなくなる。

## 3. ファイル変更範囲

### bath_system リポジトリ（ブランチ `feature/name-based-sensors`, commit `e28187e`）

| ファイル | 変更内容 |
|---|---|
| `shared/adb_reader.py` | `update_temps()` を「名前をキーに見つかった分だけ全部保存」に書き換え。`fetch_remote_baths()` / `remote_gateway_cfg()`（CMS事前登録リストの取得・キャッシュ）を削除。ゲートウェイ（外気温）判定は `is_gateway_device()` の型番自動検出のみに一本化（元々あった仕組みでCMS設定は不要）。`run_once()` のログ出力・ゲートウェイ上書き処理もこれに合わせて簡略化 |
| `method_a/run_lite.py` | `refresh_baths()`（クラウドの事前登録リストを毎周期反映する処理）を削除。`build_payload()` を「`temperatures.json` の全センサーをそのまま `{"sensors":[{name,temp,...}]}` で送るだけ」に書き換え |
| `deploy_cloud/cloud_server.py` | `/api/push` が **新形式(`sensors`配列) と 旧形式(`baths`配列、id decidedスマホとの互換用) の両方を受理**するように変更。新形式は `name_id_map.json`（**現行の `bath-config.json` から現在の id 対応を種まきして作成**）で名前→id変換してから、従来と全く同じ `{"baths":[...]}` 形式で `latest.json` に保存する。これにより `/api/baths` 以降（CMS・案内板テンプレ）は**無変更で動く** |

### yubatake_cms リポジトリ（ブランチ `feature/name-based-sensors`, commit `71b964a`）

| ファイル | 変更内容 |
|---|---|
| `static/index.html` | `loadLiveTemps()` の `bathConfigLive` 取得元を、CMS自身が作る `/api/bath-config`（事前登録リスト）から、**実際に届いているデータ `/api/baths`** に変更。新しいセンサーが増えても自動でCMSのピン一覧候補に出るようにするための変更 |

`server.py`（Python側）は**今回変更していない**。センサー登録UI（`config.sensors` / `build_bath_config`）は今回のブランチでもまだコード上に残っている（消していない・害はない・当面は使われなくなるだけ）。

## 4. その他、必須の前提事項

### ⚠️ 物理的なスマホ更新が必須（最重要）

`shared/adb_reader.py` と `method_a/run_lite.py` は **現地のスマホ（Termux）上で動く実物のスクリプト**。GitHubにpushしても自動デプロイされない。**このブランチをmainにマージしただけでは何も変わらない。** 効果を出すには:

1. `feature/name-based-sensors` の `shared/`・`method_a/` の内容を、実機スマホにADB経由でコピー
2. スマホ側のサービスを再起動（`ctl.sh` 等。詳細は `shared/docs/PHONE_OPS.md`）
3. ここまでやって初めて新方式が動く

**このタスクを依頼したユーザーは「スマホが手元にないため、最終実行（本番反映）はまだ実施しない」と明言している。** 次のセッションが安易に `main` へマージ・本番デプロイしないよう注意。

### 後方互換性（重要な安全設計）

- `cloud_server.py` の `/api/push` は新旧両方の形式を受理する。**スマホ側を更新していなくても、cloud_server.py だけ先に本番反映しても壊れない。**
- ただし安全のため、まずは `main` マージ＝本番デプロイをせず、**スマホ更新のタイミングと合わせる**のが望ましい。

### id自動採番の仕組み（`name_id_map.json`）

- 初回実行時、`deploy_cloud/bath-config.json`（現行の公開済みファイル）から `sensor_name（無ければname）→id` を種まきする。これにより既存の案内板テンプレート（`base-all-cut.html`/`rotenburo.html`等のSPOTS配列に書かれたid）とズレずに引き継がれる。
- 初めて見る名前だけ、使われていない最小の番号を新規採番する。
- ローカルでの動作確認済み（`/tmp` 上のスクリプトで、既存id保持・新規id採番・再現性（同じ入力→同じid）を検証済み）。

### 巻き戻し（ロールバック）方法

- **今の時点**: 何もマージ・デプロイしていないので、`feature/name-based-sensors` ブランチを削除するだけで元通り。
- **本番反映後に戻す場合**:
  - クラウド側（cloud_server.py／CMS）: 該当コミットを `git revert` して再デプロイするだけ
  - スマホ側: 旧バージョンの `shared/`・`method_a/` をADBで戻して再起動

### センサー登録UI（`config.sensors`）の扱いについて

この移行が完了すれば、CMSの「🌡センサー登録」の仕組み（`config.sensors` / `sensor_name` / `build_bath_config` の一致確認ロジック）は**役目を終える**。今回は削除していないが、将来的に整理してよい（ただし外気温ゲートウェイの手動指定機能だけは要検討＝現状 `is_gateway_device()` の型番自動検出に一本化したため、CMSからの明示指定は使われなくなっている）。

## 次にやること（このブランチの完了条件）

1. ユーザーが現地でスマホを用意できたら、上記「物理的なスマホ更新」を実施
2. 動作確認（CMSの「🌡 温度データ」で新方式のデータが正しく出るか、既存の温度表示が壊れていないか）
3. 問題なければ `feature/name-based-sensors` を両リポジトリとも `main` にマージ → 通常のデプロイ手順（CMSの「🚀公開」／Render Manual Deploy）で本番反映
