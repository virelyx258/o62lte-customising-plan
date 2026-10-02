#!/bin/sh
# S5 41mm 充电动画 -> S4 eSIM（只写负载）
# 把 flash.sh 与 payload/ 放到同一个目录，例如 /data/s4panim/
# 然后:  sh /data/s4panim/flash.sh     最后:  reboot
# 还原用 restore.sh 或安装还原盘 S4ChgRestore.face

DEV=/dev/system
BASE=/data/s4panim/payload

echo "target check"
ls -l $DEV

echo "== charge0 ==
dd if=$BASE/000_charge0.bin of=$DEV bs=4 seek=18062976 count=28182
dd if=$DEV of=/tmp/chk.bin bs=4 skip=18062976 count=28182
cmp /tmp/chk.bin $BASE/000_charge0.bin

echo "== charge1 ==
dd if=$BASE/001_charge1.bin of=$DEV bs=1 seek=72172032 count=79834
dd if=$DEV of=/tmp/chk.bin bs=1 skip=72172032 count=79834
cmp /tmp/chk.bin $BASE/001_charge1.bin

echo "== charge2 ==
dd if=$BASE/002_charge2.bin of=$DEV bs=4 seek=17786752 count=20313
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17786752 count=20313
cmp /tmp/chk.bin $BASE/002_charge2.bin

echo "== charge3 ==
dd if=$BASE/003_charge3.bin of=$DEV bs=1 seek=70018048 count=82007
dd if=$DEV of=/tmp/chk.bin bs=1 skip=70018048 count=82007
cmp /tmp/chk.bin $BASE/003_charge3.bin

echo "== charge4 ==
dd if=$BASE/004_charge4.bin of=$DEV bs=1 seek=68788224 count=83347
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68788224 count=83347
cmp /tmp/chk.bin $BASE/004_charge4.bin

echo "== charge5 ==
dd if=$BASE/005_charge5.bin of=$DEV bs=1 seek=67532800 count=84305
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67532800 count=84305
cmp /tmp/chk.bin $BASE/005_charge5.bin

echo "== charge6 ==
dd if=$BASE/006_charge6.bin of=$DEV bs=1 seek=66615296 count=84281
dd if=$DEV of=/tmp/chk.bin bs=1 skip=66615296 count=84281
cmp /tmp/chk.bin $BASE/006_charge6.bin

echo "== charge7 ==
dd if=$BASE/007_charge7.bin of=$DEV bs=4 seek=16632704 count=21023
dd if=$DEV of=/tmp/chk.bin bs=4 skip=16632704 count=21023
cmp /tmp/chk.bin $BASE/007_charge7.bin

echo "== charge8 ==
dd if=$BASE/008_charge8.bin of=$DEV bs=1 seek=66445312 count=85403
dd if=$DEV of=/tmp/chk.bin bs=1 skip=66445312 count=85403
cmp /tmp/chk.bin $BASE/008_charge8.bin

echo "== charge9 ==
dd if=$BASE/009_charge9.bin of=$DEV bs=1 seek=66357760 count=87097
dd if=$DEV of=/tmp/chk.bin bs=1 skip=66357760 count=87097
cmp /tmp/chk.bin $BASE/009_charge9.bin

echo "== charge10 ==
dd if=$BASE/010_charge10.bin of=$DEV bs=4 seek=18020864 count=22109
dd if=$DEV of=/tmp/chk.bin bs=4 skip=18020864 count=22109
cmp /tmp/chk.bin $BASE/010_charge10.bin

echo "== charge11 ==
dd if=$BASE/011_charge11.bin of=$DEV bs=1 seek=71994368 count=88566
dd if=$DEV of=/tmp/chk.bin bs=1 skip=71994368 count=88566
cmp /tmp/chk.bin $BASE/011_charge11.bin

