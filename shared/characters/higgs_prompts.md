# Higgsfield 生成用プロンプト（Aちゃん・ちゃみうさぎ）

## 使い方
1. 参照画像として `girl_sheet.jpg`（Aちゃん）と `bunny_sheet.jpg`（ちゃみうさぎ）の2枚をアップロードする
   - 参照画像を複数入れられるモデルを選ぶと、キャラの見た目が崩れにくい
2. 下の「共通の指示」と、作りたいポーズのプロンプトをつなげて貼る
3. 1つのプロンプトにつき3〜4枚生成して、いちばん設定画に近いものを選ぶ
4. 選んだ画像をClaudeに渡すと、切り抜き・ピンク版の作成・包装紙とカードへの差し替えまで進める

## 共通の指示（毎回プロンプトの先頭に付ける）
```
Use the two reference sheets as the exact character designs. Do not change their designs.
Character 1 "A-chan": girl with long straight black hair, blunt bangs with a pink wavy highlight line,
white headphones with small wings and a pink star on the ear cups, light blue cropped short-sleeve top with
pink trim and a pink sparkle mark, grey wide-leg pants with pink panel lines, chunky white sneakers.
Big eyes with sparkle highlights, small freckles under the eyes.
Character 2 "Chami-usagi": plush-toy style bunny with long floppy ears, light blue and beige patchwork,
black eyes with white diamond sparkles and tear marks, ":3" mouth, yellow scalloped cape collar,
fluffy yellow pom-pom tail, dashed stitch lines.
Style: same as the reference sheets — hand-drawn dark purple outlines, flat pastel colors, soft cel shading.
Full body, plain white background, no text, no logo, no extra characters.
```

## ポーズ案

### 1. ぎゅっと抱っこ（カード表面向け）
```
A-chan hugging Chami-usagi tightly against her chest with both arms, cheek pressed against the bunny's head,
eyes closed, small happy smile. Chami-usagi looks content. Slight three-quarter view.
```

### 2. いっしょに手を振る
```
A-chan standing relaxed with weight on one leg, waving at the viewer with a shy small smile.
Chami-usagi sits on her shoulder, also waving one paw, ears bouncing.
```

### 3. ステッキでキラキラ
```
A-chan holding the winged star wand from the reference sheet up high, one eye winking, confident smile,
small sparkles around the wand tip. Chami-usagi jumps beside her with paws raised in excitement.
```

### 4. プレゼントの箱からのぞく（忘年会向け）
```
A-chan and Chami-usagi peeking out together from a large pink gift box with a white ribbon,
both with surprised happy expressions, hands and paws resting on the box edge.
```

### 5. ちゃみうさぎ単体：ぴょんと跳ねる
```
Chami-usagi alone, mid-jump with all four paws spread and ears flying up, joyful expression,
small motion lines. No A-chan in this image.
```

### 6. Aちゃん単体：座ってヘッドホン
```
A-chan alone sitting cross-legged on the floor, one hand pressing her headphones, eyes half closed,
calm content expression as if enjoying music. No bunny in this image.
```

## 包装紙に散らす用（小さく使うポーズ）
包装紙では1体3〜6cmで印刷するので、シルエットがはっきりしたポーズが向いている。上の2・3・5・6がおすすめ。
印刷に使うので、長い辺が2000px以上になる設定で生成する。
