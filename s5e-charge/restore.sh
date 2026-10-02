#!/bin/sh
# 把 S5 eSIM 46mm 的充电动画写回原厂（还原盘）

DEV=/dev/system
BASE=/data/s5panim/payload_restore

echo "target check"
ls -l $DEV

echo "== charge0 ==
dd if=$BASE/000_charge0.bin of=$DEV bs=1 seek=84231168 count=197959
dd if=$DEV of=/tmp/chk.bin bs=1 skip=84231168 count=197959
cmp /tmp/chk.bin $BASE/000_charge0.bin

echo "== charge1 ==
dd if=$BASE/001_charge1.bin of=$DEV bs=4 seek=21008000 count=49712
dd if=$DEV of=/tmp/chk.bin bs=4 skip=21008000 count=49712
cmp /tmp/chk.bin $BASE/001_charge1.bin

echo "== charge2 ==
dd if=$BASE/002_charge2.bin of=$DEV bs=4 seek=20459008 count=49835
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20459008 count=49835
cmp /tmp/chk.bin $BASE/002_charge2.bin

echo "== charge3 ==
dd if=$BASE/003_charge3.bin of=$DEV bs=1 seek=79569408 count=198921
dd if=$DEV of=/tmp/chk.bin bs=1 skip=79569408 count=198921
cmp /tmp/chk.bin $BASE/003_charge3.bin

echo "== charge4 ==
dd if=$BASE/004_charge4.bin of=$DEV bs=4 seek=19341952 count=49966
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19341952 count=49966
cmp /tmp/chk.bin $BASE/004_charge4.bin

echo "== charge5 ==
dd if=$BASE/005_charge5.bin of=$DEV bs=1 seek=75496960 count=199227
dd if=$DEV of=/tmp/chk.bin bs=1 skip=75496960 count=199227
cmp /tmp/chk.bin $BASE/005_charge5.bin

echo "== charge6 ==
dd if=$BASE/006_charge6.bin of=$DEV bs=1 seek=73385984 count=197829
dd if=$DEV of=/tmp/chk.bin bs=1 skip=73385984 count=197829
cmp /tmp/chk.bin $BASE/006_charge6.bin

echo "== charge7 ==
dd if=$BASE/007_charge7.bin of=$DEV bs=1 seek=72987648 count=196511
dd if=$DEV of=/tmp/chk.bin bs=1 skip=72987648 count=196511
cmp /tmp/chk.bin $BASE/007_charge7.bin

echo "== charge8 ==
dd if=$BASE/008_charge8.bin of=$DEV bs=4 seek=18197888 count=48897
dd if=$DEV of=/tmp/chk.bin bs=4 skip=18197888 count=48897
cmp /tmp/chk.bin $BASE/008_charge8.bin

echo "== charge9 ==
dd if=$BASE/009_charge9.bin of=$DEV bs=1 seek=72595456 count=196017
dd if=$DEV of=/tmp/chk.bin bs=1 skip=72595456 count=196017
cmp /tmp/chk.bin $BASE/009_charge9.bin

echo "== charge10 ==
dd if=$BASE/010_charge10.bin of=$DEV bs=4 seek=20958080 count=49823
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20958080 count=49823
cmp /tmp/chk.bin $BASE/010_charge10.bin

echo "== charge11 ==
dd if=$BASE/011_charge11.bin of=$DEV bs=4 seek=20908800 count=49236
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20908800 count=49236
cmp /tmp/chk.bin $BASE/011_charge11.bin

echo "== charge12 ==
dd if=$BASE/012_charge12.bin of=$DEV bs=4 seek=20860032 count=48700
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20860032 count=48700
cmp /tmp/chk.bin $BASE/012_charge12.bin

echo "== charge13 ==
dd if=$BASE/013_charge13.bin of=$DEV bs=1 seek=83244032 count=195933
dd if=$DEV of=/tmp/chk.bin bs=1 skip=83244032 count=195933
cmp /tmp/chk.bin $BASE/013_charge13.bin

echo "== charge14 ==
dd if=$BASE/014_charge14.bin of=$DEV bs=4 seek=20761856 count=49022
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20761856 count=49022
cmp /tmp/chk.bin $BASE/014_charge14.bin

