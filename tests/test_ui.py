"""pygameのダミー画面で実際のクリックと画面遷移を確認。"""
import os
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

# 環境変数でpygameの描画・音声をダミーにし、実際のモニターや音声機器なしで確認する。
# setdefaultはすでに指定がある場合には上書きしない。
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    # pygameがないPythonでも、ルールのテストだけなら実行できるようにimport失敗を扱う。
    import pygame
    from app import Application
    from cards import Card, Hand
    from game import Game
except ImportError:
    pygame = None


@unittest.skipIf(pygame is None, "pygameのあるPython環境で実行してください")
class ScreenTests(unittest.TestCase):
    # skipIfは条件がTrueならこのクラスのテストをスキップするデコレーター。
    # テストが実行される場合は、描画とクリックに本体のApplicationをそのまま使う。
    def setUp(self):
        # seedを固定して、画面操作のテストで毎回同じ対戦から始める。
        self.app = Application(8)

    def tearDown(self):
        # tearDownは各テストの後に実行される。次のテストへ表示機能の状態を残さない。
        pygame.quit()

    def click(self, rect):
        # 本体のclickは実際のウィンドウ座標を受け取る。
        # テストでは仮想座標の矩形中心を倍率・余白で変換してクリックする。
        self.app.click((self.app.viewport.x + rect.centerx * self.app.scale,
                        self.app.viewport.y + rect.centery * self.app.scale))
        self.app.draw()
        # 操作後に描画して、次の操作用のボタン・候補の当たり判定を最新にする。

    def button(self, action):
        # 指定した動作名の有効なボタンを探し、中心をクリックする補助関数。
        self.app.draw()
        item = next(b for b in self.app.buttons if b.action == action and b.enabled)
        self.click(item.rect)

    def resolve_exchange(self):
        # 交換が終わるまでポップアップを操作する。上位なら札を選び、下位なら確認だけ。
        while self.app.game.phase == "exchange":
            self.app.draw()
            popup = self.app.popup
            if popup.kind == "exchange":
                for _ in range(popup.count):
                    # まだ選んでいない札を探し、必要枚数だけクリックする。
                    rect, _ = next((r, c) for r, c in self.app.option_hits if c not in popup.selected)
                    self.click(rect)
            self.button("confirm")

    def test_all_four_titles_exchange_in_popup(self):
        # 自分の身分を大富豪→富豪→貧民→大貧民と変えて、全ての交換画面を確認する。
        for title_position in range(4):
            order = [1, 2, 3]
            order.insert(title_position, 0)
            # 身分順の指定位置へ自分（席0）を挿入し、その身分になる対戦を作る。
            self.app.game = Game(order, random.Random(3))
            self.app.screen = "game"
            self.app.popup = None
            self.app.sync_game()
            before = [len(p.hand) for p in self.app.game.players]
            self.resolve_exchange()
            self.assertEqual(self.app.game.phase, "playing")
            self.assertEqual(self.app.banner_frames, 120)
            self.assertEqual(before, [len(p.hand) for p in self.app.game.players])
            # 交換は同じ枚数を渡し合うので、各人の手札枚数は交換前と同じはず。

    def test_hover_lists_combinations_and_cancel(self):
        # 5のペアとジョーカーを用意し、マウスを重ねた札を含む複数候補が出るか確認。
        self.app.new_game()
        self.resolve_exchange()
        self.app.banner_frames = 0
        self.app.game.turn = 0
        self.app.game.players[0].hand = Hand([Card(0, 5), Card(1, 5), Card(0, 14)])
        self.app.draw()
        rect, card, _ = self.app.card_hits[0]
        with patch.object(self.app, "mouse_position", return_value=rect.center):
            # patch.objectでマウス座標の戻り値を一時的に固定する。
            # withの範囲を抜けると元のメソッドへ戻るので、他のテストには影響しない。
            for _ in range(10):
                self.app.update()
            self.assertEqual(self.app.popup.kind, "play")
            self.assertTrue(all(card in m.cards for m in self.app.popup.moves))
            self.assertTrue(any(m.count == 2 for m in self.app.popup.moves))
        self.button("cancel")
        # 同じ札へ重ねたままでも、キャンセル後にはすぐ再表示しないことを確認する。
        with patch.object(self.app, "mouse_position", return_value=rect.center):
            for _ in range(30):
                self.app.update()
            self.assertIsNone(self.app.popup)

    def test_rules_pause_and_resize_hit_positions(self):
        # 800×600に縮めても役確認ボタンをクリックでき、説明を見ている間は手札が変わらない。
        self.app.new_game()
        self.resolve_exchange()
        self.app.banner_frames = 0
        self.app.window = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        self.app.layout()
        self.button("rules")
        self.assertEqual(self.app.screen, "rules")
        snapshot = [list(p.hand.cards) for p in self.app.game.players]
        # listで手札をコピーし、「その時点の状態」を残す。同じリストの参照だと変化を見逃す。
        for _ in range(100):
            self.app.update()
        self.assertEqual(snapshot, [list(p.hand.cards) for p in self.app.game.players])
        self.button("back")
        self.assertEqual(self.app.screen, "game")
        self.assertTrue(all(pygame.Rect(0, 0, 1280, 800).contains(r) for r, _, _ in self.app.card_hits))
        # allは全条件がTrueならTrue。全ての手札が仮想画面内に収まっているか確認する。

    def test_banner_lasts_120_rendered_frames(self):
        # 本体のメインループを120フレーム動かし、赤文字の時間だけが進むことを確認する。
        self.app.new_game()
        self.resolve_exchange()
        snapshot = [list(p.hand.cards) for p in self.app.game.players]
        self.app.run(max_frames=120)
        self.assertEqual(self.app.banner_frames, 0)
        self.assertEqual(snapshot, [list(p.hand.cards) for p in self.app.game.players])

    def test_full_game_via_clicks_then_rematch(self):
        # スタートから終了・再戦まで、本体のクリック処理と更新処理を使って進める。
        self.button("start")
        self.resolve_exchange()
        self.app.banner_frames = 0
        for _ in range(1000):
            # 終わらない場合にもテストを止められるよう、操作回数に上限を付ける。
            self.app.draw()
            game = self.app.game
            if game.phase == "finished":
                break
            if self.app.popup and self.app.popup.kind == "gift":
                # 人間の7渡しは画面から札を選択し、決定ボタンで確定する。
                popup = self.app.popup
                for _ in range(popup.count):
                    rect, _ = next((r, c) for r, c in self.app.option_hits if c not in popup.selected)
                    self.click(rect)
                self.button("confirm")
            elif game.phase == "playing" and game.turn == 0:
                # 出せる札があれば、その札の候補画面から最初の組を選ぶ。なければパスする。
                legal = [rect for rect, _, playable in self.app.card_hits if playable]
                if legal:
                    self.click(legal[0])
                    self.assertEqual(self.app.popup.kind, "play")
                    self.click(self.app.option_hits[0][0])
                else:
                    self.button("pass")
            else:
                # CPUの操作は通常の24フレーム待ちを経て進める。
                for _ in range(24):
                    self.app.update()
        else:
            # breakで終了できなかった場合だけ、対戦未終了として失敗を報告する。
            self.fail("UI操作の対戦が終了しません")
        order = list(self.app.game.finish_order)
        self.assertEqual(sorted(order), [0, 1, 2, 3])
        self.assertEqual(self.app.banner, "ゲーム終了")
        self.assertEqual(self.app.banner_frames, 120)
        self.app.banner_frames = 0
        # ここでは再戦への遷移を確認するため、終了表示の待ち時間を省いて結果ボタンへ進める。
        self.button("rematch")
        self.assertEqual(self.app.game.title_order, order)


if __name__ == "__main__":
    # 単独実行時のテスト入口。discoverによる実行ではこのブロックは呼ばれない。
    unittest.main()
