## セットアップ

1. Raspberry Piを起動します。
2. Raspberry PiにSSH接続し、以下のコマンドを実行します。
   ```bash
   sudo apt-get install bluetooth libbluetooth3 libusb-dev
   sudo systemctl enable bluetooth.service
   sudo usermod -G bluetooth -a pi
   sudo shutdown -h now
   ```
3. Raspberry Piを再起動します。
4. PS3コントローラをRaspberry PiへUSBケーブルで接続します。
5. PSロゴボタンを押します。
6. Raspberry PiにSSH接続し、以下のコマンドを実行します。
   ```bash
   wget http://www.pabr.org/sixlinux/sixpair.c
   gcc -o sixpair sixpair.c -lusb
   sudo ./sixpair
   ```
7. 以下のコマンドを実行してペアリングを行います。
   ```bash
   bluetoothctl
   agent on
   devices
   trust <MAC ADDRESS>
   default-agent
   quit
   ```
8. USBケーブルを外します。
9. PSロゴボタンを押します。
10. Raspberry PiにSSH接続し、以下のコマンドを実行します。
   ```bash
   ls /dev/input/js0
   ```

## 充電

何らかの理由で、PS3ジョイスティックは、有効ななBluetoothコントロールとOSドライバをセットアップしていないと電源供給されたUSBポートで充電できません。 これは、電話機のUSB充電器では充電できず、Windowsマシンからの充電がうまくいかないことを意味します。

そのかわり設定済みのRaspberry Piからは充電することができます。 ジョイスティックをPiに接続し、充電器またはPCを使用してRaspberry Piに電源を入れるだけです。

### バッテリ交換

古いコントローラーを使っていると、バッテリがうまく機能しなくなることがあるとおもいます。ここに [新しいバッテリ](http://a.co/5k1lbns) へのリンクがあります。 カバーを取り外すときは注意してください。 5本のネジを外す必要があります。ハンドグリップの上半分にタブがあります。 あなたは分割/正面から開いて、下を前方に引っ張ってみてください。そうしないと、タブを壊してしまいます。

## 操作方法

* 左側アナログスティック
  * 左右：ステアリング操作

* 右側アナログスティック
  * 上：スロットル前進増速
  * ２回下：スロットル後進増速

> スロットルがゼロでないときは、User モードの場合でスロットルがゼロではない状態では常に運転データが記録されます！

* Selectボタン：モード変更
  * User モード → Local Angle モード → Local(操舵およびスロットル) → User モード..

* △ボタン：最大スロットル値をあげる
* ✕ボタン：最大スロットル値をさげる
* ◯ボタン：記録の切り替え（デフォルトでは無効、スロットルの自動記録はデフォルトで有効）
* 上ボタン：スロットル値を増やす
* 下ボタン：スロットル値をへらす
* 左ボタン：ステアリング値を増やす
* 右ボタン：ステアリング値をへらす
* Startボタン：一定のスロットルを切り替え。 スロットルを最大に設定する（XとTriangleで変更）