echo "== charge15 ==
dd if=$BASE/015_charge15.bin of=$DEV bs=4 seek=20713088 count=48723
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20713088 count=48723
cmp /tmp/chk.bin $BASE/015_charge15.bin

echo "== charge16 ==
dd if=$BASE/016_charge16.bin of=$DEV bs=1 seek=82649088 count=203070
dd if=$DEV of=/tmp/chk.bin bs=1 skip=82649088 count=203070
cmp /tmp/chk.bin $BASE/016_charge16.bin

echo "== charge17 ==
dd if=$BASE/017_charge17.bin of=$DEV bs=1 seek=82446336 count=202394
dd if=$DEV of=/tmp/chk.bin bs=1 skip=82446336 count=202394
cmp /tmp/chk.bin $BASE/017_charge17.bin

echo "== charge18 ==
dd if=$BASE/018_charge18.bin of=$DEV bs=1 seek=82244608 count=201551
dd if=$DEV of=/tmp/chk.bin bs=1 skip=82244608 count=201551
cmp /tmp/chk.bin $BASE/018_charge18.bin

echo "== charge19 ==
dd if=$BASE/019_charge19.bin of=$DEV bs=1 seek=82035712 count=208701
dd if=$DEV of=/tmp/chk.bin bs=1 skip=82035712 count=208701
cmp /tmp/chk.bin $BASE/019_charge19.bin

echo "== charge20 ==
dd if=$BASE/020_charge20.bin of=$DEV bs=1 seek=81623040 count=212929
dd if=$DEV of=/tmp/chk.bin bs=1 skip=81623040 count=212929
cmp /tmp/chk.bin $BASE/020_charge20.bin

echo "== charge21 ==
dd if=$BASE/021_charge21.bin of=$DEV bs=1 seek=81409024 count=213511
dd if=$DEV of=/tmp/chk.bin bs=1 skip=81409024 count=213511
cmp /tmp/chk.bin $BASE/021_charge21.bin

echo "== charge22 ==
dd if=$BASE/022_charge22.bin of=$DEV bs=4 seek=20299520 count=52636
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20299520 count=52636
cmp /tmp/chk.bin $BASE/022_charge22.bin

echo "== charge23 ==
dd if=$BASE/023_charge23.bin of=$DEV bs=1 seek=80989696 count=208113
dd if=$DEV of=/tmp/chk.bin bs=1 skip=80989696 count=208113
cmp /tmp/chk.bin $BASE/023_charge23.bin

echo "== charge24 ==
dd if=$BASE/024_charge24.bin of=$DEV bs=1 seek=80780288 count=209043
dd if=$DEV of=/tmp/chk.bin bs=1 skip=80780288 count=209043
cmp /tmp/chk.bin $BASE/024_charge24.bin

echo "== charge25 ==
dd if=$BASE/025_charge25.bin of=$DEV bs=4 seek=20144128 count=50926
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20144128 count=50926
cmp /tmp/chk.bin $BASE/025_charge25.bin

echo "== charge26 ==
dd if=$BASE/026_charge26.bin of=$DEV bs=4 seek=20094080 count=50034
dd if=$DEV of=/tmp/chk.bin bs=4 skip=20094080 count=50034
cmp /tmp/chk.bin $BASE/026_charge26.bin

echo "== charge27 ==
dd if=$BASE/027_charge27.bin of=$DEV bs=1 seek=80176128 count=199722
dd if=$DEV of=/tmp/chk.bin bs=1 skip=80176128 count=199722
cmp /tmp/chk.bin $BASE/027_charge27.bin

echo "== charge28 ==
dd if=$BASE/028_charge28.bin of=$DEV bs=4 seek=19993344 count=50579
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19993344 count=50579
cmp /tmp/chk.bin $BASE/028_charge28.bin

echo "== charge29 ==
dd if=$BASE/029_charge29.bin of=$DEV bs=1 seek=79768576 count=204746
dd if=$DEV of=/tmp/chk.bin bs=1 skip=79768576 count=204746
cmp /tmp/chk.bin $BASE/029_charge29.bin

