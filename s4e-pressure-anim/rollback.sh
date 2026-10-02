#!/bin/sh
# 写回 S4 原厂图标

DEV=/dev/app
BASE=/data/s5icons/payload_rollback

echo "target check"
ls -l $DEV

echo "== canary_superblock ==
dd if=$BASE/000_canary_superblock.bin of=$DEV bs=4 seek=0 count=8
echo "== 003_Measuring4_4 ==
dd if=$BASE/001_003_Measuring4_4.bin of=$DEV bs=1 seek=121341952 count=5078
echo "== 004_Measuring5_5 ==
dd if=$BASE/002_004_Measuring5_5.bin of=$DEV bs=1 seek=119374336 count=6327
echo "== 005_Measuring6_6 ==
dd if=$BASE/003_005_Measuring6_6.bin of=$DEV bs=4 seek=29353344 count=2109
echo "== 006_Measuring7_7 ==
dd if=$BASE/004_006_Measuring7_7.bin of=$DEV bs=1 seek=115506688 count=11785
echo "== 007_Measuring8_8 ==
dd if=$BASE/005_007_Measuring8_8.bin of=$DEV bs=1 seek=113678336 count=17510
echo "== 008_Measuring9_9 ==
dd if=$BASE/006_008_Measuring9_9.bin of=$DEV bs=1 seek=112016384 count=23011
echo "== 009_Measuring10_10 ==
dd if=$BASE/007_009_Measuring10_10.bin of=$DEV bs=1 seek=126875136 count=31377
echo "== 010_Measuring11_11 ==
dd if=$BASE/008_010_Measuring11_11.bin of=$DEV bs=4 seek=31503616 count=10776
echo "== 011_Measuring12_12 ==
dd if=$BASE/009_011_Measuring12_12.bin of=$DEV bs=1 seek=125605888 count=54415
echo "== 012_Measuring13_13 ==
dd if=$BASE/010_012_Measuring13_13.bin of=$DEV bs=1 seek=125539840 count=65693
echo "== 013_Measuring14_14 ==
dd if=$BASE/011_013_Measuring14_14.bin of=$DEV bs=1 seek=125463552 count=75926
echo "== 014_Measuring15_15 ==
dd if=$BASE/012_014_Measuring15_15.bin of=$DEV bs=1 seek=125372928 count=90514
echo "== 015_Measuring16_16 ==
dd if=$BASE/013_015_Measuring16_16.bin of=$DEV bs=1 seek=125251584 count=120902
echo "== 016_Measuring17_17 ==
dd if=$BASE/014_016_Measuring17_17.bin of=$DEV bs=4 seek=31280896 count=31895
echo "== 017_Measuring18_18 ==
dd if=$BASE/015_017_Measuring18_18.bin of=$DEV bs=1 seek=124991488 count=131691
echo "== 018_Measuring19_19 ==
dd if=$BASE/016_018_Measuring19_19.bin of=$DEV bs=1 seek=124854784 count=136658
echo "== 019_Measuring20_20 ==
dd if=$BASE/017_019_Measuring20_20.bin of=$DEV bs=1 seek=124708352 count=141610
echo "== 020_Measuring21_21 ==
dd if=$BASE/018_020_Measuring21_21.bin of=$DEV bs=1 seek=124561920 count=145939
echo "== 021_Measuring22_22 ==
dd if=$BASE/019_021_Measuring22_22.bin of=$DEV bs=1 seek=124407296 count=154315
echo "== 022_Measuring23_23 ==
dd if=$BASE/020_022_Measuring23_23.bin of=$DEV bs=1 seek=124248064 count=158922
echo "== 023_Measuring24_24 ==
dd if=$BASE/021_023_Measuring24_24.bin of=$DEV bs=1 seek=124083712 count=164011
echo "== 024_Measuring25_25 ==
dd if=$BASE/022_024_Measuring25_25.bin of=$DEV bs=1 seek=123916288 count=166983
echo "== 025_Measuring26_26 ==
dd if=$BASE/023_025_Measuring26_26.bin of=$DEV bs=1 seek=123746816 count=169431
echo "== 026_Measuring27_27 ==
dd if=$BASE/024_026_Measuring27_27.bin of=$DEV bs=1 seek=123574784 count=171709
echo "== 027_Measuring28_28 ==
dd if=$BASE/025_027_Measuring28_28.bin of=$DEV bs=1 seek=123400704 count=173905
echo "== 028_Measuring29_29 ==
dd if=$BASE/026_028_Measuring29_29.bin of=$DEV bs=1 seek=123225088 count=175146
echo "== 029_Measuring30_30 ==
dd if=$BASE/027_029_Measuring30_30.bin of=$DEV bs=1 seek=123042816 count=176699
echo "== 030_Measuring31_31 ==
dd if=$BASE/028_030_Measuring31_31.bin of=$DEV bs=4 seek=30716032 count=44562
echo "== 031_Measuring32_32 ==
dd if=$BASE/029_031_Measuring32_32.bin of=$DEV bs=4 seek=30670848 count=45167
echo "== 032_Measuring33_33 ==
dd if=$BASE/030_032_Measuring33_33.bin of=$DEV bs=1 seek=122497024 count=186322
echo "== 033_Measuring34_34 ==
dd if=$BASE/031_033_Measuring34_34.bin of=$DEV bs=4 seek=30577152 count=47065
echo "== 034_Measuring35_35 ==
dd if=$BASE/032_034_Measuring35_35.bin of=$DEV bs=1 seek=122118656 count=189862
echo "== 035_Measuring36_36 ==
dd if=$BASE/033_035_Measuring36_36.bin of=$DEV bs=1 seek=121927680 count=190691
echo "== 036_Measuring37_37 ==
dd if=$BASE/034_036_Measuring37_37.bin of=$DEV bs=1 seek=121735680 count=191837
echo "== 037_Measuring38_38 ==
dd if=$BASE/035_037_Measuring38_38.bin of=$DEV bs=1 seek=121542144 count=193189
echo "== 038_Measuring39_39 ==
dd if=$BASE/036_038_Measuring39_39.bin of=$DEV bs=1 seek=121347072 count=194939
echo "== 039_Measuring40_40 ==
dd if=$BASE/037_039_Measuring40_40.bin of=$DEV bs=1 seek=121146368 count=195239
echo "== 040_Measuring41_41 ==
dd if=$BASE/038_040_Measuring41_41.bin of=$DEV bs=1 seek=120950272 count=195793
echo "== 041_Measuring42_42 ==
dd if=$BASE/039_041_Measuring42_42.bin of=$DEV bs=1 seek=120754176 count=196046
echo "== 042_Measuring43_43 ==
dd if=$BASE/040_042_Measuring43_43.bin of=$DEV bs=1 seek=120558080 count=196021
echo "== 043_Measuring44_44 ==
dd if=$BASE/041_043_Measuring44_44.bin of=$DEV bs=1 seek=120361472 count=196086
echo "== 044_Measuring45_45 ==
dd if=$BASE/042_044_Measuring45_45.bin of=$DEV bs=4 seek=30041344 count=48913
echo "== 045_Measuring46_46 ==
dd if=$BASE/043_045_Measuring46_46.bin of=$DEV bs=1 seek=119969280 count=195974
echo "== 046_Measuring47_47 ==
dd if=$BASE/044_046_Measuring47_47.bin of=$DEV bs=1 seek=119773184 count=195999
echo "== 047_Measuring48_48 ==
dd if=$BASE/045_047_Measuring48_48.bin of=$DEV bs=1 seek=119577088 count=195847
echo "== 048_Measuring49_49 ==
dd if=$BASE/046_048_Measuring49_49.bin of=$DEV bs=1 seek=119380992 count=195899
echo "== 049_Measuring50_50 ==
dd if=$BASE/047_049_Measuring50_50.bin of=$DEV bs=1 seek=119177728 count=196154
echo "== 050_Measuring51_51 ==
dd if=$BASE/048_050_Measuring51_51.bin of=$DEV bs=1 seek=118981120 count=196246
echo "== 051_Measuring52_52 ==
dd if=$BASE/049_051_Measuring52_52.bin of=$DEV bs=1 seek=118785024 count=196042
echo "== 052_Measuring53_53 ==
dd if=$BASE/050_052_Measuring53_53.bin of=$DEV bs=1 seek=118588928 count=195985
echo "== 053_Measuring54_54 ==
dd if=$BASE/051_053_Measuring54_54.bin of=$DEV bs=1 seek=118392320 count=196538
echo "== 054_Measuring55_55 ==
dd if=$BASE/052_054_Measuring55_55.bin of=$DEV bs=1 seek=118198272 count=193546
echo "== 055_Measuring56_56 ==
dd if=$BASE/053_055_Measuring56_56.bin of=$DEV bs=4 seek=29501056 count=48496
echo "== 056_Measuring57_57 ==
dd if=$BASE/054_056_Measuring57_57.bin of=$DEV bs=1 seek=117810176 count=193954
echo "== 057_Measuring58_58 ==
dd if=$BASE/055_057_Measuring58_58.bin of=$DEV bs=1 seek=117616128 count=193929
echo "== 058_Measuring59_59 ==
dd if=$BASE/056_058_Measuring59_59.bin of=$DEV bs=1 seek=117422080 count=193761
echo "== 059_Measuring60_60 ==
dd if=$BASE/057_059_Measuring60_60.bin of=$DEV bs=1 seek=117218816 count=194029
echo "== 060_Measuring61_61 ==
dd if=$BASE/058_060_Measuring61_61.bin of=$DEV bs=1 seek=117029376 count=189089
echo "== 061_Measuring62_62 ==
dd if=$BASE/059_061_Measuring62_62.bin of=$DEV bs=1 seek=116838400 count=190474
echo "== 062_Measuring63_63 ==
dd if=$BASE/060_062_Measuring63_63.bin of=$DEV bs=4 seek=29161856 count=47687
echo "== 063_Measuring64_64 ==
dd if=$BASE/061_063_Measuring64_64.bin of=$DEV bs=1 seek=116455936 count=190975
echo "== 064_Measuring65_65 ==
dd if=$BASE/062_064_Measuring65_65.bin of=$DEV bs=1 seek=116263424 count=192023
echo "== 065_Measuring66_66 ==
dd if=$BASE/063_065_Measuring66_66.bin of=$DEV bs=1 seek=116071424 count=191903
echo "== 066_Measuring67_67 ==
dd if=$BASE/064_066_Measuring67_67.bin of=$DEV bs=1 seek=115888640 count=182358
echo "== 067_Measuring68_68 ==
dd if=$BASE/065_067_Measuring68_68.bin of=$DEV bs=1 seek=115704320 count=183906
echo "== 068_Measuring69_69 ==
dd if=$BASE/066_068_Measuring69_69.bin of=$DEV bs=1 seek=115518976 count=185033
echo "== 069_Measuring70_70 ==
dd if=$BASE/067_069_Measuring70_70.bin of=$DEV bs=1 seek=115321856 count=184662
echo "== 070_Measuring71_71 ==
dd if=$BASE/068_070_Measuring71_71.bin of=$DEV bs=1 seek=115136512 count=184877
echo "== 071_Measuring72_72 ==
dd if=$BASE/069_071_Measuring72_72.bin of=$DEV bs=1 seek=114951680 count=184574
echo "== 072_Measuring73_73 ==
dd if=$BASE/070_072_Measuring73_73.bin of=$DEV bs=1 seek=114770432 count=180773
echo "== 073_Measuring74_74 ==
dd if=$BASE/071_073_Measuring74_74.bin of=$DEV bs=4 seek=28647424 count=45157
echo "== 074_Measuring75_75 ==
dd if=$BASE/072_074_Measuring75_75.bin of=$DEV bs=1 seek=114409472 count=179919
echo "== 075_Measuring76_76 ==
dd if=$BASE/073_075_Measuring76_76.bin of=$DEV bs=1 seek=114228736 count=180517
echo "== 076_Measuring77_77 ==
dd if=$BASE/074_076_Measuring77_77.bin of=$DEV bs=1 seek=114048000 count=180677
echo "== 077_Measuring78_78 ==
dd if=$BASE/075_077_Measuring78_78.bin of=$DEV bs=1 seek=113867264 count=180537
echo "== 078_Measuring79_79 ==
dd if=$BASE/076_078_Measuring79_79.bin of=$DEV bs=1 seek=113696256 count=170518
echo "== 079_Measuring80_80 ==
dd if=$BASE/077_079_Measuring80_80.bin of=$DEV bs=1 seek=113507840 count=170059
echo "== 080_Measuring81_81 ==
dd if=$BASE/078_080_Measuring81_81.bin of=$DEV bs=1 seek=113336320 count=171247
echo "== 081_Measuring82_82 ==
dd if=$BASE/079_081_Measuring82_82.bin of=$DEV bs=1 seek=113165312 count=170939
echo "== 082_Measuring83_83 ==
dd if=$BASE/080_082_Measuring83_83.bin of=$DEV bs=1 seek=112994816 count=170193
echo "== 083_Measuring84_84 ==
dd if=$BASE/081_083_Measuring84_84.bin of=$DEV bs=1 seek=112840704 count=153998
echo "== 084_Measuring85_85 ==
dd if=$BASE/082_084_Measuring85_85.bin of=$DEV bs=4 seek=28170880 count=39261
echo "== 085_Measuring86_86 ==
dd if=$BASE/083_085_Measuring86_86.bin of=$DEV bs=4 seek=28131200 count=39545
echo "== 086_Measuring87_87 ==
dd if=$BASE/084_086_Measuring87_87.bin of=$DEV bs=1 seek=112364544 count=160025
echo "== 087_Measuring88_88 ==
dd if=$BASE/085_087_Measuring88_88.bin of=$DEV bs=1 seek=112203264 count=160963
echo "== 088_Measuring89_89 ==
dd if=$BASE/086_088_Measuring89_89.bin of=$DEV bs=1 seek=112039936 count=163153
echo "== 089_Measuring90_90 ==
dd if=$BASE/087_089_Measuring90_90.bin of=$DEV bs=1 seek=111863808 count=152329
echo "== 090_Measuring91_91 ==
dd if=$BASE/088_090_Measuring91_91.bin of=$DEV bs=1 seek=111712256 count=151129
echo "== 091_Measuring92_92 ==
dd if=$BASE/089_091_Measuring92_92.bin of=$DEV bs=1 seek=111562240 count=149917
echo "== 092_Measuring93_93 ==
dd if=$BASE/090_092_Measuring93_93.bin of=$DEV bs=1 seek=111413248 count=148930
echo "== 093_Measuring94_94 ==
dd if=$BASE/091_093_Measuring94_94.bin of=$DEV bs=4 seek=27816192 count=37010
echo "== 094_Measuring95_95 ==
dd if=$BASE/092_094_Measuring95_95.bin of=$DEV bs=4 seek=27779712 count=36439
echo "== 095_Measuring96_96 ==
dd if=$BASE/093_095_Measuring96_96.bin of=$DEV bs=4 seek=27749504 count=30142
echo "== 096_Measuring97_97 ==
dd if=$BASE/094_096_Measuring97_97.bin of=$DEV bs=1 seek=110875648 count=121902
echo "== 097_Measuring98_98 ==
dd if=$BASE/095_097_Measuring98_98.bin of=$DEV bs=1 seek=110754304 count=121294
echo "== 098_Measuring99_99 ==
dd if=$BASE/096_098_Measuring99_99.bin of=$DEV bs=1 seek=110638592 count=115589
echo "== 099_Measuring100_100 ==
dd if=$BASE/097_099_Measuring100_100.bin of=$DEV bs=1 seek=126764032 count=110723
echo "== 100_Measuring101_101 ==
dd if=$BASE/098_100_Measuring101_101.bin of=$DEV bs=4 seek=31664128 count=26810
echo "== 101_Measuring102_102 ==
dd if=$BASE/099_101_Measuring102_102.bin of=$DEV bs=1 seek=126569984 count=86055
echo "== 102_Measuring103_103 ==
dd if=$BASE/100_102_Measuring103_103.bin of=$DEV bs=1 seek=126484480 count=85118
echo "== 103_Measuring104_104 ==
dd if=$BASE/101_103_Measuring104_104.bin of=$DEV bs=4 seek=31600000 count=21003
echo "== 104_Measuring105_105 ==
dd if=$BASE/102_104_Measuring105_105.bin of=$DEV bs=4 seek=31579648 count=20267
echo "== 105_Measuring106_106 ==
dd if=$BASE/103_105_Measuring106_106.bin of=$DEV bs=1 seek=126240256 count=77823
echo "== 106_Measuring107_107 ==
dd if=$BASE/104_106_Measuring107_107.bin of=$DEV bs=1 seek=126164480 count=75410
echo "== 107_Measuring108_108 ==
dd if=$BASE/105_107_Measuring108_108.bin of=$DEV bs=4 seek=31527936 count=13116
echo "== 108_Measuring109_109 ==
dd if=$BASE/106_108_Measuring109_109.bin of=$DEV bs=4 seek=31514496 count=13398
echo "== 109_Measuring110_110 ==
dd if=$BASE/107_109_Measuring110_110.bin of=$DEV bs=1 seek=125961728 count=52559
echo "== 110_Measuring111_111 ==
dd if=$BASE/108_110_Measuring111_111.bin of=$DEV bs=1 seek=125914624 count=46569
echo "== 111_Measuring112_112 ==
dd if=$BASE/109_111_Measuring112_112.bin of=$DEV bs=1 seek=125874176 count=40243
echo "== 112_Measuring113_113 ==
dd if=$BASE/110_112_Measuring113_113.bin of=$DEV bs=1 seek=125828608 count=45031
echo "== 113_Measuring114_114 ==
dd if=$BASE/111_113_Measuring114_114.bin of=$DEV bs=4 seek=31447040 count=10034
echo "== 114_Measuring115_115 ==
dd if=$BASE/112_114_Measuring115_115.bin of=$DEV bs=4 seek=31438720 count=8231
echo "== 115_Measuring116_116 ==
dd if=$BASE/113_115_Measuring116_116.bin of=$DEV bs=1 seek=125727744 count=27031
echo "== 116_Measuring117_117 ==
dd if=$BASE/114_116_Measuring117_117.bin of=$DEV bs=1 seek=125703168 count=24325
echo "== 117_Measuring118_118 ==
dd if=$BASE/115_117_Measuring118_118.bin of=$DEV bs=1 seek=125680128 count=22811
echo "== 118_Measuring119_119 ==
dd if=$BASE/116_118_Measuring119_119.bin of=$DEV bs=1 seek=125660672 count=19025
echo "rollback done - run reboot to apply"
