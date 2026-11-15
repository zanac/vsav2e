"""The endings of Donovan, Huitzil and Pyron, assembled from tools/dev/new_endings.s by
tools/dev/assemble_new_endings.py (do not edit). RELOCATIONS: where the build writes the
address of each external (a long); LABELS: the offsets of the entry points."""

CODE = bytes.fromhex(
    '302d001067160c4000026700009a4a2d740266064ef97e0201014e75546d001070003b4000163b400fec3b7cffc00022'
    '3b7c010000243b40002a3b40002c2b500fe83b7c0b4e00323b7c2461003a3b7c90c0002048e700804eb97e0001014eb9'
    '7e030101673228bc01017c04197c00020039197c00000009397c00c00010397c00800014397ce000001a4eb97e040101'
    '670628bc0100041f4cdf0100202800104ef97e01010148e73f383e2d0fec226800082228000cd2813007d0403b710000'
    '0026d3c13b7100000028d3c13b710000002ad3c13b710000002c2468000430120c40ffff672ab0476220be6a0002621a'
    '30079052266a0008760016330000382a000c266a00046100008845ea000e60ce246d0fe8be526552266a0004286a0008'
    '302a000267160c4000016726300b323c0fff38c0425c51c9fffa6028321b67245341301b399b0000399b000251c9fff4'
    '60122253286b0004322b0008534138d951c9fffc45ea000c60aa2b4a0fe84cdf1cfc526d0fec302d0fecb068000e650e'
    '546d001050ed00164ef97e0501014e753f072253286b00043a2b000853453019323cf000740861127404610e7400610a'
    '38c151cdffea3e1f4e753c00e46e0246000f4a44660eccc3ccfc001106460080e04e60127e0f9e46cec3cefc00110647'
    '0080e04fdc47e56e82464e75'
)

RELOCATIONS = [(22, 'LEAVE'), (90, 'CREATE_TEXT'), (96, 'ALLOC_FAR'), (140, 'ALLOC_NEAR'), (162, 'MUSIC'), (394, 'FADE_OUT')]

LABELS = {'cell': 322, 'channel': 222, 'copy': 350, 'copy_palette': 338, 'event': 276, 'events': 272, 'events_done': 362, 'fade': 400, 'fade_component': 442, 'fade_word': 414, 'fill': 306, 'finished': 26, 'next_channel': 266, 'next_event': 356, 'not_yet': 398, 'put_cells': 316, 'put_component': 486, 'run': 166, 'set_up': 28, 'timeline': 0, 'to_white': 468, 'walls_done': 152}
