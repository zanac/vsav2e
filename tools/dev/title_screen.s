| vsav2e: the Darkstalkers 3 title screen of the PlayStation (zoom, white flash, logo).
| The source of the routines that tools/build/title_screen.py writes as hex, to check
| them with GNU as. --defsym: STEPS, PALETTES, BLEND (extension addresses), LOGO_X,
| LOGO_Y, LOGO_PALETTE_BYTES, LOGO_PALETTE_RAM, LOGO_PALETTE_WORDS, INSERT_COIN_Y and
| NAME_FALLBACK: the build puts the name object's own work there in place of the jump.
| Order: title_dispatch (from 0x6b66), clear_text (from 0x6bd0, 0x6bde), title_frame
| (the name object's work when it is not the stage choice's).
        .equ MARK_FIELD, 0x40
        .equ TITLE_MARK, 0x544c
        .equ COUNTER, 0x42
        .equ SCENE, 0x44
        .equ SAVED, 0x60
        .equ ZOOM_FRAMES, 8
        .equ FLASH_FRAMES, 15
        .equ ARRIVAL_FRAMES, 25
        .equ COPYRIGHT_PALETTE, 0x90c7e0
        .equ BACKDROP, 0x90dffe
        .equ BLANK_TEXT, 0x00200000
        .text
| the title scene's states: 0 the game's set up, 2 and 4 the arrival, then the game's
title_dispatch:
        move.w  8(%a5), %d0
        beq.s   9f
        cmpi.w  #10, %d0
        bcc.s   9f
        cmpi.w  #2, %d0
        bne.s   2f
        move.w  #0x90c0, 0x20(%a5)
        jsr     0x15702
        beq.s   1f
        move.l  #0x0100071a, (%a4)
        move.w  #TITLE_MARK, MARK_FIELD(%a4)
        clr.w   COUNTER(%a4)
        move.w  4(%a5), SCENE(%a4)
1:      jsr     0x6de2
        move.w  #ARRIVAL_FRAMES, 0xa(%a5)
        move.w  #4, 8(%a5)
        rts
2:      subq.w  #1, 0xa(%a5)
        bne.s   3f
        move.w  #10, 8(%a5)
3:      rts
9:      lea     0x6b72, %a0
        move.w  0(%a0,%d0.w), %d1
        jmp     0(%a0,%d1.w)

| a1: 0x1000 bytes of the text layer, made blank (in place of the band)
clear_text:
        move.w  #0x3ff, %d0
1:      move.l  #BLANK_TEXT, (%a1)+
        dbra    %d0, 1b
        rts

| the logo object (the stage name object, marked)
title_frame:
        cmpi.w  #TITLE_MARK, MARK_FIELD(%a6)
        bne.w   fallback
        move.w  4(%a5), %d0
        cmp.w   SCENE(%a6), %d0
        beq.s   1f
        clr.w   MARK_FIELD(%a6)
        move.b  #4, 4(%a6)
        rts
1:      movem.l %d2-%d7/%a2, -(%a7)
        move.w  COUNTER(%a6), %d2
        moveq   #ZOOM_FRAMES, %d1
        cmp.w   %d1, %d2
        bcc.s   2f
        move.w  %d2, %d1
2:      lsl.w   #3, %d1
        lea     STEPS, %a0
        adda.w  %d1, %a0
        move.l  %a0, 0x1c(%a6)
        move.w  #LOGO_X, 0x10(%a6)
        move.w  #LOGO_Y, 0x14(%a6)
        moveq   #0, %d3
        move.w  %d2, %d0
        subq.w  #ZOOM_FRAMES-1, %d0
        ble.s   3f
        cmpi.w  #FLASH_FRAMES+1, %d0
        bhi.s   3f
        cmpi.w  #FLASH_FRAMES, %d0
        bls.s   14f
        moveq   #FLASH_FRAMES, %d0
14:     move.w  %d0, %d3
3:      cmpi.w  #ZOOM_FRAMES, %d2
        bne.s   4f
        lea     COPYRIGHT_PALETTE, %a0
        lea     SAVED(%a6), %a1
        moveq   #15, %d7
5:      move.w  (%a0)+, (%a1)+
        dbra    %d7, 5b
        move.w  BACKDROP, (%a1)
4:      move.w  %d3, %d0
        mulu.w  #LOGO_PALETTE_BYTES, %d0
        lea     PALETTES, %a0
        adda.l  %d0, %a0
        lea     LOGO_PALETTE_RAM, %a1
        move.w  #LOGO_PALETTE_WORDS-1, %d7
6:      move.w  (%a0)+, (%a1)+
        dbra    %d7, 6b
        tst.w   %d3
        beq.s   8f
        lea     BLEND, %a2
        lsl.w   #4, %d3
        adda.w  %d3, %a2
        lea     SAVED(%a6), %a0
        lea     COPYRIGHT_PALETTE, %a1
        moveq   #15, %d7
7:      move.w  (%a0)+, %d0
        bsr.s   whiten
        move.w  %d0, (%a1)+
        dbra    %d7, 7b
        move.w  (%a0), %d0
        bsr.s   whiten
        move.w  %d0, BACKDROP
        bra.s   10f
8:      cmpi.w  #ARRIVAL_FRAMES-1, %d2
        bne.s   10f
        lea     SAVED(%a6), %a0
        lea     COPYRIGHT_PALETTE, %a1
        moveq   #15, %d7
11:     move.w  (%a0)+, (%a1)+
        dbra    %d7, 11b
        move.w  (%a0), BACKDROP
10:     cmpi.w  #0x7fff, %d2
        bcc.s   12f
        addq.w  #1, COUNTER(%a6)
12:     cmpi.w  #0x0310, 0x7202(%a5)
        bne.s   13f
        move.w  #INSERT_COIN_Y, 0x7214(%a5)
13:     movem.l (%a7)+, %d2-%d7/%a2
        jmp     0x13c3a

| d0: a colour, made whiter by the blend row at a2 (brightness full)
whiten:
        moveq   #0, %d4
        moveq   #2, %d6
        rol.w   #4, %d0
1:      lsl.w   #4, %d4
        rol.w   #4, %d0
        move.w  %d0, %d5
        andi.w  #0xf, %d5
        or.b    0(%a2,%d5.w), %d4
        dbra    %d6, 1b
        ori.w   #0xf000, %d4
        move.w  %d4, %d0
        rts
fallback:
        jmp     NAME_FALLBACK
