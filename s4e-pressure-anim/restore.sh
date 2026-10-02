#!/bin/sh
# 把 S4 eSIM 的压力检测动画写回原厂（还原盘）

DEV=/dev/app
BASE=/data/s4panim/payload_restore

echo "target check"
ls -l $DEV

echo "== 000_Measuring1_1 ==
dd if=$BASE/000_000_Measuring1_1.bin of=$DEV bs=1 seek=126906880 count=4485
dd if=$DEV of=/tmp/chk.bin bs=1 skip=126906880 count=4485
cmp /tmp/chk.bin $BASE/000_000_Measuring1_1.bin

echo "== 001_Measuring2_2 ==
dd if=$BASE/001_001_Measuring2_2.bin of=$DEV bs=1 seek=124850176 count=4530
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124850176 count=4530
cmp /tmp/chk.bin $BASE/001_001_Measuring2_2.bin

echo "== 002_Measuring3_3 ==
dd if=$BASE/002_002_Measuring3_3.bin of=$DEV bs=1 seek=123219968 count=4695
dd if=$DEV of=/tmp/chk.bin bs=1 skip=123219968 count=4695
cmp /tmp/chk.bin $BASE/002_002_Measuring3_3.bin

echo "== 003_Measuring4_4 ==
dd if=$BASE/003_003_Measuring4_4.bin of=$DEV bs=1 seek=121341952 count=5078
dd if=$DEV of=/tmp/chk.bin bs=1 skip=121341952 count=5078
cmp /tmp/chk.bin $BASE/003_003_Measuring4_4.bin

echo "== 004_Measuring5_5 ==
dd if=$BASE/004_004_Measuring5_5.bin of=$DEV bs=1 seek=119374336 count=6327
dd if=$DEV of=/tmp/chk.bin bs=1 skip=119374336 count=6327
cmp /tmp/chk.bin $BASE/004_004_Measuring5_5.bin

echo "== 005_Measuring6_6 ==
dd if=$BASE/005_005_Measuring6_6.bin of=$DEV bs=4 seek=29353344 count=2109
dd if=$DEV of=/tmp/chk.bin bs=4 skip=29353344 count=2109
cmp /tmp/chk.bin $BASE/005_005_Measuring6_6.bin

echo "== 006_Measuring7_7 ==
dd if=$BASE/006_006_Measuring7_7.bin of=$DEV bs=1 seek=115506688 count=11785
dd if=$DEV of=/tmp/chk.bin bs=1 skip=115506688 count=11785
cmp /tmp/chk.bin $BASE/006_006_Measuring7_7.bin

echo "== 007_Measuring8_8 ==
dd if=$BASE/007_007_Measuring8_8.bin of=$DEV bs=1 seek=113678336 count=17510
dd if=$DEV of=/tmp/chk.bin bs=1 skip=113678336 count=17510
cmp /tmp/chk.bin $BASE/007_007_Measuring8_8.bin

echo "== 008_Measuring9_9 ==
dd if=$BASE/008_008_Measuring9_9.bin of=$DEV bs=1 seek=112016384 count=23011
dd if=$DEV of=/tmp/chk.bin bs=1 skip=112016384 count=23011
cmp /tmp/chk.bin $BASE/008_008_Measuring9_9.bin

echo "== 009_Measuring10_10 ==
dd if=$BASE/009_009_Measuring10_10.bin of=$DEV bs=1 seek=126875136 count=31377
dd if=$DEV of=/tmp/chk.bin bs=1 skip=126875136 count=31377
cmp /tmp/chk.bin $BASE/009_009_Measuring10_10.bin

echo "== 010_Measuring11_11 ==
dd if=$BASE/010_010_Measuring11_11.bin of=$DEV bs=4 seek=31503616 count=10776
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31503616 count=10776
cmp /tmp/chk.bin $BASE/010_010_Measuring11_11.bin

echo "== 011_Measuring12_12 ==
dd if=$BASE/011_011_Measuring12_12.bin of=$DEV bs=1 seek=125605888 count=54415
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125605888 count=54415
cmp /tmp/chk.bin $BASE/011_011_Measuring12_12.bin

echo "== 012_Measuring13_13 ==
dd if=$BASE/012_012_Measuring13_13.bin of=$DEV bs=1 seek=125539840 count=65693
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125539840 count=65693
cmp /tmp/chk.bin $BASE/012_012_Measuring13_13.bin

echo "== 013_Measuring14_14 ==
dd if=$BASE/013_013_Measuring14_14.bin of=$DEV bs=1 seek=125463552 count=75926
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125463552 count=75926
cmp /tmp/chk.bin $BASE/013_013_Measuring14_14.bin

echo "== 014_Measuring15_15 ==
dd if=$BASE/014_014_Measuring15_15.bin of=$DEV bs=1 seek=125372928 count=90514
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125372928 count=90514
cmp /tmp/chk.bin $BASE/014_014_Measuring15_15.bin

