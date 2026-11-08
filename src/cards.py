"""カード・山札・手札。教材のクラス、リスト、for文を使って管理する。"""
import random

# スート（マーク）の番号は、0=スペード、1=ハート、2=ダイヤ、3=クラブ。
SUITS = ("♠", "♥", "♦", "♣")
RANK_NAMES = {1: "A", 11: "J", 12: "Q", 13: "K"}


class Card:
    def __init__(self, suit, rank):
        # Card(0, 3)ならスペード3。14はジョーカー専用の数字。
        # 作ったカードの属性は変更せず、配る・出すときは手札のリストを変更する。
        self.suit = suit
        self.rank = rank
        self.joker = rank == 14

        # 表示する数字と、強さを比較するための数値を分ける。
        # 通常の強さは 3 < … < K < A < 2 < ジョーカー。
        if self.joker:
            self.strength = 99
        elif rank == 1 or rank == 2:
            self.strength = rank + 13
        else:
            self.strength = rank

        if self.joker:
            self.label = "JOKER"
        else:
            if rank in RANK_NAMES:
                name = RANK_NAMES[rank]
            else:
                name = str(rank)
            self.label = SUITS[suit] + name

    def __eq__(self, other):
        # 補足：== や「card in 手札」で呼ばれる特別なメソッド。
        # 別々に作ったCardでも、マークと数字が同じなら同じ札として扱う。
        if not isinstance(other, Card):
            return NotImplemented
        return self.suit == other.suit and self.rank == other.rank


def card_sort_key(card):
    # sortのkeyに渡す関数。強さが同じならマークの番号で並べる。
    return (card.strength, card.suit)


class Deck:
    def __init__(self, rng=None):
        # 乱数生成器を渡すと、テストで同じ配り方を再現できる。
        if rng is None:
            rng = random.Random()
        self.rng = rng
        self.cards = []
        for suit in range(4):
            for rank in range(1, 14):
                self.cards.append(Card(suit, rank))
        # マークの番号を変え、2枚のジョーカーを区別する。
        self.cards.append(Card(0, 14))
        self.cards.append(Card(1, 14))

    def deal(self, players):
        self.rng.shuffle(self.cards)
        player_index = 0
        for card in self.cards:
            # Hand.addは複数枚を受け取るため、1枚でもリストで渡す。
            players[player_index].hand.add([card])
            player_index += 1
            if player_index == len(players):
                player_index = 0


class Hand:
    def __init__(self, cards=None):
        if cards is None:
            self.cards = []
        else:
            # コピーして、渡されたリストとは別に手札を管理する。
            self.cards = list(cards)
        self.sort()

    def sort(self):
        # keyには関数名を渡す。sortがカードごとにcard_sort_keyを呼び出す。
        self.cards.sort(key=card_sort_key)

    def add(self, cards):
        for card in cards:
            self.cards.append(card)
        self.sort()

    def remove(self, cards):
        for card in cards:
            self.cards.remove(card)

    def can_remove(self, cards):
        # コピーから1枚ずつ探すと、手札にない札も同じ札の二重指定も確認できる。
        remaining = self.cards.copy()
        for card in cards:
            if card not in remaining:
                return False
            remaining.remove(card)
        return True

    def strongest(self, count):
        # 手札は弱い順なので、コピーを逆順にして先頭から必要枚数を取る。
        # 元の手札は変更しない。
        cards = self.cards.copy()
        cards.reverse()
        return cards[:count]

    def __len__(self):
        # 補足：len(hand)で呼ばれる特別なメソッド。
        # if handでも枚数が使われ、0枚ならFalseになる。
        return len(self.cards)
