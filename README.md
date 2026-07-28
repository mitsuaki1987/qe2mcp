# qe2mcp - Quantum ESPRESSO to MCP JSON Converter

QE (Quantum ESPRESSO) の出力ファイル（例：`AgAl-1.out`）を読み込み、MCPサーバー用のJSON形式に変換するツールです。

## 機能

- **QE出力ファイルのパース**: Quantum ESPRESSO pw.x（v7.x）の vc-relax 計算出力を対応
- **単一・複数ファイル処理**: 単一ファイルまたはバッチモードで複数ファイルを処理可能
- **ワイルドカード対応**: `*.out` などのグロブパターンで複数ファイルを指定可能
- **構造化データの抽出**:
  - プログラム情報（バージョン、計算タイプ）
  - 計算パラメータ（カットオフ、交換相関汎関数など）
  - 初期構造と最終構造
  - イオンステップごとのエネルギー、力、磁気モーメント
  - タイミング情報
- **磁気モーメント情報**:
  - 全磁気モーメント（3次元ベクトル）と絶対磁気モーメント
  - **各原子の磁化情報**（3次元ベクトル、電荷あたりの磁化、位置、電荷）
- **JSON形式での出力**: MCPサーバーとの連携に適した形式

## インストール

```bash
pip install -e .
```

## 使用方法

### コマンドライン

#### 単一ファイル処理
```bash
# 基本的な使用方法
python3 main.py AgAl-1.out

# 出力ファイルを指定する場合
python3 main.py AgAl-1.out -o output.json

# 詳細出力
python3 main.py AgAl-1.out -v
```

#### 複数ファイル処理
```bash
# 複数ファイルを明示的に指定
python3 main.py AgAl-1.out CuSn-2.out

# ワイルドカードパターン
python3 main.py *.out

# 複数ファイルを出力ディレクトリに保存
python3 main.py *.out -o json_output/

# 複数ファイル処理（詳細出力）
python3 main.py AgAl-1.out CuSn-2.out -v
```

### Pythonスクリプトでの使用

```python
from parser import QEParser

# パーサーを作成
parser = QEParser()

# QE出力ファイルをパース
data = parser.parse('AgAl-1.out')

# JSONとして保存
parser.save_json('agal.json')

# JSONストリングとして取得
json_str = parser.to_json()
```

## 出力JSON構造

```json
{
  "program": {
    "version": "7.5",
    "git_revision": "...",
    "calculation": "vc-relax",
    "completed": true
  },
  "input": {
    "nat": 6,
    "ntyp": 4,
    "nbnd": 88,
    "nelec": 74.0,
    "ecutwfc_ry": 65.0,
    "ecutrho_ry": 780.0,
    "xc": "PBESOL",
    "fft_grid": [50, 50, 64],
    "smooth_grid": [50, 50, 64]
  },
  "structure_initial": {
    "alat_bohr": 8.3461,
    "volume_bohr3": 737.849,
    "cell_parameters": [[...], [...], [...]],
    "atomic_positions": [...],
    "magnetization": {"x": 0.0, "y": 0.0, "z": 0.0},
    "abs_magnetization": 9.42,
    "atomic_magnetizations": {
      "1": {
        "position": [0.0, 0.0, 0.6346],
        "charge": 13.4698,
        "magnetization": {"x": 0.0, "y": 0.0, "z": -6.571554},
        "magnetization_per_charge": {"x": 0.0, "y": 0.0, "z": -0.487872}
      },
      ...
    }
  },
  "ionic_steps": [
    {
      "index": 0,
      "energy_ry": -1073.44271308,
      "forces": {
        "1": [0.001, 0.002, 0.003],
        ...
      },
      "total_force": 0.01234,
      "magnetization": {"x": 0.0, "y": 0.0, "z": 0.0},
      "abs_magnetization": 9.42,
      "atomic_magnetizations": {
        "1": {
          "position": [0.0, 0.0, 0.6346],
          "charge": 13.4698,
          "magnetization": {"x": 0.0, "y": 0.0, "z": -6.571554},
          "magnetization_per_charge": {"x": 0.0, "y": 0.0, "z": -0.487872}
        },
        ...
      }
    },
    ...
  ],
  "structure_final": {
    "cell_parameters": [[...], [...], [...]],
    "atomic_positions": [...],
    "magnetization": {"x": 0.0, "y": 0.0, "z": 0.0},
    "abs_magnetization": 8.28,
    "atomic_magnetizations": {
      "1": {
        "position": [0.0, 0.0, 0.6366],
        "charge": 13.3378,
        "magnetization": {"x": 0.0, "y": 0.0, "z": -3.704097},
        "magnetization_per_charge": {"x": 0.0, "y": 0.0, "z": -0.277715}
      },
      ...
    }
  },
  "timing": {
    "cpu_wall": "..."
  }
}
```

## 対応フォーマット

- **Quantum ESPRESSO**: v7.x
- **計算タイプ**: vc-relax（体積と原子位置の構造最適化）
- **ファイルフォーマット**: テキスト形式の標準出力

## サンプル実行

### 単一ファイル処理
テストデータ (`AgAl-1.out`) を使用:

```bash
python3 main.py AgAl-1.out -v
```

出力:
```
Processing 1 file(s)...

📖 Reading: AgAl-1.out
✓ JSON saved to AgAl-1.json
✅ Successfully parsed: AgAl-1.out
   - Program: 7.5
   - Atoms: 6
   - Ionic steps: 10
   - Completed: True
```

### 複数ファイル処理
複数ファイルをバッチ処理:

```bash
python3 main.py AgAl-1.out CuSn-2.out -v
```

出力ディレクトリに保存:

```bash
python3 main.py *.out -o json_output/
```

出力:
```
✓ JSON saved to json_output/AgAl-1.json
✓ AgAl-1.out → AgAl-1.json
✓ JSON saved to json_output/CuSn-2.json
✓ CuSn-2.out → CuSn-2.json

📊 Summary: 2/2 files processed successfully
```

## 構造

- `parser.py` - QEParserクラス: QE出力ファイルのパースロジック
- `regex.py` - 正規表現定義: ファイル解析用の各種パターン
- `main.py` - CLIスクリプト: コマンドラインインターフェース

## ライセンス

MIT License

## 作成者

Mitsuaki Kawamura
