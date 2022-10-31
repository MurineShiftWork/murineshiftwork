

## DHCP identities

RPi racks:
    evephys
    tripleboxes-left
    tripleboxes-right
    doubleboxes-shelf
    npx

| MAC               |             IP | Setup         | RPi rack        | Position (left->right)  | Cam Loc                  | Use           | TODO              |
|:------------------|---------------:|---------------|-----------------|-------------------------|--------------------------|---------------|-------------------|
| dc:a6:32:34:b1:0d |            101 | 1             | evephys         | 2 (3 physical location) | blue blue/cam            |               |                   |
| dc:a6:32:34:ae:79 |            102 | 1             | evephys         | 1 (2 same as above)     | white white              |               |                   |
| dc:a6:32:45:a7:e1 |            103 | 1             | evephys         | 3 (4 same as above)     |                          |               |                   |
|                   |                |               |                 |                         |                          |               |                   |
| dc:a6:32:a2:0f:16 |             21 | 2             | triple left     | 1                       | green                    | bottom tongue |                   |
| dc:a6:32:d1:28:11 |             22 | 2             | triple left     | 3                       | purple                   | left face     |                   |
| DC:A6:32:45:E4:5F |             23 | 2             | triple left     | 2                       | red yellow               | right face    |                   |
|                   |                |               |                 |                         |                          |               |                   |
| dc:a6:32:a9:61:aa |             31 | 3             | triple left     | 6                       | blue/rpi blue/cam        | bottom tongue |                   |
| dc:a6:32:45:a8:89 |             32 | 3             | triple right    | 1                       | green green              | left face     |                   |
| e4:5f:01:1f:d7:10 |             33 | 3             | triple right    | 2                       | orange orange            | right face    |                   |
|                   |                |               |                 |                         |                          |               |                   |
| e4:5f:01:1f:d7:4c |             41 | 4             | triple right    | 4                       | green-white blue/cam     | right face    |                   |
| dc:a6:32:a9:61:d1 |             42 | 4             | triple right    | 5                       | white/red red/cam        | bottom tonuge |                   |
| e4:5f:01:1f:cc:a2 |             43 | 4             | triple right    | 6                       | white/blue green/cam     | left face     |                   |
|                   |                |               |                 |                         |                          |               |                   |
| e4:5f:01:1f:d7:45 |             51 | 5             | double          | 2                       | green-orange/rpi red/cam | left face     |                   |
| dc:a6:32:d1:27:b4 |             52 | 5             | double          | 1                       | red/rpi purple/cam       | right face    |                   |
| dc:a6:32:f5:3f:cc |             53 | 5             | double          | 3                       | red-yellow/rpi           | bottom tongue |                   |
|                   |                |               |                 |                         |                          |               |                   |
| dc:a6:32:45:e4:92 |             61 | 6             | double          | 4                       | yellow/rpi white/cam     |               |                   |
| dc:a6:32:a9:56:a9 |             62 | 6             | double          | 6                       | purple purple            | left face     |                   |
| e4:5f:01:1f:d3:94 |             63 | 6             | double          | 5                       | pink green               |               | INSTALL conda etc |
|                   |                |               |                 |                         |                          |               |                   |
| dc:a6:32:a9:61:d7 |             71 | 7/npx         | npx             | 3                       | yellow yellow            | tbd           |                   |
| dc:a6:32:f5:3f:0f |             72 | 7/npx         | npx             | 2                       | white white              | tbd           |                   |
| dc:a6:32:f5:3f:ba |             73 | 7/npx         | npx             | 1                       | pink pink                | tbd           |                   |
|                   |                |               |                 |                         |                          |               |                   |
| 04:d4:c4:f2:13:da |             11 | 1/evephys     | SETUP PC        |                         |                          |               |                   |
| 00:e0:4c:80:db:42 |  169.254.8.175 | 1/evephys     | SETUP PC        |                         |                          |               | enp6s0:avahi:     |
|                   |                |               |                 |                         |                          |               |                   |
| 04:d4:c4:91:fe:2a |             12 | 2             |                 |                         |                          |               |                   |
| 6c:4b:90:cf:27:c4 |             13 | 3             |                 |                         |                          |               |                   |
| 6c:4b:90:cf:20:dd |             14 | 4             |                 |                         |                          |               |                   |
| 00:e0:4c:80:e1:51 |             15 | 5             |                 |                         |                          |               |                   |
| 00:e0:4c:80:e1:66 |             16 | 6             |                 |                         |                          |               |                   |
|                   |                |               |                 |                         |                          |               |                   |
| 00:e0:4c:80:da:64 |             20 | 7/npx-b       | SETUP FOR NPX   |                         |                          |               | enp9s0            |
| 00:e0:4c:80:da:63 | 172.24.242.131 | 7/npx-b       | SETUP FOR NPX   |                         |                          |               | enp8s0            |
|                   |                |               |                 |                         |                          |               |                   |
| 00:e0:4c:81:14:19 |             48 | npx-e         | NPX WIN PC      |                         |                          |               |                   |
|                   |                |               |                 |                         |                          |               |                   |
| e8:ea:6a:03:36:95 | 192.168.100.10 | murinemanager | DHCP SERVER     |                         |                          |               | enp1s0f0          |
| e8:ea:6a:03:36:96 | 172.24.242.210 | murinemanager | DHCP SERVER     |                         |                          |               | enp1s0f1          |
|                   |                |               |                 |                         |                          |               |                   |
| 94:c6:91:7b:04:03 | 192.168.100.18 | rtpp          | SETUP FOR RTPP  |                         |                          |               | enp1s0            |
|                   |                |               |                 |                         |                          |               |                   |
| 00:e0:4c:80:ca:e1 |  172.24.242.85 | epsilon       | OFFICE COMPUTER |                         |                          |               | enp9s0            |
| 3c:52:82:5e:f0:ca | 172.24.242.122 | hermes        | OFFICE COMPUTER |                         |                          |               | eno1              |
|                   |                |               |                 |                         |                          |               |                   |
|                   |                |               |                 |                         |                          |               |                   |

CHECK & IDENTIFY the actual device for: 22, 52

OK: 31, 42, 43, 53, 72, 73, 63

dc:a6:32:d1:27:b4 - .50 - host: rpi-22-TEST

sudo apt install -y tmux
sudo dhclient -v -r eth0 && sudo dhclient -v eth0
