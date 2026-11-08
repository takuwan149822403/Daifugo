# 教材から大富豪のソースへ

隣接する `../pygame` の教材を踏まえ、まず `cards.py` → `players.py` → `judge.py` → `game.py` の順に読めるようにしています。教材を配置していない環境でも、ゲームの起動には影響しません。画面を起動しなくても、カードや判定だけを動かせます。

## 教材との対応

| 教材 | このゲームで使うところ |
| --- | --- |
| [06_function](../../pygame/06_function/README.md) | 引数を受け取り、判定結果を `return` するメソッド |
| [11_multidimensional_list](../../pygame/11_multidimensional_list/README.md) | 手札のリスト、カードの組のタプル、数字別の辞書 |
| [15_class](../../pygame/15_class/README.md) | `__init__` と `self`、`Player` を継承する `NPCPlayer` |
| [18_module](../../pygame/18_module/README.md) | `from cards import Hand`、`random` の利用 |
| [19_shooting_game_class_ver](../../pygame/19_shooting_game_class_ver/README.md) | データと処理をクラスにまとめ、役割ごとにファイルを分ける |
| [文法リファレンス・発展](../../pygame/docs/python_grammar/03_advanced.md) | 並べ替えの `key` に関数を渡す考え方 |

通常のクラスと `__init__` で属性を用意します。山札の生成や判定は、`for` と `if` で処理を順に追えるようにしています。並べ替えの基準にも `lambda` の代わりに名前を付けた関数を使っています。

## 1. Card：カード1枚の情報を持つ

`src/cards.py` の `Card(0, 3)` はスペード3です。`suit` はマーク、`rank` は数字で、14はジョーカーを表します。

`__init__` では、画面に表示する `label` と、比較に使う `strength` も用意します。Aは数字が1でも強さは14、2は強さが15です。ジョーカーの99は、通常札より大きくするための値です。

作ったカードの属性は変更しない約束です。交換・カード出しでは、カード自体を書き換えず、手札のリストから取り除いたり、別の手札へ加えたりします。`Move` も作成後に属性を変更しません。変更禁止をPythonに強制させる仕組みは設けていません。

## 2. DeckとHand：カードをリストで管理する

`Deck.__init__` は、マーク4種類と数字13種類の二重ループで52枚を作り、ジョーカー2枚を加えます。`deal` は山札をシャッフルした後、配る相手の番号を1つずつ進め、最後の人の次は0番へ戻します。

`Hand` は手札のリストを持ちます。`add` は追加、`remove` は削除、`strongest` は強い札の取得です。`strongest` はコピーを使うので、取得しても元の手札は減りません。

`can_remove` もコピーから1枚ずつ取り除いて確認します。同じ札を2回指定すると、2回目にはコピーに残っていないので `False` になります。実際に移動する前に確認するため、途中まで交換して止まることを防げます。

`sort(key=card_sort_key)` は、各カードについて `card_sort_key(card)` の戻り値を調べて並べます。戻り値が `(強さ, マーク)` なので、強さが等しければマークの番号で順番を決めます。

## 3. MoveとJudge：出し方を確認する

`Card` は1枚、`Move` は1回で出す札の組です。通常は `Move` を直接作らず、`Judge.make_move` にカードを渡します。

`make_move` は次の順に確認します。

1. 1〜4枚であるか。
2. 同じ札を重複して指定していないか。
3. ジョーカー以外の数字がそろっているか。

違反があれば `None`、有効なら `Move` を返します。ジョーカーを含む組の `rank` は通常札の数字、ジョーカーだけなら14です。

`beats` は、有効な組どうしを比較します。空の場、枚数違い、スペード3返し、ジョーカーの特例を先に確認し、最後に通常札の強さを比べます。革命・イレブンバックによる逆順なら、小さい強さの札が勝ちます。

`legal_moves` は、手札を数字別に分け、各数字の札とジョーカーから候補を作ります。`make_move` と `beats` を通して、出せる候補だけをリストに追加します。ジョーカーだけの候補は、数字14を調べるときに一度だけ追加します。

## 4. 教材から追加で覚えること

### combinations：組み合わせを選ぶ

組み合わせを作る部分には、標準ライブラリの `itertools.combinations` を使っています。自分で再帰や複雑な選択処理を書く必要はありません。

```python
from itertools import combinations

for pair in combinations(["スペード6", "ハート6", "ジョーカー"], 2):
    print(pair)
```

結果は次の3組です。選ぶ順番だけが違う組は作りません。

```text
('スペード6', 'ハート6')
('スペード6', 'ジョーカー')
('ハート6', 'ジョーカー')
```

### __eq__と__len__：Pythonから呼ばれるメソッド

`__init__` と同じように、決まった場面でPythonが呼ぶメソッドがあります。

- `__eq__` は `==` の比較に使われます。`Card(0, 3) == Card(0, 3)` を、マークと数字が同じなので `True` にします。リストの `in` や `remove` でも使われます。`Move` はカードの組と数字で比較します。
- `__len__` は `len(hand)` に使われます。`if hand` でも枚数が調べられ、0枚なら `False` になります。

`isinstance(other, Card)` は、相手がCardかどうかを確認します。比較対象が違う種類なら `NotImplemented` を返し、Pythonに比較を任せます。これは例外を発生させる命令ではありません。

CardやMoveの重複確認にはリストを使っています。集合で重複を除きたい場合は、カードそのものではなく `(card.suit, card.rank)` のタプルを使えます。

### random.Random：再現できる乱数

教材の `random.choice(...)` と同じように、`rng.choice(...)` で候補を選べます。`rng = random.Random(1)` のように番号を渡すと、同じ操作をしたときに同じ乱数の列を再現できるため、テストに使っています。

### @property：現在の状態から値を計算する

`Game.reversed_order` と `Popup.page_count` には `@property` が残っています。メソッドですが、括弧を付けずに値を取得できます。

たとえば `game.reversed_order` を読むと、その時点の革命とイレブンバックから逆順かを計算します。状態が途中で変わるため、初期化時に一度保存する方法とは使い分けています。

## 5. 画面を使わず試す

プロジェクトのルートで、次のコマンドからPythonを開きます。

```sh
PYTHONPATH=src .venv/bin/python
```

以下を順に入力できます。

```python
from cards import Card, Hand
from judge import Judge

hand = Hand([Card(0, 6), Card(1, 6), Card(0, 14)])
judge = Judge()
pair = judge.make_move([Card(0, 6), Card(0, 14)])
print(pair.label)  # ♠6  JOKER
print(pair.count)  # 2
print(pair.rank)   # 6

invalid = judge.make_move([Card(0, 6), Card(1, 7)])
print(invalid)  # None

top = judge.make_move([Card(0, 5), Card(1, 5)])
for move in judge.legal_moves(hand, top):
    print(move.label)
# ♠6  JOKER
# ♠6  ♥6
# ♥6  JOKER
```

この後は `game.py` の `play` を読むと、「札を出す → 役を調べる → 必要なら7渡しを待つ → 上がりと次のターンを決める」という流れにつながります。
