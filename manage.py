#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Donkey2 準拠の車両の運転やモデルのトレーニングを行うためのスクリプトファイル。

使い方:
    manage.py (drive) [--model=<model>] [--js] [--chaos]
    manage.py (train) [--tub=<tub1,tub2,..tubn>]  (--model=<model>) [--base_model=<base_model>] [--no_cache]

オプション:
    -h --help        使い方を表示。
    --tub TUBPATHS   tubファイルが格納されているディレクトリへのパスを指定する。カンマ区切り指定可能。"~/tubs/*"といったワイルドカード指定も可能。
    --js             ジョイスティックを使用する。
    --chaos          手動運転中に周期的なランダム操舵を加える。
"""
import os
from docopt import docopt

import donkeycar as dk
from donkeycar.parts.camera import PiCamera
from donkeycar.parts.transform import Lambda
from donkeycar.parts.keras import KerasLinear
from donkeycar.parts.actuator import PCA9685, PWMSteering, PWMThrottle
from donkeycar.parts.datastore import TubGroup, TubWriter
from donkeycar.parts.web_controller import LocalWebController
from donkeycar.parts.clock import Timestamp


def drive(cfg, model_path=None, use_joystick=False, use_chaos=False):
    """
    （手動・自動）運転する。

    多くの部品(part)から作業用のロボット車両を構築する。
    各partはVehicleループ内のジョブとして実行され、コンストラクタフラグ `threaded`に応じて 
    `run` メソッドまたは `run_threaded` メソッドを呼び出す。
    すべてのパーツは、 `cfg.DRIVE_LOOP_HZ` で指定されたフレームレートで順次更新され、
    各partが適時に処理を終了すると仮定する。
    partには名前付きの出力と入力が存在する(どちらかがない場合や複数存在する場合もある)。 
    Vehicle フレームワークは、名前付き出力を同じ名前の入力を要求するpartに渡すことを処理する。

    引数
        cfg             個別車両設定オブジェクト、`config.py`がロードされたオブジェクト。
        model_path      自動運転時のモデルファイルパスを指定する（デフォルトはNone）。
        use_joystick    ジョイスティックを使用するかどうかの真偽値（デフォルトはFalse）。
        use_chaos       手動運転中に周期的なランダム操舵を加えるかどうかの真偽値（デフォルトはFalse）。
    """

    # Vehicle オブジェクトの生成
    V = dk.vehicle.Vehicle()

    # Timestamp part の生成
    clock = Timestamp()
    # Timestamp part をVehicleループへ追加
    # 入力：
    #     なし
    # 出力：
    #     'timestamp'    現在時刻
    V.add(clock, outputs=['timestamp'])

    # PiCamera part の生成
    cam = PiCamera(resolution=cfg.CAMERA_RESOLUTION)
    # 別スレッド実行される PiCamera part をVehicleループへ追加
    # 入力：
    #     なし
    # 出力：
    #     'cam/image_array'    cfg.CAMERA_RESOLUTION 型式の画像データ
    V.add(cam, outputs=['cam/image_array'], threaded=True)

    # manage.py デフォルトのジョイスティックpart生成
    #if use_joystick or cfg.USE_JOYSTICK_AS_DEFAULT:
    #    ctr = JoystickController(max_throttle=cfg.JOYSTICK_MAX_THROTTLE,
    #                             steering_scale=cfg.JOYSTICK_STEERING_SCALE,
    #                             throttle_axis=cfg.JOYSTICK_THROTTLE_AXIS,
    #                             auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
    # ジョイスティック part の生成
    if use_joystick or cfg.USE_JOYSTICK_AS_DEFAULT:
        # F710用ジョイスティックコントローラを使用
        #from parts.logicool import F710_JoystickController
        #ctr = F710_JoystickController(
        # PS4 Dualshock4 ジョイスティックコントローラを使用
        from donkeypart_ps3_controller.part import PS4JoystickController
        ctr = PS4JoystickController(
        # ELECOM JC-U3912T ジョイスティックコントローラを使用
        #from parts.elecom import JC_U3912T_JoystickController
        #ctr = JC_U3912T_JoystickController(
                                 throttle_scale=cfg.JOYSTICK_MAX_THROTTLE,
                                 steering_scale=cfg.JOYSTICK_STEERING_SCALE,
                                # throttle_axis=cfg.JOYSTICK_THROTTLE_AXIS,
                                 auto_record_on_throttle=cfg.AUTO_RECORD_ON_THROTTLE)
    else:
        # ステアリング、スロットル、モードなどを管理するWebサーバを作成する
        # Web Controller part の生成
        ctr = LocalWebController(use_chaos=use_chaos)

    # 別スレッド実行される Web Controller part もしくはジョイスティック part をVehiecleループへ追加
    # 入力：
    #     'cam/image_array'     cfg.CAMERA_RESOLUTION 型式の画像データ
    # 出力：
    #     'user/angle'          Web/Joystickにより手動指定した次に取るべきステアリング値
    #     'user/throttle'       Web/Joystickにより手動指定した次に取るべきスロットル値
    #     'user/mode'           Web/Joystickにより手動指定した次に取るべきUserモード(入力なしの場合は前回値のまま)
    #     'recording'           tubデータとして保管するかどうかの真偽値
    V.add(ctr,
          inputs=['cam/image_array'],
          outputs=['user/angle', 'user/throttle', 'user/mode', 'recording'],
          threaded=True)

    # オートパイロットモジュールを実行すべきかどうかを確認する関数を定義する。
    def pilot_condition(mode):
        '''
        オートパイロットモジュール実行判定関数。
        引数で指定されたモードを判別して、オートパイロットモジュールを実行するべきかどうか
        真偽値を返却する関数。

        引数
            mode     Userモード('user':全手動、'local_angle':操舵のみ自動、'local':全自動)
        戻り値
            boolean  オートパイロットモジュールを実行するかどうかの真偽値
        '''
        if mode == 'user':
            # 全手動時のみ実行しない
            return False
        else:
            return True

    # オートパイロットモジュール実行判定関数を part 化したオブジェクトを生成
    pilot_condition_part = Lambda(pilot_condition)
    # オートパイロットモジュール実行判定 part を Vehiecle ループへ追加
    # 入力：
    #     'user/mode'    Userモード('user':全手動、'local_angle':操舵のみ自動、'local':全自動)
    # 出力：
    #     'run_pilot'    オートパイロットモジュールを実行するかどうかの真偽値
    V.add(pilot_condition_part,
          inputs=['user/mode'],
          outputs=['run_pilot'])

    # Userモードでない場合、オートパイロットを実行する
    # CNNベースの線形回帰モデル(オートパイロット) part を生成する。
    kl = KerasLinear()
    # 関数driveの引数 model_part 指定がある場合
    if model_path:
        # 学習済みモデルファイルを読み込む
        kl.load(model_path)

    # run_condition が真の場合のみ実行されるオートパイロット part をVehicleループへ追加する
    # 入力：
    #     'cam/image_array'    cfg.CAMERA_RESOLUTION 型式の画像データ
    # 出力：
    #     'pilot/angle'        オートパイロットが指定した次に取るべきステアリング値
    #     'pilot/throttle'     オートパイロットが指定した次に取るべきスロットル値
    V.add(kl,
          inputs=['cam/image_array'],
          outputs=['pilot/angle', 'pilot/throttle'],
          run_condition='run_pilot')

    # 車両にどの値を入力にするかを判別する
    def drive_mode(mode,
                   user_angle, user_throttle,
                   pilot_angle, pilot_throttle):
        '''
        引数で指定された項目から、車両への入力とするステアリング値、スロットル値を確定する関数。
        引数
            mode            Web/Joystickにより手動指定した次に取るべきUserモード(入力なしの場合は前回値のまま)
            user_angle      Web/Joystickにより手動指定した次に取るべきステアリング値
            user_throttle   Web/Joystickにより手動指定した次に取るべきスロットル値
            pilot_angle     オートパイロットが指定した次に取るべきステアリング値
            pilot_throttle  オートパイロットが指定した次に取るべきスロットル値
        戻り値
            angle           車両への入力とするステアリング値
            throttle        車両への入力とするスロットル値
        '''
        if mode == 'user':
            return user_angle, user_throttle

        elif mode == 'local_angle':
            return pilot_angle, user_throttle

        else:
            return pilot_angle, pilot_throttle

    # 車両にどの値を入力にするかを判別する関数を part 化したオブジェクトを生成
    drive_mode_part = Lambda(drive_mode)

    # 車両にどの値を入力にするかを判別する part を Vehicle ループへ追加
    # 入力
    #     'user/mode'       Web/Joystickにより手動指定した次に取るべきUserモード(入力なしの場合は前回値のまま)
    #     'user/angle'      Web/Joystickにより手動指定した次に取るべきステアリング値
    #     'user/throttle'   Web/Joystickにより手動指定した次に取るべきスロットル値
    #     'pilot/angle'     オートパイロットが指定した次に取るべきステアリング値
    #     'pilot/throttle'  オートパイロットが指定した次に取るべきスロットル値
    # 戻り値
    #     'angle'           車両への入力とするステアリング値
    #     'throttle'        車両への入力とするスロットル値
    V.add(drive_mode_part,
          inputs=['user/mode', 'user/angle', 'user/throttle',
                  'pilot/angle', 'pilot/throttle'],
          outputs=['angle', 'throttle'])

    # 実車両のステアリングサーボを操作するオブジェクトを生成
    steering_controller = PCA9685(cfg.STEERING_CHANNEL)
    # 実車両へステアリング値を指示する part を生成
    steering = PWMSteering(controller=steering_controller,
                           left_pulse=cfg.STEERING_LEFT_PWM,
                           right_pulse=cfg.STEERING_RIGHT_PWM) 

    # 実車両のスロットルECSを操作するオブジェクトを生成
    throttle_controller = PCA9685(cfg.THROTTLE_CHANNEL)
    # 実車両へスロットル値を指示する part を生成
    throttle = PWMThrottle(controller=throttle_controller,
                           max_pulse=cfg.THROTTLE_FORWARD_PWM,
                           zero_pulse=cfg.THROTTLE_STOPPED_PWM,
                           min_pulse=cfg.THROTTLE_REVERSE_PWM)

    # 実車両へステアリング値を指示する part を Vehiecle ループへ追加
    # 入力：
    #     'angle'          車両への入力とするステアリング値
    # 出力：
    #     なし(実車両の操舵へ)
    V.add(steering, inputs=['angle'])
    # 実車両へスロットル値を指示する part を Vehiecle ループへ追加
    # 入力：
    #     'throttle'       車両への入力とするスロットル値
    # 出力：
    #     なし(実車両のスロットル操作へ)
    V.add(throttle, inputs=['throttle'])

    # 保存データを tub ディレクトリに追加
    inputs = ['cam/image_array', 'user/angle', 'user/throttle', 'user/mode', 'timestamp']
    types = ['image_array', 'float', 'float',  'str', 'str']

    # 複数 tub ディレクトリの場合
    # th = TubHandler(path=cfg.DATA_PATH)
    # tub = th.new_tub_writer(inputs=inputs, types=types)

    # 単一 tub ディレクトリの場合
    # tub ディレクトリへ書き込む part を生成
    tub = TubWriter(path=cfg.TUB_PATH, inputs=inputs, types=types)
    # 'recording'が正であれば tub ディレクトリへ書き込む part を Vehiecle ループへ追加
    # 入力
    #     'cam/image_array'    cfg.CAMERA_RESOLUTION 型式の画像データ
    #     'user/angle'         Web/Joystickにより手動指定した次に取るべきステアリング値
    #     'user/throttle'      Web/Joystickにより手動指定した次に取るべきスロットル値
    #     'user/mode'          Web/Joystickにより手動指定した次に取るべきUserモード(入力なしの場合は前回値のまま)
    #     'timestamp'          現在時刻
    V.add(tub, inputs=inputs, run_condition='recording')

    # Vehicle ループを開始
    V.start(rate_hz=cfg.DRIVE_LOOP_HZ,
            max_loop_count=cfg.MAX_LOOPS)


def train(cfg, tub_names, new_model_path, base_model_path=None):
    """
    引数 tub_names 似て指定されたパスに格納されている tub データを学習データとして
    トレーニングを行い、引数 new_model_path にて指定されたパスへ学習済みモデルファイルを格納する。
    引数：
        cfg                個別車両設定オブジェクト、`config.py`がロードされたオブジェクト。
        tub_names          学習データとして使用するtubディレクトリのパスを指定する。
        new_model_path     トレーニング後モデルファイルとして保管するパスを指定する。
        base_model_path    ファインチューニングを行う場合、ベースとなるモデルファイルを指定する。
    戻り値
        なし
    """

    # モデルの入力データとなる項目
    X_keys = ['cam/image_array']
    # モデルの出力データとなる項目
    y_keys = ['user/angle', 'user/throttle']

    # トレーニング後モデルファイルとして保管するパスをフルパス化
    new_model_path = os.path.expanduser(new_model_path)

    # トレーニング後モデルファイルとして保管するパスをフルパス化
    kl = KerasLinear()
    # ファインチューニングを行う場合は base_model_path にベースモデルファイルパスが指定されている
    if base_model_path is not None:
        # ベースモデルファイルパスをフルパス化
        base_model_path = os.path.expanduser(base_model_path)
        # ベースモデルファイルを読み込む
        kl.load(base_model_path)

    print('tub_names', tub_names)
    # 引数tub_names 指定がない場合
    if not tub_names:
        # config.py 上に指定されたデータファイルパスを使用
        tub_names = os.path.join(cfg.DATA_PATH, '*')
    # Tub データ群をあらわすオブジェクトを生成
    tubgroup = TubGroup(tub_names)
    # トレーニングデータGenerator、評価データGeneratorを生成
    train_gen, val_gen = tubgroup.get_train_val_gen(X_keys, y_keys,
                                                    batch_size=cfg.BATCH_SIZE,
                                                    train_frac=cfg.TRAIN_TEST_SPLIT)

    # 全学習データ件数を取得
    total_records = len(tubgroup.df)
    # トレーニングデータ件数の取得
    total_train = int(total_records * cfg.TRAIN_TEST_SPLIT)
    # 評価データ件数の取得
    total_val = total_records - total_train
    print('train: %d, validation: %d' % (total_train, total_val))
    # 1epochごとのステップ数の取得
    steps_per_epoch = total_train // cfg.BATCH_SIZE
    print('steps_per_epoch', steps_per_epoch)

    # トレーニングの開始
    kl.train(train_gen,
             val_gen,
             saved_model_path=new_model_path,
             steps=steps_per_epoch,
             train_split=cfg.TRAIN_TEST_SPLIT)

# 本ファイル自体が実行された場合
if __name__ == '__main__':
    # 引数処理
    args = docopt(__doc__)
    cfg = dk.load_config()

    # 引数として 'drive' が指定された場合
    if args['drive']:
        # 【手動・自動）運転を開始する
        drive(cfg, model_path=args['--model'], use_joystick=args['--js'], use_chaos=args['--chaos'])

    # 引数として 'drive' が指定されず、かわりに'train'が指定された場合
    elif args['train']:
        tub = args['--tub']
        new_model_path = args['--model']
        base_model_path = args['--base_model']
        cache = not args['--no_cache']
        # トレーニングを開始する
        train(cfg, tub, new_model_path, base_model_path)





