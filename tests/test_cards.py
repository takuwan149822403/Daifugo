"""カード管理の書き換え後も、配布・表示順・カードの移動を維持する。"""
import random
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cards import Card, Deck, Hand
from players import Player


class CardTests(unittest.TestCase):
    def test_deal_distributes_all_54_unique_cards(self):
        players = [Player(index, str(index)) for index in range(4)]
        Deck(random.Random(1)).deal(players)
        self.assertEqual([len(player.hand) for player in players], [14, 14, 13, 13])
        actual = []
        for player in players:
            for card in player.hand.cards:
                actual.append((card.suit, card.rank))
        expected = [(suit, rank) for suit in range(4) for rank in range(1, 14)]
        expected.extend([(0, 14), (1, 14)])
        self.assertEqual(sorted(actual), sorted(expected))

    def test_hand_order_labels_and_strongest_do_not_modify_input(self):
        original = [Card(1, 14), Card(0, 2), Card(0, 1), Card(0, 13),
                    Card(1, 3), Card(0, 3), Card(0, 14)]
        snapshot = list(original)
        hand = Hand(original)
        self.assertEqual([card.label for card in hand.cards],
                         ["♠3", "♥3", "♠K", "♠A", "♠2", "JOKER", "JOKER"])
        before = list(hand.cards)
        self.assertEqual(hand.strongest(2), [Card(1, 14), Card(0, 14)])
        self.assertEqual(hand.strongest(0), [])
        self.assertEqual(hand.strongest(20), list(reversed(before)))
        self.assertEqual(hand.cards, before)
        self.assertEqual(original, snapshot)

    def test_separately_created_cards_can_be_found_and_removed(self):
        hand = Hand([Card(0, 3), Card(1, 14)])
        self.assertTrue(hand.can_remove([Card(0, 3), Card(1, 14)]))
        self.assertFalse(hand.can_remove([Card(0, 3), Card(0, 3)]))
        self.assertFalse(hand.can_remove([Card(0, 14)]))
        self.assertEqual(len(hand), 2)
        hand.remove([Card(0, 3)])
        hand.add([Card(0, 4)])
        self.assertEqual(hand.cards, [Card(0, 4), Card(1, 14)])
        hand.remove([Card(0, 4), Card(1, 14)])
        self.assertFalse(hand)


if __name__ == "__main__":
    unittest.main()
