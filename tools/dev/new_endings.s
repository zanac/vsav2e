| vsav2e: the endings of Donovan, Huitzil and Pyron (docs/endings.md). Assembled by
| tools/dev/assemble_new_endings.py into tools/build/new_endings_code.py; the build
| (tools/build/new_endings.py) puts the code in the program extension and writes the
| addresses of the EXTERNAL names where the assembled code has them.
|
| One engine plays the three endings: a timeline. Each ending is data (a header, built by
| new_endings.py): what to draw into the scroll layers and the palettes at which frame, which
| palettes fade (and by how much at each frame), and where the layers scroll at every frame.
| The text, its pages and their durations are the text pager's (Vampire Savior's code).
|
| The script is called every frame by the ending mode (hooked, endings.py); a5 is the game's
| RAM. $10(a5) is the step (0 set up, 2 the timeline, 4 the fade to black), $12(a5) the frame,
| $50(a5) a long, the next event. The header (a0 on entry):
|   0 events   4 channels   8 scroll tables   12 frames   16 music
| events: frame.w type.w pointer.l argument.l, ended by frame 0xffff
|   type 0: the cells of a list (n.w, then n of offset.w code.w attribute.w) into the layer
|           at the address `argument`; type 1: palette block at `pointer` (source.l,
|           destination.l, words.w) copied; type 2: the layer at `argument` filled with the
|           tile code in the low word of `pointer`.
| channels: first.w last.w block.l levels.l mode.w, ended by first 0xffff: from the first
|           to the last frame the block's palette is shown faded by levels[frame - first]
|           (0-15); mode 0 to black (15: as it is), mode 1 to white (0: as it is)
| scroll tables: four of `frames` words (scroll 2 x and y, scroll 3 x and y)
| EXTERNAL CREATE_TEXT
| EXTERNAL MUSIC
| EXTERNAL LEAVE
| EXTERNAL ALLOC_FAR
| EXTERNAL ALLOC_NEAR
| EXTERNAL FADE_OUT
        .equ CLASS_WALL, 0x01017c04    | Vampire Savior class 0x40 of the first pool (renumbered)
        .equ CLASS_WALL_B, 0x0100041f
        .equ FADE_DONE, 0x7402
        .equ ENDING_FRAME, 0xfec       | not $12(a5): the objects of the ending read that
        .equ NEXT_EVENT, 0xfe8        | a long in the game's RAM that nothing else uses
        .text
        .globl timeline
| entered with a0 = the ending's header (each ending has a stub that loads it)
timeline:
        move.w  0x10(%a5), %d0
        beq.s   set_up
        cmpi.w  #2, %d0
        beq.w   run
| step 4: the fade to black, then the ending is over
        tst.b   FADE_DONE(%a5)
        bne.s   finished
        jmp     LEAVE.l
finished:
        rts
set_up:
        addq.w  #2, 0x10(%a5)
        moveq   #0, %d0
        move.w  %d0, 0x16(%a5)
        move.w  %d0, ENDING_FRAME(%a5)
        move.w  #0xffc0, 0x22(%a5)       | the positions Vampire Savior's endings start with
        move.w  #0x100, 0x24(%a5)
        move.w  %d0, 0x2a(%a5)
        move.w  %d0, 0x2c(%a5)
        move.l  (%a0), NEXT_EVENT(%a5)
        move.w  #0x0b4e, 0x32(%a5)       | order: scroll 1, 3, 2, then the objects (the band hides the pictures)
        move.w  #0x2461, 0x3a(%a5)
        move.w  #0x90c0, 0x20(%a5)
        movem.l %a0, -(%sp)
        jsr     CREATE_TEXT.l
| the purple walls: an object whose sprites make the frame (Vampire Savior's endings
| make it so: class 4 of the pool, kind 2), and another one
        jsr     ALLOC_FAR.l
        beq.s   walls_done
        move.l  #CLASS_WALL, (%a4)
        move.b  #2, 0x39(%a4)
        move.b  #0, 9(%a4)
        move.w  #0xc0, 0x10(%a4)
        move.w  #0x80, 0x14(%a4)
        move.w  #0xe000, 0x1a(%a4)
        jsr     ALLOC_NEAR.l
        beq.s   walls_done
        move.l  #CLASS_WALL_B, (%a4)
walls_done:
        movem.l (%sp)+, %a0
        move.l  16(%a0), %d0
        jmp     MUSIC.l
run:
        movem.l %d2-%d7/%a2-%a4, -(%sp)
        move.w  ENDING_FRAME(%a5), %d7
