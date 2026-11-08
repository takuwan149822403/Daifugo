# 大富豪 · Emerald Table

Python標準ライブラリとpygameだけで遊べる、プレイヤー1人＋CPU3人の大富豪です。

## 起動

ビルド後のLinux実行ファイルは `obj/Daifugo` です。ファイルを開くか、ターミナルで `./obj/Daifugo` を実行してください。画像と日本語フォントも実行ファイルに同梱します。`obj/` は生成物なのでGitには含めません。

ソースから起動する場合はPython 3.10以上（動作確認済みは3.13）とpygameを用意します。以下はPython 3.13を使う例です。

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/main.py
```

## 操作

- スタート画面の「ゲームスタート」で開始。初回の身分はランダムです。
- 開始前の交換では、大富豪／富豪なら渡すカードをクリックして選び「決定」。貧民／大貧民なら強いカードが自動で選ばれるので「交換して開始」で確認します。
- 自分の番は出せる札が黄色い枠になります。マウスを重ねるかクリックして、ポップアップから出す組み合わせを選びます。候補が多い場合は前へ／次へ、またはマウスホイールで切り替えます。
- 出さない場合は「パス」。場が空のときはパスできません。
- 7渡しは渡す札を選び「決定」。受け取る相手は次の未上がりのプレイヤーです。
- 右上「役確認」で説明画面へ。「戻る」で対戦へ戻ります。説明を見ている間、ゲームの進行と表示時間は停止します。
- F11で全画面の切り替え。Escで説明画面から戻る、またはカード出しをキャンセルできます。
- 3人目の上がりでゲーム終了。再戦では前回の順位を身分として使用します。

## 採用ルール

54枚（52枚＋ジョーカー2枚）を配ります。通常の強さは3、4、…、K、A、2、ジョーカーの順。大貧民から開始し、あなた→2P→3P→4Pの順で巡回します。

単独札、同じ数字の2〜4枚組が出せます。ジョーカーは同じ数字の代用にできます。場には直前と同じ枚数で、より強い組を出します。ジョーカーだけの組は最強です。パスした人は場が流れるまで参加できません。全員がパスすると最後に出した人から再開し、その人が上がっていれば次の未上がりの人から開始します。

- **8切り**：実際の8を含む組で場をリセットし、出した人が続けて出します。
- **7渡し**：実際の7の枚数だけ、次の未上がりの人へ好きな手札を渡します。残り手札が足りなければ残りの全札を渡します。渡した結果手札が空になった場合も上がりです。
- **革命**：同じ数字の4枚（ジョーカー代用可）で強さが反転します。次の革命で元に戻ります。
- **イレブンバック**：実際のJを含む組を出すたびに強さが反転し、場が流れると解除します。革命と重なった場合は通常順になります。
- **スペード3**：単独ジョーカーに対してのみ出せ、出すと場をリセットします。革命中でも有効です。

階段、スート縛り、都落ち、反則上がりは採用しません。ジョーカーは革命・イレブンバック中も最強です。NPCは合法手とパスからランダムに判断し、交換・7渡しのカードもランダムに選びます。

開始前には大富豪と大貧民が2枚、富豪と貧民が1枚交換します。上位の人は自由に選択し、下位の人は強い順に渡します。交換時の強さは通常順です。ゲーム開始・終了の赤い文字は60FPSで120フレーム表示します。

## 構成

| ファイル | 役割 |
| --- | --- |
| `src/cards.py` | カード、山札、手札 |
| `src/players.py` | プレイヤー、ランダムに行動するNPC |
| `src/judge.py` | 合法手と役の判定 |
| `src/game.py` | 交換、ターン、7渡し、順位の管理 |
| `src/assets.py` | 分割済み画像の読み込み・拡縮・日本語フォント |
| `src/widgets.py` | ボタン、ポップアップ |
| `src/app.py` | 画面描画・マウス操作・メインループ |
| `src/main.py` | 起動入口 |
| `rebuild.sh` / `rebuild.desktop` | Linuxの再ビルド用ファイル |
| `rebuild.bat` | Windowsの再ビルド用ファイル |
| `rebuild.py` | 環境の準備・テスト・ビルド・起動確認の共通処理 |
| `build.py` | PyInstallerによる実行ファイルの作成 |

画像は `images/cards/`（52枚＋裏面）、`images/portraits/`（NPC12人）、`images/buttons/`（5個）に分割済みのPNGを置き、ゲームはそのまま読み込みます。カードの透過は保持しています。分割前の3画像は `images/old/` に保管し、実行時や実行ファイルのビルドには使いません。追加ジョーカーはpygameで描画します。

ファイル名と元画像上の切り出し位置は [画像素材の構成](images/README.md) を参照してください。

## 教材を学んだ後に読む

`../pygame` の教材に合わせ、`cards.py`・`judge.py`を中心に、通常のクラスと`__init__`、リスト、`for`・`if`で処理を追える書き方にしています。

[教材との対応・ソースを読む順番・追加知識](docs/learning_guide.md)を参照してください。組み合わせを選ぶ`combinations`などの補足と、画面を使わず判定を試す例も載せています。

## 検証と再ビルド

コマンドに慣れていない場合は、プロジェクト直下の再ビルド用ファイルを実行してください。

| 環境 | 実行するファイル | 完成品 |
| --- | --- | --- |
| Ubuntu / Linux | `rebuild.sh` を右クリックして「プログラムとして実行」。ランチャーに対応する環境では `rebuild.desktop` も使用可 | `obj/Daifugo` |
| Windows | `rebuild.bat` をダブルクリック | `obj/Daifugo.exe` |

Ubuntuで実行を許可するよう求められた場合は、ファイルの「プロパティ」から実行権限を付けてください。`rebuild.desktop` に「起動を許可」が表示される場合は選択します。ランチャーと `rebuild.sh` は、このフォルダに置いたまま使用してください。ファイルマネージャーが実行に対応していない場合は、端末で `bash rebuild.sh` を実行できます。Windowsでは、エクスプローラーで拡張子を表示すると `.bat` を見つけやすくなります。

実行すると、使用する仮想環境を自動で選び、依存パッケージの準備 → テスト → ソースの起動確認 → ビルド → 完成品の起動確認を順番に実施します。途中で失敗すると停止し、結果は画面と `obj/rebuild.log` に残ります。ランチャーから開いた画面はEnterキー（Windowsは任意のキー）で閉じられます。起動確認は画面を表示せず3フレーム描画して終了します。

この作業環境では `.venv313` を優先します。別のPCではPython 3.13をインストールしてから実行してください。pygame入りの仮想環境がなければ `.venv-build` を自動作成します。初回のパッケージ導入にはインターネット接続が必要です。Windows版はWindows上、Linux版はLinux上で作成します。

以下は、各コマンドを手動で実行する場合の手順です。

この作業環境では、pygameとPyInstallerが入っているPython 3.13の仮想環境 `.venv313` を使います。プロジェクトのルートで、次のコマンドを実行して有効化してください。

```sh
source .venv313/bin/activate
```

仮想環境を終了するには `deactivate` を実行します。

以下は仮想環境を有効化した状態で実行します。別の環境で「起動」の手順から `.venv` を作成した場合は、代わりに `source .venv/bin/activate` を実行してください。pygameとPyInstallerは、ビルドに使う同じ仮想環境へインストールする必要があります。

```sh
# ゲーム本体の依存パッケージと、ビルド用のPyInstallerを用意します
python -m pip install -r requirements.txt pyinstaller
python -m unittest discover -s tests -v
# pygameで画面を3フレームだけ描画（GUIのない環境でも確認可）
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python src/main.py --smoke
python build.py
# ビルドした実行ファイルも3フレーム描画して確認します
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./obj/Daifugo --smoke
```

出力先は `obj/`。Windows版はWindows上のPython環境で同じ `build.py` を実行すると `obj/Daifugo.exe` になります。
日本語フォントの再配布ライセンスは `fonts/LICENSE.txt` を参照してください。

## GitHubへの登録

`PyGame/` をリポジトリのルートにし、`.gitignore` は `PyGame/.gitignore` に置きます。この1ファイルで配下全体に適用されるため、各サブフォルダにコピーする必要はありません。

| 登録するもの | 除外するもの |
| --- | --- |
| `src/`、`tests/`、`docs/`、README | `__pycache__/`、テストキャッシュ |
| `images/`（`old/` の原本も含む） | `.venv/`、`.venv313/`、`.venv-build/`、`.python-runtime/` |
| `fonts/` とそのライセンス | `obj/`、`build/`、`dist/`、`*.spec`、ログ |
| `requirements.txt`、`build.py`、`rebuild`で始まる各ファイル | `.env`、`.aws/`、`.ssh/`、`.codex/`、`.agents/`、エディターのローカル設定 |
| `.gitignore`、`.gitattributes` | OSの一時ファイル、`.cache/` |

`.gitattributes` は、Linux用スクリプトの改行をLF、Windows用 `.bat` の改行をCRLFに揃えます。

フォルダ全体を `git add .` しても、未追跡の除外対象は登録されません（[Git公式の説明](https://git-scm.com/docs/gitignore)）。GitHubのブラウザーにフォルダをドラッグしてアップロードする方法では `.gitignore` による除外が適用されないため、GitHub Desktopまたは下記のGitコマンドを使ってください。

Windows/macOSでGitHub Desktopを使う場合は、`PyGame/` をローカルリポジトリとして追加（未作成ならこの場所に作成）し、Changesで登録対象を確認してからコミット・Publish repositoryを実行できます（[既存リポジトリの追加方法](https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-a-repository-from-your-local-computer-to-github-desktop)）。

すでにGitに登録済みのファイルは `.gitignore` を追記しても除外されません。その場合は `git ls-files` で確認し、対象だけ `git rm --cached`（フォルダなら `git rm -r --cached`）で追跡を解除します。配布用実行ファイルはGitHub Releasesへ添付できます。

新しいリポジトリへ登録する場合の例です。GitHub側に空のリポジトリを作成し、URLを置き換えて実行してください。既存のGitリポジトリがある場合はその設定を使います。

```sh
git init -b main
git status --short
git add .
git diff --cached --stat
git commit -m "Add Emerald Table game"
git remote add origin https://github.com/<ユーザー名>/<リポジトリ名>.git
git push -u origin main
```
