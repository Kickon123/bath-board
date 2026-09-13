# 引き継ぎ: 温度センサーの「名前ベース方式」への移行（未マージ・未デプロイ）

作業日: 2026-09-13　ブランチ: `feature/name-based-sensors`（`bath_system`・`yubatake_cms` 両リポジトリ、
それぞれ `catrin48`・`Kickon123` の両GitHubアカウントにpush済み）
状態: **コード実装済み・両方にpush済み。まだ main には未マージ、本番デプロイもしていない。**

**このファイル1本だけで完結するように書いています。他の `.md`（`HANDOVER.md`・`ISSUE_*.md` 等）を
読まなくても、この移行作業の背景・内容・注意点・次の一手がすべて分かります。**

---

## 1. GitHubに関すること

### 1-1. なぜGitHubアカウントが2つあるのか

このプロジェクトは、過去に GitHub アカウントを `catrin48` から `Kickon123` へ移行しようとした
形跡があるが、**移行が完了しないまま両方が並行して生き残っている**。具体的には：

| 用途 | `catrin48` 側 | `Kickon123` 側 |
|---|---|---|
| bath-board（案内板の本番表示） | `catrin48/bath-board`。**2026-08-29 で更新が完全に停止**（それ以降のコミットが無い＝実質使われていない） | `bath-board`。ほぼ毎日 `cms: 温度マップ更新` の自動コミットが入っている＝**これが本物** |
| yubatake-cms（CMS管理画面） | `catrin48/yubatake-cms`。**こちらも実際に人が作業して更新している**（後述） | `yubatake-cms`。CMSの自動下書き保存コミットが継続的に入っている＝**こちらも本物** |
| CMSのRenderサービス | `yubatake-cms.onrender.com`（`catrin48/yubatake-cms` を自動デプロイ元にしている） | `yubatake-cms-5ea4.onrender.com`（`Kickon123/yubatake-cms` を自動デプロイ元にしている。**実際にユーザーが日常使っているのはこちら**。CMS画面右上の build 表示 `build: Kickon123/yubatake-cms@main #<sha>` で確認済み） |
| bath-boardのRenderサービス | `bath-board.onrender.com`（古い・実質未使用） | `bath-board-1az8.onrender.com`（**本物**。案内板の各URLはすべてここ） |

つまり **bath-board は Kickon123 だけが本物**（catrin48側は死んでいる）だが、
**yubatake-cms は少し事情が違い、catrin48側も現在進行形で人が触っている**。実際に、
今回の作業に入る前の調査で、`catrin48/yubatake-cms` に **`catrin48 <kussorin@gmail.com>`**
（＝このプロジェクトの依頼者本人のGitHubアカウント）による直接コミットが複数見つかっている
（例: バグ修正コミット `2854e61`）。一方 `Kickon123/yubatake-cms` にも同じ依頼者の
下書き保存コミットが継続的に入っている。

**この2つのアカウントは完全に独立しているのではなく、collaborator関係（お互いに書き込み権限が
ある状態）になっている。** 証拠: このセッションのSSH鍵だけで、パスワード入力等なしに両方の
リポジトリへ普通に push できている。また `Kickon123/bath-board` の履歴には
`catrin48 <kussorin@gmail.com>` のコミットも、`Kickon123 <roddyhui@hotmail.com>`
（別人、おそらく共同作業者）のコミットも両方混在している。

### 1-2. なぜ両方に push するのか（今回の方針）

上記のとおり、**「どちらか一方だけが本物」と言い切れない状態**（少なくとも yubatake-cms は
両方に実際の作業が入っている）。加えて、過去に何度も「片方にだけpushして、もう片方を見ている
人には反映されなかった」という事故が起きている（`ISSUE_deploy_not_reflected.md` ／
`ISSUE_multiple_repos_render.md` に詳細記録あり）。

このため、このセッションでは **「迷ったら両方に push する」を徹底ルールにしている**：