echo "== 015_Measuring16_16 ==
dd if=$BASE/015_015_Measuring16_16.bin of=$DEV bs=1 seek=125251584 count=120902
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125251584 count=120902
cmp /tmp/chk.bin $BASE/015_015_Measuring16_16.bin

echo "== 016_Measuring17_17 ==
dd if=$BASE/016_016_Measuring17_17.bin of=$DEV bs=4 seek=31280896 count=31895
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31280896 count=31895
cmp /tmp/chk.bin $BASE/016_016_Measuring17_17.bin

echo "== 017_Measuring18_18 ==
dd if=$BASE/017_017_Measuring18_18.bin of=$DEV bs=1 seek=124991488 count=131691
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124991488 count=131691
cmp /tmp/chk.bin $BASE/017_017_Measuring18_18.bin

echo "== 018_Measuring19_19 ==
dd if=$BASE/018_018_Measuring19_19.bin of=$DEV bs=1 seek=124854784 count=136658
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124854784 count=136658
cmp /tmp/chk.bin $BASE/018_018_Measuring19_19.bin

echo "== 019_Measuring20_20 ==
dd if=$BASE/019_019_Measuring20_20.bin of=$DEV bs=1 seek=124708352 count=141610
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124708352 count=141610
cmp /tmp/chk.bin $BASE/019_019_Measuring20_20.bin

echo "== 020_Measuring21_21 ==
dd if=$BASE/020_020_Measuring21_21.bin of=$DEV bs=1 seek=124561920 count=145939
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124561920 count=145939
cmp /tmp/chk.bin $BASE/020_020_Measuring21_21.bin

echo "== 021_Measuring22_22 ==
dd if=$BASE/021_021_Measuring22_22.bin of=$DEV bs=1 seek=124407296 count=154315
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124407296 count=154315
cmp /tmp/chk.bin $BASE/021_021_Measuring22_22.bin

echo "== 022_Measuring23_23 ==
dd if=$BASE/022_022_Measuring23_23.bin of=$DEV bs=1 seek=124248064 count=158922
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124248064 count=158922
cmp /tmp/chk.bin $BASE/022_022_Measuring23_23.bin

echo "== 023_Measuring24_24 ==
dd if=$BASE/023_023_Measuring24_24.bin of=$DEV bs=1 seek=124083712 count=164011
dd if=$DEV of=/tmp/chk.bin bs=1 skip=124083712 count=164011
cmp /tmp/chk.bin $BASE/023_023_Measuring24_24.bin

echo "== 024_Measuring25_25 ==
dd if=$BASE/024_024_Measuring25_25.bin of=$DEV bs=1 seek=123916288 count=166983
dd if=$DEV of=/tmp/chk.bin bs=1 skip=123916288 count=166983
cmp /tmp/chk.bin $BASE/024_024_Measuring25_25.bin

echo "== 025_Measuring26_26 ==
dd if=$BASE/025_025_Measuring26_26.bin of=$DEV bs=1 seek=123746816 count=169431
dd if=$DEV of=/tmp/chk.bin bs=1 skip=123746816 count=169431
cmp /tmp/chk.bin $BASE/025_025_Measuring26_26.bin

echo "== 026_Measuring27_27 ==
dd if=$BASE/026_026_Measuring27_27.bin of=$DEV bs=1 seek=123574784 count=171709
dd if=$DEV of=/tmp/chk.bin bs=1 skip=123574784 count=171709
cmp /tmp/chk.bin $BASE/026_026_Measuring27_27.bin

echo "== 027_Measuring28_28 ==
dd if=$BASE/027_027_Measuring28_28.bin of=$DEV bs=1 seek=123400704 count=173905
dd if=$DEV of=/tmp/chk.bin bs=1 skip=123400704 count=173905
cmp /tmp/chk.bin $BASE/027_027_Measuring28_28.bin

echo "== 028_Measuring29_29 ==
dd if=$BASE/028_028_Measuring29_29.bin of=$DEV bs=1 seek=123225088 count=175146
dd if=$DEV of=/tmp/chk.bin bs=1 skip=123225088 count=175146
cmp /tmp/chk.bin $BASE/028_028_Measuring29_29.bin

echo "== 029_Measuring30_30 ==
dd if=$BASE/029_029_Measuring30_30.bin of=$DEV bs=1 seek=123042816 count=176699
dd if=$DEV of=/tmp/chk.bin bs=1 skip=123042816 count=176699
cmp /tmp/chk.bin $BASE/029_029_Measuring30_30.bin

echo "== 030_Measuring31_31 ==
dd if=$BASE/030_030_Measuring31_31.bin of=$DEV bs=4 seek=30716032 count=44562
dd if=$DEV of=/tmp/chk.bin bs=4 skip=30716032 count=44562
cmp /tmp/chk.bin $BASE/030_030_Measuring31_31.bin

