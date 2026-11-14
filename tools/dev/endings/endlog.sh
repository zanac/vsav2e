#!/bin/sh
# endlog.sh ID: Vampire Savior arcade to the ending with character ID, logging the sprite list
id=$1; o=/tmp/claude-0/vs/el_$id; rm -rf $o; mkdir -p $o
AUTOWIN=1 TRACE_OUT=$o LAST=16000 BIN=60 MASH=1600 SEED=$id POKES="1000-1500:ff8782:$id" OBJLOG="6000:16000:4" SHOTS="$(seq -s ' ' 6000 500 16000)" PRESS="600:IN2:Coin 1;650:IN2:Coin 1;700:IN2:1 Player Start;1030:IN0:P1 Button 1;1100:IN0:P1 Button 1" timeout 2400 /usr/games/mame vsav -rompath /tmp/claude-0/vs/t -nvram_directory /tmp/claude-0/vs/nv_el_$id -video none -sound none -nothrottle -snapshot_directory $o -autoboot_script /tmp/claude-0/vs/lua/drive.lua >/dev/null 2>&1
echo done $id
