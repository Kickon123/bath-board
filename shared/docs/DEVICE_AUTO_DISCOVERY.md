# デバイス自動検出（Inkbirdアプリのホーム一覧を自動巡回）は可能か

日付: 2026-09-15

## 背景・現状

現在の温度取得（`shared/adb_reader.py`）は、config.json（雛形: `method_a/config.phone.json`）の
`adb.devices` に書かれたデバイス名だけを、`find_device_coords()` で
ホーム画面のテキストから**ピンポイント検索**してタップする方式（[adb_reader.py:277-292](../shared/adb_reader.py#L277-L292)）。
「名前をあらかじめ知っている前提」の実装で、新しいデバイス（Inkbirdアプリでの新規ペアリング）を
追加すると：

1. `config.phone.json` の `adb.devices`（単体センサーなら `single_sensor_devices` にも）を編集
2. スマホの実ファイル `config.json` へ手動コピー（`phone_setup.sh` の手順、CMS/GitHubからの自動配信は廃止済み）
3. `run_lite.py` は起動時に一度だけ `load_config()` するため、**プロセス再起動が必須**
   （`bash ctl.sh restart`）

という3ステップの手動作業が必要になっている。

## 自動検出は技術的に可能か → 可能。ただし実機確認が1回必要

ホーム画面のUIダンプ（`dump_ui()`、既存関数）から**画面上の全デバイスタイル名を列挙**する処理を
新設すれば、config側の事前登録なしに毎サイクル「今ホーム画面に並んでいるデバイス」を
自動で全部巡回できる。実装イメージ：

```
1. dump_ui() でホーム画面を取得
2. 画面上のデバイスタイル名を全部拾う（新規関数。要: 実機ダンプでのresource-id確認）
3. scroll_device_list() で下までスクロールしながら②を繰り返し、重複除去した全デバイス名リストを得る
4. そのリストの各名前に対して refresh_device_view() → collect_device_temperatures() を回す
   （＝現状の adb.devices ループと同じ処理を「自動収集した名前」に差し替えるだけ）
5. update_temps() へそのまま渡す（ここは変更不要）
```

②〜④は既存部品（`dump_ui`, `refresh_device_view`, `collect_device_temperatures`,
`scroll_device_list`）の組み合わせで作れる。

## 実装前に確認が必要な点

### 1. ホーム画面のデバイス名を確実に判別するresource-id

`find_device_coords()` は「画面上の全テキストノードから一致するものを探す」という雑な実装
（[adb_reader.py:284-285](../shared/adb_reader.py#L284-L285)）で、
「これがデバイス名専用のresource-idだ」という確認をしていない。ホーム画面には検索欄・追加ボタン・
タブ見出し等デバイス名以外のテキストも並ぶはずなので、実機で一度
`adb shell uiautomator dump` を取り、ホーム画面のデバイスタイル名がどの `resource-id` /
構造で出ているか確認してから判定ロジックを書く必要がある。

（リポジトリ内 `bath_system/archive/dump_s1.xml` 等はサンプルとして残っているが中身が空で参照不可だった。）

### 2. 単体センサー（パントリー等）の名前解決の罠

単体センサーは、そのデバイス**自身の画面**には「IBS-M2」のような型番しか表示されず、
「パントリー 4F」のような場所名はホーム画面のタイル名にしか出ない。
現状は `single_sensor_devices` に登録されているデバイスだけ、config側の名前を強制的に
使うことでこれを回避している（[adb_reader.py:393-396](../shared/adb_reader.py#L393-L396)、
[418-421行](../shared/adb_reader.py#L418-L421)）。

自動検出にする場合も、**ホーム画面のタイル名（人が付けた分かりやすい名前）をデータのキーにする**
必要があり、デバイス画面側のテキスト（型番）をそのまま使うと：
- 複数の単体センサーが同じ型番名に潰れる
- `is_gateway_device()` が "IBS-M2" を外気温ゲートウェイと誤判定する

という問題が起きる。単体/ハブ（タブあり）の判別も、`find_sensor_tabs()` の結果が空かどうかで
自動判定するロジックに変える必要がある（現状は config の `single_sensor_devices` フラグで判定）。

## まとめ

- 実現可能。UI構造（resource-id）さえ実機ダンプで特定できれば、
  「ホーム一覧を毎回スキャンして全デバイスを自動巡回」に作り替えられる。
- 実装すれば、「config.phone.json編集 → 実機コピー → プロセス再起動」という3手順が丸ごと不要になり、
  新しいセンサーをペアリングするだけで次サイクルから自動的に拾われるようになる。
- 着手前に、実機で `adb shell uiautomator dump` を1回取得し、ホーム画面のデバイス名の
  resource-id／構造を確認する必要がある（未着手）。
