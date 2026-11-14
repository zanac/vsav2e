"""English for the texts written for Vampire Savior 2 (they are not in Vampire Savior, so
Capcom never translated them): the two endings and Jedah's words before the last fight.
Translated from the Japanese of the arcade game; the terms follow Capcom's English
(Majigen, Makai, "Fetus of God" for the stage and the body Jedah prepared).

Each quote is a list of lines; the line counts are the original ones. A line of the
endings holds at most 24 letters (several lines are on screen at once, and longer
ones crash the game); the other lines at most 30, like Capcom's.
"""

# The ending (one line per quote, scrolling over the pictures).
# 冥王ジェダの「救済」の儀式は / 失敗に終わった。 ...
ENDING = [
    ['Jedah\'s "salvation" rite'],
    ['ended in failure.'],
    ['This space, the Majigen,'],
    ['vanished with Jedah.'],
    ['But his "Fetus of God"'],
    ['still kept its form.'],
    ['In the near future...'],
    ['after but a short sleep,'],
    ['the Dark Lord will rise.'],
    ['He has a mission.'],
    ['To make all souls one,'],
    ['and to turn the "Makai"'],
    ['into one perfect being.'],
    ['Life longs to go back'],
    ['to when all was one.'],
    ['While that wish lives,'],
    ['the savior will return.'],
    ['Again and again...'],
]

# The ending when Jedah himself wins.
# 戦いの末、最後に残ったジェダの姿。 ...
ENDING_JEDAH = [
    ['Only Jedah was left.'],
    ['Was this no illusion,'],
    ['but his true soul?'],
    ['The Majigen was done,'],
    ['ready for worthy souls.'],
    ['It only remained to make'],
    ['the "Fetus of God".'],
    ['And now, toward Makai,'],
    ['the Dark Lord speaks.'],
    ['"All souls, join me.'],
    [' That is salvation."'],
]

# Jedah before the last fight.
# ようこそわが「神体」の間へ / 完全復活に必要な魔次元も もうすぐ完成する ...
JEDAH_WELCOME = [
    ['Welcome to my Fetus of God.'],
    ['The Majigen my rebirth needs', 'is almost complete.'],
    ['You have earned the right', 'to be its foundation.'],
    ['Now gratefully accept', 'my mercy...!'],
]

# Jedah before the last fight, when the player is Jedah too.
# ようこそわが「神体」の間へ / 君はなにか大きな間違いを おかしているようだ ...
JEDAH_WELCOME_TO_JEDAH = [
    ['Welcome to my Fetus of God.'],
    ['You seem to be making', 'a grave mistake.'],
    ['That form is a phantom of me,', 'a ghost born of the Majigen.'],
    ['In short, you are one', 'who must vanish here.'],
]
