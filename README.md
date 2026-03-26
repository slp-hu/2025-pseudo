# CREST 複数人の対話音声データの仮名化

本リポジトリは、複数話者による対話音声データに対して、話者の匿名性を保ちながら音声を変換 (仮名化) するデモを提供します。
Google Colab 上で `.ipynb` を実行するだけで、環境構築から音声変換・可視化まで一通り試すことができます。

---

# DEMO

https://github.com/user-attachments/assets/e6a735fc-6b81-466f-a07b-e596cf9b22f4

---

# Requirement

基本的にローカル環境構築は不要です。
**Google Colab の利用を前提**としています。

内部的には以下のようなライブラリを使用します (ノートブック内で自動インストールされます) ：

* Python 3.10+
* PyTorch
* librosa
* numpy
* matplotlib
* scikit-learn
* umap-learn
* soundfile

---

# Installation

Google Colab を使用する場合、特別なインストールは不要です。
ノートブック内で自動的にセットアップされます。

---

# Usage

## ✔ 最も簡単な使い方 (推奨) 

1. 本リポジトリをクローン

```bash
git clone https://github.com/slp-hu/2025-pseudo.git
```

2. Google Colab を開く

3. `crest_demo_1.ipynb` をアップロード or Drive から開く

4. 上から順にセルを実行

---

## ✔ ファイル入力 (重要) 

ノートブック実行中に、**ファイルチューザーが表示されます**

* `.wav` ファイルを複数選択してください
* **1ファイル = 1話者** として扱われます

例：

```
speaker1.wav
speaker2.wav
speaker3.wav
speaker4.wav
```

---

## ✔ 出力内容

実行後、以下が確認できます：

### 1. 合体音声

* 元の対話音声 (全話者) 
* 仮名化後の対話音声 (全話者) 

### 2. 各話者ごとの音声

* 元音声
* 仮名化後音声

→ UI 上で個別に再生可能

---

### 3. x-vector 可視化

話者特徴量 (x-vector) の変換関係を2次元で可視化します。

* ○：元話者
* ★：仮名化後話者
* 線：対応関係
* 薄いグレー：pool (候補話者群)

---

## ✔ 入力人数について

* **制限なし (理論上) **
* アップロードした wav の数だけ処理されます

※ ただし Colab の都合上、4〜8人程度が現実的です

---

## ✔ 出力ディレクトリ

```
outputs_seedvc/
├── speaker0/
├── speaker1/
├── speaker2/
└── ...
```

各フォルダに変換後音声が保存されます。

---

# Note

* 入力は モノラル wav 推奨
* サンプリングレートは自動変換されます
* 長時間音声は処理に時間がかかります
* GPU 使用を推奨 (Colab: Runtime → GPU) 

---

# Author

* Aoi Ito

  * Hosei Univ.
  * [24t0002@cis.k.hosei.ac.jp](mailto:24t0002@cis.k.hosei.ac.jp)

---

# License

本プロジェクトのライセンスは、使用している各種モデル・ライブラリに準拠します。
詳細は各リポジトリを参照してください。

