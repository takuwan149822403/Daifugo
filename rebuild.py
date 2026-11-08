"""rebuild.sh / rebuild.batから呼ぶ、環境準備・検証・再ビルドの共通処理。"""
from pathlib import Path
import os
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def environment_python(folder):
    """OSに合わせて仮想環境内のPythonを探す。"""
    return folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def available(command, code):
    try:
        return subprocess.run(
            [*command, "-c", code], cwd=ROOT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def choose_python(run):
    # 今の作業環境では.venv313が動作確認済み。.venvはpygame未導入の場合がある。
    candidates = [environment_python(ROOT / name)
                  for name in (".venv313", ".venv-build", ".venv")]
    # pygameが入っている環境を優先し、PyInstallerは後から必要に応じて追加する。
    for candidate in candidates:
        if candidate.is_file() and available([str(candidate)], "import pygame"):
            return candidate

    managed = environment_python(ROOT / ".venv-build")
    supported = "import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] <= (3, 13)))"
    if managed.is_file() and available([str(managed)], supported):
        return managed

    # 新しいPCでは既存の環境を変更せず、専用の仮想環境を作る。
    commands = [[str(candidate)] for candidate in candidates if candidate.is_file()]
    if os.name == "nt" and shutil.which("py"):
        commands.append(["py", "-3.13"])
    if shutil.which("python3.13"):
        commands.append(["python3.13"])
    commands.append([sys.executable])
    for command in commands:
        if available(command, supported):
            run("再ビルド用の仮想環境を作成", [*command, "-m", "venv", str(ROOT / ".venv-build")])
            return managed
    raise RuntimeError("Python 3.13をインストールしてから、もう一度実行してください。")


def main():
    os.chdir(ROOT)
    output = ROOT / "obj"
    output.mkdir(exist_ok=True)
    log_path = output / "rebuild.log"
    environment = os.environ.copy()
    environment.update({
        "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1",
        "PYGAME_HIDE_SUPPORT_PROMPT": "1",
        "PIP_CACHE_DIR": str(ROOT / ".cache" / "pip"),
    })

    with log_path.open("w", encoding="utf-8") as log:
        def report(message):
            print(message, flush=True)
            log.write(message + "\n")
            log.flush()

        def run(label, command, *, smoke=False):
            report("\n--- " + label + " ---")
            child_environment = environment.copy()
            if smoke:
                child_environment.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
            with subprocess.Popen(
                [str(part) for part in command], cwd=ROOT, env=child_environment,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            ) as process:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                log.flush()
                if process.wait():
                    raise RuntimeError(label + "に失敗しました。以降の処理は実行しません。")

        try:
            report("大富豪の再ビルドを開始します。初回のパッケージ導入にはインターネット接続が必要です。")
            python = choose_python(run)
            report("使用するPython: " + str(python))
            run("依存パッケージの準備", [python, "-m", "pip", "install", "--disable-pip-version-check",
                                     "-r", ROOT / "requirements.txt", "pyinstaller"])
            # テストがpygame不足でスキップされてしまう前に、実際にimportできることを確認する。
            run("必須パッケージの確認", [python, "-c", "import pygame, PyInstaller"])
            run("テスト", [python, "-m", "unittest", "discover", "-s", "tests", "-v"])
            run("ソースの起動確認", [python, ROOT / "src" / "main.py", "--smoke"], smoke=True)
            run("実行ファイルの作成", [python, ROOT / "build.py"])
            executable = output / ("Daifugo.exe" if os.name == "nt" else "Daifugo")
            run("完成した実行ファイルの起動確認", [executable, "--smoke"], smoke=True)
            report("\n完了しました: " + str(executable))
            report("ログ: " + str(log_path))
            return 0
        except (OSError, RuntimeError) as error:
            report("\nエラー: " + str(error))
            report("ログ: " + str(log_path))
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