echo "== 031_Measuring32_32 ==
dd if=$BASE/031_031_Measuring32_32.bin of=$DEV bs=4 seek=30670848 count=45167
dd if=$DEV of=/tmp/chk.bin bs=4 skip=30670848 count=45167
cmp /tmp/chk.bin $BASE/031_031_Measuring32_32.bin

echo "== 032_Measuring33_33 ==
dd if=$BASE/032_032_Measuring33_33.bin of=$DEV bs=1 seek=122497024 count=186322
dd if=$DEV of=/tmp/chk.bin bs=1 skip=122497024 count=186322
cmp /tmp/chk.bin $BASE/032_032_Measuring33_33.bin

echo "== 033_Measuring34_34 ==
dd if=$BASE/033_033_Measuring34_34.bin of=$DEV bs=4 seek=30577152 count=47065
dd if=$DEV of=/tmp/chk.bin bs=4 skip=30577152 count=47065
cmp /tmp/chk.bin $BASE/033_033_Measuring34_34.bin

echo "== 034_Measuring35_35 ==
dd if=$BASE/034_034_Measuring35_35.bin of=$DEV bs=1 seek=122118656 count=189862
dd if=$DEV of=/tmp/chk.bin bs=1 skip=122118656 count=189862
cmp /tmp/chk.bin $BASE/034_034_Measuring35_35.bin

echo "== 035_Measuring36_36 ==
dd if=$BASE/035_035_Measuring36_36.bin of=$DEV bs=1 seek=121927680 count=190691
dd if=$DEV of=/tmp/chk.bin bs=1 skip=121927680 count=190691
cmp /tmp/chk.bin $BASE/035_035_Measuring36_36.bin

echo "== 036_Measuring37_37 ==
dd if=$BASE/036_036_Measuring37_37.bin of=$DEV bs=1 seek=121735680 count=191837
dd if=$DEV of=/tmp/chk.bin bs=1 skip=121735680 count=191837
cmp /tmp/chk.bin $BASE/036_036_Measuring37_37.bin

echo "== 037_Measuring38_38 ==
dd if=$BASE/037_037_Measuring38_38.bin of=$DEV bs=1 seek=121542144 count=193189
dd if=$DEV of=/tmp/chk.bin bs=1 skip=121542144 count=193189
cmp /tmp/chk.bin $BASE/037_037_Measuring38_38.bin

echo "== 038_Measuring39_39 ==
dd if=$BASE/038_038_Measuring39_39.bin of=$DEV bs=1 seek=121347072 count=194939
dd if=$DEV of=/tmp/chk.bin bs=1 skip=121347072 count=194939
cmp /tmp/chk.bin $BASE/038_038_Measuring39_39.bin

echo "== 039_Measuring40_40 ==
dd if=$BASE/039_039_Measuring40_40.bin of=$DEV bs=1 seek=121146368 count=195239
dd if=$DEV of=/tmp/chk.bin bs=1 skip=121146368 count=195239
cmp /tmp/chk.bin $BASE/039_039_Measuring40_40.bin

echo "== 040_Measuring41_41 ==
dd if=$BASE/040_040_Measuring41_41.bin of=$DEV bs=1 seek=120950272 count=195793
dd if=$DEV of=/tmp/chk.bin bs=1 skip=120950272 count=195793
cmp /tmp/chk.bin $BASE/040_040_Measuring41_41.bin

echo "== 041_Measuring42_42 ==
dd if=$BASE/041_041_Measuring42_42.bin of=$DEV bs=1 seek=120754176 count=196046
dd if=$DEV of=/tmp/chk.bin bs=1 skip=120754176 count=196046
cmp /tmp/chk.bin $BASE/041_041_Measuring42_42.bin

echo "== 042_Measuring43_43 ==
dd if=$BASE/042_042_Measuring43_43.bin of=$DEV bs=1 seek=120558080 count=196021
dd if=$DEV of=/tmp/chk.bin bs=1 skip=120558080 count=196021
cmp /tmp/chk.bin $BASE/042_042_Measuring43_43.bin

echo "== 043_Measuring44_44 ==
dd if=$BASE/043_043_Measuring44_44.bin of=$DEV bs=1 seek=120361472 count=196086
dd if=$DEV of=/tmp/chk.bin bs=1 skip=120361472 count=196086
cmp /tmp/chk.bin $BASE/043_043_Measuring44_44.bin

echo "== 044_Measuring45_45 ==
dd if=$BASE/044_044_Measuring45_45.bin of=$DEV bs=4 seek=30041344 count=48913
dd if=$DEV of=/tmp/chk.bin bs=4 skip=30041344 count=48913
cmp /tmp/chk.bin $BASE/044_044_Measuring45_45.bin

