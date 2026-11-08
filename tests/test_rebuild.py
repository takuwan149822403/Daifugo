"""依存パッケージや検証の失敗時に、既存の実行ファイルを上書きしない。"""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rebuild


class RebuildTests(unittest.TestCase):
    def test_prebuild_failure_preserves_existing_executable(self):
        # pip成功でもimportに失敗する場合、テスト失敗、ソース起動失敗を確認する。
        for failed_step in (1, 2, 3):
            with self.subTest(failed_step=failed_step), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "obj").mkdir()
                executable = root / "obj" / "Daifugo"
                executable.write_bytes(b"previous working build")
                processes = []
                for index in range(failed_step + 1):
                    process = MagicMock()
                    process.__enter__.return_value = process
                    process.stdout = io.StringIO("verification output\n")
                    process.wait.return_value = 1 if index == failed_step else 0
                    processes.append(process)

                # mainは作業フォルダを変えるので、削除前に元へ戻す。
                previous = Path.cwd()
                try:
                    with patch.object(rebuild, "ROOT", root), \
                         patch.object(rebuild, "choose_python", return_value=Path(sys.executable)), \
                         patch.object(rebuild.subprocess, "Popen", side_effect=processes) as launch, \
                         contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(rebuild.main(), 1)
                    self.assertEqual(launch.call_count, failed_step + 1)
                    self.assertEqual(executable.read_bytes(), b"previous working build")
                    self.assertIn("以降の処理は実行しません", (root / "obj" / "rebuild.log").read_text(encoding="utf-8"))
                    self.assertFalse(any("build.py" in str(call.args[0]) for call in launch.call_args_list))
                finally:
                    rebuild.os.chdir(previous)
