# RTL-SDR 直接受信セットアップ（エミュレータ不要化）

IBS-P02R センサーが 433.92MHz で約80秒ごとに送信する電波を、
USBドングル（RTL-SDR）で直接受信して温度を取得する。
クラウド・アプリ・エミュレータ・ADB すべて不要になる。

```
[IBS-P02R×5] --433MHz--> [RTL-SDRドングル] --USB--> [サーバーPC: rtl_433 → rf_reader.py → temperatures.json]
```

## 1. 必要なハードウェア

- RTL-SDR ドングル 1個（RTL2832U チップ搭載のもの）
  - 推奨: RTL-SDR Blog V3 / V4（Amazonで3,000〜6,000円）
  - 付属アンテナで可。受信が弱ければ433MHz用アンテナに交換
- 設置場所: センサー（湯舟）から見通しの良い場所が理想。
  IBS-M2ゲートウェイが届いている場所なら同等の場所でOK

## 2. ソフトウェア導入（Linux）

```bash
sudo apt update
sudo apt install rtl-433          # rtl-sdrドライバも一緒に入る

# DVB-TのTVドライバが横取りしないようにブラックリスト登録
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtlsdr.conf
sudo modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true
```

Windowsの場合は rtl_433 のリリースバイナリ + Zadigでドライバ導入。

## 3. 受信テスト

ドングルを挿して:

```bash
rtl_433 -f 433.92M -F json -R 194
```

約80秒待つと、センサーごとに以下のようなJSONが流れてくれば成功:

```json
{"time":"...","model":"Inkbird-ITH20R","sensor_num":1,"temperature_C":40.2,...}
```

※ プロトコル194は IBS-P01R/ITH-20R 用。P02R が194でデコードできない場合は
`-R` を外して全プロトコルで受信し、何かしら出るか確認する。
それでも出ない場合は `rtl_433 -f 433.92M -A` で生信号を解析（要相談）。

## 4. センサー対応付け（初回のみ）

```bash
python3 rf_reader.py --discover
```

全受信パケットがログに出る。アプリの表示と照合するか、
1本ずつセンサーをお湯から出し入れして温度変化で特定し、
`config.json` の `rf.sensor_map` に **RFのsensor_num → 湯舟ID** を記入:

```json
"rf": {
  "enabled": true,
  "sensor_map": { "1": 1, "2": 2, "3": 3, "5": 5, "6": 6 },
  "gateway_sensor_num": "9"
}
```

- `sensor_map` のキーが電波側の番号、値が config.json `baths` の id
- 湿度付きの外気センサーがあれば `gateway_sensor_num` に指定（外気温表示に使われる）
- 水温が `temperature_2_C` 側に入る機種だった場合は `"temp_field": "temperature_2_C"` を追加

## 5. 運用開始

`config.json` で `rf.enabled: true` にして server.py を起動するだけ。
（rf.enabled が true のとき ADB は使われない。false に戻せば従来のADB取得に戻る）

単体実行も可能:

```bash
python3 rf_reader.py            # 受信し続けて temperatures.json を更新
python3 rf_reader.py --replay sample.log   # 保存ログでテスト（ドングル不要）
```

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `usb_open error` | ブラックリスト設定後に再起動 / ドングル挿し直し |
| 何も受信しない | `-R` なしで全プロトコル受信 → 周辺の他機器が見えるか確認（アンテナ・位置調整） |
| 一部センサーだけ受信できない | ドングルの設置場所を湯舟寄りに / アンテナ交換 |
| 画面が「未接続」になる | 10分（stale_after）以上受信なし。電波状況を確認 |
