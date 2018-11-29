# Donkey Car 1号車 "Rocinante号" 用アプリリポジトリ

香港 [Robocar Store](https://www.robocarstore.com/) のフルキットベースのDonkey Car用アプリのディレクトリをリポジトリ化したものです。

![my first donkey car](./docs/mycar.jpg)



## 部品リスト

### 車体

|品名|参考価格|用途|
|:-|-:|:-|
| [Robocar Store Donkey Car Starter Kit](https://www.robocarstore.com/) | HK$2,180 + 送料 | Donkey2準拠の標準車両をベースとしたフルキット。Raspberry Piや書き込み済みSDカードも同梱。 |
| [十字穴付き ボルト セット ステンレス マシンネジ 修理ツール ナット ロックワッシャ 平ワッシャー 収纳ケース付き 400本入り M2 M2.5 M3 M4 M5 ](https://amzn.to/2ReUdWE) | 1,799円 | すべての基盤の四隅を2.5Mナット＆ねじが不足したため購入 |
| [3M スコッチ プラスチック用接着剤 30ml 6225N](https://amzn.to/2RbUycP) | 364円 |ロールバーと天板はこれで接着した |

参考価格は約3万3千7百円＋送料です。

* マイナスドライバ
* はさみ

### ジョイスティック

SONY PlayStation4で使用している Dualshock4 コントローラを使用した。

|品名|参考価格|用途|
|:-|-:|:-|
| [ワイヤレスコントローラー (DUALSHOCK 4) ](https://amzn.to/2RcT4yV) | 7,728円 | PS4を持っていない場合は購入できる |
| [SIE ソニー・インタラクティブエンタテインメント CUH-ZWA1J PS4対応 ワイヤレスコントローラー DUALSHOCK 4 USBワイヤレスアダプター](https://www.yodobashi.com/product/100000001003225422/) | 2,890円 | Bluetoothドングル、Raspberry Piに刺す|

上記ジョイスティックは充電式なので、別途mini-b USBケーブルが必要となる。

### 参考ドキュメント

以下の日本語リンクを参考にしてください。

* [Raspberry Pi/donkeycar セットアップ](https://github.com/coolerking/donkeycar_jpdocs/blob/master/donkeycar/docs/guide/install_software.md)
* [donkeypart_ps3_controller セットアップ](https://github.com/coolerking/donkeycar_jpdocs/tree/master/donkeypart_ps3_controller)
* [結線図参考](https://www.slideshare.net/HoriTasuku/donkey-car)


## 車両の制作

* [写真で見る Donkey Carの組み立て](https://www.slideshare.net/HoriTasuku/donkey-car)

## インストール


1. emperor 上のRaspberry Piにターミナル接続します。

2. 以下のコマンドを実行して、python donkeycar パッケージのバージョンが2.5.8であることを確認します。
   ```bash
   pip install donkeycar[pi]
   python -c "import donkeycar as dk; print(dk.__version__)"
   ```

3. 以下のコマンドを実行して、PS4コントローラ用partパッケージを導入します。
   ```bash
   git clone　https://github.com/autorope/donkeypart_ps3_controller.git
   cd donkeypart_ps3_controller
   pip install -e .
   ```

4. 以下のコマンドを実行して、リポジトリをRaspberry Pi上に展開します。
   ```bash
   cd
   git clone https://github.com/coolerking/rocinante.git
   cd emperor
   ```

## Bluetooth ペアリング

1. DUALSHOCK 4 USBワイヤレスアダプタ をRaspberry Piに接続します。
2. DUALSHOCK 4 USBワイヤレスアダプタ を刺したまま、Raspberry Pi本体側に3秒以上押し込み、アダプタの点滅速度を早くします。
3. DUALSHOCK 4 ジョイスティックのSHAREボタンとPSロゴボタンを同時に3秒以上押し、アダプタの点滅が点灯状態にします・
4. Raspberry Pi へSSH接続し、以下のコマンドを実行して、PS4コントローラを操作すると、ヘキサ文字列が表示されれば成功です。
    ```bash
    hexdump /dev/input/js0
    ```

｀/dev/input/js0` はアダプタを装着し再起動すれば生成されます。

## 実行

1. キャリブレーション

   スロットル、ステアリングの調整を以下のコマンドで行い、取得した値を `config.py` に書き込みます。


   * スロットル(Ch0)
     本車体はシャーシに対して重量があるため、やや速度早めに設定しておくことをすすめます。
     ```bash
     donkey calibrate --channel 0
     ```

   * ステアリング(Ch1)
     本車体は、自重のせいでシャコタン状態であるため、最大舵角をとると車輪が浮くので、それほど最大舵角をとることができません。
     ```bash
     donkey calibrate --channel 1
     ```

2. 手動運転(データ収集)

   以下の手順で手動運転を行い、学習データ(tubデータ)を `data` ディレクトリに収集します。

   * 携帯もしくはWeb画面から操作
      ```bash
      cd rocinante
      python manage.py drive
      ```

   * ジョイスティックから操作
      ```bash
      cd rocinante
      python manage.py drive --js
      ```

3. トレーニング

   トレーニングは Raspberry Pi上ではなく、PC等で実行します。
   `rocinante/data` ディレクトリをトレーニングを実行するノードへコピーし、`python manage.py --tub <tubデータディレクトリ> --model models/mypylot` を実行します。

   > トレーニングを実行するノードのdonkeycar パッケージのバージョンも 2.5.8 を使用してください。

   上記コマンドを実行すると、`mypilot`が新たに作成されるので、これを Raspberry Pi 側の `rocinante/models` ディレクトリにコピーします。

4. 自動運転

   以下の手順で自動運転を実行します。
   ```bash
   cd
   cd rocinate
   python manage.py drive --model models/mypilot
   ```



## 利用OSS

* GitHub [autorope/donkeycar](https://github.com/autorope/donkeycar) v2.5.8
  Donkey Car の基本機能OSS、MITライセンス準拠です。2.5.1から2.5.8へ更新した際にpartsのリポジトリは分割されました。

* GitHub [autorope/donkeypart_ps3_controller](https://github.com/autorope/donkeypart_ps3_controller)
  `old`ディレクトリ内のコントローラが基底クラスとして使用しています。

* GitHub [autorope/donkeypart_bluetooth_game_controller](https://github.com/autorope/donkeypart_bluetooth_game_controller)
  F710やJC-U3912Tの各コントローラが基底クラスとして使用しています。

## ライセンス

本リポジトリの上記OSSで生成、コピーしたコード以外のすべてのコードはMITライセンス準拠とします。