echo "== 045_Measuring46_46 ==
dd if=$BASE/045_045_Measuring46_46.bin of=$DEV bs=1 seek=119969280 count=195974
dd if=$DEV of=/tmp/chk.bin bs=1 skip=119969280 count=195974
cmp /tmp/chk.bin $BASE/045_045_Measuring46_46.bin

echo "== 046_Measuring47_47 ==
dd if=$BASE/046_046_Measuring47_47.bin of=$DEV bs=1 seek=119773184 count=195999
dd if=$DEV of=/tmp/chk.bin bs=1 skip=119773184 count=195999
cmp /tmp/chk.bin $BASE/046_046_Measuring47_47.bin

echo "== 047_Measuring48_48 ==
dd if=$BASE/047_047_Measuring48_48.bin of=$DEV bs=1 seek=119577088 count=195847
dd if=$DEV of=/tmp/chk.bin bs=1 skip=119577088 count=195847
cmp /tmp/chk.bin $BASE/047_047_Measuring48_48.bin

echo "== 048_Measuring49_49 ==
dd if=$BASE/048_048_Measuring49_49.bin of=$DEV bs=1 seek=119380992 count=195899
dd if=$DEV of=/tmp/chk.bin bs=1 skip=119380992 count=195899
cmp /tmp/chk.bin $BASE/048_048_Measuring49_49.bin

echo "== 049_Measuring50_50 ==
dd if=$BASE/049_049_Measuring50_50.bin of=$DEV bs=1 seek=119177728 count=196154
dd if=$DEV of=/tmp/chk.bin bs=1 skip=119177728 count=196154
cmp /tmp/chk.bin $BASE/049_049_Measuring50_50.bin

echo "== 050_Measuring51_51 ==
dd if=$BASE/050_050_Measuring51_51.bin of=$DEV bs=1 seek=118981120 count=196246
dd if=$DEV of=/tmp/chk.bin bs=1 skip=118981120 count=196246
cmp /tmp/chk.bin $BASE/050_050_Measuring51_51.bin

echo "== 051_Measuring52_52 ==
dd if=$BASE/051_051_Measuring52_52.bin of=$DEV bs=1 seek=118785024 count=196042
dd if=$DEV of=/tmp/chk.bin bs=1 skip=118785024 count=196042
cmp /tmp/chk.bin $BASE/051_051_Measuring52_52.bin

echo "== 052_Measuring53_53 ==
dd if=$BASE/052_052_Measuring53_53.bin of=$DEV bs=1 seek=118588928 count=195985
dd if=$DEV of=/tmp/chk.bin bs=1 skip=118588928 count=195985
cmp /tmp/chk.bin $BASE/052_052_Measuring53_53.bin

echo "== 053_Measuring54_54 ==
dd if=$BASE/053_053_Measuring54_54.bin of=$DEV bs=1 seek=118392320 count=196538
dd if=$DEV of=/tmp/chk.bin bs=1 skip=118392320 count=196538
cmp /tmp/chk.bin $BASE/053_053_Measuring54_54.bin

echo "== 054_Measuring55_55 ==
dd if=$BASE/054_054_Measuring55_55.bin of=$DEV bs=1 seek=118198272 count=193546
dd if=$DEV of=/tmp/chk.bin bs=1 skip=118198272 count=193546
cmp /tmp/chk.bin $BASE/054_054_Measuring55_55.bin

echo "== 055_Measuring56_56 ==
dd if=$BASE/055_055_Measuring56_56.bin of=$DEV bs=4 seek=29501056 count=48496
dd if=$DEV of=/tmp/chk.bin bs=4 skip=29501056 count=48496
cmp /tmp/chk.bin $BASE/055_055_Measuring56_56.bin

echo "== 056_Measuring57_57 ==
dd if=$BASE/056_056_Measuring57_57.bin of=$DEV bs=1 seek=117810176 count=193954
dd if=$DEV of=/tmp/chk.bin bs=1 skip=117810176 count=193954
cmp /tmp/chk.bin $BASE/056_056_Measuring57_57.bin

echo "== 057_Measuring58_58 ==
dd if=$BASE/057_057_Measuring58_58.bin of=$DEV bs=1 seek=117616128 count=193929
dd if=$DEV of=/tmp/chk.bin bs=1 skip=117616128 count=193929
cmp /tmp/chk.bin $BASE/057_057_Measuring58_58.bin

echo "== 058_Measuring59_59 ==
dd if=$BASE/058_058_Measuring59_59.bin of=$DEV bs=1 seek=117422080 count=193761
dd if=$DEV of=/tmp/chk.bin bs=1 skip=117422080 count=193761
cmp /tmp/chk.bin $BASE/058_058_Measuring59_59.bin

