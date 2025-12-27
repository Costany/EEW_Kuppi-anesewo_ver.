# EEW_Kuppi-anesewo_ver.

**地震の到達時間シミュレーション** の Python/Pygame 復刻版

原作 1 Scratch プロジェクト: https://scratch.mit.edu/projects/525151751/
原作 2 Turbowarp 強震モニタ風地震シュミレーション v1.10.1 : https://turbowarp.org/1220818872?fps=250&clones=Infinity&offscreen&hqpen

使用 Geojson： https://github.com/0Quake/JMA_Region/tree/main

## 概要

日本における地震波（P 波・S 波）の伝播をリアルタイムでシミュレーションし、JMA（気象庁）震度階級を可視化するインタラクティブなシミュレーターです。

## 機能

- P 波・S 波の伝播アニメーション
- JMA 震度計算（距離減衰式）
- 震央地名の自動判定
- 站点モード / 区域モード切替
- マウスホイールによる地図ズーム
- 震度に応じた色分け表示
- EEW（緊急地震速報）追標システム
- 1748箇所の観測站点データ
- 震度別音声アラート
- 自動カメラ追跡（站点追跡 / P波追跡 / S波追跡）
- 多震源シミュレーション対応

## 操作方法

### 設定モード
- **左クリック**: 震央を設置
- **←→**: マグニチュード調整（M1.0〜M9.5）
- **↑↓**: 深度調整（0〜700km）
- **Enter**: シミュレーション開始
- **Tab**: 単震源/多震源モード切替
- **R**: 初期位置にリセット

### シミュレーション中
- **Space**: 一時停止/再開
- **R**: 設定モードに戻る
- **T**: 表示モード切替（站点/区域）
- **S**: 履歴データをエクスポート
- **+/-**: 再生速度調整
- **マウスホイール**: 地図ズーム（自動追跡を解除）

### 多震源モード
- **ステップ1**: 左クリックで断層線を描画、Enter で確定
- **ステップ2**: 左クリックで震源を配置、Enter で確定
- **ステップ3**: 左クリックで開始点を選択、D で破裂方向切替、Enter で開始
- **C/V**: 破裂速度調整

## インストール

### 必要条件
- Python 3.8 以上
- Cairo ライブラリ（SVG レンダリング用）

### Windows の場合

1. **GTK3 Runtime のインストール**（Cairo 依存）
   - [GTK3 Runtime](https://github.com/nickvidal/gtk-win64/releases) からダウンロード
   - または [MSYS2](https://www.msys2.org/) で `pacman -S mingw-w64-x86_64-gtk3` を実行

2. **Python パッケージのインストール**
   ```bash
   cd earthquake_sim
   pip install -r requirements.txt
   ```

3. **実行**
   ```bash
   python main.py
   ```

### macOS の場合

```bash
# Homebrew で Cairo をインストール
brew install cairo

# Python パッケージのインストール
cd earthquake_sim
pip install -r requirements.txt

# 実行
python main.py
```

### Linux の場合

```bash
# Cairo ライブラリのインストール（Ubuntu/Debian）
sudo apt-get install libcairo2-dev

# Python パッケージのインストール
cd earthquake_sim
pip install -r requirements.txt

# 実行
python main.py
```

## 必要なライブラリ

- pygame >= 2.0.0
- numpy >= 1.20.0
- cairosvg >= 2.5.0

## プロジェクト構成

```
earthquake_sim/
├── main.py              # メインプログラム
├── config.py            # 設定（波速、画面サイズ等）
├── earthquake.py        # 地震モデル
├── intensity.py         # JMA震度計算
├── epicenter.py         # 震央地名検索
├── station_manager.py   # 観測站点管理（1748箇所）
├── eew_tracker.py       # EEW追標システム
├── eew_alert.py         # EEW警報UI
├── sound_manager.py     # 音声管理
├── assets/              # SVGアイコン、音声ファイル
└── data/                # 站点・区域データ
```

## ライセンス

MIT License
