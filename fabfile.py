import os
from pathlib import Path

from fabric import task
from patchwork import files


setups_msw = ["setup1", "setup2", "setup3", "setup4", "setup5", "setup-npxb"]

setups_rcc = [f"rpi-{id}" for id in [40, 41, 43, 50, 51, 60, 61, 62]]

# # users msw setups
# # users rcc setups
#
# # tasks for msw setups
# # - mkdir data
# # - install miniconda, create env acq or py36
# # - clone msw, uninstall, install
#
# # tasks for rcc setups
# # - mkdir data
# # - install miniconda, create env acq or py36
# # - clone msw, uninstall, install
#
# # Setup ssh
# # copy .ssh/config
# # ssh-keygen
# # ssh-copy-id to all ssh/config
#
# # Setup dhcp on main router
# # /etc/dhcp/dhcpd.conf
# # /etc
#
# sudo apt install isc-dhcp-server --reinstall
# sudo nano /etc/dhcp/dhcpd.conf  # add config
# sudo nano /etc/default/isc-dhcp-server  # add interface to monitor with DHCP server
#
# sudo journalctl -u isc-dhcp-server
# cat /var/lib/dhcp/dhclient.leases
#
# # sudo nano /etc/sysctl.conf
# # sudo sysctl - w net.ipv4.ip_forward = 1
#
# #  1426  sudo ufw disable
# #  1427  ifconfig
# #  1428  iptables -A INPUT -i enp8s0 -j ACCEPT
# #  1429  sudo iptables -A INPUT -i enp8s0 -j ACCEPT
# #  1430  ptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# #  1431  sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# #  1432  sudo iptables -t nat -A POSTROUTING -o enp7s0 -j MASQUERADE
# #  1433  iptables -A FORWARD -i enp7s0 -o enp8s0 -m state --state RELATED,ESTABLISHED -j ACCEPT
# #  1434  sudo iptables -A FORWARD -i enp7s0 -o enp8s0 -m state --state RELATED,ESTABLISHED -j ACCEPT
# #  1435  sudo iptables -A FORWARD -i enp8s0 -o enp7s0 -j ACCEPT
#
# # (acq) lbr@setup1:~$ cat /etc/netplan/01-network-manager-all.yaml
# # # Let NetworkManager manage all devices on this system
# # network:
# #   version: 2
# #   renderer: NetworkManager
# #   ethernets:
# #     enp2s0:  # external/WAN
# #       dhcp4: yes
# #       dhcp6: no
# #     enp9s0:  # internal/LAN
# #       dhcp4: no
# #       dhcp6: no
# #       addresses: [192.168.100.10/24]
# #       gateway4: 192.168.100.1
# #       nameservers:
# #         addresses: [192.168.238.208]sw setups
# # users rcc setups
#
# # tasks for msw setups
# # - mkdir data
# # - install miniconda, create env acq or py36
# # - clone msw, uninstall, install
#
# # tasks for rcc setups
# # - mkdir data
# # - install miniconda, create env acq or py36
# # - clone msw, uninstall, install
#
# # Setup ssh
# # copy .ssh/config
# # ssh-keygen
# # ssh-copy-id to all ssh/config
#
# # Setup dhcp on main router
# # /etc/dhcp/dhcpd.conf
# # /etc
#
# sudo apt install isc-dhcp-server --reinstall
# sudo nano /etc/dhcp/dhcpd.conf  # add config
# sudo nano /etc/default/isc-dhcp-server  # add interface to monitor with DHCP server
#
# sudo journalctl -u isc-dhcp-server
# cat /var/lib/dhcp/dhclient.leases
#
# # sudo nano /etc/sysctl.conf
# # sudo sysctl - w net.ipv4.ip_forward = 1
#
# #  1426  sudo ufw disable
# #  1427  ifconfig
# #  1428  iptables -A INPUT -i enp8s0 -j ACCEPT
# #  1429  sudo iptables -A INPUT -i enp8s0 -j ACCEPT
# #  1430  ptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# #  1431  sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# #  1432  sudo iptables -t nat -A POSTROUTING -o enp7s0 -j MASQUERADE
# #  1433  iptables -A FORWARD -i enp7s0 -o enp8s0 -m state --state RELATED,ESTABLISHED -j ACCEPT
# #  1434  sudo iptables -A FORWARD -i enp7s0 -o enp8s0 -m state --state RELATED,ESTABLISHED -j ACCEPT
# #  1435  sudo iptables -A FORWARD -i enp8s0 -o enp7s0 -j ACCEPT
#
# # (acq) lbr@setup1:~$ cat /etc/netplan/01-network-manager-all.yaml
# # # Let NetworkManager manage all devices on this system
# # network:
# #   version: 2
# #   renderer: NetworkManager
# #   ethernets:
# #     enp2s0:  # external/WAN
# #       dhcp4: yes
# #       dhcp6: no
# #     enp9s0:  # internal/LAN
# #       dhcp4: no
# #       dhcp6: no
# #       addresses: [192.168.100.10/24]
# #       gateway4: 192.168.100.1
# #       nameservers:
# #         addresses: [192.168.238.208]
