| vsav2e: the challenger of a versus match picks the stage on the select grid.
| The source of the routines that tools/build/versus_stage.py writes as hex, to check
| them with GNU as (same bytes, given the same addresses):
|   m68k-linux-gnu-as -m68000 --defsym STEPS=<steps> --defsym STAGE_OF_CELL=<stages> \
|       --defsym STAGE_SECONDS=10 --defsym BUTTON_WAIT=16 --defsym NAME_X=0xc0 \
|       --defsym NAME_Y=0x18 --defsym NAME_OTHER=<title_frame> -o stage.o versus_stage.s
|   m68k-linux-gnu-objcopy -O binary stage.o stage.bin
| Order: cursor_hook (jumped to from 0x1f5e6), confirm_hook (from 0x1f65e), name_frame
| (from 0x6c67e), stage_apply (from 0x970a).
        .equ STATE, 0x3f0
        .equ STAGE_CELL, 0x3f1
        .equ SAVED_CELL, 0x3f2
        .equ SAVED_CHARACTER, 0x3f3
        .equ SAVED_BUTTONS, 0x3f4
        .equ CHOSEN_STAGE, 0x3f6
        .equ CHOOSER, 0x3f8
        .equ LAST_VALID, 0x1000
        .equ LAST_CELL, 0x0c80
        .equ CELLS, 0x14
        .equ RANDOM_CELL, 0x0b
        .equ NO_COUNTDOWN, 11
        .equ MARK, 0x5354
        .equ MARK_FIELD, 0x40
        .text
cursor_hook:
        cmpi.b  #1, STATE(%a5)
        bne.s   1f
        move.b  0x381(%a6), %d0
        cmp.b   CHOOSER(%a5), %d0
        beq.s   stage_mode
1:      subq.b  #1, 0x27(%a6)
        bne.s   2f
        jmp     0x1f5ec
2:      jmp     0x1f5fc
stage_mode:
        subq.b  #1, 0x27(%a6)
        bne.s   3f
        move.b  #0x3c, 0x27(%a6)
        subq.b  #1, 0x26(%a6)
        bmi.s   choose
3:      tst.b   0x39(%a6)
        beq.s   4f
        subq.b  #1, 0x39(%a6)
4:      move.w  0x396(%a6), %d0
        not.w   %d0
        and.w   0x394(%a6), %d0
        move.w  %d0, %d2
        tst.b   0x39(%a6)
        bne.s   5f
        andi.w  #0x7700, %d0
        bne.s   choose
5:      andi.w  #0xf, %d2
        lea     0x1fe2c, %a0
        moveq   #0, %d1
        move.b  0(%a0,%d2.w), %d1
        bmi.s   6f
        moveq   #0, %d0
        move.b  3(%a6), %d0
        lsl.w   #3, %d0
        movea.l #0x1588e, %a0
        adda.w  %d0, %a0
        move.b  0(%a0,%d1.w), 3(%a6)
6:      move.b  3(%a6), STAGE_CELL(%a5)
        rts
choose:
        moveq   #0, %d0
        move.b  3(%a6), %d0
        lea     STAGE_OF_CELL, %a0
        move.b  0(%a0,%d0.w), %d0
        ext.w   %d0
        move.w  %d0, CHOSEN_STAGE(%a5)
        move.b  #2, STATE(%a5)
        move.b  SAVED_CELL(%a5), 3(%a6)
        move.b  SAVED_CHARACTER(%a5), 0x382(%a6)
        move.w  SAVED_BUTTONS(%a5), %d0     | falls through

confirm_original:
        clr.b   0x3c1(%a6)
        cmpi.b  #0xb, 3(%a6)
        jmp     0x1f668

confirm_hook:
        move.b  0x8d(%a5), %d2
        or.b    0xac(%a5), %d2
        cmpi.b  #3, %d2
        bne.s   confirm_original
        tst.b   STATE(%a5)
        bne.s   confirm_original
        move.b  0x381(%a6), %d1
        move.b  0x8d(%a5), %d2
        cmpi.b  #1, %d2
        beq.s   player_1_joined
        cmpi.b  #2, %d2
        beq.s   player_2_joined
        lea     0x400(%a5), %a0
        tst.b   %d1
        bne.s   7f
        lea     0x800(%a5), %a0
7:      tst.b   4(%a0)
        beq.s   confirm_original
        bra.s   chooser
player_1_joined:
        tst.b   %d1
        bne.s   confirm_original
        bra.s   chooser
player_2_joined:
        tst.b   %d1
        beq.s   confirm_original
chooser:
        move.b  #1, STATE(%a5)
        move.b  %d1, CHOOSER(%a5)
        move.b  3(%a6), SAVED_CELL(%a5)
        moveq   #RANDOM_CELL, %d2
        tst.b   LAST_VALID(%a5)
        beq.s   12f
        tst.b   0x383(%a6)
        beq.s   12f
        move.b  LAST_CELL(%a5), %d2
12:     move.b  %d2, 3(%a6)
        move.b  %d2, STAGE_CELL(%a5)
        move.b  0x382(%a6), SAVED_CHARACTER(%a5)
        move.w  %d0, SAVED_BUTTONS(%a5)
        move.b  #STAGE_SECONDS, 0x26(%a6)
        move.b  #0x3c, 0x27(%a6)
        move.b  #BUTTON_WAIT, 0x39(%a6)
        jsr     0x15702
        beq.s   8f
        move.l  #0x0100071a, (%a4)
        move.w  #MARK, MARK_FIELD(%a4)
8:      rts

name_frame:
        cmpi.w  #MARK, MARK_FIELD(%a6)
        bne.s   10f
        tst.b   STATE(%a5)
        beq.s   9f
        moveq   #0, %d1
        move.b  STAGE_CELL(%a5), %d1
        moveq   #NO_COUNTDOWN, %d2
        cmpi.b  #1, STATE(%a5)
        bne.s   14f
        lea     0x400(%a5), %a0
        tst.b   CHOOSER(%a5)
        beq.s   13f
        lea     0x800(%a5), %a0
13:     move.b  0x26(%a0), %d2
        cmpi.b  #10, %d2
        bls.s   14f
        moveq   #10, %d2
14:     mulu.w  #CELLS, %d2
        add.w   %d2, %d1
        lsl.w   #3, %d1
        lea     STEPS, %a0
        adda.w  %d1, %a0
        move.l  %a0, 0x1c(%a6)
        move.w  #NAME_X, 0x10(%a6)
        move.w  #NAME_Y, 0x14(%a6)
        jmp     0x13c3a
9:      clr.w   MARK_FIELD(%a6)
        move.b  #4, 4(%a6)
        rts
10:     jmp     NAME_OTHER

stage_apply:
        cmpi.b  #2, STATE(%a5)
        bne.s   11f
        tst.w   CHOSEN_STAGE(%a5)
        bmi.s   11f
        move.w  CHOSEN_STAGE(%a5), %d0
11:     cmpi.b  #2, STATE(%a5)
        bne.s   15f
        move.b  STAGE_CELL(%a5), LAST_CELL(%a5)
        move.b  #1, LAST_VALID(%a5)
15:     clr.b   STATE(%a5)
        move.w  %d0, 0x100(%a5)
        rts
