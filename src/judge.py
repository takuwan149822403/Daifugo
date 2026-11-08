"""出すカードの形と、場のカードに勝てるかを判定する。"""
from itertools import combinations


class Move:
    def __init__(self, cards, rank):
        # Moveは1回で出すカードの組。タプルにして、カードの追加・削除を防ぐ。
        self.cards = tuple(cards)
        self.rank = rank
        self.count = len(self.cards)
        names = []
        for card in self.cards:
            names.append(card.label)
        self.label = "  ".join(names)

    def __eq__(self, other):
        # Game.playは候補を作り直して確認するため、別のMoveでも内容で比較する。
        if not isinstance(other, Move):
            return NotImplemented
        return self.cards == other.cards and self.rank == other.rank


def move_sort_key(move):
    # 候補は枚数→数字→表示名の順で並べ、画面での表示順をそろえる。
    return (move.count, move.rank, move.label)


class Judge:
    # 判定だけを行い、手札やターンは変更しない。
    def make_move(self, cards):
        cards = tuple(cards)
        if len(cards) < 1 or len(cards) > 4:
            return None

        checked = []
        rank = 14  # 通常札がなければ、ジョーカーだけの組。
        for card in cards:
            if card in checked:
                return None
            checked.append(card)
            if card.joker:
                continue
            if rank == 14:
                # 最初の通常札の数字を、この組の数字として覚える。
                rank = card.rank
            elif card.rank != rank:
                return None
        return Move(cards, rank)

    def is_spade_three(self, move, top):
        # 単独ジョーカーに、単独スペード3を出す場合だけ成立する。
        if top is None:
            return False
        if top.count != 1 or move.count != 1:
            return False
        if not top.cards[0].joker:
            return False
        card = move.cards[0]
        return card.rank == 3 and card.suit == 0

    def beats(self, move, top, reversed_order=False):
        if top is None:
            return True
        if move.count != top.count:
            return False
        if self.is_spade_three(move, top):
            return True
        # ジョーカーだけの組は革命中でも最強。同じ強さの組には勝てない。
        if top.rank == 14:
            return False
        if move.rank == 14:
            return True

        # 代用のジョーカーが先頭でも、通常札の強さで比較する。
        for card in move.cards:
            if not card.joker:
                strength = card.strength
                break
        for card in top.cards:
            if not card.joker:
                top_strength = card.strength
                break
        if reversed_order:
            return strength < top_strength
        return strength > top_strength

    def legal_moves(self, hand, top=None, reversed_order=False):
        # 1. 通常札を数字別のリストに分け、ジョーカーは別に集める。
        groups = {}
        for rank in range(1, 14):
            groups[rank] = []
        jokers = []
        for card in hand.cards:
            if card.joker:
                jokers.append(card)
            else:
                groups[card.rank].append(card)

        # 2. 数字ごとに、通常札＋代用のジョーカーから候補を作る。
        result = []
        if top is None:
            sizes = range(1, 5)
        else:
            sizes = [top.count]
        for rank in range(1, 15):
            if rank == 14:
                pool = jokers
            else:
                pool = groups[rank] + jokers
            for size in sizes:
                # 教材からの補足：combinations(pool, 2)は2枚を選ぶ全組み合わせ。
                # (A, B)と(B, A)を重複して作らない。具体例はdocs/learning_guide.mdへ。
                for cards in combinations(pool, size):
                    move = self.make_move(cards)
                    if move is None:
                        continue
                    # ジョーカーだけの組はrank=14のときに一度だけ調べる。
                    if move.rank != rank:
                        continue
                    # 3. 場の札に勝てる組だけを残す。
                    if self.beats(move, top, reversed_order):
                        result.append(move)
        return sorted(result, key=move_sort_key)
