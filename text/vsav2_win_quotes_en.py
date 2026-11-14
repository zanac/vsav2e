"""English win quotes for the three characters whose quotes were written for Vampire
Savior 2 (Capcom's English Vampire Savior has none for them): Huitzil, Pyron and
Donovan. Translated from the Japanese of the arcade game, read by drawing the text with
the game's own font.

Keyed by character id; 16 quotes each, every quote with the original number of lines
(at most 30 letters per line). The Japanese is in the comments.
"""

HUITZIL, PYRON, DONOVAN = 0x10, 0x11, 0x13

QUOTES = {
    # Huitzil speaks as a machine log (katakana, every quote starting with 》).
    HUITZIL: [
        # セーフティエリア 確保 / 進路ヲ 検索中：
        ['Safety area secured.', 'Searching for a route...'],
        # 敵 戦闘能力 ブンセキ / 類型データ ニ 格納中：
        ['Enemy combat ability analyzed.', 'Storing as pattern data...'],
        # 現在 特別コード ニテ 作動中 / 保護対象ノ 生命維持 最優先：
        ['Now running on special code.', "Ward's life is top priority."],
        # 敵戦力 ゼジャク / 生命反応 急激ニ低下：
        ['Enemy strength is weak.', 'Life signs dropping fast.'],
        # 索敵 オヨビ / 早期警戒モード 持続：
        ['Search and early warning', 'mode continuing.'],
        # 敵 完全破壊 / 戦闘ノ 継続不能：
        ['Enemy fully destroyed.', 'Combat cannot continue.'],
        # 未知エネルギー 異常増大 / 警戒レベル４ 撤退ヲ推奨：
        ['Unknown energy rising.', 'Alert four. Retreat advised.'],
        # 自動修復モード ON / 引キツヅキ 索敵ヲ続行：
        ['Auto-repair mode ON.', 'Continuing the search.'],
        # 索敵レンジ内ニ 複数ノ 生体反応 / 警戒ヲ要ス 警戒ヲ要ス：
        ['Many life signs in range.', 'Caution. Caution.'],
        # 熱源追跡 開始‥‥‥ / 目標ヨリ 離脱セシ 反応 ナシ：
        ['Heat source tracking begun...', 'No sign of the target fleeing.'],
        # ボディ ニ レベル６ノ 損傷 / ２００秒ノ 修復時間ヲ 要ス：
        ['Level six damage to the body.', 'Two hundred seconds to repair.'],
        # 保護対象 ニ 異常ナシ：
        ['The ward is unharmed.'],
        # 有視界内ニ 敵影 反応ナシ / 警戒レベル ２ ニ 移行：
        ['No enemy in visual range.', 'Moving to alert level two.'],
        # 命令待機中： / 命令待機中：
        ['Awaiting orders.', 'Awaiting orders.'],
        # 迎撃システム 正常ニ 作動中：
        ['Intercept system working.'],
        # 敵戦力 解析不能 / データ不足 データ不足：
        ['Enemy strength unknown.', 'Not enough data. No data.'],
    ],
    PYRON: [
        # 砕け散る命は美しい / 新星にも似た至宝の輝きだよ
        ['A shattering life is beautiful', "A jewel's glow, like a nova."],
        # 美は守られるべきだ / 絶対の力によってね
        ['Beauty must be protected.', 'By absolute power, that is.'],
        # 時の流れとは無粋なものだ / ほとんどの美をくだらぬゴミにする
        ['The flow of time is so crude.', 'It turns most beauty to trash.'],
        # 勝利に最大の価値を見出せないのは / 私の数少ない不幸ではあるな
        ['Finding no value in victory', 'is one of my few misfortunes.'],
        # せめて楽しみたまえ / いずれ君はそれすらできなくなる
        ['Enjoy it while you can.', 'Soon even that will be gone.'],
        # 大宇宙の原理にそぐわぬ者は / ただ消滅するしかない
        ['Those who defy the cosmos', 'can only vanish.'],
        # この私の力が抑制されるとは‥‥ / 興味深い空間だ
        ['My own power, held back...', 'What an interesting space.'],
        # お前たちの言う「魂の力」‥‥ / わずかだが理解できるよ
        ['Your so-called power of souls', 'I begin to understand it.'],
        # 滅ぶために戦うというのか / まあいい、退屈な勝者に用はない
        ['You fight only to perish?', 'Fine. Dull winners bore me.'],
        # 勝利が目的ではない、しかし / 負けてやるほど寛大でもないのだ
        ['Victory is not my goal, but', 'I am not so kind as to lose.'],
        # 全てを超越した私に / 負ける要因があろうはずがない
        ['I have transcended all.', 'There is no way I could lose.'],
        # 物質として / 君たちに勝機はないのだよ
        ['As mere matter,', 'you have no chance to win.'],
        # １５０億年の歴史の前では / 君の命などチリに等しい
        ['Before fifteen billion years,', 'your life is but dust.'],
        # 結果はともかく / 過程はそれなりに楽しめたよ
        ['Whatever the result,', 'I rather enjoyed the process.'],
        # 輝け‥‥そして散るのだ
        ['Shine... and then scatter.'],
        # 肉体という弱点がある限り / 究極生命体にはなれぬのだ
        ['While bound to a body, you', "can't be the ultimate life."],
    ],
    DONOVAN: [
        # 私はダークハンター / すべての闇を滅する！
        ['I am a Dark Hunter.', 'I destroy all darkness!'],
        # アニタよ‥‥これがお前の / 望む未来だというのか
        ['Anita... is this the future', 'that you wish for?'],
        # 必ず戻ってみせる‥‥ / 光ある世界に！
        ['I will return, I swear...', 'to the world of light!'],
        # しょせんは幻 / この私を惑わすことはできぬ
        ['A mere illusion.', 'It cannot lead me astray.'],
        # 魔道とは己の心に巣食う闇 / 私は堕ちぬ、人の血に賭けて
        ['Evil is the dark in the heart.', "I'll not fall. I am human too."],
        # 一筋の希望を捨てぬのが人 / この絶望にさえ光は届くのだ
        ['Humans never give up hope.', 'Light reaches even despair.'],
        # 幻ならそれでいい / 一片の情けも要らぬというもの
        ['If an illusion, so be it.', 'Then I need show no mercy.'],
        # 世を捨て、心を捨てた私に、 / 今また誇りさえも捨てよと言うのか
        ['I gave up the world, my heart.', 'Must I give up my pride too?'],
        # 立ち向かうこと / すべてはそこから始まる
        ['To stand and face it.', 'Everything begins from there.'],
        # お前たちもまた / この闇にとらわれし罪人なのか
        ['Are you, too, sinners', 'trapped in this darkness?'],
        # どうした！ / その程度では我が心は揺るがぬぞ！
        ["What's wrong!", "That won't shake my heart!"],
        # この悪夢から覚めるとき / 私は何を思うのだろうか
        ['When I wake from this dream,', 'what will I be thinking?'],
        # たとえこの身が滅びようと / お前たちに屈しはしない！
        ['Even if my body perishes,', 'I will not yield to you!'],
        # この怖気とも歓喜ともつかぬ震え / 魔族の血がなせるワザなのか
        ['This shiver of dread or joy...', "Is it my demon blood's doing?"],
        # 私は、私の信じる道を行く / 先に地獄が待っていようと
        ['I walk the path I believe in.', 'Even if hell waits ahead.'],
        # 神も悪魔も / 私の罪を赦しはしない
        ['Neither god nor devil', 'will forgive my sins.'],
    ],
}