1. 両方に書き込み権限があるので、両方に push すること自体のコストはほぼゼロ
2. 二重に push しておけば、「実は見ていたのはcatrin48の方だった／Kickon123の方だった」が
   後から判明しても、**取りこぼしが発生しない**
3. bath-board のように片方が完全に死んでいる場合でも、push すること自体に副作用は無い
   （誰もそのリポジトリの更新を見ていないなら、そこへの push は単に「無害な二重保管」になるだけ）
4. 逆に「本物と思われる方にしか push しない」方針だと、判断を間違えたときに
   **今回のような「反映されない」トラブルがまた再発する**

つまり、**「本当にどちらが本物か100%の確信が持てない」という状況そのものへの対処**として、
両方に push する運用にしている。将来、どちらか一方（使われていない方）のリポジトリ・Render
サービスを削除するかリネームして一本化すれば、このルール自体が不要になる（未実施）。

### 1-3. 今回の変更のpush状況

| リポジトリ | ブランチ | commit | push先 |
|---|---|---|---|
| `bath_system` | `feature/name-based-sensors` | コード変更 `e28187e`、本ドキュメント追加でさらに1つ | `catrin48/bath-board` と `Kickon123/bath-board` の両方 |
| `yubatake_cms` | `feature/name-based-sensors` | コード変更 `71b964a`、本ドキュメント追加でさらに1つ | `catrin48/yubatake-cms` と `Kickon123/yubatake-cms` の両方 |

**`main` ブランチには一切触れていない。** Render は `main` を見てデプロイするので、
このブランチの内容は**まだどちらのRenderサービスにもデプロイされていない**。

---

## 2. 今回の問題（なぜこの変更をしたか）

### 2-1. 元の設計とその欠陥

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

具体的には、`shared/adb_reader.py` の `update_temps()`（旧版）にこう書かれていた：

```python
for bath in cfg["baths"]:
    # sensor_name が無ければ表示名(name)でセンサーを探す（案a: ピン名=センサー名）
    sname = (bath.get("sensor_name") or bath["name"]).strip()
    s = sensors_norm.get(sname)          # ← ここで名前が完全一致するものだけ拾う
    if s is None:
        # 一致しなかった → 前回値のまま stale=True（新しいデータは来ない）
```

### 2-2. 問題点

CMSでピンの表示名を変えたり、Inkbird側の名前とCMS側の名前が少しでもズレる
（全角半角・空白・表記ゆれ等）と、**そのセンサーの温度取得が黙って止まる**。しかも
CMS画面上は「表示/非表示」を選ぶだけの単純な操作に見えるのに、実は裏で
「Inkbirdアプリ上の実物の名前と1文字も違わず一致させる」という厳しい制約が
隠れていた。依頼者はこれを「本末転倒」「表示のON/OFFのはずが、なぜ温度取得の
成否に関わるのか」と判断し、この制約自体を無くす設計への変更を提案した。

（この経緯の詳細なやり取り・実コード確認の過程は、このセッションの会話ログ内に
残っている。要点だけ言うと、`update_temps()` のこの一致チェックが実際にコードで
動いていることを、依頼者からの「本当に？実際のコードを確認して」という指摘を受けて
逐一 `grep`・読解して確認済み。）

### 2-3. 提案された新方式

```
スマホが Inkbird アプリで見えているセンサーを、名前が何であれ無条件に全部アップロード
        ↓
クラウド(cloud_server.py)が受け取り、初めて見る名前には自動でidを採番して保存
        ↓
CMSは「実際に届いている全センサー」をそのまま一覧表示し、
画面ごとに「表示/非表示」を選ぶだけ（一致確認という概念自体が無くなる）
```

事前登録・名前の一致確認が丸ごと不要になり、「表示名を変えたら温度が止まった」という
事故が原理的に起きなくなる。

---