| the scroll registers: four tables of `frames` words
        movea.l 8(%a0), %a1
        move.l  12(%a0), %d1
        add.l   %d1, %d1
        move.w  %d7, %d0
        add.w   %d0, %d0
        move.w  (%a1, %d0.w), 0x26(%a5)
        adda.l  %d1, %a1
        move.w  (%a1, %d0.w), 0x28(%a5)
        adda.l  %d1, %a1
        move.w  (%a1, %d0.w), 0x2a(%a5)
        adda.l  %d1, %a1
        move.w  (%a1, %d0.w), 0x2c(%a5)
| the channels: palettes faded at this frame
        movea.l 4(%a0), %a2
channel:
        move.w  (%a2), %d0
        cmpi.w  #-1, %d0
        beq.s   events
        cmp.w   %d7, %d0
        bhi.s   next_channel
        cmp.w   2(%a2), %d7
        bhi.s   next_channel
        move.w  %d7, %d0
        sub.w   (%a2), %d0
        movea.l 8(%a2), %a3
        moveq   #0, %d3
        move.b  (%a3, %d0.w), %d3
        move.w  12(%a2), %d4
        movea.l 4(%a2), %a3
        bsr.w   fade
next_channel:
        lea     14(%a2), %a2
        bra.s   channel
| the events whose frame has come
events:
        movea.l NEXT_EVENT(%a5), %a2
event:
        cmp.w   (%a2), %d7
        bcs.s   events_done
        movea.l 4(%a2), %a3
        movea.l 8(%a2), %a4
        move.w  2(%a2), %d0
        beq.s   put_cells
        cmpi.w  #1, %d0
        beq.s   copy_palette
| type 2: fill a layer with one tile
        move.w  %a3, %d0
        move.w  #4095, %d1
fill:
        move.w  %d0, (%a4)+
        clr.w   (%a4)+
        dbra    %d1, fill
        bra.s   next_event
put_cells:
        move.w  (%a3)+, %d1
        beq.s   next_event
        subq.w  #1, %d1
cell:
        move.w  (%a3)+, %d0
        move.w  (%a3)+, 0(%a4, %d0.w)
        move.w  (%a3)+, 2(%a4, %d0.w)
        dbra    %d1, cell
        bra.s   next_event
copy_palette:
        movea.l (%a3), %a1
        movea.l 4(%a3), %a4
        move.w  8(%a3), %d1
        subq.w  #1, %d1
copy:
        move.w  (%a1)+, (%a4)+
        dbra    %d1, copy
next_event:
        lea     12(%a2), %a2
        bra.s   event
events_done:
        move.l  %a2, NEXT_EVENT(%a5)
        movem.l (%sp)+, %d2-%d7/%a2-%a4
| the next frame, or the end
        addq.w  #1, ENDING_FRAME(%a5)
        move.w  ENDING_FRAME(%a5), %d0
        cmp.w   14(%a0), %d0
        bcs.s   not_yet
        addq.w  #2, 0x10(%a5)
        st      0x16(%a5)
        jmp     FADE_OUT.l
not_yet:
        rts
| a3 = a palette block (source.l, destination.l, words.w), d3 = the level 0-15, d4 = the mode:
| the palette shown, each component c of every word 0xfrgb scaled
fade:
        move.w  %d7, -(%sp)             | d7 is the frame, the components use it
        movea.l (%a3), %a1
        movea.l 4(%a3), %a4
        move.w  8(%a3), %d5
        subq.w  #1, %d5
fade_word:
        move.w  (%a1)+, %d0
        move.w  #0xf000, %d1
        moveq   #8, %d2
        bsr.s   fade_component
        moveq   #4, %d2
        bsr.s   fade_component
        moveq   #0, %d2
        bsr.s   fade_component
        move.w  %d1, (%a4)+
        dbra    %d5, fade_word
        move.w  (%sp)+, %d7
        rts
| d0 the word, d2 the shift of the component, d1 the word being made
fade_component:
        move.w  %d0, %d6
        lsr.w   %d2, %d6
        andi.w  #15, %d6
        tst.w   %d4
        bne.s   to_white
        mulu    %d3, %d6                | c * level / 15
        mulu    #17, %d6
        addi.w  #128, %d6
        lsr.w   #8, %d6
        bra.s   put_component
to_white:
        moveq   #15, %d7
        sub.w   %d6, %d7                | c + (15 - c) * level / 15
        mulu    %d3, %d7
        mulu    #17, %d7
        addi.w  #128, %d7
        lsr.w   #8, %d7
        add.w   %d7, %d6
put_component:
        lsl.w   %d2, %d6
        or.w    %d6, %d1
        rts