echo "== charge12 ==
dd if=$BASE/012_charge12.bin of=$DEV bs=1 seek=71904256 count=89914
dd if=$DEV of=/tmp/chk.bin bs=1 skip=71904256 count=89914
cmp /tmp/chk.bin $BASE/012_charge12.bin

echo "== charge13 ==
dd if=$BASE/013_charge13.bin of=$DEV bs=1 seek=71813120 count=91103
dd if=$DEV of=/tmp/chk.bin bs=1 skip=71813120 count=91103
cmp /tmp/chk.bin $BASE/013_charge13.bin

echo "== charge14 ==
dd if=$BASE/014_charge14.bin of=$DEV bs=4 seek=17929856 count=23345
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17929856 count=23345
cmp /tmp/chk.bin $BASE/014_charge14.bin

echo "== charge15 ==
dd if=$BASE/015_charge15.bin of=$DEV bs=4 seek=17906176 count=23632
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17906176 count=23632
cmp /tmp/chk.bin $BASE/015_charge15.bin

echo "== charge16 ==
dd if=$BASE/016_charge16.bin of=$DEV bs=1 seek=71527936 count=96705
dd if=$DEV of=/tmp/chk.bin bs=1 skip=71527936 count=96705
cmp /tmp/chk.bin $BASE/016_charge16.bin

echo "== charge17 ==
dd if=$BASE/017_charge17.bin of=$DEV bs=1 seek=71429120 count=98295
dd if=$DEV of=/tmp/chk.bin bs=1 skip=71429120 count=98295
cmp /tmp/chk.bin $BASE/017_charge17.bin

echo "== charge18 ==
dd if=$BASE/018_charge18.bin of=$DEV bs=1 seek=71329280 count=99525
dd if=$DEV of=/tmp/chk.bin bs=1 skip=71329280 count=99525
cmp /tmp/chk.bin $BASE/018_charge18.bin

echo "== charge19 ==
dd if=$BASE/019_charge19.bin of=$DEV bs=4 seek=17807104 count=25201
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17807104 count=25201
cmp /tmp/chk.bin $BASE/019_charge19.bin

echo "== charge20 ==
dd if=$BASE/020_charge20.bin of=$DEV bs=1 seek=71045632 count=101014
dd if=$DEV of=/tmp/chk.bin bs=1 skip=71045632 count=101014
cmp /tmp/chk.bin $BASE/020_charge20.bin

echo "== charge21 ==
dd if=$BASE/021_charge21.bin of=$DEV bs=1 seek=70943744 count=101755
dd if=$DEV of=/tmp/chk.bin bs=1 skip=70943744 count=101755
cmp /tmp/chk.bin $BASE/021_charge21.bin

echo "== charge22 ==
dd if=$BASE/022_charge22.bin of=$DEV bs=4 seek=17710080 count=25758
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17710080 count=25758
cmp /tmp/chk.bin $BASE/022_charge22.bin

echo "== charge23 ==
dd if=$BASE/023_charge23.bin of=$DEV bs=1 seek=70736384 count=103826
dd if=$DEV of=/tmp/chk.bin bs=1 skip=70736384 count=103826
cmp /tmp/chk.bin $BASE/023_charge23.bin

echo "== charge24 ==
dd if=$BASE/024_charge24.bin of=$DEV bs=1 seek=70631936 count=104085
dd if=$DEV of=/tmp/chk.bin bs=1 skip=70631936 count=104085
cmp /tmp/chk.bin $BASE/024_charge24.bin

echo "== charge25 ==
dd if=$BASE/025_charge25.bin of=$DEV bs=4 seek=17632000 count=25960
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17632000 count=25960
cmp /tmp/chk.bin $BASE/025_charge25.bin

echo "== charge26 ==
dd if=$BASE/026_charge26.bin of=$DEV bs=4 seek=17605888 count=26104
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17605888 count=26104
cmp /tmp/chk.bin $BASE/026_charge26.bin