echo "== 059_Measuring60_60 ==
dd if=$BASE/059_059_Measuring60_60.bin of=$DEV bs=1 seek=117218816 count=194029
dd if=$DEV of=/tmp/chk.bin bs=1 skip=117218816 count=194029
cmp /tmp/chk.bin $BASE/059_059_Measuring60_60.bin

echo "== 060_Measuring61_61 ==
dd if=$BASE/060_060_Measuring61_61.bin of=$DEV bs=1 seek=117029376 count=189089
dd if=$DEV of=/tmp/chk.bin bs=1 skip=117029376 count=189089
cmp /tmp/chk.bin $BASE/060_060_Measuring61_61.bin

echo "== 061_Measuring62_62 ==
dd if=$BASE/061_061_Measuring62_62.bin of=$DEV bs=1 seek=116838400 count=190474
dd if=$DEV of=/tmp/chk.bin bs=1 skip=116838400 count=190474
cmp /tmp/chk.bin $BASE/061_061_Measuring62_62.bin

echo "== 062_Measuring63_63 ==
dd if=$BASE/062_062_Measuring63_63.bin of=$DEV bs=4 seek=29161856 count=47687
dd if=$DEV of=/tmp/chk.bin bs=4 skip=29161856 count=47687
cmp /tmp/chk.bin $BASE/062_062_Measuring63_63.bin

echo "== 063_Measuring64_64 ==
dd if=$BASE/063_063_Measuring64_64.bin of=$DEV bs=1 seek=116455936 count=190975
dd if=$DEV of=/tmp/chk.bin bs=1 skip=116455936 count=190975
cmp /tmp/chk.bin $BASE/063_063_Measuring64_64.bin

echo "== 064_Measuring65_65 ==
dd if=$BASE/064_064_Measuring65_65.bin of=$DEV bs=1 seek=116263424 count=192023
dd if=$DEV of=/tmp/chk.bin bs=1 skip=116263424 count=192023
cmp /tmp/chk.bin $BASE/064_064_Measuring65_65.bin

echo "== 065_Measuring66_66 ==
dd if=$BASE/065_065_Measuring66_66.bin of=$DEV bs=1 seek=116071424 count=191903
dd if=$DEV of=/tmp/chk.bin bs=1 skip=116071424 count=191903
cmp /tmp/chk.bin $BASE/065_065_Measuring66_66.bin

echo "== 066_Measuring67_67 ==
dd if=$BASE/066_066_Measuring67_67.bin of=$DEV bs=1 seek=115888640 count=182358
dd if=$DEV of=/tmp/chk.bin bs=1 skip=115888640 count=182358
cmp /tmp/chk.bin $BASE/066_066_Measuring67_67.bin

echo "== 067_Measuring68_68 ==
dd if=$BASE/067_067_Measuring68_68.bin of=$DEV bs=1 seek=115704320 count=183906
dd if=$DEV of=/tmp/chk.bin bs=1 skip=115704320 count=183906
cmp /tmp/chk.bin $BASE/067_067_Measuring68_68.bin

echo "== 068_Measuring69_69 ==
dd if=$BASE/068_068_Measuring69_69.bin of=$DEV bs=1 seek=115518976 count=185033
dd if=$DEV of=/tmp/chk.bin bs=1 skip=115518976 count=185033
cmp /tmp/chk.bin $BASE/068_068_Measuring69_69.bin

echo "== 069_Measuring70_70 ==
dd if=$BASE/069_069_Measuring70_70.bin of=$DEV bs=1 seek=115321856 count=184662
dd if=$DEV of=/tmp/chk.bin bs=1 skip=115321856 count=184662
cmp /tmp/chk.bin $BASE/069_069_Measuring70_70.bin

echo "== 070_Measuring71_71 ==
dd if=$BASE/070_070_Measuring71_71.bin of=$DEV bs=1 seek=115136512 count=184877
dd if=$DEV of=/tmp/chk.bin bs=1 skip=115136512 count=184877
cmp /tmp/chk.bin $BASE/070_070_Measuring71_71.bin

echo "== 071_Measuring72_72 ==
dd if=$BASE/071_071_Measuring72_72.bin of=$DEV bs=1 seek=114951680 count=184574
dd if=$DEV of=/tmp/chk.bin bs=1 skip=114951680 count=184574
cmp /tmp/chk.bin $BASE/071_071_Measuring72_72.bin

echo "== 072_Measuring73_73 ==
dd if=$BASE/072_072_Measuring73_73.bin of=$DEV bs=1 seek=114770432 count=180773
dd if=$DEV of=/tmp/chk.bin bs=1 skip=114770432 count=180773
cmp /tmp/chk.bin $BASE/072_072_Measuring73_73.bin

echo "== 073_Measuring74_74 ==
dd if=$BASE/073_073_Measuring74_74.bin of=$DEV bs=4 seek=28647424 count=45157
dd if=$DEV of=/tmp/chk.bin bs=4 skip=28647424 count=45157
cmp /tmp/chk.bin $BASE/073_073_Measuring74_74.bin

