#!/bin/sh
# endtap.sh ID [SET]: program ROM reads during the ending of character ID
id=$1; set=${2:-vsav}; o=/tmp/claude-0/vs/et_${set}_$id; rm -rf $o; mkdir -p $o
AUTOWIN=1 TRACE_OUT=$o LAST=17000 BIN=60 MASH=1600 SEED=$id POKES="1000-1500:ff8782:$id" PRESS="600:IN2:Coin 1;650:IN2:Coin 1;700:IN2:1 Player Start;1030:IN0:P1 Button 1;1100:IN0:P1 Button 1" timeout 3600 /usr/games/mame $set -rompath /tmp/claude-0/vs/t -nvram_directory /tmp/claude-0/vs/nv_et_${set}_$id -video none -sound none -nothrottle -autoboot_script /tmp/claude-0/vs/lua/tap.lua >$o/log.txt 2>&1
echo done $set $id $(wc -l < $o/reads.txt)
