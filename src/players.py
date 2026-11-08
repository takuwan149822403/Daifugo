"""プレイヤーは手札を所有。NPCの意思決定は乱数で行う。"""
from cards import Hand


class Player:
    # 人間もNPCも持つ共通の情報。画面操作や強さの判定は別クラスが担当する。
    def __init__(self, index, name):
        # indexは席の番号（0が自分、1〜3がCPU）。リストから探すときにも使う。
        self.index = index
        self.name = name
        self.hand = Hand()
        # titleは今回の身分。placeは今回の終了順位で、未確定ならNone。
        self.title = ""
        self.place = None


class NPCPlayer(Player):
    # 括弧内のPlayerを継承し、共通の初期化・属性をそのまま使う。
    # このクラスではNPCに必要な「何を選ぶか」だけを追加する。
    def choose_play(self, moves, can_pass, rng):
        # movesはジャッジが判定済みの合法手一覧、can_passはパス可能かどうか。
        # rng.random()は0以上1未満の値。0.12未満になる確率は約12%。
        # 出せる札がない場合、またはパス可能で抽選に当たった場合はNone（パス）を返す。
        if not moves:
            return None
        if can_pass and rng.random() < 0.12:
            return None
        # choiceは候補一覧から1つをランダムに選ぶ。候補は判定済みなので違反する札を選ばない。
        return rng.choice(moves)

    def choose_cards(self, count, rng):
        # sampleは同じ要素を重複して選ばない抽選。手札そのものはここでは変更しない。
        # minで枚数を手札の範囲内に収め、存在する枚数以上を選ぶエラーを防ぐ。
        return rng.sample(self.hand.cards, min(count, len(self.hand)))
