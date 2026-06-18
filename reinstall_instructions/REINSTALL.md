# Documentation for reinstall and tools on acquisition machines

## tmux config in $HOME
```shell
set -g mouse on
```

## cron jobs
1. send interface config to gateway (in case ip is not reachable)
`crontab -e`
`* * * * * /usr/bin/sh cron-script-send-ip-addr.sh`
```shell
#/bin/sh

HOST=$(hostname)

RCMD="rm ~/log/$HOST.ip* ; cat - > ~/log/$HOST.ip.$(date +'%Y%m%d-%H%M%S').log"

echo $HOST
echo $RCMD

/usr/sbin/ip addr | ssh sgw "$RCMD"
```

2. update systems overnight
```sudo crontab -e```
```0 0 * * 0 root (apt-get update && apt-get -y -d upgrade) > /dev/null```

3. murinemanager dhclient renew lease
```sudo crontab -e```
```shell
*/10 * * * *  sudo dhclient -v enp1s0f1 -r && sudo dhclient -v enp1s0f1 && sudo bash /home/lbr/routing_script.bash
```
routing_script:
```shell
#! /bin/bash

IPTABLES=/usr/sbin/iptables

WANIF='enp1s0f1'
LANIF='enp1s0f0'

# enable ip forwarding in the kernel
echo 'Enabling Kernel IP forwarding...'
/bin/echo 1 > /proc/sys/net/ipv4/ip_forward

# flush rules and delete chains
echo 'Flushing rules and deleting existing chains...'
$IPTABLES -F
$IPTABLES -X

# enable masquerading to allow LAN internet access
echo 'Enabling IP Masquerading and other rules...'
$IPTABLES -t nat -A POSTROUTING -o $LANIF -j MASQUERADE
$IPTABLES -A FORWARD -i $LANIF -o $WANIF -m state --state RELATED,ESTABLISHED -j ACCEPT
$IPTABLES -A FORWARD -i $WANIF -o $LANIF -j ACCEPT

$IPTABLES -t nat -A POSTROUTING -o $WANIF -j MASQUERADE
$IPTABLES -A FORWARD -i $WANIF -o $LANIF -m state --state RELATED,ESTABLISHED -j ACCEPT
$IPTABLES -A FORWARD -i $LANIF -o $WANIF -j ACCEPT

echo 'Done.'

```
