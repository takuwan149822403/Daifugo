"""画面・入力を担当。ルール変更はgame/judge側で行う。"""
import argparse
import math
import random
import pygame
from assets import Assets
from cards import Card
from game import Game, TITLES
from widgets import Button, Popup, CREAM, GOLD

# ここでの幅・高さは「配置を考えるための仮想画面」のサイズ。
# 全ての部品をこの座標で描いてから、実際のウィンドウに合わせて全体を拡縮する。
# 座標は左上が(0,0)、右が+x、下が+y。サイズや位置の数字はピクセル単位。
WIDTH, HEIGHT = 1280, 800
# 1秒に60回の更新・描画を目標にする。1回の繰り返しが1フレーム。
FPS = 60


class Application:
    # ゲームの表示と入力をまとめる。Gameはルールの状態、Applicationは見せ方を担当する。
    def __init__(self, seed=None):
        # pygame.initで各機能を初期化し、set_modeで表示するウィンドウを作る。
        pygame.init()
        pygame.display.set_caption("大富豪 · Emerald Table")
        self.window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        # windowが実際の表示先、canvasは部品を描く仮想の画用紙（Surface）。
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        # フォントや画像のconvertには表示先が必要なので、Assetsはウィンドウ作成後に用意する。
        self.assets = Assets()
        self.rng = random.Random(seed)
        # seedを指定すれば同じ乱数の列を再現できる。通常はNoneで毎回違う対戦になる。
        # screenは表示画面（home/game/rules）、gameは対戦データ、popupは現在の選択画面。
        self.screen = "home"
        self.game = None
        self.popup = None
        # 以下のリストは描画した部品の当たり判定。毎回のdrawで作り直す。
        # card_hits:（矩形,カード,出せるか）、option_hits:（矩形,選択対象）。
        self.buttons = []
        self.card_hits = []
        self.option_hits = []
        self.running = True
        # bannerは開始・終了の赤文字。banner_framesは残り表示フレーム数。
        # npc_framesはCPU操作までの待ち時間、hover_framesはマウス重なりの継続時間。
        self.banner = ""
        self.banner_frames = 0
        self.npc_frames = 0
        self.hover_blocked = None
        # hover_blockedはキャンセル後の即再表示を防ぐカード、hover_cardは現在重なっている札。
        self.hover_card = None
        self.hover_frames = 0
        self.layout()

    def layout(self):
        # ウィンドウの変更に合わせて、仮想画面の倍率と表示位置を再計算する。
        w, h = self.window.get_size()
        self.scale = min(w / WIDTH, h / HEIGHT)
        # 縦横の倍率の小さい方なら全体が画面内に収まる。縦横比も維持される。
        self.viewport = pygame.Rect(0, 0, round(WIDTH * self.scale), round(HEIGHT * self.scale))
        self.viewport.center = (w // 2, h // 2)
        # viewportは実際にゲーム画面を置く矩形。余った領域が左右・上下へ均等になる。

    def mouse_position(self, pos=None):
        # マウスは実際のウィンドウ座標なので、余白を引いて倍率で割り、仮想座標へ戻す。
        # 引数posがあればクリック時の座標、なければ現在のマウス位置を使う。
        x, y = pos or pygame.mouse.get_pos()
        return ((x - self.viewport.x) / self.scale, (y - self.viewport.y) / self.scale)

    def text(self, value, position, size=24, color=CREAM, center=False, max_width=None):
        # 共通の文字描画処理。既定ではpositionを左上とし、center=Trueなら中心にする。
        font = self.assets.font(size)
        if max_width:
            # font.size(value)[0]は文字列の描画幅。収まるまで1ずつ文字サイズを下げる。
            while font.size(value)[0] > max_width and size > 12:
                size -= 1
                font = self.assets.font(size)
        surface = font.render(value, True, color)
        # renderのTrueは文字の輪郭を滑らかにする指定。作った文字画像をcanvasへ貼る。
        rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
        self.canvas.blit(surface, rect)

    def panel(self, rect, color=(8, 38, 32), border=True):
        # 各画面で共通して使う、角丸の背景と枠線。border=Falseなら枠線を省く。
        pygame.draw.rect(self.canvas, color, rect, border_radius=14)
        if border:
            pygame.draw.rect(self.canvas, (155, 126, 65), rect, 2, border_radius=14)

    def button(self, rect, label, action, enabled=True, sprite=None):
        # ボタンを描くだけでなく一覧にも登録し、後からclickで同じ矩形を調べられるようにする。
        # actionはクリック時の処理を表す文字列。ボタン自体はゲームの操作を実行しない。
        item = Button(pygame.Rect(rect), label, action, enabled, sprite)
        item.draw(self.canvas, self.assets, self.mouse_position())
        self.buttons.append(item)

    def new_game(self):
        # 初回は身分を抽選し、前の対戦が終了していれば上がり順を次の身分に引き継ぐ。
        previous = self.game.finish_order if self.game and self.game.phase == "finished" else None
        self.game = Game(previous, self.rng)
        self.screen = "game"
        # 前の対戦のポップアップや待ち時間を残さず、新しい対戦の状態に合わせる。
        self.popup = None
        self.banner_frames = 0
        self.npc_frames = 0
        self.hover_blocked = None
        self.sync_game()

    def sync_game(self):
        # Gameの進行段階を読み、必要な選択画面や開始・終了の赤文字を用意する。
        # すでにpopupがある場合は作り直さず、途中の選択を保持する。
        game = self.game
        if game.phase == "exchange" and self.popup is None:
            high, low, count = game.exchange_queue[0]
            if high == 0:
                # 自分が上位なら渡す札を選ぶ。受取札は下位の最強札なので、先に説明に表示できる。
                received = game.players[low].hand.strongest(count)
                self.popup = Popup("exchange", "開始前のカード交換", "渡すカードを" + str(count) + "枚選択。受取：" + " / ".join(c.label for c in received), list(game.players[0].hand.cards), count)
            else:
                # 自分が下位なら渡す札は固定。交換を確認する画面だけを開く。
                given = game.players[0].hand.strongest(count)
                self.popup = Popup("receive", "開始前のカード交換", "あなたの強いカードを自動で渡します。", given, count)
        elif game.phase == "ready":
            # 交換完了で対戦へ進むが、updateは赤文字の120フレーム中のCPU操作を止める。
            game.start()
            self.banner = "ゲーム開始"
            self.banner_frames = 120
        elif game.phase == "gift" and game.pending_gift[0] == 0 and self.popup is None:
            # CPUの7渡しはGameが処理する。自分が渡すときだけ選択ポップアップを開く。
            _, receiver, count, _ = game.pending_gift
            self.popup = Popup("gift", "7渡し", game.players[receiver].name + "に渡すカードを" + str(count) + "枚選んでください。", list(game.players[0].hand.cards), count)
        elif game.phase == "finished" and self.banner != "ゲーム終了":
            # 赤文字が終了したあとに毎回120へ戻らないよう、文字の内容で一度だけ設定する。
            self.banner = "ゲーム終了"
            self.banner_frames = 120

    def update(self):
        # 1フレーム分の進行。ここでは描画しないので、表示処理とゲームの更新を分けられる。
        if self.screen != "game" or not self.game:
            # スタート画面・役確認画面では対戦を進めない。
            return
        if self.banner_frames:
            # 赤文字中は操作の自動進行を止める。残りフレームの減算はrunで描画後に行う。
            return
        self.sync_game()
        if self.banner_frames or self.popup:
            # 選択が終わるまではCPUも待ち、人間の選択中に場が変わることを防ぐ。
            return
        game = self.game
        if game.phase == "playing" and game.turn == 0:
            mouse = self.mouse_position()
            hovered = None
            for rect, card, legal in self.card_hits:
                if legal and rect.collidepoint(mouse):
                    hovered = card
                    break
            if hovered != self.hover_card:
                self.hover_card = hovered
                self.hover_frames = 0
            if hovered is None:
                # カードからマウスを離したら、キャンセル後の再表示防止を解除する。
                self.hover_blocked = None
            elif hovered != self.hover_blocked:
                self.hover_frames += 1
                # 短い待ち時間でマウス移動中の意図しない連続表示を抑える。
                if self.hover_frames >= 10:
                    # 重なった札を含む合法手だけを抜き出し、1枚出し・複数枚出しを選べるようにする。
                    moves = [move for move in game.legal_moves() if hovered in move.cards]
                    self.popup = Popup("play", "このカードを出しますか？", "出せる組み合わせを選んでください。", moves=moves)
                    self.hover_blocked = hovered
                    self.hover_frames = 0
        else:
            # 24フレーム（60FPSなら約0.4秒）ごとにCPUの操作を1回だけ進める。
            self.npc_frames += 1
            if self.npc_frames >= 24:
                game.step_npc()
                self.npc_frames = 0
                self.sync_game()

    def draw(self):
        # 1フレームの描画。背景→画面の部品→ポップアップの順で上へ重ねる。
        self.buttons = []
        self.card_hits = []
        self.option_hits = []
        # 古い位置のボタンや札が反応しないよう、当たり判定も描画時に作り直す。
        background = self.assets.home if self.screen == "home" else self.assets.table
        self.canvas.blit(self.assets.resize(background, (WIDTH, HEIGHT)), (0, 0))
        match self.screen:
            # match-caseは値による分岐。この場合は画面名に一致するcaseだけを実行する。
            case "home":
                self.draw_home()
            case "game":
                self.draw_game()
            case "rules":
                self.draw_rules()
        if self.popup and self.screen == "game":
            # 一番最後に選択画面を描き、対戦画面より手前に表示する。
            self.draw_popup()
        self.window.fill((5, 18, 15))
        # 仮想画面全体を実際の表示サイズへ変換して貼り、flipで画面へ反映する。
        self.window.blit(pygame.transform.smoothscale(self.canvas, self.viewport.size), self.viewport)
        pygame.display.flip()

    def draw_home(self):
        # スタート画面はタイトルと2つの大きなボタンだけにする。
        self.panel(pygame.Rect(270, 60, 740, 180))
        self.text("大 富 豪", (640, 118), 68, GOLD, True)
        self.text("あなた ＋ CPU 3人", (640, 197), 27, center=True)
        # 幅をウィンドウの50%にし、縦並び・中央揃え。
        self.button((320, 300, 640, 157), "ゲームスタート", "start", sprite=0)
        self.button((320, 505, 640, 157), "やめる", "quit", sprite=1)
        self.text("マウスで操作  ·  F11：全画面  ·  Esc：戻る", (640, 745), 22, center=True)

    def draw_player(self, index, rect):
        # CPU1席分の表示。位置と大きさをrectとして受け、同じ処理を3席で使う。
        player = self.game.players[index]
        active = self.game.phase == "playing" and self.game.turn == index
        # 現在のターンの席だけ背景と枠線を明るくし、誰の番かを示す。
        self.panel(rect, (24, 78, 57) if active else (8, 38, 32))
        if active:
            pygame.draw.rect(self.canvas, GOLD, rect, 4, border_radius=14)
        portrait_size = 84
        # NPCの席番号は1〜3、画像リストの番号は0〜2なので、indexから1を引く。
        self.canvas.blit(self.assets.resize(self.assets.portraits[index - 1], (portrait_size, portrait_size)), (rect.x + 13, rect.y + 14))
        self.text(player.name, (rect.x + 108, rect.y + 12), 22, max_width=rect.width - 116)
        self.text(player.title, (rect.x + 108, rect.y + 47), 24, GOLD)
        state = str(player.place) + "位で上がり" if player.place else "手札 " + str(len(player.hand)) + "枚"
        # 順位が決まっていれば順位を、まだなら残り枚数を表示する。
        self.text(state, (rect.x + 16, rect.y + 112), 24)
        if index in self.game.passed:
            self.text("パス", (rect.right - 74, rect.y + 113), 24, (190, 196, 177))
        # 各席の裏向きカードは残り枚数に合わせて並べる。
        count = len(player.hand)
        for n in range(count):
            # 手札が多いほど間隔を詰めて枠内に収める。max(1,...)で0による割り算を防ぐ。
            step = min(19, (rect.width - 72) / max(1, count - 1))
            self.canvas.blit(self.assets.resize(self.assets.back, (42, 54)), (rect.x + 14 + n * step, rect.y + 154))

    def draw_game(self):
        # 対戦画面全体。上部情報→CPU各席→中央の場→自分の手札→案内の順に描く。
        game = self.game
        self.panel(pygame.Rect(22, 14, 1236, 53))
        mode = "逆順：2 → 3" if game.reversed_order else "通常：3 → 2"
        effects = ("  / 革命中" if game.revolution else "") + ("  / Jバック中" if game.eleven_back else "")
        # 革命とJバックを別々に示し、現在どちらの効果が残っているか分かるようにする。
        self.text("EMERALD TABLE   " + mode + effects, (42, 27), 22, max_width=955)
        self.button((1082, 19, 157, 43), "役確認", "rules")
        # CPUを左（2P）、上（3P）、右（4P）へ配置。自分の手札は下のパネルへ配置する。
        self.draw_player(1, pygame.Rect(38, 264, 265, 224))
        self.draw_player(2, pygame.Rect(461, 83, 358, 224))
        self.draw_player(3, pygame.Rect(977, 264, 265, 224))
        self.draw_table()
        self.panel(pygame.Rect(32, 555, 1216, 225))
        player = game.players[0]
        self.text("あなた  / " + player.title + "  / " + str(len(player.hand)) + "枚", (55, 568), 25, GOLD)
        status = "あなたの番：黄色のカードにマウスを重ねてください" if game.phase == "playing" and game.turn == 0 else "CPUの操作を待っています"
        # 進行段階で案内文を切り替える。描画は状況を読むだけで、ルールを変更しない。
        if game.phase == "exchange":
            status = "開始前のカード交換"
        elif game.phase == "gift":
            status = "7渡し：渡すカードを選択中"
        elif game.phase == "finished":
            status = str(player.place) + "位で終了"
        self.text(status, (865, 582), 20, center=True, max_width=650)
        moves = game.legal_moves(0)
        # 合法手に含まれる札を集める。同じ札は一度だけ追加する。
        playable = []
        for move in moves:
            for card in move.cards:
                if card not in playable:
                    playable.append(card)
        cards = player.hand.cards
        rows = max(1, math.ceil(len(cards) / 14))
        # 1段は最大14枚。ceilは切り上げなので、15枚なら2段となる。空でも最低1段にする。
        columns = max(1, min(14, len(cards)))
        available_width = (1160 - 8 * (columns - 1)) / columns
        # パネル内の横幅から札の間隔を引き、1枚あたりに使える横幅を求める。
        # 縦の段数、横の枚数、上限148の全てを満たす最大サイズをminで選ぶ。
        card_h = min(148, int(157 / rows) - (6 if rows > 1 else 0), int(available_width / 0.78))
        card_w = int(card_h * 0.78)
        for row in range(rows):
            # スライスで今回の段の札だけを取り出す。終わりの番号の札は含まれない。
            subset = cards[row * 14:(row + 1) * 14]
            gap = min(12, max(4, (1160 - len(subset) * card_w) / max(1, len(subset) - 1)))
            total = len(subset) * card_w + max(0, len(subset) - 1) * gap
            # 全体幅から札列の幅を引いて半分にすると、左右の余白が等しくなる。
            start_x = (WIDTH - total) / 2
            for i, card in enumerate(subset):
                rect = pygame.Rect(int(start_x + i * (card_w + gap)), 610 + row * (card_h + 6), card_w, card_h)
                self.canvas.blit(self.assets.card(card, rect.size), rect)
                if card in playable:
                    # inflateは元の矩形を変更せず少し大きい矩形を返す。外側へ黄色枠を描く。
                    pygame.draw.rect(self.canvas, (255, 224, 55), rect.inflate(4, 4), 3, border_radius=7)
                self.card_hits.append((rect, card, card in playable))
                # 表示した札と矩形・合法性を登録し、hoverやクリックで同じ範囲を判定する。
        self.panel(pygame.Rect(38, 497, 1060, 45), border=False)
        self.text(game.message, (52, 506), 20, max_width=1030)
        self.button((1110, 497, 132, 45), "パス", "pass", game.phase == "playing" and game.turn == 0 and game.top is not None and not self.banner_frames)
        # 自分の通常ターンで場に札がある場合だけパス可能。赤文字表示中は操作を止める。
        if self.banner_frames:
            self.panel(pygame.Rect(380, 339, 520, 110))
            self.text(self.banner, (640, 394), 64, (255, 68, 71), True)
        elif game.phase == "finished":
            # 終了の赤文字を120フレーム表示し終えてから、結果と再戦ボタンを重ねる。
            self.draw_result()

    def draw_table(self):
        # 中央の場を描く。historyは古い順なので、その順に貼ると新しい札が手前になる。
        self.panel(pygame.Rect(326, 324, 628, 159), (7, 52, 40))
        if not self.game.history:
            # まだ誰も出していない、8切りされた、全員パスした、などの空の場。
            self.text("場は空です", (640, 390), 32, (152, 178, 150), True)
            return
        history = self.game.history
        # 古い札から描画し、新しい札ほど手前に積む。長い場では間隔を詰める。
        step = min(24, 235 / max(1, len(history) - 1))
        # 1回のカード出しごとの横ずれ。履歴が多ければずれを小さくして全体を収める。
        for index, (actor, move) in enumerate(history):
            x = 352 + index * step
            y = 345 + (index % 3) * 7
            # %3で縦位置を3パターンにし、重なっていても札の積み重なりが分かるようにする。
            for n, card in enumerate(move.cards):
                rect = pygame.Rect(x + n * 51, y, 75, 97)
                self.canvas.blit(self.assets.card(card, rect.size), rect)
                if index == len(history) - 1:
                    # 最後の組が現在の強さ比較の対象なので、金色の枠で示す。
                    pygame.draw.rect(self.canvas, GOLD, rect, 2, border_radius=6)
        actor = self.game.last_player
        self.text(self.game.players[actor].name + "  /  " + str(self.game.top.count) + "枚出し", (640, 463), 19, center=True)

    def draw_result(self):
        # finish_orderの席番号を、順位・名前・次回の身分へ対応させて表示する。
        self.panel(pygame.Rect(365, 185, 550, 354))
        self.text("対戦結果", (640, 220), 35, GOLD, True)
        for place, index in enumerate(self.game.finish_order):
            # enumerateの番号は0始まりなので、表示順位はplace+1とする。
            self.text(str(place + 1) + "位   " + self.game.players[index].name + "   → " + TITLES[place], (640, 270 + place * 42), 25, center=True)
        self.button((391, 457, 240, 58), "再戦", "rematch")
        self.button((649, 457, 240, 58), "やめる", "quit")

    def draw_rules(self):
        # 説明内容もリストにまとめ、同じレイアウトで5種類の役を描く。
        # ここでのCardは説明用の画像指定で、実際のプレイヤーの手札には加わらない。
        self.panel(pygame.Rect(45, 28, 1190, 737))
        self.text("役とルール", (640, 73), 42, GOLD, True)
        rows = [
            ([Card(0, 8)], "8切り", "8を出すと場が流れます。出した人から新しい場を開始します。"),
            ([Card(1, 7)], "7渡し", "実際に出した7の枚数だけ、次の未上がりの人に好きな手札を渡します。"),
            ([Card(suit, 6) for suit in range(4)], "革命", "同じ数字を4枚出すと強さが逆転。もう一度4枚出すと元に戻ります。"),
            ([Card(0, 11)], "イレブンバック", "Jを出すたびに強さが逆転。場が流れると解除されます。"),
            ([Card(0, 3)], "スペード3", "単独ジョーカーにだけ勝てます。返すと場が流れます。"),
        ]
        for index, (cards, title, description) in enumerate(rows):
            # 各項目は（表示するカード一覧、見出し、説明文）のタプル。
            # 行番号×99を足して縦に並べ、革命だけは4枚を横に重ねて表示する。
            y = 123 + index * 99
            for n, card in enumerate(cards):
                self.canvas.blit(self.assets.card(card, (58, 78)), (71 + n * 43, y))
            self.text(title, (279, y + 2), 27, GOLD)
            self.text(description, (279, y + 42), 22, max_width=904)
        self.text("54枚（ジョーカー2枚）。同じ枚数・同じ数字の組で、より強い札を出します。", (76, 635), 22)
        self.text("ジョーカーは代用可・常に最強。革命とJバックは重なると通常順。", (76, 670), 21)
        self.text("階段・縛り・反則上がりなし。パス後は場が流れるまで参加できません。", (76, 705), 20, max_width=880)
        self.button((1014, 689, 189, 57), "戻る", "back")

    def draw_popup(self):
        # 背景を暗くする半透明の画像を重ねてから、選択用のパネルを描く。
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 10, 7, 185))
        # 4つ目の数値が透明度。0なら透明、255なら不透明で、185は背景が少し透ける。
        self.canvas.blit(shade, (0, 0))
        self.buttons = []
        # 対戦画面のボタンを一覧から外し、選択中に背後のボタンへ操作が届かないようにする。
        popup = self.popup
        self.panel(pygame.Rect(165, 120, 950, 568), (12, 48, 39))
        self.text(popup.title, (640, 161), 36, GOLD, True)
        self.text(popup.note, (640, 208), 23, center=True, max_width=885)
        if popup.kind == "play":
            # カード出しは1ページ4候補。pageは0始まりなので先頭番号はpage*4。
            start = popup.page * 4
            for index, move in enumerate(popup.moves[start:start + 4]):
                # 行全体がクリック対象。左に札の画像、中央に組の名前、右に枚数を表示する。
                rect = pygame.Rect(196, 244 + index * 80, 888, 71)
                self.panel(rect, (31, 92, 67))
                for n, card in enumerate(move.cards):
                    self.canvas.blit(self.assets.card(card, (44, 59)), (rect.x + 13 + n * 51, rect.y + 6))
                self.text(move.label, (rect.x + 245, rect.y + 22), 22, max_width=520)
                self.text(str(move.count) + "枚", (rect.right - 66, rect.y + 22), 21, GOLD)
                self.option_hits.append((rect, move))
                # この行をクリックしたら、ここで表示したMoveをそのままGame.playへ渡す。
            self.button((896, 620, 184, 47), "キャンセル", "cancel")
        elif popup.kind == "receive":
            # 下位の交換では選択の余地がないため、渡す最強札と確認ボタンだけを描く。
            for index, card in enumerate(popup.cards):
                self.canvas.blit(self.assets.card(card, (122, 163)), (500 + index * 155, 282))
            high, _, count = self.game.exchange_queue[0]
            self.text(self.game.players[high].name + "からランダムに選んだ" + str(count) + "枚を受け取ります。", (640, 502), 25, center=True)
            self.button((500, 610, 280, 55), "交換して開始", "confirm")
        else:
            # 上位の交換と7渡しは、どちらも手札から指定枚数を選ぶ画面なので共通の描画。
            start = popup.page * 16
            for index, card in enumerate(popup.cards[start:start + 16]):
                # %8は列番号（0〜7）、//8は段番号（0または1）。8列×2段で16枚を置く。
                rect = pygame.Rect(213 + index % 8 * 108, 255 + index // 8 * 147, 88, 126)
                self.canvas.blit(self.assets.card(card, rect.size), rect)
                if card in popup.selected:
                    # 選択済みの札だけ黄色で囲む。表示ページを変えてもselectedは保持される。
                    pygame.draw.rect(self.canvas, (255, 224, 55), rect.inflate(5, 5), 4, border_radius=7)
                self.option_hits.append((rect, card))
            self.text("選択 " + str(len(popup.selected)) + " / " + str(popup.count) + " 枚", (640, 572), 26, GOLD, True)
            self.button((884, 614, 200, 51), "決定", "confirm", len(popup.selected) == popup.count)
            # 必要枚数ぴったりになったときだけ、決定ボタンを押せるようにする。
        if popup.page_count > 1:
            # 2ページ以上のときだけページ送りを出し、範囲外へ進むボタンは無効にする。
            self.button((198, 620, 110, 47), "前へ", "prev", popup.page > 0)
            self.text(str(popup.page + 1) + " / " + str(popup.page_count), (368, 644), 22, center=True)
            self.button((430, 620, 110, 47), "次へ", "next", popup.page + 1 < popup.page_count)

    def click(self, pos):
        # マウスの位置を仮想座標へ変換し、ボタン→選択候補→手札の順で調べる。
        # 操作を1つ実行したらreturnで終了し、1クリックが複数の部品へ届くことを防ぐ。
        point = self.mouse_position(pos)
        for button in self.buttons:
            if button.enabled and button.rect.collidepoint(point):
                self.action(button.action)
                return
        if self.popup:
            # ポップアップ中はその中の候補だけを選ぶ。背景の自分の手札は操作しない。
            for rect, value in self.option_hits:
                if not rect.collidepoint(point):
                    # continueは今回の繰り返しの残りを飛ばし、次の候補を調べる。
                    continue
                if self.popup.kind == "play":
                    # カード出しは行を選んだ時点で確定。役で7渡しが必要ならsync_gameが次を開く。
                    self.game.play(value)
                    self.popup = None
                    self.npc_frames = 0
                    self.sync_game()
                elif self.popup.kind in ("exchange", "gift"):
                    # 交換・7渡しは札を選択状態にするだけ。「決定」するまで手札を動かさない。
                    if value in self.popup.selected:
                        # 選択済みの札を再度クリックすると解除する。
                        self.popup.selected.remove(value)
                    elif len(self.popup.selected) < self.popup.count:
                        self.popup.selected.append(value)
                return
        elif self.screen == "game" and not self.banner_frames:
            # マウスを重ねる操作に加え、合法札を直接クリックして候補を開くこともできる。
            for rect, card, legal in self.card_hits:
                if legal and rect.collidepoint(point):
                    self.popup = Popup("play", "このカードを出しますか？", "出せる組み合わせを選んでください。", moves=[m for m in self.game.legal_moves() if card in m.cards])
                    self.hover_blocked = card
                    return

    def action(self, action):
        # Button.actionに登録された文字列を、実際の処理へ対応させる。
        # caseで「|」を使うと複数の値を同じ処理にできる。startとrematchは同じ入口を使う。
        match action:
            case "start" | "rematch":
                self.new_game()
            case "quit":
                # ループ終了用のフラグを下げる。pygameの終了処理はrunの最後で行う。
                self.running = False
            case "rules":
                # 画面名だけを変更するので、手札やターンはそのまま保持される。
                self.screen = "rules"
            case "back":
                self.screen = "game"
            case "pass":
                # 連続クリックなどに備え、描画時のenabledだけでなく最新の状態でも確認する。
                if self.game.phase == "playing" and self.game.turn == 0 and self.game.top is not None:
                    self.game.pass_turn()
                    self.npc_frames = 0
            case "cancel":
                # 出す札の候補だけを閉じる。hover_blockedは残し、すぐ同じ札で開き直さない。
                self.popup = None
            case "prev":
                self.popup.page -= 1
            case "next":
                self.popup.page += 1
            case "confirm":
                popup = self.popup
                if popup is None or (popup.kind != "receive" and len(popup.selected) != popup.count):
                    # 確認だけのreceive以外は、指定枚数が選ばれていなければ処理しない。
                    return
                self.popup = None
                # 古いポップアップを閉じてから操作する。次に必要なものをsync_gameで開ける。
                if popup.kind == "gift":
                    self.game.give(popup.selected)
                else:
                    # 自分が上位なら選択札を渡し、下位ならNoneを渡して上位NPCに選ばせる。
                    self.game.exchange(popup.selected if popup.kind == "exchange" else None)
                    self.game.advance_exchange()
                self.sync_game()

    def run(self, max_frames=0):
        # ゲームのメインループ。入力→更新→描画→時間調整を、終了まで繰り返す。
        # max_frames=0は無制限。テストでは上限を指定して、自動で終了させる。
        frames = 0
        while self.running:
            # event.getで、前回から溜まったクリック・キー入力などのイベントを取り出す。
            for event in pygame.event.get():
                match event.type:
                    case pygame.QUIT:
                        # ウィンドウの閉じるボタンが押された場合。
                        self.running = False
                    case pygame.VIDEORESIZE:
                        # 画面が小さすぎるのを防ぐ下限を設け、拡縮率と余白を再計算する。
                        self.window = pygame.display.set_mode((max(640, event.w), max(480, event.h)), pygame.RESIZABLE)
                        self.layout()
                    case pygame.MOUSEBUTTONDOWN:
                        # button=1は左クリック、4/5はこの処理で扱うホイールの上/下。
                        if event.button == 1:
                            self.click(event.pos)
                            # 同じフレームの連続クリックにも最新の当たり判定を使う。
                            self.draw()
                        elif self.popup and event.button in (4, 5):
                            # min/maxでページ番号を0〜最終ページの間に収める。
                            self.popup.page = max(0, min(self.popup.page_count - 1, self.popup.page + (1 if event.button == 5 else -1)))
                    case pygame.KEYDOWN:
                        # Escは説明から戻る／出す札の候補を閉じる。交換・7渡しは途中で閉じない。
                        if event.key == pygame.K_ESCAPE:
                            if self.screen == "rules":
                                self.screen = "game"
                            elif self.popup and self.popup.kind == "play":
                                self.popup = None
                        elif event.key == pygame.K_F11:
                            # &はビット演算。現在の画面フラグにFULLSCREENが含まれるかを調べる。
                            fullscreen = bool(self.window.get_flags() & pygame.FULLSCREEN)
                            # 全画面なら通常窓へ戻し、通常窓なら(0,0)で画面全体のサイズを使う。
                            self.window = pygame.display.set_mode((WIDTH, HEIGHT) if fullscreen else (0, 0), pygame.RESIZABLE if fullscreen else pygame.FULLSCREEN)
                            self.layout()
            self.update()
            self.draw()
            if self.screen == "game" and self.banner_frames:
                # 描画した後に1減らすことで、赤文字を120フレーム分表示する。
                # 役確認画面では減らさないので、説明を読んでいる間は表示時間も停止する。
                self.banner_frames -= 1
            self.clock.tick(FPS)
            # tickで速すぎるループを待機させ、目標FPSに近づける。負荷が高い場合は遅くなり得る。
            frames += 1
            if max_frames and frames >= max_frames:
                break
        pygame.quit()
        # pygameが使っていた画面などの機能を終了する。


def main():
    # コマンドラインのオプションを読み、Applicationを作って起動する関数。
    # argparseはPython標準の引数解析ライブラリで、--helpの表示も作ってくれる。
    parser = argparse.ArgumentParser(description="CPU3人と大富豪")
    parser.add_argument("--smoke", action="store_true", help="3フレームだけ描画して終了")
    # store_trueはオプションが付いたらTrue。--seedは指定値を整数として読み取る。
    parser.add_argument("--seed", type=int, help="乱数の固定（動作確認用）")
    args = parser.parse_args()
    Application(args.seed).run(3 if args.smoke else 0)
    # smoke確認では3フレームだけ動かし、通常は終了操作まで無制限に動かす。


if __name__ == "__main__":
    # app.pyを直接実行した場合の入口。通常のsrc/main.py起動でも同じmainが呼ばれる。
    main()
