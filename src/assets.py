"""分割済み画像の読み込みと、拡縮した画像・日本語フォントの管理。"""
from pathlib import Path
import sys
import pygame


class Assets:
    # Assetsは表示用の素材をまとめて持つ。カードの強さやターンは扱わない。
    def __init__(self):
        # __file__はこのファイルの場所。resolveで絶対パスにし、parentで親フォルダを取得。
        # ソース起動ではプロジェクトのルート、PyInstaller版では展開先_MEIPASSを使う。
        # getattr(対象, 属性名, 初期値)は属性がない場合に第3引数を返す。
        self.root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        folder = self.root / "images"
        # Pathの「/」はフォルダ名をつなぐ。strでpygameへ渡せる文字列のパスへ変換する。
        # convertは表示に適した画像形式へ変換する。画面を作った後に呼ぶ必要がある。
        self.home = pygame.image.load(str(folder / "ホーム背景.png")).convert()
        self.table = pygame.image.load(str(folder / "16ビットのエメラルドカードテーブル.png")).convert()
        # convert_alphaは透明度も保つ。カードの角などの透明部分を背景に重ねられる。
        # 素材はimages内で分割済み。起動時は個別PNGを読み込むだけにする。
        self.cards = {}
        for suit, name in enumerate(("spades", "hearts", "diamonds", "clubs")):
            for rank in range(1, 14):
                # 辞書のキーは（スート,数字）のタプル。例えばself.cards[0,3]でスペード3。
                path = folder / "cards" / f"{name}_{rank:02}.png"
                self.cards[suit, rank] = pygame.image.load(str(path)).convert_alpha()
        self.back = pygame.image.load(str(folder / "cards" / "back.png")).convert_alpha()
        # 12人分を左上から行ごとの順で読み込み、画面では従来と同じ先頭3人を使う。
        self.portraits = [pygame.image.load(str(folder / "portraits" / f"npc_{number:02}.png")).convert()
                          for number in range(1, 13)]
        self.buttons = [pygame.image.load(str(folder / "buttons" / f"{name}.png")).convert()
                        for name in ("start", "quit", "back", "confirm", "rules")]
        # 一度作った拡縮画像やフォントを辞書へ保存する仕組みをキャッシュと呼ぶ。
        # 毎フレーム作り直さず再利用することで、描画の負荷を減らす。
        self.scaled = {}
        self.fonts = {}
        bundled = self.root / "fonts" / "NotoSansCJK-Regular.ttc"
        # 同梱フォントを優先し、なければOSの日本語フォントを探す。
        self.font_path = str(bundled) if bundled.exists() else pygame.font.match_font("notosanscjk,notosanscjkjp,droidsansfallback")
        if not self.font_path:
            for candidate in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                              "C:/Windows/Fonts/meiryo.ttc", "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"):
                if Path(candidate).exists():
                    self.font_path = candidate
                    break

    def font(self, size):
        # フォントの大きさは整数で、仮想画面上で最低12ピクセルにする。
        size = max(12, int(size))
        if size not in self.fonts:
            # そのサイズを初めて使うときだけ生成する。2回目以降は保存済みのものを返す。
            self.fonts[size] = pygame.font.Font(self.font_path, size)
        return self.fonts[size]

    def resize(self, surface, size):
        # Surfaceはpygameの画像・描画領域。sizeは（幅,高さ）の組。
        # 小数を整数にそろえ、画像サイズが0以下になるエラーを防ぐ。
        size = tuple(max(1, int(value)) for value in size)
        key = (id(surface), size)
        # idはオブジェクトを識別する値。元画像と出力サイズの両方でキャッシュを区別する。
        if key not in self.scaled:
            self.scaled[key] = pygame.transform.smoothscale(surface, size)
        return self.scaled[key]

    def card(self, card, size):
        # 通常札は分割済み画像を使い、素材にないジョーカーは図形と文字で画像を作る。
        if not card.joker:
            return self.resize(self.cards[card.suit, card.rank], size)
        key = ("joker", card.suit, tuple(size))
        if key not in self.scaled:
            surface = pygame.Surface(size, pygame.SRCALPHA)
            # SRCALPHAで背景が透ける描画面を作る。RGBの3値は赤・緑・青の強さ（0〜255）。
            # rectの幅指定を省略すると塗りつぶし、3を指定すると太さ3の枠になる。
            pygame.draw.rect(surface, (253, 242, 216), surface.get_rect(), border_radius=9)
            pygame.draw.rect(surface, (26, 41, 46), surface.get_rect(), 3, border_radius=9)
            ink = (180, 35, 55) if card.suit else (28, 46, 69)
            # 縦にJOKERと書く。//は小数部を切り捨てる割り算で、座標や文字サイズに使う。
            for index, letter in enumerate("JOKER"):
                glyph = self.font(size[1] // 8).render(letter, True, ink)
                # renderは文字を画像にし、blitはその画像を指定位置へ貼り付ける。
                surface.blit(glyph, (9, 6 + index * size[1] // 7))
            star = self.font(size[0] // 2).render("★", True, ink)
            surface.blit(star, star.get_rect(center=(size[0] * 0.65, size[1] * 0.53)))
            # get_rect(center=...)は画像の中心が指定位置になるように矩形を作る。
            self.scaled[key] = surface
        return self.scaled[key]
