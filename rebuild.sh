#!/usr/bin/env bash
# ダブルクリック用ランチャーと、ターミナルの両方から利用する。
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 1
# ファイルマネージャーからの実行時は、結果を読めるように端末を開く。
# CIなど画面のない自動実行では --no-pause を指定する。
if [[ ! -t 1 && "${1:-}" != "--no-pause" && "${1:-}" != "--pause" ]]; then
    for terminal in x-terminal-emulator konsole xterm; do
        if command -v "$terminal" >/dev/null 2>&1; then
            exec "$terminal" -e bash "$PWD/rebuild.sh" --pause
        fi
    done
    if command -v gnome-terminal >/dev/null 2>&1; then
        exec gnome-terminal -- bash "$PWD/rebuild.sh" --pause
    fi
    echo "端末から bash rebuild.sh --no-pause を実行してください。"
    exit 1
fi
export PYTHONUTF8=1
export PYTHONUNBUFFERED=1

rebuild_python=""
for candidate in .venv313/bin/python .venv-build/bin/python .venv/bin/python; do
    if [[ -x "$candidate" ]] && "$candidate" -c 'import sys' >/dev/null 2>&1; then
        rebuild_python="$candidate"
        break
    fi
done
if [[ -z "$rebuild_python" ]]; then
    for candidate in python3.13 python3; do
        if command -v "$candidate" >/dev/null 2>&1; then
            rebuild_python="$candidate"
            break
        fi
    done
fi

if [[ -n "$rebuild_python" ]]; then
    "$rebuild_python" -u rebuild.py
    rebuild_status=$?
else
    echo "Python 3.13をインストールしてから、もう一度実行してください。"
    rebuild_status=1
fi

if [[ "${1:-}" == "--pause" && -t 0 ]]; then
    read -r -p "Enterキーで閉じます。" || true
fi
exit "$rebuild_status"
