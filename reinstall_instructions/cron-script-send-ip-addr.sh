#/bin/sh

HOST=$(hostname)

RCMD="rm ~/log/$HOST.ip* ; cat - > ~/log/$HOST.ip.$(date +'%Y%m%d-%H%M%S').log"

echo $HOST
echo $RCMD

/usr/sbin/ip addr | ssh sgw "$RCMD"