echo "== charge30 ==
dd if=$BASE/030_charge30.bin of=$DEV bs=4 seek=19840896 count=51412
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19840896 count=51412
cmp /tmp/chk.bin $BASE/030_charge30.bin

echo "== charge31 ==
dd if=$BASE/031_charge31.bin of=$DEV bs=1 seek=79160320 count=203001
dd if=$DEV of=/tmp/chk.bin bs=1 skip=79160320 count=203001
cmp /tmp/chk.bin $BASE/031_charge31.bin

echo "== charge32 ==
dd if=$BASE/032_charge32.bin of=$DEV bs=1 seek=78957056 count=203131
dd if=$DEV of=/tmp/chk.bin bs=1 skip=78957056 count=203131
cmp /tmp/chk.bin $BASE/032_charge32.bin

echo "== charge33 ==
dd if=$BASE/033_charge33.bin of=$DEV bs=4 seek=19687680 count=51562
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19687680 count=51562
cmp /tmp/chk.bin $BASE/033_charge33.bin

echo "== charge34 ==
dd if=$BASE/034_charge34.bin of=$DEV bs=4 seek=19636864 count=50739
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19636864 count=50739
cmp /tmp/chk.bin $BASE/034_charge34.bin

echo "== charge35 ==
dd if=$BASE/035_charge35.bin of=$DEV bs=4 seek=19587328 count=49490
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19587328 count=49490
cmp /tmp/chk.bin $BASE/035_charge35.bin

echo "== charge36 ==
dd if=$BASE/036_charge36.bin of=$DEV bs=4 seek=19537792 count=49525
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19537792 count=49525
cmp /tmp/chk.bin $BASE/036_charge36.bin

echo "== charge37 ==
dd if=$BASE/037_charge37.bin of=$DEV bs=1 seek=77954048 count=196965
dd if=$DEV of=/tmp/chk.bin bs=1 skip=77954048 count=196965
cmp /tmp/chk.bin $BASE/037_charge37.bin

echo "== charge38 ==
dd if=$BASE/038_charge38.bin of=$DEV bs=4 seek=19439616 count=48761
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19439616 count=48761
cmp /tmp/chk.bin $BASE/038_charge38.bin

echo "== charge39 ==
dd if=$BASE/039_charge39.bin of=$DEV bs=1 seek=77568000 count=189981
dd if=$DEV of=/tmp/chk.bin bs=1 skip=77568000 count=189981
cmp /tmp/chk.bin $BASE/039_charge39.bin

echo "== charge40 ==
dd if=$BASE/040_charge40.bin of=$DEV bs=1 seek=77182976 count=184335
dd if=$DEV of=/tmp/chk.bin bs=1 skip=77182976 count=184335
cmp /tmp/chk.bin $BASE/040_charge40.bin

echo "== charge41 ==
dd if=$BASE/041_charge41.bin of=$DEV bs=1 seek=76999680 count=183226
dd if=$DEV of=/tmp/chk.bin bs=1 skip=76999680 count=183226
cmp /tmp/chk.bin $BASE/041_charge41.bin

echo "== charge42 ==
dd if=$BASE/042_charge42.bin of=$DEV bs=4 seek=19204736 count=45059
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19204736 count=45059
cmp /tmp/chk.bin $BASE/042_charge42.bin

echo "== charge43 ==
dd if=$BASE/043_charge43.bin of=$DEV bs=1 seek=76642304 count=176325
dd if=$DEV of=/tmp/chk.bin bs=1 skip=76642304 count=176325
cmp /tmp/chk.bin $BASE/043_charge43.bin

echo "== charge44 ==
dd if=$BASE/044_charge44.bin of=$DEV bs=4 seek=19117696 count=42805
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19117696 count=42805
cmp /tmp/chk.bin $BASE/044_charge44.bin

echo "== charge45 ==
dd if=$BASE/045_charge45.bin of=$DEV bs=1 seek=76307968 count=162630
dd if=$DEV of=/tmp/chk.bin bs=1 skip=76307968 count=162630
cmp /tmp/chk.bin $BASE/045_charge45.bin

echo "== charge46 ==
dd if=$BASE/046_charge46.bin of=$DEV bs=4 seek=19041024 count=35958
dd if=$DEV of=/tmp/chk.bin bs=4 skip=19041024 count=35958
cmp /tmp/chk.bin $BASE/046_charge46.bin

