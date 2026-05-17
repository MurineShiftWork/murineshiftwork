acq) murinemanager@murinemanager:/ceph/sjones/users/lars/data/_test_subject/_test_subject__20260503_135509__ephys_multi_behavior$ python /mnt/maindata/code/murineshiftwork/tests/test_rce_barcode_alignment.py --session _test_subject__20260503_135544___test_barcode_iti_with_video --ttl_in _test_subject__20260503_135544___test_barcode_iti_with_video/_test_subject__20260503_135544___test_barcode_iti_with_video.rce.rpi-172.20260503135545.ttl_in.npz


(acq) murinemanager@murinemanager:/ceph/sjones/users/lars/data/_test_subject/_test_subject__20260503_135509__ephys_multi_behavior$ python /mnt/maindata/code/murineshiftwork/tests/test_rce_barcode_alignment.py --session _test_subject__20260503_135544___test_barcode_iti_with_video --ttl_in _test_subject__20260503_135544___test_barcode_iti_with_video/_test_subject__20260503_135544___test_barcode_iti_with_video.rce.rpi-172.20260503135545.ttl_in.npz

Session   : _test_subject__20260503_135544___test_barcode_iti_with_video
ttl_in    : _test_subject__20260503_135544___test_barcode_iti_with_video/_test_subject__20260503_135544___test_barcode_iti_with_video.rce.rpi-172.20260503135545.ttl_in.npz
Config    : BarcodeConfig(timestamp, 37-bit, ms precision, 4.4yr coverage, 35.0ms bits, 1355ms total)

Raw edges in ttl_in.npz : 6124
Edge time span          : 20.1s (0.3min)
Inter-edge gaps (ms)    : min=0.0  median=1.7  max=66
Gaps <500ms (within barcode): 6123   >=500ms (between barcodes): 0

=== Verification result ===
MSW barcodes        : 20
RCE decoded         : 0
Matched             : 0
Decode rate         : 0.000
Match rate          : 0.000

Unmatched MSW barcodes (20):
  [128545506488, 128545510017, 128545514043, 128545519070, 128545524598, 128545529625, 128545534173, 128545537197, 128545540222, 128545544248, 128545547773, 128545550798, 128545555325, 128545560852, 128545565379, 128545571408, 128545575934, 128545578959, 128545583987, 128545589515]

FAIL — check unmatched values above
