#!/bin/sh
# 写回 S4 原厂图标

DEV=/dev/app
BASE=/data/s5icons/payload_rollback

echo "target check"
ls -l $DEV

echo "== canary_superblock ==
dd if=$BASE/000_canary_superblock.bin of=$DEV bs=4 seek=0 count=8
echo "== activities ==
dd if=$BASE/001_activities.bin of=$DEV bs=4 seek=66401536 count=5443
echo "== alarm ==
dd if=$BASE/002_alarm.bin of=$DEV bs=4 seek=63872896 count=20739
echo "== barometer ==
dd if=$BASE/003_barometer.bin of=$DEV bs=4 seek=60856064 count=20739
echo "== breath ==
dd if=$BASE/004_breath.bin of=$DEV bs=4 seek=49632000 count=20739
echo "== calendar ==
dd if=$BASE/005_calendar.bin of=$DEV bs=4 seek=49360000 count=20739
echo "== chronograph ==
dd if=$BASE/006_chronograph.bin of=$DEV bs=4 seek=48832384 count=20739
echo "== compass ==
dd if=$BASE/007_compass.bin of=$DEV bs=4 seek=48399616 count=5443
echo "== debug ==
dd if=$BASE/008_debug.bin of=$DEV bs=4 seek=48261248 count=5443
echo "== esimsms ==
dd if=$BASE/009_esimsms.bin of=$DEV bs=4 seek=48072832 count=20739
echo "== find_phone ==
dd if=$BASE/010_find_phone.bin of=$DEV bs=4 seek=47955968 count=20739
echo "== flashlight ==
dd if=$BASE/011_flashlight.bin of=$DEV bs=4 seek=47935104 count=20739
echo "== health_today ==
dd if=$BASE/012_health_today.bin of=$DEV bs=4 seek=42503808 count=20739
echo "== heartrate ==
dd if=$BASE/013_heartrate.bin of=$DEV bs=4 seek=41921024 count=20739
echo "== innovation_research ==
dd if=$BASE/014_innovation_research.bin of=$DEV bs=4 seek=39566976 count=20739
echo "== interconnect ==
dd if=$BASE/015_interconnect.bin of=$DEV bs=4 seek=39542784 count=20739
echo "== lua ==
dd if=$BASE/016_lua.bin of=$DEV bs=4 seek=39507072 count=5443
echo "== media ==
dd if=$BASE/017_media.bin of=$DEV bs=4 seek=39467136 count=20739
echo "== mijia ==
dd if=$BASE/018_mijia.bin of=$DEV bs=4 seek=39216256 count=20739
echo "== nfccard ==
dd if=$BASE/019_nfccard.bin of=$DEV bs=4 seek=38783744 count=20739
echo "== oxygen ==
dd if=$BASE/020_oxygen.bin of=$DEV bs=4 seek=37495552 count=20739
echo "== perpetual_calendar ==
dd if=$BASE/021_perpetual_calendar.bin of=$DEV bs=4 seek=32305024 count=5443
echo "== phone ==
dd if=$BASE/022_phone.bin of=$DEV bs=4 seek=32060416 count=20739
echo "== phone_contacts ==
dd if=$BASE/023_phone_contacts.bin of=$DEV bs=4 seek=32114816 count=20739
echo "== pressure ==
dd if=$BASE/024_pressure.bin of=$DEV bs=4 seek=31727872 count=20739
echo "== recorder ==
dd if=$BASE/025_recorder.bin of=$DEV bs=4 seek=27169152 count=20739
echo "== remote_camera ==
dd if=$BASE/026_remote_camera.bin of=$DEV bs=4 seek=26627712 count=5443
echo "== settings ==
dd if=$BASE/027_settings.bin of=$DEV bs=4 seek=21733376 count=20739
echo "== sleep ==
dd if=$BASE/028_sleep.bin of=$DEV bs=4 seek=21321984 count=20739
echo "== sports ==
dd if=$BASE/029_sports.bin of=$DEV bs=4 seek=19839872 count=20739
echo "== sports_course ==
dd if=$BASE/030_sports_course.bin of=$DEV bs=4 seek=21285120 count=20739
echo "== sports_record ==
dd if=$BASE/031_sports_record.bin of=$DEV bs=4 seek=19500032 count=20739
echo "== sports_training ==
dd if=$BASE/032_sports_training.bin of=$DEV bs=4 seek=18459648 count=20739
echo "== timer ==
dd if=$BASE/033_timer.bin of=$DEV bs=4 seek=15421184 count=20739
echo "== todolist ==
dd if=$BASE/034_todolist.bin of=$DEV bs=4 seek=15377408 count=20739
echo "== voice_aivs ==
dd if=$BASE/035_voice_aivs.bin of=$DEV bs=4 seek=13660416 count=20739
echo "== weather ==
dd if=$BASE/036_weather.bin of=$DEV bs=4 seek=6256768 count=20739
echo "== womenhealth ==
dd if=$BASE/037_womenhealth.bin of=$DEV bs=4 seek=73344 count=20739
echo "== cc_add ==
dd if=$BASE/038_cc_add.bin of=$DEV bs=4 seek=48398592 count=835
echo "== cc_air_mode_close ==
dd if=$BASE/039_cc_air_mode_close.bin of=$DEV bs=4 seek=48394112 count=4355
echo "== cc_air_mode_conn ==
dd if=$BASE/040_cc_air_mode_conn.bin of=$DEV bs=4 seek=48393216 count=835
echo "== cc_air_mode_open ==
dd if=$BASE/041_cc_air_mode_open.bin of=$DEV bs=4 seek=48384256 count=4355
echo "== cc_battery_close ==
dd if=$BASE/042_cc_battery_close.bin of=$DEV bs=4 seek=48379776 count=4355
echo "== cc_battery_open ==
dd if=$BASE/043_cc_battery_open.bin of=$DEV bs=4 seek=48375296 count=4355
echo "== cc_bt_connect ==
dd if=$BASE/044_cc_bt_connect.bin of=$DEV bs=4 seek=48374400 count=835
echo "== cc_bt_disconnect ==
dd if=$BASE/045_cc_bt_disconnect.bin of=$DEV bs=4 seek=48373504 count=835
echo "== cc_cancel ==
dd if=$BASE/046_cc_cancel.bin of=$DEV bs=4 seek=48372608 count=835
echo "== cc_drain_close ==
dd if=$BASE/047_cc_drain_close.bin of=$DEV bs=4 seek=48368128 count=4355
echo "== cc_earphone ==
dd if=$BASE/048_cc_earphone.bin of=$DEV bs=4 seek=48353408 count=835
echo "== cc_find_phone_close ==
dd if=$BASE/049_cc_find_phone_close.bin of=$DEV bs=4 seek=48348928 count=4355
echo "== cc_flashlight ==
dd if=$BASE/050_cc_flashlight.bin of=$DEV bs=4 seek=48339968 count=4355
echo "== cc_mobile_network_close ==
dd if=$BASE/051_cc_mobile_network_close.bin of=$DEV bs=4 seek=48334592 count=4355
echo "== cc_mobile_network_open ==
dd if=$BASE/052_cc_mobile_network_open.bin of=$DEV bs=4 seek=48325632 count=4355
echo "== cc_mute_close ==
dd if=$BASE/053_cc_mute_close.bin of=$DEV bs=4 seek=48321152 count=4355
echo "== cc_mute_open ==
dd if=$BASE/054_cc_mute_open.bin of=$DEV bs=4 seek=48316672 count=4355
echo "== cc_not_disturb_close ==
dd if=$BASE/055_cc_not_disturb_close.bin of=$DEV bs=4 seek=48301440 count=4355
echo "== cc_not_disturb_open ==
dd if=$BASE/056_cc_not_disturb_open.bin of=$DEV bs=4 seek=48296960 count=4355
echo "== cc_raise_bright_close ==
dd if=$BASE/057_cc_raise_bright_close.bin of=$DEV bs=4 seek=48288000 count=4355
echo "== cc_raise_bright_open ==
dd if=$BASE/058_cc_raise_bright_open.bin of=$DEV bs=4 seek=48283520 count=4355
echo "== cc_settings ==
dd if=$BASE/059_cc_settings.bin of=$DEV bs=4 seek=48279040 count=4355
echo "== sys_lock_icon ==
dd if=$BASE/060_sys_lock_icon.bin of=$DEV bs=4 seek=15582848 count=515
echo "== sys_system_lock ==
dd if=$BASE/061_sys_system_lock.bin of=$DEV bs=4 seek=48587776 count=835
echo "== sys_quiet_mode ==
dd if=$BASE/062_sys_quiet_mode.bin of=$DEV bs=4 seek=48616576 count=835
echo "== sys_notifications_no_message ==
dd if=$BASE/063_sys_notifications_no_message.bin of=$DEV bs=4 seek=37691776 count=1859
echo "== sys_notify ==
dd if=$BASE/064_sys_notify.bin of=$DEV bs=4 seek=21762688 count=1283
echo "== sys_esim_sms_reminder ==
dd if=$BASE/065_sys_esim_sms_reminder.bin of=$DEV bs=4 seek=48108800 count=1859
echo "== sys_enable_donot_disturb ==
dd if=$BASE/066_sys_enable_donot_disturb.bin of=$DEV bs=4 seek=39244160 count=1283
echo "== sys_disable_donot_disturb ==
dd if=$BASE/067_sys_disable_donot_disturb.bin of=$DEV bs=4 seek=39247488 count=1283
echo "== sys_presure_relax ==
dd if=$BASE/068_sys_presure_relax.bin of=$DEV bs=4 seek=31843328 count=835
echo "== sys_presure_mild ==
dd if=$BASE/069_sys_presure_mild.bin of=$DEV bs=4 seek=31847552 count=835
echo "== sys_presure_mid ==
dd if=$BASE/070_sys_presure_mid.bin of=$DEV bs=4 seek=31851776 count=835
echo "== sys_presure_severe ==
dd if=$BASE/071_sys_presure_severe.bin of=$DEV bs=4 seek=31839104 count=835
echo "== sys_presure_mild32 ==
dd if=$BASE/072_sys_presure_mild32.bin of=$DEV bs=4 seek=31846912 count=515
echo "== sys_presure_mid32 ==
dd if=$BASE/073_sys_presure_mid32.bin of=$DEV bs=4 seek=31851136 count=515
echo "== sys_presure_severe32 ==
dd if=$BASE/074_sys_presure_severe32.bin of=$DEV bs=4 seek=31838464 count=515
echo "== sys_presure_icon ==
dd if=$BASE/075_sys_presure_icon.bin of=$DEV bs=4 seek=31852672 count=835
echo "== sys_press_grade1 ==
dd if=$BASE/076_sys_press_grade1.bin of=$DEV bs=4 seek=32011648 count=515
echo "== sys_press_grade2 ==
dd if=$BASE/077_sys_press_grade2.bin of=$DEV bs=4 seek=32011008 count=515
echo "== sys_press_grade3 ==
dd if=$BASE/078_sys_press_grade3.bin of=$DEV bs=4 seek=32010368 count=515
echo "== sys_press_grade4 ==
dd if=$BASE/079_sys_press_grade4.bin of=$DEV bs=4 seek=32009728 count=515
echo "== cc_network_4g ==
dd if=$BASE/080_cc_network_4g.bin of=$DEV bs=4 seek=48310400 count=835
echo "== cc_network_3g ==
dd if=$BASE/081_cc_network_3g.bin of=$DEV bs=4 seek=48315776 count=835
echo "== cc_signal_strength ==
dd if=$BASE/082_cc_signal_strength.bin of=$DEV bs=4 seek=48278144 count=835
echo "== cc_signal_strength1 ==
dd if=$BASE/083_cc_signal_strength1.bin of=$DEV bs=4 seek=48277248 count=835
echo "== cc_signal_strength2 ==
dd if=$BASE/084_cc_signal_strength2.bin of=$DEV bs=4 seek=48276352 count=835
echo "== cc_signal_strength3 ==
dd if=$BASE/085_cc_signal_strength3.bin of=$DEV bs=4 seek=48275456 count=835
echo "== cc_signal_strength4 ==
dd if=$BASE/086_cc_signal_strength4.bin of=$DEV bs=4 seek=48274560 count=835
echo "== cc_location ==
dd if=$BASE/087_cc_location.bin of=$DEV bs=4 seek=48339072 count=835
echo "== cc_network_3g_signal_1 ==
dd if=$BASE/088_cc_network_3g_signal_1.bin of=$DEV bs=4 seek=48313984 count=835
echo "== cc_network_3g_signal_2 ==
dd if=$BASE/089_cc_network_3g_signal_2.bin of=$DEV bs=4 seek=48313088 count=835
echo "== cc_network_3g_signal_3 ==
dd if=$BASE/090_cc_network_3g_signal_3.bin of=$DEV bs=4 seek=48312192 count=835
echo "== cc_network_3g_signal_4 ==
dd if=$BASE/091_cc_network_3g_signal_4.bin of=$DEV bs=4 seek=48311296 count=835
echo "== cc_network_3g_no_signal ==
dd if=$BASE/092_cc_network_3g_no_signal.bin of=$DEV bs=4 seek=48314880 count=835
echo "== cc_network_4g_signal_1 ==
dd if=$BASE/093_cc_network_4g_signal_1.bin of=$DEV bs=4 seek=48308608 count=835
echo "== cc_network_4g_signal_2 ==
dd if=$BASE/094_cc_network_4g_signal_2.bin of=$DEV bs=4 seek=48307712 count=835
echo "== cc_network_4g_signal_3 ==
dd if=$BASE/095_cc_network_4g_signal_3.bin of=$DEV bs=4 seek=48306816 count=835
echo "== cc_network_4g_signal_4 ==
dd if=$BASE/096_cc_network_4g_signal_4.bin of=$DEV bs=4 seek=48305920 count=835
echo "== cc_network_4g_no_signal ==
dd if=$BASE/097_cc_network_4g_no_signal.bin of=$DEV bs=4 seek=48309504 count=835
echo "== sys_notifications_car ==
dd if=$BASE/098_sys_notifications_car.bin of=$DEV bs=4 seek=37707392 count=1315
echo "== sys_notifications_default ==
dd if=$BASE/099_sys_notifications_default.bin of=$DEV bs=4 seek=37698688 count=8003
echo "== sys_notifications_default_small ==
dd if=$BASE/100_sys_notifications_default_small.bin of=$DEV bs=4 seek=37697792 count=835
echo "== sys_notifications_half_going ==
dd if=$BASE/101_sys_notifications_half_going.bin of=$DEV bs=4 seek=37694080 count=763
echo "== sys_notifications_half_point ==
dd if=$BASE/102_sys_notifications_half_point.bin of=$DEV bs=4 seek=37693696 count=323
echo "== sys_phone_icon_app_h_w_48 ==
dd if=$BASE/103_sys_phone_icon_app_h_w_48.bin of=$DEV bs=4 seek=32112512 count=835
echo "== sys_phone_icon_dial ==
dd if=$BASE/104_sys_phone_icon_dial.bin of=$DEV bs=4 seek=32111616 count=835
echo "== sys_phone_icon_hash ==
dd if=$BASE/105_sys_phone_icon_hash.bin of=$DEV bs=4 seek=32110720 count=835
echo "== sys_phone_icon_headphone_icon ==
dd if=$BASE/106_sys_phone_icon_headphone_icon.bin of=$DEV bs=4 seek=32109312 count=1283
echo "== sys_phone_icon_keypad_icon ==
dd if=$BASE/107_sys_phone_icon_keypad_icon.bin of=$DEV bs=4 seek=32106496 count=1283
echo "== sys_phone_icon_mic_off ==
dd if=$BASE/108_sys_phone_icon_mic_off.bin of=$DEV bs=4 seek=32097408 count=835
echo "== sys_phone_icon_mic_on ==
dd if=$BASE/109_sys_phone_icon_mic_on.bin of=$DEV bs=4 seek=32096512 count=835
echo "== sys_phone_icon_no_calllog ==
dd if=$BASE/110_sys_phone_icon_no_calllog.bin of=$DEV bs=4 seek=32094592 count=1859
echo "== sys_phone_icon_no_contacts ==
dd if=$BASE/111_sys_phone_icon_no_contacts.bin of=$DEV bs=4 seek=32092672 count=1859
echo "== sys_phone_icon_phone_icon ==
dd if=$BASE/112_sys_phone_icon_phone_icon.bin of=$DEV bs=4 seek=32090368 count=1283
echo "== sys_phone_icon_phone_icon_small ==
dd if=$BASE/113_sys_phone_icon_phone_icon_small.bin of=$DEV bs=4 seek=32089728 count=515
echo "== sys_phone_icon_plus ==
dd if=$BASE/114_sys_phone_icon_plus.bin of=$DEV bs=4 seek=32088832 count=835
echo "== sys_phone_icon_spk_icon_64 ==
dd if=$BASE/115_sys_phone_icon_spk_icon_64.bin of=$DEV bs=4 seek=32084224 count=1283
echo "== sys_phone_icon_star ==
dd if=$BASE/116_sys_phone_icon_star.bin of=$DEV bs=4 seek=32083328 count=835
echo "== sys_phone_icon_watch_icon ==
dd if=$BASE/117_sys_phone_icon_watch_icon.bin of=$DEV bs=4 seek=32081920 count=1283
echo "== sys_phone_icon_watch_icon_small ==
dd if=$BASE/118_sys_phone_icon_watch_icon_small.bin of=$DEV bs=4 seek=32081280 count=515
echo "== sys_phone_widget_widget_contact ==
dd if=$BASE/119_sys_phone_widget_widget_contact.bin of=$DEV bs=4 seek=32026624 count=3395
echo "== sys_phone_widget_widget_dialpad ==
dd if=$BASE/120_sys_phone_widget_widget_dialpad.bin of=$DEV bs=4 seek=32023168 count=3395
echo "== sys_phone_widget_widget_phone ==
dd if=$BASE/121_sys_phone_widget_widget_phone.bin of=$DEV bs=4 seek=32019712 count=3395
echo "== sys_recorder_ahead3 ==
dd if=$BASE/122_sys_recorder_ahead3.bin of=$DEV bs=4 seek=27191936 count=1859
echo "== sys_recorder_back3 ==
dd if=$BASE/123_sys_recorder_back3.bin of=$DEV bs=4 seek=27190016 count=1859
echo "== sys_recorder_main ==
dd if=$BASE/124_sys_recorder_main.bin of=$DEV bs=4 seek=27168256 count=835
echo "== sys_recorder_mark ==
dd if=$BASE/125_sys_recorder_mark.bin of=$DEV bs=4 seek=27167360 count=835
echo "== sys_recorder_mute ==
dd if=$BASE/126_sys_recorder_mute.bin of=$DEV bs=4 seek=27165568 count=835
echo "== sys_recorder_sound ==
dd if=$BASE/127_sys_recorder_sound.bin of=$DEV bs=4 seek=27163776 count=835
echo "== sys_recorder_trash ==
dd if=$BASE/128_sys_recorder_trash.bin of=$DEV bs=4 seek=27152128 count=835
echo "== sys_recorder_warning ==
dd if=$BASE/129_sys_recorder_warning.bin of=$DEV bs=4 seek=27150208 count=1859
echo "== sys_timer_icon_close ==
dd if=$BASE/130_sys_timer_icon_close.bin of=$DEV bs=4 seek=15576448 count=835
echo "== sys_timer_icon_pause ==
dd if=$BASE/131_sys_timer_icon_pause.bin of=$DEV bs=4 seek=15574656 count=835
echo "== sys_timer_icon_restart ==
dd if=$BASE/132_sys_timer_icon_restart.bin of=$DEV bs=4 seek=15573760 count=835
echo "== sys_timer_icon_start ==
dd if=$BASE/133_sys_timer_icon_start.bin of=$DEV bs=4 seek=15506304 count=835
echo "== sys_timer_icon_stop ==
dd if=$BASE/134_sys_timer_icon_stop.bin of=$DEV bs=4 seek=15505408 count=835
echo "== sys_timer_icon_widget_light12 ==
dd if=$BASE/135_sys_timer_icon_widget_light12.bin of=$DEV bs=4 seek=15474176 count=30211
echo "== sys_timer_icon_widget_light12_five ==
dd if=$BASE/136_sys_timer_icon_widget_light12_five.bin of=$DEV bs=4 seek=15443840 count=30211
echo "== sys_timer_icon_widget_pause ==
dd if=$BASE/137_sys_timer_icon_widget_pause.bin of=$DEV bs=4 seek=15442944 count=835
echo "== sys_timer_icon_widget_start ==
dd if=$BASE/138_sys_timer_icon_widget_start.bin of=$DEV bs=4 seek=15442048 count=835
echo "== sys_todolist_checked ==
dd if=$BASE/139_sys_todolist_checked.bin of=$DEV bs=4 seek=15420288 count=835
echo "== sys_todolist_create_todo_btn ==
dd if=$BASE/140_sys_todolist_create_todo_btn.bin of=$DEV bs=4 seek=15416064 count=4099
echo "== sys_todolist_dark12_bg ==
dd if=$BASE/141_sys_todolist_dark12_bg.bin of=$DEV bs=4 seek=15400192 count=15747
echo "== sys_todolist_empty ==
dd if=$BASE/142_sys_todolist_empty.bin of=$DEV bs=4 seek=15398272 count=1859
echo "== sys_todolist_reminder_big ==
dd if=$BASE/143_sys_todolist_reminder_big.bin of=$DEV bs=4 seek=15372928 count=4355
echo "== sys_todolist_reminder_small ==
dd if=$BASE/144_sys_todolist_reminder_small.bin of=$DEV bs=4 seek=15371008 count=1859
echo "== sys_todolist_tdl_dark11_bg ==
dd if=$BASE/145_sys_todolist_tdl_dark11_bg.bin of=$DEV bs=4 seek=15362944 count=8003
echo "== sys_todolist_tdl_light11_bg ==
dd if=$BASE/146_sys_todolist_tdl_light11_bg.bin of=$DEV bs=4 seek=15354880 count=8003
echo "== sys_todolist_unchecked ==
dd if=$BASE/147_sys_todolist_unchecked.bin of=$DEV bs=4 seek=15353984 count=835
echo "== sys_todolist_widget_dark_icon ==
dd if=$BASE/148_sys_todolist_widget_dark_icon.bin of=$DEV bs=4 seek=15352064 count=1859
echo "== sys_todolist_widget_light_icon ==
dd if=$BASE/149_sys_todolist_widget_light_icon.bin of=$DEV bs=4 seek=15350144 count=1859
echo "rollback done - run reboot to apply"