echo "== 074_Measuring75_75 ==
dd if=$BASE/074_074_Measuring75_75.bin of=$DEV bs=1 seek=114409472 count=179919
dd if=$DEV of=/tmp/chk.bin bs=1 skip=114409472 count=179919
cmp /tmp/chk.bin $BASE/074_074_Measuring75_75.bin

echo "== 075_Measuring76_76 ==
dd if=$BASE/075_075_Measuring76_76.bin of=$DEV bs=1 seek=114228736 count=180517
dd if=$DEV of=/tmp/chk.bin bs=1 skip=114228736 count=180517
cmp /tmp/chk.bin $BASE/075_075_Measuring76_76.bin

echo "== 076_Measuring77_77 ==
dd if=$BASE/076_076_Measuring77_77.bin of=$DEV bs=1 seek=114048000 count=180677
dd if=$DEV of=/tmp/chk.bin bs=1 skip=114048000 count=180677
cmp /tmp/chk.bin $BASE/076_076_Measuring77_77.bin

echo "== 077_Measuring78_78 ==
dd if=$BASE/077_077_Measuring78_78.bin of=$DEV bs=1 seek=113867264 count=180537
dd if=$DEV of=/tmp/chk.bin bs=1 skip=113867264 count=180537
cmp /tmp/chk.bin $BASE/077_077_Measuring78_78.bin

echo "== 078_Measuring79_79 ==
dd if=$BASE/078_078_Measuring79_79.bin of=$DEV bs=1 seek=113696256 count=170518
dd if=$DEV of=/tmp/chk.bin bs=1 skip=113696256 count=170518
cmp /tmp/chk.bin $BASE/078_078_Measuring79_79.bin

echo "== 079_Measuring80_80 ==
dd if=$BASE/079_079_Measuring80_80.bin of=$DEV bs=1 seek=113507840 count=170059
dd if=$DEV of=/tmp/chk.bin bs=1 skip=113507840 count=170059
cmp /tmp/chk.bin $BASE/079_079_Measuring80_80.bin

echo "== 080_Measuring81_81 ==
dd if=$BASE/080_080_Measuring81_81.bin of=$DEV bs=1 seek=113336320 count=171247
dd if=$DEV of=/tmp/chk.bin bs=1 skip=113336320 count=171247
cmp /tmp/chk.bin $BASE/080_080_Measuring81_81.bin

echo "== 081_Measuring82_82 ==
dd if=$BASE/081_081_Measuring82_82.bin of=$DEV bs=1 seek=113165312 count=170939
dd if=$DEV of=/tmp/chk.bin bs=1 skip=113165312 count=170939
cmp /tmp/chk.bin $BASE/081_081_Measuring82_82.bin

echo "== 082_Measuring83_83 ==
dd if=$BASE/082_082_Measuring83_83.bin of=$DEV bs=1 seek=112994816 count=170193
dd if=$DEV of=/tmp/chk.bin bs=1 skip=112994816 count=170193
cmp /tmp/chk.bin $BASE/082_082_Measuring83_83.bin

echo "== 083_Measuring84_84 ==
dd if=$BASE/083_083_Measuring84_84.bin of=$DEV bs=1 seek=112840704 count=153998
dd if=$DEV of=/tmp/chk.bin bs=1 skip=112840704 count=153998
cmp /tmp/chk.bin $BASE/083_083_Measuring84_84.bin

echo "== 084_Measuring85_85 ==
dd if=$BASE/084_084_Measuring85_85.bin of=$DEV bs=4 seek=28170880 count=39261
dd if=$DEV of=/tmp/chk.bin bs=4 skip=28170880 count=39261
cmp /tmp/chk.bin $BASE/084_084_Measuring85_85.bin

echo "== 085_Measuring86_86 ==
dd if=$BASE/085_085_Measuring86_86.bin of=$DEV bs=4 seek=28131200 count=39545
dd if=$DEV of=/tmp/chk.bin bs=4 skip=28131200 count=39545
cmp /tmp/chk.bin $BASE/085_085_Measuring86_86.bin

echo "== 086_Measuring87_87 ==
dd if=$BASE/086_086_Measuring87_87.bin of=$DEV bs=1 seek=112364544 count=160025
dd if=$DEV of=/tmp/chk.bin bs=1 skip=112364544 count=160025
cmp /tmp/chk.bin $BASE/086_086_Measuring87_87.bin

echo "== 087_Measuring88_88 ==
dd if=$BASE/087_087_Measuring88_88.bin of=$DEV bs=1 seek=112203264 count=160963
dd if=$DEV of=/tmp/chk.bin bs=1 skip=112203264 count=160963
cmp /tmp/chk.bin $BASE/087_087_Measuring88_88.bin

