"""ルール・交換・順位の境界条件を標準unittestで確認。"""
import random
from itertools import combinations
import sys
from pathlib import Path
import unittest

# テストはtestsフォルダにあるため、兄弟フォルダのsrcをimportの検索先へ加える。
# このファイルの親の親がプロジェクトのルート。insert(0, ...)で検索先の先頭へ入れる。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cards import Card, Hand
from game import Game
from judge import Judge


class RuleTests(unittest.TestCase):
    # unittest.TestCaseを継承すると、assertEqualなどの検証機能を使える。
    # test_で始まるメソッドがテストとして自動実行され、条件と違う結果なら失敗になる。
    def setUp(self):
        # setUpは各テストの直前に呼ばれ、別のテストの状態が混ざらないように準備する。
        self.judge = Judge()

    def move(self, rank, suits=(0,)):
        # テスト用の組を簡単に作る補助関数。数字とスート一覧からCardを作る。
        # (0,)は要素が1つのタプル。末尾のカンマがない(0)はただの整数になる。
        return self.judge.make_move([Card(s, rank) for s in suits])

    def game(self, hands):
        # 指定した手札で、交換なし・自分のターンから始める小さなテスト用対戦を作る。
        game = Game(rng=random.Random(2))
        game.exchange_queue.clear()
        game.phase = "playing"
        game.turn = 0
        for player, cards in zip(game.players, hands):
            # zipでプレイヤーと対応する手札を1組ずつ取り出す。
            player.hand = Hand(cards)
        return game

    def choose(self, game, rank, count=1):
        # 合法手から指定の数字・枚数に一致する最初の組を探す。
        # 見つからなければnextが例外を出すので、予想した札を出せないテスト状況にも気付ける。
        return next(m for m in game.legal_moves() if m.rank == rank and m.count == count)

    def test_strength_and_reversal(self):
        # Aと2の特別な強さ、逆順時の比較、枚数違いの禁止を確認。
        # assertTrueはTrueを、assertFalseはFalseを期待する検証。
        self.assertTrue(self.judge.beats(self.move(2), self.move(1)))
        self.assertTrue(self.judge.beats(self.move(1), self.move(13)))
        self.assertFalse(self.judge.beats(self.move(3), self.move(2)))
        self.assertTrue(self.judge.beats(self.move(3), self.move(2), True))
        self.assertFalse(self.judge.beats(self.move(4, (0, 1)), self.move(3)))

    def test_joker_and_spade_three(self):
        # ジョーカーは逆順でも最強だが、単独スペード3だけは返せることを確認。
        # ハート3や2枚組では同じ特例が働かないことも確認する。
        joker = self.move(14)
        self.assertTrue(self.judge.beats(joker, self.move(2), True))
        self.assertTrue(self.judge.beats(self.move(3), joker))
        self.assertTrue(self.judge.beats(self.move(3), joker, True))
        self.assertFalse(self.judge.beats(self.move(3, (1,)), joker))
        self.assertFalse(self.judge.beats(self.move(3, (0, 1)), self.move(14, (0, 1))))

    def test_joker_substitutions_and_no_duplicates(self):
        # ジョーカー2枚を代用した4枚組が候補にあり、同じ候補は重複しないことを確認。
        hand = Hand([Card(0, 6), Card(1, 6), Card(0, 14), Card(1, 14)])
        moves = self.judge.legal_moves(hand)
        for index, move in enumerate(moves):
            self.assertNotIn(move, moves[:index])
        self.assertTrue(any(m.count == 4 and m.rank == 6 for m in moves))
        self.assertIsNone(self.judge.make_move([Card(0, 3), Card(1, 4)]))
        # assertIsNoneは「結果がNone」を期待する。数字の違う組は無効である。

    def test_invalid_move_shapes(self):
        self.assertIsNone(self.judge.make_move([]))
        self.assertIsNone(self.judge.make_move([Card(0, 3), Card(0, 3)]))
        self.assertIsNone(self.judge.make_move(
            [Card(s, 6) for s in range(4)] + [Card(0, 14)]))

    def test_legal_moves_match_all_hand_combinations(self):
        # 数字ごとに分ける候補生成に、漏れや重複がないか全ての選び方と照合する。
        hand = Hand([Card(0, 3), Card(0, 6), Card(1, 6), Card(2, 6),
                     Card(3, 6), Card(0, 2), Card(0, 14), Card(1, 14)])
        tops = [None, self.move(5), self.move(5, (0, 1)),
                self.move(5, (0, 1, 2)), self.move(5, (0, 1, 2, 3)),
                self.move(14), self.move(14, (0, 1))]
        for top in tops:
            for reversed_order in (False, True):
                expected = []
                for size in range(1, 5):
                    for cards in combinations(hand.cards, size):
                        move = self.judge.make_move(cards)
                        if move is not None and self.judge.beats(move, top, reversed_order):
                            expected.append(move)
                actual = self.judge.legal_moves(hand, top, reversed_order)
                # 候補内の札の順番には依存せず、どの札を出せるかを比較する。
                expected_keys = []
                for move in expected:
                    expected_keys.append(sorted((c.suit, c.rank) for c in move.cards))
                actual_keys = []
                for move in actual:
                    actual_keys.append(sorted((c.suit, c.rank) for c in move.cards))
                self.assertEqual(sorted(actual_keys), sorted(expected_keys))

    def test_exchange_uses_two_strongest(self):
        # 下位の手札をK・A・2・ジョーカーに固定し、交換で2とジョーカーを受け取るか確認。
        game = Game([0, 1, 2, 3], random.Random(1))
        game.players[0].hand = Hand([Card(0, 3), Card(0, 4), Card(0, 5)])
        game.players[3].hand = Hand([Card(0, 13), Card(0, 1), Card(0, 2), Card(0, 14)])
        game.exchange([Card(0, 3), Card(0, 4)])
        self.assertIn(Card(0, 14), game.players[0].hand.cards)
        # assertInは指定要素が一覧にあるか確認する。残るAも調べて交換枚数を確認する。
        self.assertIn(Card(0, 2), game.players[0].hand.cards)
        self.assertIn(Card(0, 1), game.players[3].hand.cards)

    def test_invalid_exchange_keeps_hands_unchanged(self):
        game = Game([0, 1, 2, 3], random.Random(1))
        own_card = game.players[0].hand.cards[0]
        other_card = game.players[1].hand.cards[0]
        before = [list(player.hand.cards) for player in game.players]
        queue = list(game.exchange_queue)
        for chosen in ([own_card], [own_card, own_card], [own_card, other_card]):
            with self.assertRaises(ValueError):
                game.exchange(chosen)
            self.assertEqual(before, [list(player.hand.cards) for player in game.players])
            self.assertEqual(queue, game.exchange_queue)

    def test_invalid_gift_keeps_hands_unchanged(self):
        game = self.game([[Card(0, 7), Card(1, 7), Card(0, 2), Card(0, 3)],
                          [Card(1, 4)], [Card(2, 5)], [Card(3, 6)]])
        game.play(self.choose(game, 7, 2))
        before = [list(player.hand.cards) for player in game.players]
        pending = game.pending_gift
        for chosen in ([Card(0, 2)], [Card(0, 2), Card(0, 2)], [Card(0, 2), Card(1, 4)]):
            with self.assertRaises(ValueError):
                game.give(chosen)
            self.assertEqual(before, [list(player.hand.cards) for player in game.players])
            self.assertEqual(pending, game.pending_gift)
            self.assertEqual(game.phase, "gift")

    def test_eight_clears_history_and_back(self):
        # 8切りで描画履歴、最新札、Jバックが消え、出した本人のターンになるか確認。
        game = self.game([[Card(0, 8), Card(0, 9)], [Card(1, 9)], [Card(2, 9)], [Card(3, 9)]])
        game.eleven_back = True
        game.play(self.choose(game, 8))
        self.assertEqual(game.history, [])
        self.assertIsNone(game.top)
        self.assertFalse(game.eleven_back)
        self.assertEqual(game.turn, 0)

    def test_revolution_and_j_back_cancel(self):
        # 4枚出しで逆順になり、Jバックが重なると通常順に戻ることを確認。
        # 場を流したあとにはJバックだけが消え、革命は残る。
        game = self.game([[Card(s, 6) for s in range(4)] + [Card(0, 12)],
                          [Card(0, 5), Card(1, 5), Card(2, 5), Card(3, 5), Card(1, 12)],
                          [Card(2, 12)], [Card(3, 12)]])
        game.play(self.choose(game, 6, 4))
        self.assertTrue(game.reversed_order)
        self.assertTrue(any(m.rank == 5 for m in game.legal_moves()))
        game.eleven_back = True
        self.assertFalse(game.reversed_order)
        game.clear_table(1)
        self.assertTrue(game.revolution)
        self.assertFalse(game.eleven_back)

    def test_seven_gift_can_finish(self):
        # 7を出した時点では手札が残るが、最後の1枚を渡すと上がれるケースを確認。
        game = self.game([[Card(0, 7), Card(0, 2)], [Card(1, 4)], [Card(2, 5)], [Card(3, 6)]])
        game.play(self.choose(game, 7))
        self.assertEqual(game.phase, "gift")
        self.assertIsNone(game.players[0].place)
        game.give([Card(0, 2)])
        self.assertEqual(game.players[0].place, 1)
        self.assertIn(Card(0, 2), game.players[1].hand.cards)

    def test_passed_player_cannot_rejoin(self):
        # 2Pがパスしたあと3Pが出しても、2Pは参加できない。全員パス後にだけ復帰する。
        game = self.game([[Card(0, 4), Card(0, 9)], [Card(1, 5)], [Card(2, 6), Card(2, 10)], [Card(3, 7)]])
        game.play(self.choose(game, 4))
        game.pass_turn()
        game.play(self.choose(game, 6))
        game.pass_turn()
        self.assertEqual(game.turn, 0)
        game.pass_turn()
        self.assertIsNone(game.top)
        self.assertEqual(game.turn, 2)
        self.assertEqual(game.passed, set())

    def test_finished_leader_all_survivors_pass(self):
        # 自分が2で上がり、残った3人が全員パスしたら、次の2Pから空の場を始める。
        game = self.game([[Card(0, 2)], [Card(1, 4)], [Card(2, 5)], [Card(3, 6)]])
        game.play(self.choose(game, 2))
        for _ in range(3):
            game.pass_turn()
        self.assertIsNone(game.top)
        self.assertEqual(game.turn, 1)

    def test_spade_three_resets_field(self):
        # 単独ジョーカーへスペード3を出す操作で、場が流れ、出した2Pが続けるか確認。
        game = self.game([[Card(0, 14), Card(0, 9)], [Card(0, 3), Card(1, 9)], [Card(2, 9)], [Card(3, 9)]])
        game.play(self.choose(game, 14))
        game.play(self.choose(game, 3))
        self.assertEqual(game.history, [])
        self.assertEqual(game.turn, 1)

    def test_three_finishes_assign_last_place(self):
        # 3人が続けて上がった時点で4位も確定し、その順番が再戦の身分に引き継がれるか確認。
        game = self.game([[Card(0, 3)], [Card(1, 4)], [Card(2, 5)], [Card(3, 6)]])
        for rank in (3, 4, 5):
            game.play(self.choose(game, rank))
        self.assertEqual(game.phase, "finished")
        self.assertEqual(game.finish_order, [0, 1, 2, 3])
        again = Game(game.finish_order, random.Random(3))
        self.assertEqual(again.title_order, game.finish_order)

    def test_200_complete_games_preserve_cards(self):
        # 決まった乱数seedを0〜199まで変えて、自動対戦を200回行う。
        # 手札と出した札を合算し、常に全54枚が重複も消失もなく存在するか調べる。
        for seed in range(200):
            game = Game(rng=random.Random(seed))
            while game.phase == "exchange":
                # このテストでは人間の交換もランダムで選び、入力待ちなしで進める。
                high, _, count = game.exchange_queue[0]
                game.exchange(game.rng.sample(game.players[high].hand.cards, count))
                game.advance_exchange()
            game.start()
            played = []
            # 場のhistoryは8切りで消えるので、枚数の検証用には別の出した札一覧を残す。
            for _ in range(1000):
                # 万一ゲームが終わらないバグがあってもテストが無限に続かないよう上限を設ける。
                all_cards = played + [c for p in game.players for c in p.hand.cards]
                self.assertEqual(len(all_cards), 54)
                card_keys = [(card.suit, card.rank) for card in all_cards]
                self.assertEqual(len(set(card_keys)), 54)
                # 数字とマークの組で重複を確認し、カードの消失・増殖を検出する。
                if game.phase == "finished":
                    break
                if game.phase == "gift":
                    # 7渡しは出した人の手札から選び、通常のgiveを使って移動させる。
                    actor, _, count, _ = game.pending_gift
                    game.give(game.rng.sample(game.players[actor].hand.cards, count))
                else:
                    moves = game.legal_moves()
                    if game.top and (not moves or game.rng.random() < 0.12):
                        # 場が空でなければ、出せない場合または約12%の確率でパスする。
                        game.pass_turn()
                    else:
                        move = game.rng.choice(moves)
                        played.extend(move.cards)
                        game.play(move)
            else:
                # for-elseのelseは、breakせず1000回終わったときだけ実行される。
                # つまりゲームが終了しなかった場合で、failによってテスト失敗にする。
                self.fail("対戦が終了しません: " + str(seed))
            self.assertEqual(sorted(game.finish_order), [0, 1, 2, 3])


if __name__ == "__main__":
    # このテストファイルを直接実行する場合も、unittestで各test_メソッドを実行できる。
    unittest.main()
