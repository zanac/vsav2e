#!/bin/sh
HERE=$(cd "$(dirname "$0")" && pwd); WORK=${VS_WORK:-$PWD/work}; ROMS=${VS_ROMS:-$PWD/roms}; export VS_TOOLS=$HERE
# force.sh game id tag [last] [pokeuntil]
g=$1; id=$2; o=$WORK/fc_${g}_$3; rm -rf $o; mkdir -p $o
L=${4:-6000}; U=${5:-1500}
TRACE_OUT=$o LAST=$L MASH=1600 SEED=$id POKES="1000-$U:ff8782:$id" SHOTS="1100 1700 2400 3500 5000 6000" DUMPS="2400 4000" PRESS="600:IN2:Coin 1;700:IN2:1 Player Start;1030:IN0:P1 Button 1;1100:IN0:P1 Button 1" timeout 900 /usr/games/mame $g -rompath $ROMS -video none -sound none -nothrottle -snapshot_directory $o -autoboot_script $HERE/drive.lua >/dev/null 2>&1