## 3. ファイル変更範囲（全差分）

### 3-1. `bath_system` リポジトリ（3ファイル）

#### `deploy_cloud/cloud_server.py`（Render上で動くクラウド中継サーバー）

新規追加した関数と `/api/push` の変更点：

```python
BASE_DIR = Path(__file__).parent
STORE    = BASE_DIR / "latest.json"
NAME_ID_MAP = BASE_DIR / "name_id_map.json"   # ★新規: センサー名→id の自動採番テーブル（永続化）

def _load_name_id_map() -> dict:
    """センサー名→id の対応表。無ければ、現行 bath-config.json の
    sensor_name/name→id を初期値として作る（＝既存の案内板テンプレ(SPOTS)の
    id とズレないようにするための種まき）。以後は初めて見る名前にだけ、
    使われていない最小の空き番号を新規採番する。"""
    if NAME_ID_MAP.exists():
        return json.loads(NAME_ID_MAP.read_text(encoding="utf-8"))
    seed = {}
    if BATH_CONFIG.exists():
        cur = json.loads(BATH_CONFIG.read_text(encoding="utf-8"))
        for b in cur.get("baths", []):
            key = (b.get("sensor_name") or b.get("name") or "").strip()
            if key and isinstance(b.get("id"), int):
                seed[key] = b["id"]
    _save_name_id_map(seed)
    return seed

def _id_for_name(m: dict, name: str) -> int:
    """名前に対応するidを返す。未登録なら、使われていない最小の番号を新規採番する。"""
    if name in m:
        return m[name]
    used = set(m.values())
    nid = 1
    while nid in used:
        nid += 1
    m[name] = nid
    return nid

def _sensors_payload_to_baths(sensors: list) -> list:
    """新方式(名前ベース)の {"sensors": [{"name","temp",...}]} を、
    旧方式と同じ {"baths": [{"id","name","temp",...}]} 形へ変換する。"""
    m = _load_name_id_map()
    baths = []
    for s in sensors:
        name = str(s.get("name", "")).strip()
        if not name:
            continue
        bid = _id_for_name(m, name)
        baths.append({"id": bid, "name": name, "device": "湯畑",
                      "temp": s.get("temp"), "humidity": s.get("humidity"),
                      "stale": s.get("stale", False), "at": s.get("at")})
    _save_name_id_map(m)
    return baths

@app.post("/api/push")
def api_push():
    if not SECRET or request.headers.get("X-Token") != SECRET:
        return jsonify(error="forbidden"), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="no json"), 400
    # ★新規: 新形式("sensors"配列)が来たら、旧形式("baths"配列)へ変換してから保存。
    # 旧形式で送ってくる（＝まだ更新していない）スマホともそのまま互換動作する。
    if isinstance(data.get("sensors"), list):
        data = {**data, "baths": _sensors_payload_to_baths(data["sensors"])}
        data.pop("sensors", None)
    STORE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    supa_insert(data)
    _history.append(data)
    return jsonify(ok=True)
```

**ポイント**: `/api/baths`・Supabase保存・CMS・案内板テンプレなど、`api_push` より
「後ろ」の処理は一切変更していない。すべて従来どおり `{"baths":[{id,name,temp,...}]}`
形式のまま流れる。変わるのは「`/api/push` に届いた時点でのデータの作り方」だけ。

#### `method_a/run_lite.py`（スマホ上で動く軽量ランナー）

```python
# 変更前: from adb_reader import load_config, run_once, load_temps, log, fetch_remote_baths
# 変更後:
from adb_reader import load_config, run_once, load_temps, log

_META_KEYS = {"gateway", "last_updated", "last_attempt", "online"}

# ── Inkbirdで見つかった全センサーを、名前ベースでそのまま送るペイロード ──
def build_payload(cfg: dict) -> dict:
    """temperatures.json（名前をキーに全センサーを保持）をそのままクラウドへ送る形にする。
    以前のように「CMSが決めた固定リスト(cfg['baths'])」に絞り込むことはしない。"""
    temps = load_temps()
    sensors = [{"name": name, **v} for name, v in temps.items()
              if name not in _META_KEYS and isinstance(v, dict)]
    return {
        "sensors":      sensors,
        "gateway":      temps.get("gateway"),
        "last_updated": temps.get("last_updated"),
        "last_attempt": temps.get("last_attempt"),
        "online":       temps.get("online", True),
    }
```