echo "== 088_Measuring89_89 ==
dd if=$BASE/088_088_Measuring89_89.bin of=$DEV bs=1 seek=112039936 count=163153
dd if=$DEV of=/tmp/chk.bin bs=1 skip=112039936 count=163153
cmp /tmp/chk.bin $BASE/088_088_Measuring89_89.bin

echo "== 089_Measuring90_90 ==
dd if=$BASE/089_089_Measuring90_90.bin of=$DEV bs=1 seek=111863808 count=152329
dd if=$DEV of=/tmp/chk.bin bs=1 skip=111863808 count=152329
cmp /tmp/chk.bin $BASE/089_089_Measuring90_90.bin

echo "== 090_Measuring91_91 ==
dd if=$BASE/090_090_Measuring91_91.bin of=$DEV bs=1 seek=111712256 count=151129
dd if=$DEV of=/tmp/chk.bin bs=1 skip=111712256 count=151129
cmp /tmp/chk.bin $BASE/090_090_Measuring91_91.bin

echo "== 091_Measuring92_92 ==
dd if=$BASE/091_091_Measuring92_92.bin of=$DEV bs=1 seek=111562240 count=149917
dd if=$DEV of=/tmp/chk.bin bs=1 skip=111562240 count=149917
cmp /tmp/chk.bin $BASE/091_091_Measuring92_92.bin

echo "== 092_Measuring93_93 ==
dd if=$BASE/092_092_Measuring93_93.bin of=$DEV bs=1 seek=111413248 count=148930
dd if=$DEV of=/tmp/chk.bin bs=1 skip=111413248 count=148930
cmp /tmp/chk.bin $BASE/092_092_Measuring93_93.bin

echo "== 093_Measuring94_94 ==
dd if=$BASE/093_093_Measuring94_94.bin of=$DEV bs=4 seek=27816192 count=37010
dd if=$DEV of=/tmp/chk.bin bs=4 skip=27816192 count=37010
cmp /tmp/chk.bin $BASE/093_093_Measuring94_94.bin

echo "== 094_Measuring95_95 ==
dd if=$BASE/094_094_Measuring95_95.bin of=$DEV bs=4 seek=27779712 count=36439
dd if=$DEV of=/tmp/chk.bin bs=4 skip=27779712 count=36439
cmp /tmp/chk.bin $BASE/094_094_Measuring95_95.bin

echo "== 095_Measuring96_96 ==
dd if=$BASE/095_095_Measuring96_96.bin of=$DEV bs=4 seek=27749504 count=30142
dd if=$DEV of=/tmp/chk.bin bs=4 skip=27749504 count=30142
cmp /tmp/chk.bin $BASE/095_095_Measuring96_96.bin

echo "== 096_Measuring97_97 ==
dd if=$BASE/096_096_Measuring97_97.bin of=$DEV bs=1 seek=110875648 count=121902
dd if=$DEV of=/tmp/chk.bin bs=1 skip=110875648 count=121902
cmp /tmp/chk.bin $BASE/096_096_Measuring97_97.bin

echo "== 097_Measuring98_98 ==
dd if=$BASE/097_097_Measuring98_98.bin of=$DEV bs=1 seek=110754304 count=121294
dd if=$DEV of=/tmp/chk.bin bs=1 skip=110754304 count=121294
cmp /tmp/chk.bin $BASE/097_097_Measuring98_98.bin

echo "== 098_Measuring99_99 ==
dd if=$BASE/098_098_Measuring99_99.bin of=$DEV bs=1 seek=110638592 count=115589
dd if=$DEV of=/tmp/chk.bin bs=1 skip=110638592 count=115589
cmp /tmp/chk.bin $BASE/098_098_Measuring99_99.bin

echo "== 099_Measuring100_100 ==
dd if=$BASE/099_099_Measuring100_100.bin of=$DEV bs=1 seek=126764032 count=110723
dd if=$DEV of=/tmp/chk.bin bs=1 skip=126764032 count=110723
cmp /tmp/chk.bin $BASE/099_099_Measuring100_100.bin

echo "== 100_Measuring101_101 ==
dd if=$BASE/100_100_Measuring101_101.bin of=$DEV bs=4 seek=31664128 count=26810
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31664128 count=26810
cmp /tmp/chk.bin $BASE/100_100_Measuring101_101.bin

echo "== 101_Measuring102_102 ==
dd if=$BASE/101_101_Measuring102_102.bin of=$DEV bs=1 seek=126569984 count=86055
dd if=$DEV of=/tmp/chk.bin bs=1 skip=126569984 count=86055
cmp /tmp/chk.bin $BASE/101_101_Measuring102_102.bin

