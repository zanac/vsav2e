#!/bin/sh
HERE=$(cd "$(dirname "$0")" && pwd); WORK=${VS_WORK:-$PWD/work}; ROMS=${VS_ROMS:-$PWD/roms}; export VS_TOOLS=$HERE
# fight.sh game downs rights tag [last]
g=$1; d=$2; r=$3; o=$WORK/fx_${g}_$4; rm -rf $o; mkdir -p $o
P="600:IN2:Coin 1;700:IN2:1 Player Start"; fr=880
for k in $(seq 1 $d); do P="$P;$fr:IN0:P1 Down"; fr=$((fr+30)); done
fr=1000; if [ $r -lt 0 ]; then for k in $(seq 1 $((-r))); do P="$P;$fr:IN0:P1 Left"; fr=$((fr+40)); done; else for k in $(seq 1 $r); do P="$P;$fr:IN0:P1 Right"; fr=$((fr+40)); done; fi
P="$P;$((fr+30)):IN0:P1 Button 1;$((fr+100)):IN0:P1 Button 1"
L=${5:-6000}
TRACE_OUT=$o LAST=$L MASH=1600 SEED=$(echo $d$r | tr -d -) SHOTS="$((fr+20)) 2000 3000 4000 5000 6000" DUMPS="2000 2400" PRESS="$P" timeout 900 /usr/games/mame $g -rompath $ROMS -video none -sound none -nothrottle -snapshot_directory $o -autoboot_script $HERE/drive.lua >/dev/null 2>&1