`refresh_baths()`（クラウドの事前登録リストを毎周期スマホ側に反映していた関数）は
**丸ごと削除**。`run_loop()` と `--once` 実行部からもその呼び出しを削除した。

#### `shared/adb_reader.py`（method_a・method_b共通のInkbird操作コア）

- `fetch_remote_baths()` / `remote_gateway_cfg()`（CMSの事前登録リストを取得・キャッシュする
  関数）を**削除**。コメントとして削除理由を残してある。
- `update_temps()` を全面書き換え。**引数から `cfg` を削除**し、`sensors`（見つかった
  センサー全部の辞書）をそのまま名前キーで `temperatures.json` に保存するだけの単純な
  関数にした：

```python
def update_temps(sensors: dict, gateway: dict | None = None) -> int:
    """見つかったセンサーを、名前をキーにそのまま temperatures.json へ書き込む
    （フィルタ・一致確認は行わない）。前回は見えていたが今回見えなかった名前は、
    前回値を保持して stale=True にする。"""
    prev: dict = load_temps()
    now = datetime.now().isoformat()
    temps: dict = {}
    sensors_norm = {str(k).strip(): v for k, v in sensors.items()}
    for name, s in sensors_norm.items():
        temps[name] = {"temp": s["temp"], "humidity": s.get("humidity"),
                       "stale": False, "at": now}
    for name, p in prev.items():
        if name in _META_KEYS or name in temps or not isinstance(p, dict):
            continue
        temps[name] = {**p, "stale": True}   # 今回見えなかった名前は前回値を維持
    # ゲートウェイ処理・保存は従来どおり
    ...
    return len(sensors_norm)
```

- ゲートウェイ（外気温）判定は、既存の `is_gateway_device()`（Inkbirdの型番
  "IBS-M2"等をキーワードで判定する関数、CMS設定とは無関係に元から存在した仕組み）
  **のみ**に一本化。CMSが特定のセンサーを外気温として明示指定する経路
  （`remote_gateway_cfg()` 経由）は廃止した。
- `run_once()` のログ出力・ゲートウェイ上書き処理もこれに合わせて簡略化（`cfg["baths"]`
  をループするコードを削除し、見つかったセンサーをそのままログに出すだけに変更）。

**Inkbirdアプリの画面を実際に読み取る部分**（`collect_all_temperatures()` /
`collect_device_temperatures()` / `find_sensor_tabs()` / ADB接続まわり）は
**一切変更していない**。変わったのは「読み取った後、どう選別・保存するか」だけ。

### 3-2. `yubatake_cms` リポジトリ（1ファイルのみ）

#### `static/index.html`

```javascript
// 変更前:
async function loadLiveTemps(){
  const base = ...;
  try{
    const d = await (await fetch(base + '/api/baths')).json();
    liveTemps = {};
    for(const b of (d.baths||[])) if(b.temp!=null) liveTemps[b.id] = b.temp;
    if(d.gateway && d.gateway.temp!=null) liveTemps[0] = d.gateway.temp;
  }catch{}
  try{
    const c = await (await fetch(base + '/api/bath-config')).json();   // ← CMS自身が作った事前登録リスト
    bathConfigLive = Array.isArray(c.baths) ? c.baths : [];
    bcGateway = (c.gateway && typeof c.gateway==='object') ? c.gateway : null;
  }catch{}
  ...
}

// 変更後:
async function loadLiveTemps(){
  const base = ...;
  try{
    const d = await (await fetch(base + '/api/baths')).json();         // ← 1回のfetchで両方まかなう
    liveTemps = {};
    for(const b of (d.baths||[])) if(b.temp!=null) liveTemps[b.id] = b.temp;
    if(d.gateway && d.gateway.temp!=null) liveTemps[0] = d.gateway.temp;
    bathConfigLive = Array.isArray(d.baths) ? d.baths : [];             // ← 実際に届いているデータをそのまま使う
    bcGateway = (d.gateway && typeof d.gateway==='object') ? d.gateway : null;
  }catch{}
  ...
}
```