echo "== 102_Measuring103_103 ==
dd if=$BASE/102_102_Measuring103_103.bin of=$DEV bs=1 seek=126484480 count=85118
dd if=$DEV of=/tmp/chk.bin bs=1 skip=126484480 count=85118
cmp /tmp/chk.bin $BASE/102_102_Measuring103_103.bin

echo "== 103_Measuring104_104 ==
dd if=$BASE/103_103_Measuring104_104.bin of=$DEV bs=4 seek=31600000 count=21003
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31600000 count=21003
cmp /tmp/chk.bin $BASE/103_103_Measuring104_104.bin

echo "== 104_Measuring105_105 ==
dd if=$BASE/104_104_Measuring105_105.bin of=$DEV bs=4 seek=31579648 count=20267
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31579648 count=20267
cmp /tmp/chk.bin $BASE/104_104_Measuring105_105.bin

echo "== 105_Measuring106_106 ==
dd if=$BASE/105_105_Measuring106_106.bin of=$DEV bs=1 seek=126240256 count=77823
dd if=$DEV of=/tmp/chk.bin bs=1 skip=126240256 count=77823
cmp /tmp/chk.bin $BASE/105_105_Measuring106_106.bin

echo "== 106_Measuring107_107 ==
dd if=$BASE/106_106_Measuring107_107.bin of=$DEV bs=1 seek=126164480 count=75410
dd if=$DEV of=/tmp/chk.bin bs=1 skip=126164480 count=75410
cmp /tmp/chk.bin $BASE/106_106_Measuring107_107.bin

echo "== 107_Measuring108_108 ==
dd if=$BASE/107_107_Measuring108_108.bin of=$DEV bs=4 seek=31527936 count=13116
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31527936 count=13116
cmp /tmp/chk.bin $BASE/107_107_Measuring108_108.bin

echo "== 108_Measuring109_109 ==
dd if=$BASE/108_108_Measuring109_109.bin of=$DEV bs=4 seek=31514496 count=13398
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31514496 count=13398
cmp /tmp/chk.bin $BASE/108_108_Measuring109_109.bin

echo "== 109_Measuring110_110 ==
dd if=$BASE/109_109_Measuring110_110.bin of=$DEV bs=1 seek=125961728 count=52559
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125961728 count=52559
cmp /tmp/chk.bin $BASE/109_109_Measuring110_110.bin

echo "== 110_Measuring111_111 ==
dd if=$BASE/110_110_Measuring111_111.bin of=$DEV bs=1 seek=125914624 count=46569
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125914624 count=46569
cmp /tmp/chk.bin $BASE/110_110_Measuring111_111.bin

echo "== 111_Measuring112_112 ==
dd if=$BASE/111_111_Measuring112_112.bin of=$DEV bs=1 seek=125874176 count=40243
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125874176 count=40243
cmp /tmp/chk.bin $BASE/111_111_Measuring112_112.bin

echo "== 112_Measuring113_113 ==
dd if=$BASE/112_112_Measuring113_113.bin of=$DEV bs=1 seek=125828608 count=45031
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125828608 count=45031
cmp /tmp/chk.bin $BASE/112_112_Measuring113_113.bin

echo "== 113_Measuring114_114 ==
dd if=$BASE/113_113_Measuring114_114.bin of=$DEV bs=4 seek=31447040 count=10034
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31447040 count=10034
cmp /tmp/chk.bin $BASE/113_113_Measuring114_114.bin

echo "== 114_Measuring115_115 ==
dd if=$BASE/114_114_Measuring115_115.bin of=$DEV bs=4 seek=31438720 count=8231
dd if=$DEV of=/tmp/chk.bin bs=4 skip=31438720 count=8231
cmp /tmp/chk.bin $BASE/114_114_Measuring115_115.bin

echo "== 115_Measuring116_116 ==
dd if=$BASE/115_115_Measuring116_116.bin of=$DEV bs=1 seek=125727744 count=27031
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125727744 count=27031
cmp /tmp/chk.bin $BASE/115_115_Measuring116_116.bin

echo "== 116_Measuring117_117 ==
dd if=$BASE/116_116_Measuring117_117.bin of=$DEV bs=1 seek=125703168 count=24325
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125703168 count=24325
cmp /tmp/chk.bin $BASE/116_116_Measuring117_117.bin

echo "== 117_Measuring118_118 ==
dd if=$BASE/117_117_Measuring118_118.bin of=$DEV bs=1 seek=125680128 count=22811
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125680128 count=22811
cmp /tmp/chk.bin $BASE/117_117_Measuring118_118.bin

echo "== 118_Measuring119_119 ==
dd if=$BASE/118_118_Measuring119_119.bin of=$DEV bs=1 seek=125660672 count=19025
dd if=$DEV of=/tmp/chk.bin bs=1 skip=125660672 count=19025
cmp /tmp/chk.bin $BASE/118_118_Measuring119_119.bin

rm /tmp/chk.bin
echo "restore done - run reboot to apply"
