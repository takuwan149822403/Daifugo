"""ボタンと選択ポップアップ。ゲームルールには依存しない。"""
import pygame

CREAM = (249, 237, 208)
GOLD = (229, 184, 80)


class Button:
    def __init__(self, rect, label, action, enabled=True, sprite=None):
        # Rectは位置と大きさをまとめる矩形。描画とクリック判定で同じ値を使う。
        self.rect = rect
        self.label = label
        self.action = action
        # enabled=Falseなら操作不可。spriteに番号があれば素材画像を使う。
        self.enabled = enabled
        self.sprite = sprite

    def draw(self, screen, assets, mouse):
        # collidepointはマウス座標が矩形内にあるかを返す。
        # 無効なボタンはマウスが重なってもhovered（強調表示）にしない。
        hovered = self.enabled and self.rect.collidepoint(mouse)
        if self.sprite is not None:
            # 素材に文字が入っているボタンなので、画像だけを表示する。
            screen.blit(assets.resize(assets.buttons[self.sprite], self.rect.size), self.rect)
            if hovered:
                pygame.draw.rect(screen, GOLD, self.rect, 3, border_radius=12)
            return
        # 素材がないボタンはpygameで描く。操作可能・マウス重なり・無効で色を変える。
        color = (37, 108, 82) if hovered else (15, 66, 53)
        if not self.enabled:
            color = (48, 57, 55)
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        # border_radiusは角の丸み。枠線と塗りつぶしは同じRectへ重ねる。
        pygame.draw.rect(screen, GOLD if self.enabled else (102, 111, 100), self.rect, 2, border_radius=10)
        text = assets.font(min(26, self.rect.height // 2)).render(self.label, True, CREAM if self.enabled else (145, 153, 146))
        screen.blit(text, text.get_rect(center=self.rect.center))


# Popupは選択画面の「内容・選択状況」を保持する。描画と入力処理はApplicationが担当。
class Popup:
    def __init__(self, kind, title, note, cards=None, count=1, moves=None):
        # kind: play=カード出し、exchange=交換、receive=交換確認、gift=7渡し。
        self.kind = kind
        self.title = title
        self.note = note
        if cards is None:
            self.cards = []
        else:
            self.cards = list(cards)
        self.count = count
        if moves is None:
            self.moves = []
        else:
            self.moves = list(moves)
        # __init__の中で作り、ポップアップごとに別の選択リストを持たせる。
        self.selected = []
        self.page = 0

    @property
    def page_count(self):
        # カード出し候補は1ページ4組、交換・7渡しのカード選択は1ページ16枚。
        per_page = 4 if self.kind == "play" else 16
        length = len(self.moves) if self.kind == "play" else len(self.cards)
        # 整数の割り算だけで切り上げる式。例えば17枚なら(17+16-1)//16で2ページ。
        # 空の一覧でも表示側が扱いやすいよう、ページ数を最低1にする。
        return max(1, (length + per_page - 1) // per_page)