`server.py`（Python側）は今回**無変更**。CMSの「🌡センサー登録」の仕組み
（`config.sensors` / `sensor_name` / `build_bath_config` の一致確認ロジック）は
コード上まだ残っている（削除していない・実害はない・今後使われなくなるだけ）。

---

## 4. その他、必須の前提事項

### 4-1. ⚠️ 物理的なスマホ更新が必須（最重要）

`shared/adb_reader.py` と `method_a/run_lite.py` は **現地のスマホ（Termux）上で動く
実物のスクリプト**。GitHubにpushしても、bath-board/CMSのようにRenderが自動デプロイ
してくれるわけではない。**このブランチをmainにマージしただけでは、現地のスマホの
挙動は何も変わらない。**

効果を出すには：
1. `feature/name-based-sensors` の `shared/`・`method_a/` の内容を、実機スマホに
   ADB経由でコピー（例: `adb push` や、Termux側で `git pull` できるなら pull）
2. スマホ側のサービスを再起動（`ctl.sh` 等。詳細手順は `shared/docs/PHONE_OPS.md`
   ※このファイルはこのリポジトリの `shared/docs/` にある。中身は「スマホ再起動後の
   ADB復旧手順」なので、サービス起動・停止の具体コマンドはそちらを直接見ること）
3. ここまでやって初めて新方式が実際に動く

**このタスクを依頼したユーザーは「スマホが手元にないため、最終実行（本番反映）は
まだ実施しない」と明言している。** 次のセッションが安易に `main` へマージ・本番
デプロイしないよう注意すること。

### 4-2. 後方互換性（安全設計）

- `cloud_server.py` の `/api/push` は **新形式(`sensors`)・旧形式(`baths`) の両方を
  受理する**。スマホ側がまだ更新されていない（＝旧形式で送ってくる）状態でも、
  `cloud_server.py` だけ先に本番反映しても壊れない。
- とはいえ安全のため、まずは `main` マージ＝本番デプロイをせず、**スマホ更新の
  タイミングと合わせる**運用を推奨する。

### 4-3. id自動採番の仕組み（`name_id_map.json`）の詳細

- `deploy_cloud/` フォルダに新しく `name_id_map.json` というファイルができる
  （Render上の永続ディスクに保存される想定。ローカルでの動作確認はしたが、
  **Render上での実ファイル永続化の挙動そのものはまだ検証していない**点に注意。
  Renderの無料プランはディスクが再起動で消える場合があるため、再起動のたびに
  `bath-config.json` からの再シード＝既存id復元は起きるが、「初めて見た新センサー」に
  一度割り振った番号が再起動で変わる可能性はゼロではない。要現地確認）
- 初回実行時、`deploy_cloud/bath-config.json`（現行の公開済みファイル）から
  `sensor_name（無ければname）→id` を種まきする。これにより既存の案内板テンプレート
  （`base-all-cut.html`/`rotenburo.html`等のSPOTS配列に書かれたid）とズレずに引き継がれる。
