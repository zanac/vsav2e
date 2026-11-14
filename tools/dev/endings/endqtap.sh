#!/bin/sh
id=$1; o=/tmp/claude-0/vs/eq_$id; rm -rf $o; mkdir -p $o
AUTOWIN=1 TRACE_OUT=$o LAST=17000 BIN=60 MASH=1600 SEED=$id POKES="1000-1500:ff8782:$id" PRESS="600:IN2:Coin 1;650:IN2:Coin 1;700:IN2:1 Player Start;1030:IN0:P1 Button 1;1100:IN0:P1 Button 1" timeout 3600 /usr/games/mame vsav -rompath /tmp/claude-0/vs/t -nvram_directory /tmp/claude-0/vs/nv_eq_$id -video none -sound none -nothrottle -autoboot_script /tmp/claude-0/vs/lua/qtap.lua >$o/log.txt 2>&1
echo done $id
