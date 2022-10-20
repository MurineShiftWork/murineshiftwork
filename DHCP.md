

## DHCP identities

RPi racks:
    evephys
    tripleboxes-left
    tripleboxes-right
    doubleboxes-shelf
    npx

| MAC               |                          IP | Setup         | RPi rack        | Position (left->right)  | Cam Loc                  | Use | TODO              |
|:------------------|----------------------------:|---------------|-----------------|-------------------------|--------------------------|-----|-------------------|
| dc:a6:32:34:b1:0d |                          83 | 1             | evephys         | 2 (3 physical location) | blue blue/cam            |     |                   |
| dc:a6:32:34:ae:79 |                          85 | 1             | evephys         | 1 (2 same as above)     | white white              |     |                   |
| dc:a6:32:45:a7:e1 |                          86 | 1             | evephys         | 3 (4 same as above)     |                          |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
| dc:a6:32:a2:0f:16 |                          40 | 2             | triple left     | 1                       |                          |     |                   |
| dc:a6:32:d1:28:11 |                          41 | 2             | triple left     | 3                       |                          |     |                   |
| dc:a6:32:d1:28:11 |                          43 | 2             | triple left     | 2                       |                          |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
| dc:a6:32:a9:61:aa |                          61 | 3             | triple left     | 6                       | blue/rpi blue/cam        |     |                   |
| dc:a6:32:45:a8:89 |                          68 | 3             | triple right    | 1                       | green green              |     |                   |
| e4:5f:01:1f:d7:10 |                          69 | 3             | triple right    | 2                       | orange orange            |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
| e4:5f:01:1f:d7:4c |                          80 | 4             | triple right    | 4                       | green-white blue/cam     |     |                   |
| dc:a6:32:a9:61:d1 |                          81 | 4             | triple right    | 5                       | white/red red/cam        |     |                   |
| e4:5f:01:1f:cc:a2 |                          82 | 4             | triple right    | 6                       | white/blue green/cam     |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
| e4:5f:01:1f:d7:45 |                          11 | 5 (new)       | double          | 2                       | green-orange/rpi red/cam | tba | change hostname   |
| dc:a6:32:d1:28:11 |                          50 | 5             | double          | 1                       | red/rpi purple/cam       |     |                   |
| dc:a6:32:f5:3f:cc |                          60 | 5             | double          | 3                       | red-yellow/rpi           |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
| dc:a6:32:45:e4:92 |                          51 | 6             | double          | 4                       | yellow/rpi white/cam     |     |                   |
| dc:a6:32:a9:56:a9 |                          62 | 6             | double          | 6                       | purple purple            |     |                   |
| e4:5f:01:1f:d3:94 |                          70 | 6             | double          | 5                       | pink green               |     | INSTALL conda etc |
|                   |                             |               |                 |                         |                          |     |                   |
| dc:a6:32:a9:61:d7 |                          63 | 7/npx         | npx             | 3                       | yellow yellow            |     |                   |
| dc:a6:32:f5:3f:0f |                          64 | 7/npx         | npx             | 2                       | white white              |     |                   |
| dc:a6:32:f5:3f:ba |                          65 | 7/npx         | npx             | 1                       | pink pink                |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
| 04:d4:c4:f2:13:da |                          87 | 1/evephys     | SETUP PC        |                         |                          |     |                   |
| 04:d4:c4:91:fe:2a |                          17 | 2             |                 |                         |                          |     |                   |
| 6c:4b:90:cf:27:c4 |                          16 | 3             |                 |                         |                          |     |                   |
| 6c:4b:90:cf:20:dd |                          15 | 4             |                 |                         |                          |     |                   |
| 00:e0:4c:80:e1:51 |                          14 | 5             |                 |                         |                          |     |                   |
| 00:e0:4c:80:e1:66 |                          13 | 6             |                 |                         |                          |     |                   |
| 00:e0:4c:80:da:64 |                          19 | 7/npx-b       | SETUP FOR NPX   |                         |                          |     | enp7s0            |
| 00:e0:4c:80:da:63 |              172.24.242.132 | 7/npx-b       | SETUP FOR NPX   |                         |                          |     | enp8s0            |
|                   |                             |               |                 |                         |                          |     |                   |
| 00:e0:4c:81:14:19 |                          48 | npx-e         | NPX WIN PC      |                         |                          |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
| e8:ea:6a:03:36:95 |              192.168.100.10 | murinemanager | DHCP SERVER     |                         |                          |     | enp1s0f0          |
| e8:ea:6a:03:36:96 |              172.24.242.210 | murinemanager | DHCP SERVER     |                         |                          |     | enp1s0f1          |
|                   |                             |               |                 |                         |                          |     |                   |
| 00:e0:4c:80:ca:e1 |               172.24.242.85 | epsilon       | OFFICE COMPUTER |                         |                          |     | enp9s0            |
| 3c:52:82:5e:f0:ca |              172.24.242.122 | hermes        | OFFICE COMPUTER |                         |                          |     | eno1              |
|                   |                             |               |                 |                         |                          |     |                   |
|                   |                             |               |                 |                         |                          |     |                   |
