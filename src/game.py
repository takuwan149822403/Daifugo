"""対戦の進行。pygameを使わず、ルールだけを検証できる。"""
import random
from cards import Deck
from players import Player, NPCPlayer
from judge import Judge

TITLES = ("大富豪", "富豪", "貧民", "大貧民")


class Game:
    # このクラスが「現在どういう対戦状況か」を保持する。
    # 画面はGameの値を読み、操作が決まったらplay・giveなどを呼んで状況を更新する。
    def __init__(self, previous_order=None, rng=None):
        # previous_orderは前回の上がり順。初回ならNoneで、ランダムな身分にする。
        self.rng = rng or random.Random()
        self.players = [Player(0, "あなた"), NPCPlayer(1, "2P · レン"),
                        NPCPlayer(2, "3P · ミオ"), NPCPlayer(3, "4P · マスター")]
        self.judge = Judge()
        # title_orderは身分が高い順の席番号。例えば[2,0,3,1]なら3Pが大富豪、自分が富豪。
        self.title_order = list(previous_order) if previous_order else self.rng.sample(range(4), 4)
        for index, player_id in enumerate(self.title_order):
            self.players[player_id].title = TITLES[index]
        Deck(self.rng).deal(self.players)
        # 各タプルは（上位の席番号、下位の席番号、交換枚数）。リストの先頭から処理する。
        self.exchange_queue = [(self.title_order[0], self.title_order[3], 2),
                               (self.title_order[1], self.title_order[2], 1)]
        self.phase = "exchange"
        # phaseで進行段階を区別する。exchange=交換、ready=開始待ち、playing=対戦、
        # gift=7渡しの選択待ち、finished=終了。turnは次に操作する人の席番号。
        self.turn = self.title_order[3]
        # topは判定用の最新の組、historyは描画用の場の履歴。
        # last_playerは最後に出した人。空の場ではどちらもNoneにしておく。
        self.top = None
        self.last_player = None
        self.history = []
        # passedは今回の場でパスした席番号の集合。場が流れるまで再参加できない。
        self.passed = set()
        self.revolution = False
        self.eleven_back = False
        # finish_orderは上がった順の席番号。pending_giftは選択待ちの7渡し情報。
        self.finish_order = []
        self.pending_gift = None
        self.message = "身分を決定しました。開始前にカードを交換します。"
        self.advance_exchange()

    @property
    def reversed_order(self):
        # True/Falseの「!=」は、片方だけがTrueならTrue。
        # 革命とJバックのどちらか片方なら逆順、両方なら2回反転して通常順になる。
        return self.revolution != self.eleven_back

    def active_ids(self):
        # placeがまだNone（順位未確定）のプレイヤーだけ、席番号を集める。
        result = []
        for player in self.players:
            if player.place is None:
                result.append(player.index)
        return result

    def next_active(self, player_id):
        # 指定された席の次から最大4席を調べ、まだ上がっていない人を探す。
        # このメソッドはパス状態を考慮しない。パスの除外はadvance_turn側で行う。
        for offset in range(1, 5):
            # 余りを使うことで、席3の次を席0へ戻せる。
            candidate = (player_id + offset) % 4
            if self.players[candidate].place is None:
                return candidate
        return player_id

    def advance_exchange(self):
        # 自分に関係する交換だけUIに委ねる。NPC同士なら即時処理。
        while self.exchange_queue:
            # 3つの値を3変数に同時に代入する書き方を「アンパック」という。
            high, low, count = self.exchange_queue[0]
            if 0 in (high, low):
                # 人間が関係する交換では、画面の確認や選択が終わるまでここで止まる。
                return
            chosen = self.players[high].choose_cards(count, self.rng)
            self.exchange(chosen)
        # リストが空になったら全ての交換が完了したので、開始できる状態へ進む。
        self.phase = "ready"
        self.message = "大貧民から開始します。"

    def exchange(self, chosen=None):
        # 待ち行列の先頭の交換を1件だけ実行する。chosenは上位の人が渡すカード一覧。
        high, low, count = self.exchange_queue[0]
        high_player, low_player = self.players[high], self.players[low]
        if chosen is None:
            # 下位が人間のときは選べないため、上位NPCにランダムに選んでもらう。
            chosen = high_player.choose_cards(count, self.rng)
        if len(chosen) != count:
            # raiseで不正な操作を例外として知らせる。変更前に確認し、手札を壊さない。
            raise ValueError("交換するカードの枚数が違います")
        if not high_player.hand.can_remove(chosen):
            raise ValueError("手札にないカード、または重複したカードです")
        received = low_player.hand.strongest(count)
        # 双方から渡す札を取り除いてから相手の札を加える。交換で総枚数は変わらない。
        high_player.hand.remove(chosen)
        low_player.hand.remove(received)
        high_player.hand.add(received)
        low_player.hand.add(chosen)
        # pop(0)は先頭要素を取り出して削除する。次の交換が先頭に繰り上がる。
        self.exchange_queue.pop(0)

    def start(self):
        # 交換完了後だけ対戦を開始できる。開始の赤文字の表示時間は画面側が管理する。
        if self.phase == "ready":
            self.phase = "playing"

    def legal_moves(self, player_id=None):
        # 引数を省略した場合は現在のターンの人を調べる。
        if player_id is None:
            player_id = self.turn
        if self.phase != "playing" or player_id != self.turn or player_id in self.passed:
            # ターン外や7渡し中などは出せないので、空の候補一覧を返す。
            return []
        return self.judge.legal_moves(self.players[player_id].hand, self.top, self.reversed_order)

    def play(self, move):
        # 1回のカード出しを処理する。合法性の確認→札の移動→役→ターンの順で進む。
        if move not in self.legal_moves():
            raise ValueError("このカードは出せません")
        actor = self.turn
        player = self.players[actor]
        # 場を最新の札に置き換える前に、以前の札に対するスペード3返しを判定する。
        spade_cut = self.judge.is_spade_three(move, self.top)
        player.hand.remove(move.cards)
        self.top = move
        self.last_player = actor
        self.history.append((actor, move))
        # notはTrueとFalseを反転する。4枚出しのたびに革命状態を切り替える。
        if move.count == 4:
            self.revolution = not self.revolution
        # 出した通常札を順に調べ、役に必要な情報を集める。
        has_eight = False
        has_jack = False
        seven_count = 0
        for card in move.cards:
            if card.rank == 8:
                has_eight = True
            elif card.rank == 11:
                has_jack = True
            elif card.rank == 7:
                seven_count += 1
        if has_jack:
            # 同じ組にJが複数枚あっても、1回のカード出しで1回だけ反転する。
            self.eleven_back = not self.eleven_back
        cut = spade_cut or has_eight
        # messageは画面に出す説明。文字列の「+=」は元の説明の末尾に追加する。
        self.message = player.name + "：" + move.label
        if cut:
            if spade_cut:
                self.message += " / スペード3返し"
            else:
                self.message += " / 8切り"
        elif move.count == 4:
            self.message += " / 革命！"
        elif has_jack:
            self.message += " / イレブンバック"
        # ジョーカーは7の代用でも数えない。残り手札より多くは渡せないのでminを使う。
        gift_count = min(seven_count, len(player.hand))
        if gift_count:
            # （出した人、渡す相手、枚数、場を切るか）を保存し、選択待ちにする。
            # 7渡しが終わる前に上がりを決めると順位がずれるので、ここではまだ確定しない。
            self.pending_gift = (actor, self.next_active(actor), gift_count, cut)
            self.phase = "gift"
        else:
            self.complete_play(actor, cut)

    def give(self, cards):
        # 7渡しで選ばれた札を、次の未上がりの人へ移す。
        if self.phase != "gift":
            raise ValueError("7渡しの操作ではありません")
        actor, receiver, count, cut = self.pending_gift
        hand = self.players[actor].hand
        # 選択枚数、同じ札の重複、手札にあるかの3点を、移動前にまとめて確認する。
        if len(cards) != count or not hand.can_remove(cards):
            raise ValueError("渡すカードを指定枚数選んでください")
        hand.remove(cards)
        self.players[receiver].hand.add(cards)
        self.message += " / " + self.players[receiver].name + "に" + str(count) + "枚渡しました"
        self.pending_gift = None
        # 選択待ちを解除してから、手札が空になったかと次のターンを判定する。
        self.phase = "playing"
        self.complete_play(actor, cut)

    def finish_if_empty(self, actor):
        # 同じ人を2回登録しないため「手札が空」と「順位未確定」の両方を確認する。
        player = self.players[actor]
        if not player.hand and player.place is None:
            self.finish_order.append(actor)
            player.place = len(self.finish_order)
        if len(self.finish_order) == 3:
            # 3人の上がりが決まれば、残り1人は4位。最後の人の手札を出し切る必要はない。
            remaining = self.active_ids()[0]
            self.players[remaining].place = 4
            self.finish_order.append(remaining)
            self.phase = "finished"

    def complete_play(self, actor, cut):
        # 通常のカード出しと7渡し完了後に共通で使う、ターン終了の処理。
        self.finish_if_empty(actor)
        if cut:
            # 8切りなどのときは履歴も消す。終了時でも切った札は場に残さない。
            self.clear_table(actor)
        elif self.phase != "finished":
            self.advance_turn()

    def clear_table(self, leader):
        # 場を流して再開する。革命はゲーム全体に残り、Jバックはこの場だけなので解除する。
        self.top = None
        self.history.clear()
        self.passed.clear()
        self.eleven_back = False
        self.last_player = None
        # 最後に出した人がすでに上がっている場合は、次の未上がりの人から始める。
        self.turn = leader if self.players[leader].place is None else self.next_active(leader)

    def advance_turn(self):
        # 上がった人の最後の札も、残った全員がパスするまで場に残る。
        challengers = []
        for player_id in self.active_ids():
            if player_id != self.last_player and player_id not in self.passed:
                challengers.append(player_id)
        # 最後に出した本人は自分の札へ重ねない。上がり・パスを除いた残りが挑戦者。
        if not challengers:
            # 出せる立場の人がいなければ場を流す。手札の強さではなく参加状態で判断する。
            leader = self.last_player
            self.clear_table(leader)
            self.message += " / 場が流れました"
            return
        candidate = self.turn
        # 「_」は使わない値に付ける慣習。このfor文は4回まで調べるためのもの。
        for _ in range(4):
            candidate = self.next_active(candidate)
            if candidate in challengers:
                self.turn = candidate
                return

    def pass_turn(self):
        # パスは現在の場への参加を辞退する操作。空の場では誰かが札を出す必要がある。
        if self.phase != "playing" or self.top is None:
            raise ValueError("場が空のときはパスできません")
        self.passed.add(self.turn)
        self.message = self.players[self.turn].name + "：パス"
        self.advance_turn()

    def step_npc(self):
        # CPUの操作を1回だけ行う。何フレーム待つかは画面側のupdateが決める。
        if self.phase == "gift":
            actor, _, count, _ = self.pending_gift
            # アンパックの「_」は使わない受取人・cutの値。actorが0なら人間の入力を待つ。
            if actor != 0:
                self.give(self.players[actor].choose_cards(count, self.rng))
        elif self.phase == "playing" and self.turn != 0:
            # ジャッジが作った合法手だけをNPCへ渡し、選ばれた結果を人間と同じ処理に通す。
            move = self.players[self.turn].choose_play(self.legal_moves(), self.top is not None, self.rng)
            if move is None:
                self.pass_turn()
            else:
                self.play(move)