- 初めて見る名前だけ、使われていない最小の番号を新規採番する。
- ローカルで以下を検証済み（`/tmp` 上で `cloud_server.py` を直接importして実行）：
  - 既存9件（id 1-7, 20, 21）を種まきした状態で、既存名は元のidのまま返る
  - 未知の名前「新規パントリー」を渡すと、空いている最小番号（このケースでは8）が
    自動採番される
  - 同じ入力を2回渡しても、2回とも同じidが返る（再現性・冪等性を確認済み）

### 4-4. 巻き戻し（ロールバック）方法

- **今の時点**: 何もマージ・デプロイしていないので、`feature/name-based-sensors`
  ブランチを（両リポジトリとも）削除するだけで元通り。他に影響する箇所は無い。
- **本番反映後に戻す場合**:
  - クラウド側（`cloud_server.py`／CMSの`static/index.html`）: 該当コミットを
    `git revert` して、通常のデプロイ手順（CMSの「🚀公開」／Render Manual Deploy）
    で反映するだけ。
  - スマホ側: 旧バージョンの `shared/`・`method_a/` を再度ADBで書き戻して再起動。

### 4-5. センサー登録UI（`config.sensors`）の今後

この移行が完了すれば、CMSの「🌡センサー登録」の仕組み（`config.sensors` /
`sensor_name` / `server.py`の`build_bath_config()` の一致確認ロジック）は**役目を
終える**。今回は削除していない（消しても実害はないが、スコープ外として温存した）。
ただし外気温ゲートウェイの手動指定機能（CMSから「このセンサーを外気温として使う」と
明示指定する機能）は、今回の変更で `is_gateway_device()` の型番自動検出のみに
一本化されたため、**CMSからの明示指定は既に使われなくなっている**（この機能を
今後も残したいなら、別途の対応が必要）。

### 4-6. 今回、意図的にスコープ外にしたもの（要注意・確認済みの不具合あり）

- `method_b`（PC + BlueStacksエミュレータでの温度取得方式。README曰く現行本番は
  `method_a` なので優先度は低いが、**もし method_b を使う予定があるなら要対応**）:
  `method_b/server.py` の `/api/baths`（下記）が、`temperatures.json` を
  **旧方式のまま「idの文字列」をキーに読もうとしている**ため、name-based方式の
  `run_once()`（＝名前をキーに保存する）と組み合わせると**温度が一切表示されなくなる**
  ことを実際にコードで確認済み：
  ```python
  # method_b/server.py の api_baths()（未修正）
  for b in cfg["baths"]:
      entry = temps.get(str(b["id"]))   # ← temperatures.json はもう id ではなく
                                         #    センサー名がキーになっているので、
                                         #    ここは常に None になる
  ```
  同ファイルの `/api/position/<id>` 等、他にも `cfg["baths"]` を前提にした箇所が
  複数ある。**method_b を使うなら、この移行と合わせて method_b/server.py 側も
  名前ベースに書き換えるか、method_b では旧版の `shared/adb_reader.py` を使い
  続けるかを決める必要がある**（現状はこのブランチの `shared/adb_reader.py` を
  method_a・method_b の両方が共有しているため、放置すると method_b が壊れる）。
- CMSの `server.py`（Python側）・`config.sensors` 関連コードは今回無変更。

---

## 5. 次にやること（このブランチの完了条件）

1. ユーザーが現地でスマホを用意できたら、上記「4-1. 物理的なスマホ更新」を実施
2. 動作確認:
   - CMSの「🌡 温度データ」で、新方式のデータ（新しいセンサーも含めて）が
     正しく出るか
   - 既存の温度表示（高温の湯・座湯・大浴場男湯/女湯 等）が壊れていないか
   - `name_id_map.json` がRender再起動後も既存idを保持しているか（4-3参照、要確認）
3. 問題なければ、`bath_system`・`yubatake_cms` 両方の `feature/name-based-sensors` を
   `main` にマージ → 通常のデプロイ手順（CMSの「🚀公開」／Render Manual Deploy）で
   本番反映
4. 落ち着いたら `method_b` への影響有無を確認（4-6参照）