echo "== charge27 ==
dd if=$BASE/027_charge27.bin of=$DEV bs=1 seek=70319616 count=103815
dd if=$DEV of=/tmp/chk.bin bs=1 skip=70319616 count=103815
cmp /tmp/chk.bin $BASE/027_charge27.bin

echo "== charge28 ==
dd if=$BASE/028_charge28.bin of=$DEV bs=4 seek=17553024 count=26848
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17553024 count=26848
cmp /tmp/chk.bin $BASE/028_charge28.bin

echo "== charge29 ==
dd if=$BASE/029_charge29.bin of=$DEV bs=1 seek=70100480 count=111441
dd if=$DEV of=/tmp/chk.bin bs=1 skip=70100480 count=111441
cmp /tmp/chk.bin $BASE/029_charge29.bin

echo "== charge30 ==
dd if=$BASE/030_charge30.bin of=$DEV bs=1 seek=69905408 count=112118
dd if=$DEV of=/tmp/chk.bin bs=1 skip=69905408 count=112118
cmp /tmp/chk.bin $BASE/030_charge30.bin

echo "== charge31 ==
dd if=$BASE/031_charge31.bin of=$DEV bs=1 seek=69794304 count=110857
dd if=$DEV of=/tmp/chk.bin bs=1 skip=69794304 count=110857
cmp /tmp/chk.bin $BASE/031_charge31.bin

echo "== charge32 ==
dd if=$BASE/032_charge32.bin of=$DEV bs=1 seek=69680640 count=113259
dd if=$DEV of=/tmp/chk.bin bs=1 skip=69680640 count=113259
cmp /tmp/chk.bin $BASE/032_charge32.bin

echo "== charge33 ==
dd if=$BASE/033_charge33.bin of=$DEV bs=1 seek=69566464 count=113647
dd if=$DEV of=/tmp/chk.bin bs=1 skip=69566464 count=113647
cmp /tmp/chk.bin $BASE/033_charge33.bin

echo "== charge34 ==
dd if=$BASE/034_charge34.bin of=$DEV bs=1 seek=69451776 count=114281
dd if=$DEV of=/tmp/chk.bin bs=1 skip=69451776 count=114281
cmp /tmp/chk.bin $BASE/034_charge34.bin

echo "== charge35 ==
dd if=$BASE/035_charge35.bin of=$DEV bs=1 seek=69336064 count=115315
dd if=$DEV of=/tmp/chk.bin bs=1 skip=69336064 count=115315
cmp /tmp/chk.bin $BASE/035_charge35.bin

echo "== charge36 ==
dd if=$BASE/036_charge36.bin of=$DEV bs=4 seek=17304960 count=29039
dd if=$DEV of=/tmp/chk.bin bs=4 skip=17304960 count=29039
cmp /tmp/chk.bin $BASE/036_charge36.bin

echo "== charge37 ==
dd if=$BASE/037_charge37.bin of=$DEV bs=1 seek=69103616 count=116126
dd if=$DEV of=/tmp/chk.bin bs=1 skip=69103616 count=116126
cmp /tmp/chk.bin $BASE/037_charge37.bin

echo "== charge38 ==
dd if=$BASE/038_charge38.bin of=$DEV bs=1 seek=68987392 count=115971
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68987392 count=115971
cmp /tmp/chk.bin $BASE/038_charge38.bin

echo "== charge39 ==
dd if=$BASE/039_charge39.bin of=$DEV bs=1 seek=68871680 count=115563
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68871680 count=115563
cmp /tmp/chk.bin $BASE/039_charge39.bin

echo "== charge40 ==
dd if=$BASE/040_charge40.bin of=$DEV bs=1 seek=68672512 count=115334
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68672512 count=115334
cmp /tmp/chk.bin $BASE/040_charge40.bin

echo "== charge41 ==
dd if=$BASE/041_charge41.bin of=$DEV bs=1 seek=68556288 count=115723
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68556288 count=115723
cmp /tmp/chk.bin $BASE/041_charge41.bin

