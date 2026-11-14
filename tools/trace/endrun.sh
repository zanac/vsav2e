#!/bin/sh
HERE=$(cd "$(dirname "$0")" && pwd); WORK=${VS_WORK:-$PWD/work}; ROMS=${VS_ROMS:-$PWD/roms}; export VS_TOOLS=$HERE
g=$1; id=$2; o=$WORK/en_${g}_$id; rm -rf $o; mkdir -p $o
S=$(seq -s ' ' 2000 500 14000)
AUTOWIN=1 TRACE_OUT=$o LAST=14000 BIN=60 MASH=1600 SEED=$id POKES="1000-1500:ff8782:$id" SHOTS="$S" PRESS="600:IN2:Coin 1;700:IN2:1 Player Start;1030:IN0:P1 Button 1;1100:IN0:P1 Button 1" timeout 1500 /usr/games/mame $g -rompath $ROMS -video none -sound none -nothrottle -snapshot_directory $o -autoboot_script $HERE/drive.lua >/dev/null 2>&1
