# vsav2e: Vampire Savior 2 with the full roster, in English (work in progress)

Private work repository for a CPS2 bootleg of *Vampire Savior 2: The Lord of Vampire*
(MAME set `vsav2`) with the characters that only *Vampire Hunter 2* (`vhunt2`) has —
Jon Talbain, Rikuo and Sasquatch — so all 18 Darkstalkers are in one set, translated into
English with the official texts of the PlayStation *Darkstalkers 3*.

Target: a `vsav2e` entry in [mame2003-plus](https://github.com/zanac/mame2003-plus-libretro).

This repository is private: it also holds material taken from the PlayStation game.

## Layout

| Path | What |
|---|---|
| `docs/analysis.md` | measurements of the two ROM sets: what differs, what each character weighs, what can be freed |
| `make_vsav2e.py` | builds `vsav2e.zip` (program chips) from `vsav2.zip` and `vsav.zip` |
| `tools/build/` | the build steps (region, language, win quotes) |
| `tools/cps2/` | CPS2 program loader, quote text format |
| `tools/dev/install_for_mame.py` | lays the build out as MAME's `vsav2d` for testing |
| `docs/text.md` | where the texts are and how they are translated |
| `tools/psx/`, `docs/psx.md` | tools and notes for the PlayStation Darkstalkers 3 |
| `tools/trace/` | MAME Lua tile tracer and the scripts that drive the game (forced characters, auto-win to the endings) |
| `tools/analysis/` | Python: loads and unshuffles the CPS2 graphics, renders tile sheets, attributes tiles to characters |

## Running the tracer

MAME 0.264 or later, the sets in `roms/` (`vsav2.zip`, `vhunt2.zip`; the QSound DSP ROM
`dl-1425.bin` in `roms/qsound_hle/` — a placeholder of the right size is enough, sound is
not needed). Outputs go to `work/`.

```
tools/trace/force.sh vhunt2 02 talbain      # fight as character 0x02, trace 6000 frames
tools/trace/endrun.sh vsav2 05             # auto-win to character 0x05's ending
```