echo "== charge47 ==
dd if=$BASE/047_charge47.bin of=$DEV bs=1 seek=76019200 count=144563
dd if=$DEV of=/tmp/chk.bin bs=1 skip=76019200 count=144563
cmp /tmp/chk.bin $BASE/047_charge47.bin

echo "== charge48 ==
dd if=$BASE/048_charge48.bin of=$DEV bs=1 seek=75868672 count=150019
dd if=$DEV of=/tmp/chk.bin bs=1 skip=75868672 count=150019
cmp /tmp/chk.bin $BASE/048_charge48.bin

echo "== charge49 ==
dd if=$BASE/049_charge49.bin of=$DEV bs=1 seek=75696640 count=171665
dd if=$DEV of=/tmp/chk.bin bs=1 skip=75696640 count=171665
cmp /tmp/chk.bin $BASE/049_charge49.bin

echo "== charge50 ==
dd if=$BASE/050_charge50.bin of=$DEV bs=4 seek=18829824 count=44284
dd if=$DEV of=/tmp/chk.bin bs=4 skip=18829824 count=44284
cmp /tmp/chk.bin $BASE/050_charge50.bin

echo "== charge51 ==
dd if=$BASE/051_charge51.bin of=$DEV bs=1 seek=75135488 count=183445
dd if=$DEV of=/tmp/chk.bin bs=1 skip=75135488 count=183445
cmp /tmp/chk.bin $BASE/051_charge51.bin

echo "== charge52 ==
dd if=$BASE/052_charge52.bin of=$DEV bs=4 seek=18737280 count=46476
dd if=$DEV of=/tmp/chk.bin bs=4 skip=18737280 count=46476
cmp /tmp/chk.bin $BASE/052_charge52.bin

echo "== charge53 ==
dd if=$BASE/053_charge53.bin of=$DEV bs=1 seek=74759680 count=189246
dd if=$DEV of=/tmp/chk.bin bs=1 skip=74759680 count=189246
cmp /tmp/chk.bin $BASE/053_charge53.bin

echo "== charge54 ==
dd if=$BASE/054_charge54.bin of=$DEV bs=1 seek=74567680 count=191681
dd if=$DEV of=/tmp/chk.bin bs=1 skip=74567680 count=191681
cmp /tmp/chk.bin $BASE/054_charge54.bin

echo "== charge55 ==
dd if=$BASE/055_charge55.bin of=$DEV bs=1 seek=74374656 count=192782
dd if=$DEV of=/tmp/chk.bin bs=1 skip=74374656 count=192782
cmp /tmp/chk.bin $BASE/055_charge55.bin

echo "== charge56 ==
dd if=$BASE/056_charge56.bin of=$DEV bs=1 seek=74179584 count=195037
dd if=$DEV of=/tmp/chk.bin bs=1 skip=74179584 count=195037
cmp /tmp/chk.bin $BASE/056_charge56.bin

echo "== charge57 ==
dd if=$BASE/057_charge57.bin of=$DEV bs=1 seek=73982464 count=197081
dd if=$DEV of=/tmp/chk.bin bs=1 skip=73982464 count=197081
cmp /tmp/chk.bin $BASE/057_charge57.bin

echo "== charge58 ==
dd if=$BASE/058_charge58.bin of=$DEV bs=1 seek=73783808 count=198594
dd if=$DEV of=/tmp/chk.bin bs=1 skip=73783808 count=198594
cmp /tmp/chk.bin $BASE/058_charge58.bin

echo "== charge59 ==
dd if=$BASE/059_charge59.bin of=$DEV bs=1 seek=73584128 count=199473
dd if=$DEV of=/tmp/chk.bin bs=1 skip=73584128 count=199473
cmp /tmp/chk.bin $BASE/059_charge59.bin

echo "== charge60 ==
dd if=$BASE/060_charge60.bin of=$DEV bs=1 seek=73184256 count=201487
dd if=$DEV of=/tmp/chk.bin bs=1 skip=73184256 count=201487
cmp /tmp/chk.bin $BASE/060_charge60.bin

rm /tmp/chk.bin
echo "restore done - run reboot to apply"