echo "== charge42 ==
dd if=$BASE/042_charge42.bin of=$DEV bs=1 seek=68440064 count=116050
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68440064 count=116050
cmp /tmp/chk.bin $BASE/042_charge42.bin

echo "== charge43 ==
dd if=$BASE/043_charge43.bin of=$DEV bs=1 seek=68323328 count=116683
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68323328 count=116683
cmp /tmp/chk.bin $BASE/043_charge43.bin

echo "== charge44 ==
dd if=$BASE/044_charge44.bin of=$DEV bs=1 seek=68206080 count=116854
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68206080 count=116854
cmp /tmp/chk.bin $BASE/044_charge44.bin

echo "== charge45 ==
dd if=$BASE/045_charge45.bin of=$DEV bs=1 seek=68088320 count=117369
dd if=$DEV of=/tmp/chk.bin bs=1 skip=68088320 count=117369
cmp /tmp/chk.bin $BASE/045_charge45.bin

echo "== charge46 ==
dd if=$BASE/046_charge46.bin of=$DEV bs=1 seek=67970048 count=118191
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67970048 count=118191
cmp /tmp/chk.bin $BASE/046_charge46.bin

echo "== charge47 ==
dd if=$BASE/047_charge47.bin of=$DEV bs=1 seek=67852800 count=117005
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67852800 count=117005
cmp /tmp/chk.bin $BASE/047_charge47.bin

echo "== charge48 ==
dd if=$BASE/048_charge48.bin of=$DEV bs=1 seek=67735040 count=117365
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67735040 count=117365
cmp /tmp/chk.bin $BASE/048_charge48.bin

echo "== charge49 ==
dd if=$BASE/049_charge49.bin of=$DEV bs=1 seek=67617280 count=117626
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67617280 count=117626
cmp /tmp/chk.bin $BASE/049_charge49.bin

echo "== charge50 ==
dd if=$BASE/050_charge50.bin of=$DEV bs=1 seek=67414528 count=117906
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67414528 count=117906
cmp /tmp/chk.bin $BASE/050_charge50.bin

echo "== charge51 ==
dd if=$BASE/051_charge51.bin of=$DEV bs=1 seek=67295744 count=118481
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67295744 count=118481
cmp /tmp/chk.bin $BASE/051_charge51.bin

echo "== charge52 ==
dd if=$BASE/052_charge52.bin of=$DEV bs=4 seek=16793984 count=29825
dd if=$DEV of=/tmp/chk.bin bs=4 skip=16793984 count=29825
cmp /tmp/chk.bin $BASE/052_charge52.bin

echo "== charge53 ==
dd if=$BASE/053_charge53.bin of=$DEV bs=1 seek=67056128 count=119353
dd if=$DEV of=/tmp/chk.bin bs=1 skip=67056128 count=119353
cmp /tmp/chk.bin $BASE/053_charge53.bin

echo "== charge54 ==
dd if=$BASE/054_charge54.bin of=$DEV bs=1 seek=66936832 count=119135
dd if=$DEV of=/tmp/chk.bin bs=1 skip=66936832 count=119135
cmp /tmp/chk.bin $BASE/054_charge54.bin

echo "== charge55 ==
dd if=$BASE/055_charge55.bin of=$DEV bs=1 seek=66818560 count=117881
dd if=$DEV of=/tmp/chk.bin bs=1 skip=66818560 count=117881
cmp /tmp/chk.bin $BASE/055_charge55.bin

echo "== charge56 ==
dd if=$BASE/056_charge56.bin of=$DEV bs=4 seek=16674944 count=29644
dd if=$DEV of=/tmp/chk.bin bs=4 skip=16674944 count=29644
cmp /tmp/chk.bin $BASE/056_charge56.bin

rm /tmp/chk.bin
echo "all done - run reboot to apply"
