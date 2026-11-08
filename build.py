"""実行ファイルの作成。開発用のPyInstallerのみ追加で必要。"""
from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import sys

# このファイルはゲーム本体ではなく、配布用実行ファイルを作るための開発用スクリプト。
# 実行中のPythonからPyInstallerを呼び、ソース・画像・日本語フォントをまとめる。
# 必須パッケージがない環境では、起動できない実行ファイルで上書きする前に止める。
missing = [name for name in ("pygame", "PyInstaller")
           if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit(
        "ビルドに必要なパッケージがありません: " + ", ".join(missing)
        + f'\n使用中のPython: {sys.executable}'
        + f'\n同じ環境にインストールしてください:\n"{sys.executable}" -m pip install -r requirements.txt pyinstaller'
        + "\n自動で環境を準備する場合: rebuild.sh（Linux）またはrebuild.bat（Windows）を実行してください。"
    )
root = Path(__file__).resolve().parent
font_dir = root / "fonts"
font_dir.mkdir(exist_ok=True)
# exist_ok=Trueなら、フォルダがすでにある場合もエラーにしない。
font_target = font_dir / "NotoSansCJK-Regular.ttc"
if not font_target.exists():
    # フォントがまだ同梱されていなければ、このLinux環境のフォントをコピーする。
    candidates = [Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                  Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc")]
    for font in candidates:
        if font.exists():
            shutil.copy2(font, font_target)
            # copy2はファイルの内容に加えて、更新時刻などの情報もコピーする。
            break
if not font_target.exists():
    # 日本語が表示できない配布物を作らないため、フォントが見つからなければ終了する。
    raise SystemExit("日本語フォントをfonts/NotoSansCJK-Regular.ttcに配置してください。")
# コマンドを文字列1本ではなく引数のリストとして作る。空白を含むパスも正しく扱える。
# sys.executableは「このスクリプトを実行しているPython」のパス。
# --onefileは1本の実行ファイル、--windowedは対応OSでコンソールを表示しない指定。
# --distpathは完成品、--workpathは中間生成物、--specpathはビルド設定の出力先。
# --pathsでsrcをimport対象に加え、--add-dataで画像とフォントを同梱する。
command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
           "--windowed", "--name", "Daifugo", "--distpath", str(root / "obj"),
           "--workpath", str(root / "obj" / "build"), "--specpath", str(root / "obj"),
           "--paths", str(root / "src"), "--add-data", str(font_dir) + ":fonts"]
# 分割済みPNGと背景だけを同梱し、保管用のimages/oldは実行ファイルに含めない。
for image in sorted((root / "images").rglob("*.png")):
    relative = image.relative_to(root / "images")
    if "old" in relative.parts:
        continue
    destination = image.parent.relative_to(root).as_posix()
    command.extend(["--add-data", str(image) + ":" + destination])
command.append(str(root / "src" / "main.py"))
environment = os.environ.copy()
# os.environは環境変数。コピー側を変更し、ビルド用キャッシュもobj以下へまとめる。
environment["PYINSTALLER_CONFIG_DIR"] = str(root / "obj" / "build" / "cache")
# subprocess.runで外部コマンドを起動し、完了を待つ。
# cwdは作業フォルダ、envは渡す環境変数。check=Trueなら失敗時に例外で知らせる。
subprocess.run(command, cwd=root, env=environment, check=True)
