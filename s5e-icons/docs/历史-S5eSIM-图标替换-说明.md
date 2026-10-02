# Xiaomi Watch S5 eSIM 图标替换 Lua 表盘 —— 交付说明

> 目标固件：`miwear.watch.p62lte_v3.112.035_full_adbe74f0 (1).bin`（**Xiaomi Watch S5 eSIM 46mm**，平台 p62lte，480×480）
> 图标来源：**Xiaomi Watch S5 41mm（q63, v4.101.020）的 OS4 图标包**（即上一个项目里那份 S5 图标）
> 全部结论都有本机脚本证据；**真机行为未验证**，第 8 节列出了要你实测的三点。

---

## 1. 交付物

| 文件 | 说明 |
|---|---|
| `_out/faces/S5eIcons.face` | **主交付物** 8,983,508 B（sha256 17f3b9444a0477c5…），表盘 id `462150101`，b5=0（与固件自带表盘一致） |
| `_out/faces/S5eIcons_toolchain.face` | 官方工具链原样产物（b5=10）；上面那个装不上时换这个 |
| `_out/s5e_from_os4/vela_app_os4.bin` | 改好图标的整分区镜像（走刷机通道，绕开设备侧脚本） |
| `_out/s5e_from_os4/vela_health_os4.bin` | 同上（health 分区） |
| `_out/s5e_icons/s5e_before_after.png` | 47 个图标：原厂 → 替换后 对照图 |
| `_out/s5e_ui_all.png` | 480×480 七个页面预览（真 MiSans 字体渲染） |
| `watchface_s5e/main.lua` | 表盘源码（带 __UIIMG__ / __PAY__ / __RB__ 占位符） |
| `watchface_s5e/payload/`、`payload_rollback/` | 负载文件 + 清单 |
| `_tools/s5e_*.py` | 全部生成 / 构建 / 校验脚本 |

---

## 2. 目标固件的事实（从固件包里查出来的，不是猜的）

| 项 | 结论 | 证据 |
|---|---|---|
| 机型 | **Xiaomi Watch S5 eSIM 46mm** | `vela_ap.bin` / `vela_cp_image.bin` 里的机型字符串 |
| 屏幕 | **480×480** | 固件自带表盘素材 `lua/daynight/asset/theme5/bigsun.bin`、`lua/complexzone/asset/Theme1/citymage1.bin` 都是 I8 480×480（231,436 B）；`complexzone.lua` 建 480×480 根对象 |
| Lua 宿主 | **有**（Lua 5.4） | `vela_ap.bin`：`Lua 5.4`、`Copyright (C) 1994-2020`、`cannot create state`、`SCRIPT_PATH`、`watchface.db`、`luavgl`，以及**同样的 7 个 C 模块** `luaopen_activity/dataman/miwear/navigator/screen/topic/vibrator` |
| 自带 Lua 表盘 | 7 个 | `vela_watchface.bin`：outdooradv / daynight / corona / complexzone / clearheart / circle / asymmetryzone |
| 图标槽位 | `/dev/app` **34** 个 + `/dev/health` **15** 个 | ROMFS `app` / `health` 卷里的 `*/launcher.bin` |
| 图标格式 | **全部 144×144 ARGB8888 = 82,956 B** | 逐个解码确认 —— **这台机器没有 I8 图标槽位**（S4 eSIM 有 6 个），所以不会有 256 色量化损失 |
| 原厂画法 | 内容 136×136 居中（4px 透明边）；`launcher_*` 是 138@(3,3)；`debug/lua/voice_alexa/sports_game` 满幅 144 | 逐像素量 alpha 边界 |
| 分区节点 | `/dev/app`、`/dev/health` | 官方 `ota.sh`：`dd if=/ota/vela_app.bin of=/dev/app`、`... of=/dev/health` |

---

## 3. 替换了什么

- 能对上 **47** 个槽位（app 33 + health 14）；OS4 里没有对应的 2 个槽位**保持原厂**：`walkie_talkie`、`sports_game`
- 其中 **8 个槽位**的 OS4 图标与 S5 eSIM 原厂**逐字节相同**（debug / esimsms / interconnect / lua / sports / sports_course / sports_record / sports_training），照样写入，保证整套一致
- **另外搬了 8 个系统 UI 素材**（都在 `/dev/app`，从 q63 取同名文件）：`system/icon/lock_icon.bin`（锁屏上的锁）、`common/icon/system_lock.bin`（状态栏系统锁）、`common/icon/quiet_mode.bin`（免打扰小图标）、`notifications/default.bin`（通知默认图）、`notifications/no_message.bin`（通知空状态）、`settings/icon/notify.bin`（设置-通知，80→64 缩放）、`mijia/enable|disable_donot_disturb.bin`（米家免打扰，80→64 缩放）。对照图见 `docs/s5e_sysicons.png`。
- **压力 App 小表情搬了 14 张**（`pressure/icon/`，都在 `/dev/health`）：4 档情绪 48px + 32px 三张 + `press_grade1..4` + `presure_icon` + 两张表情底版
- **控制中心磁贴整套搬了 22 张**（`control_center/icon/*`，128×128 ← q63 116×116 缩放）——这就是你在 S4 eSIM 上看到效果的那批。
- **`activities` 用自制图覆盖**（`assets/override/activities.png`，112×112 的跑道/同心环，与 S4 项目同一张）：裁到实心 bbox(100×100) → 放大到目标槽位画法(136×136，LANCZOS+锐化) → 居中粘回 (4,4)；实测成品外径与原厂图标完全对齐
- **尺寸归一化**：把 OS4 的满幅 144 图按目标槽位的画法缩放（多数 136、`launcher_*` 138）并居中到同一原点 —— 这样**每条负载长度与原槽位完全相等**，ROMFS 的 inode 表和后面所有文件的偏移一个字节都不动
- 负载 **4.41 MB**（替换 + 回滚各一份），.face 共 8.98 MB

---

## 4. 91 条偏移表（由 `_out/s5e_from_os4/manifest.json` 生成）

| # | 分区 | 名称 | 分区内偏移 | 长度 | 备注 |
|---|---|---|---|---|---|
| 1 | app | alarm | 0x06226200 | 82956 |  |
| 2 | app | calendar | 0x05C23600 | 82956 |  |
| 3 | app | chronograph | 0x059D1A00 | 82956 |  |
| 4 | app | compass | 0x05802000 | 82956 |  |
| 5 | app | debug | 0x05546800 | 82956 | 与 OS4 一致 |
| 6 | app | esimsms | 0x053E6E00 | 82956 | 与 OS4 一致 |
| 7 | app | find_phone | 0x05374C00 | 82956 |  |
| 8 | app | flashlight | 0x0535CE00 | 82956 |  |
| 9 | app | interconnect | 0x05183C00 | 82956 | 与 OS4 一致 |
| 10 | app | launcher_baidumap | 0x0516F600 | 82956 |  |
| 11 | app | launcher_bdmap | 0x0515B000 | 82956 |  |
| 12 | app | launcher_calculator | 0x05146A00 | 82956 |  |
| 13 | app | launcher_kugou | 0x04DB9400 | 82956 |  |
| 14 | app | launcher_micar | 0x04D80A00 | 82956 |  |
| 15 | app | launcher_netease | 0x04D6BA00 | 82956 |  |
| 16 | app | launcher_wechat | 0x04D57400 | 82956 |  |
| 17 | app | launcher_ximalaya | 0x04D42000 | 82956 |  |
| 18 | app | lua | 0x04D2DA00 | 82956 | 与 OS4 一致 |
| 19 | app | media | 0x04CFEE00 | 82956 |  |
| 20 | app | mijia | 0x04BC8600 | 82956 |  |
| 21 | app | nfccard | 0x04900C00 | 82956 |  |
| 22 | app | perpetual_calendar | 0x04469C00 | 82956 |  |
| 23 | app | phone | 0x0433B200 | 82956 |  |
| 24 | app | phone_contacts | 0x04391A00 | 82956 |  |
| 25 | app | recorder | 0x042B9400 | 82956 |  |
| 26 | app | remote_camera | 0x04088200 | 82956 |  |
| 27 | app | settings | 0x02C41C00 | 82956 |  |
| 28 | app | timer | 0x02949E00 | 82956 |  |
| 29 | app | todolist | 0x0291F200 | 82956 |  |
| 30 | app | voice_aivs | 0x022DF800 | 82956 |  |
| 31 | app | voice_alexa | 0x021AA600 | 82956 |  |
| 32 | app | weather | 0x01B09400 | 82956 |  |
| 33 | app | wxpay | 0x0000BC00 | 82956 |  |
| 34 | health | activities | 0x0C51B600 | 82956 |  |
| 35 | health | barometer | 0x0B910400 | 82956 |  |
| 36 | health | breath | 0x08A2BC00 | 82956 |  |
| 37 | health | health_today | 0x07077E00 | 82956 |  |
| 38 | health | heartrate | 0x06EBB200 | 82956 |  |
| 39 | health | innovation_research | 0x06558600 | 82956 |  |
| 40 | health | oxygen | 0x0634AA00 | 82956 |  |
| 41 | health | pressure | 0x03B9D400 | 82956 |  |
| 42 | health | sleep | 0x0272F000 | 82956 |  |
| 43 | health | sports | 0x01E89200 | 82956 | 与 OS4 一致 |
| 44 | health | sports_course | 0x02692600 | 82956 | 与 OS4 一致 |
| 45 | health | sports_record | 0x01B5FA00 | 82956 | 与 OS4 一致 |
| 46 | health | sports_training | 0x015A6400 | 82956 | 与 OS4 一致 |
| 47 | health | womenhealth | 0x001E3A00 | 82956 |  |
| 48 | app | system/icon/lock_icon.bin | 0x02AB2200 | 2060 | 锁屏上的锁 |
| 49 | app | common/icon/system_lock.bin | 0x058DFC00 | 3340 | 状态栏系统锁 |
| 50 | app | common/icon/quiet_mode.bin | 0x058FCC00 | 3340 | 免打扰/静音小图标 |
| 51 | app | notifications/default.bin | 0x044BE800 | 32012 | 通知默认大图标 |
| 52 | app | notifications/no_message.bin | 0x044B2C00 | 7436 | 通知中心空状态 |
| 53 | app | settings/icon/notify.bin | 0x02D97C00 | 5132 | 设置-通知 |
| 54 | app | mijia/enable_donot_disturb.bin | 0x04BE3A00 | 5132 | 米家 免打扰开 |
| 55 | app | mijia/disable_donot_disturb.bin | 0x04BE6E00 | 5132 | 米家 免打扰关 |
| 56 | health | pressure/icon/presure_relax.bin | 0x03C85400 | 3340 | 压力表情-放松 48 |
| 57 | health | pressure/icon/presure_mild.bin | 0x03C89600 | 3340 | 压力表情-轻度 48 |
| 58 | health | pressure/icon/presure_mid.bin | 0x03C8D800 | 3340 | 压力表情-中度 48 |
| 59 | health | pressure/icon/presure_severe.bin | 0x03C81200 | 3340 | 压力表情-重度 48 |
| 60 | health | pressure/icon/presure_mild32.bin | 0x03C88C00 | 2060 | 压力表情-轻度 32 |
| 61 | health | pressure/icon/presure_mid32.bin | 0x03C8CE00 | 2060 | 压力表情-中度 32 |
| 62 | health | pressure/icon/presure_severe32.bin | 0x03C80800 | 2060 | 压力表情-重度 32 |
| 63 | health | pressure/icon/presure_icon.bin | 0x03C8E600 | 3340 | 压力 App 小图标 |
| 64 | health | pressure/icon/press_grade1.bin | 0x03E62A00 | 2060 | 压力等级徽标 1 |
| 65 | health | pressure/icon/press_grade2.bin | 0x03E62000 | 2060 | 压力等级徽标 2 |
| 66 | health | pressure/icon/press_grade3.bin | 0x03E61600 | 2060 | 压力等级徽标 3 |
| 67 | health | pressure/icon/press_grade4.bin | 0x03E60C00 | 2060 | 压力等级徽标 4 |
| 68 | health | pressure/icon/pressure_eomji_bg.bin | 0x03DC1E00 | 54636 | 表情底版 |
| 69 | health | pressure/icon/pressure_eomji_widbg.bin | 0x03DB9200 | 35628 | 表情底版(小) |
| 70 | app | control_center/icon/settings.bin | 0x0557CC00 | 17420 | 控制中心磁贴 |
| 71 | app | control_center/icon/raise_bright_open.bin | 0x05581200 | 17420 | 控制中心磁贴 |
| 72 | app | control_center/icon/raise_bright_close.bin | 0x05589E00 | 17420 | 控制中心磁贴 |
| 73 | app | control_center/icon/not_disturb_open.bin | 0x05592A00 | 17420 | 控制中心磁贴 |
| 74 | app | control_center/icon/not_disturb_close.bin | 0x0559B600 | 17420 | 控制中心磁贴 |
| 75 | app | control_center/icon/mute_open.bin | 0x055A1800 | 17420 | 控制中心磁贴 |
| 76 | app | control_center/icon/mute_close.bin | 0x055AA400 | 17420 | 控制中心磁贴 |
| 77 | app | control_center/icon/mobile_network_open.bin | 0x055AEA00 | 17420 | 控制中心磁贴 |
| 78 | app | control_center/icon/mobile_network_close.bin | 0x055C0200 | 17420 | 控制中心磁贴 |
| 79 | app | control_center/icon/game_mode_on.bin | 0x055D2800 | 17420 | 控制中心磁贴 |
| 80 | app | control_center/icon/game_mode_off.bin | 0x055DB400 | 17420 | 控制中心磁贴 |
| 81 | app | control_center/icon/flashlight.bin | 0x055E4000 | 17420 | 控制中心磁贴 |
| 82 | app | control_center/icon/find_phone_close.bin | 0x055F1200 | 17420 | 控制中心磁贴 |
| 83 | app | control_center/icon/earphone.bin | 0x055F6600 | 3340 | 控制中心磁贴 |
| 84 | app | control_center/icon/drain_close.bin | 0x05604600 | 17420 | 控制中心磁贴 |
| 85 | app | control_center/icon/cancel.bin | 0x05609A00 | 3340 | 控制中心磁贴 |
| 86 | app | control_center/icon/bt_connect.bin | 0x0560C400 | 3340 | 控制中心磁贴 |
| 87 | app | control_center/icon/battery_open.bin | 0x0560D200 | 17420 | 控制中心磁贴 |
| 88 | app | control_center/icon/battery_close.bin | 0x05615E00 | 17420 | 控制中心磁贴 |
| 89 | app | control_center/icon/air_mode_open.bin | 0x0561A400 | 17420 | 控制中心磁贴 |
| 90 | app | control_center/icon/air_mode_close.bin | 0x0562CA00 | 17420 | 控制中心磁贴 |
| 91 | app | control_center/icon/add.bin | 0x05631000 | 3340 | 控制中心磁贴 |
> 偏移都 512 对齐、长度都是 4 的倍数 → 设备侧 `dd bs=4` 正好写满目标区间，不会多写一个字节到相邻文件里。

---

## 5. 表盘是怎么写的（机制）

Lua 表盘不能设置图标；系统图标住在 ROMFS 分区镜像里，必须**写分区 + 重启**才生效。表盘只做运载 + 执行：

```
每条负载三步（只用官方存在的 dd，判据全看内容、不看返回码）：
  1 版本校验：dd 读出设备上该偏移处 64 字节 -> 与「原厂字节」比对
        不一致就判为「版本不符」，该分区剩余记录全部跳过（不写坏）
  2 写入    ：dd if=/tmp/s5e_wr.bin of=<分区> bs=4 seek=<偏移/4> count=<长度/4>
  3 回读校验：dd 读回整段 82,956 字节 -> 与负载逐字节比对
回滚 = 同一套流程，只是写入换成原厂字节、版本校验改比对替换后的字节
最后 sync + reboot（ROMFS 是只读挂载 + 有页缓存，不重启看不到新图标）
```

**为什么能等长原地替换**：ROMFS 把 inode、名字、数据首尾相接顺序排布，绝对偏移全靠前面所有内容的长度决定。所有替换都是等长覆盖，所以 inode 表 / superblock / 目录项 / 后续文件偏移全部不变（本机逐位验证）。
但偏移**锁固件版本**，所以第 1 步的版本校验是必须的：别的版本会全部「版本不符」跳过，而不是把图标写进别人的文件里。

表盘里的偏移是**构建时两遍测量回填**的：先编一遍，在 .face 里搜负载魔数定位，量出真实偏移写回 Lua，再编第二遍并逐条校验 0 漂移。

---

## 6. 本机验证结果（全绿）

| 验证项 | 结果 |
|---|---|
| 负载回放 == 改后镜像（`vela_app_os4.bin` / `vela_health_os4.bin`） | 逐字节相同 |
| 回滚回放 == 原厂镜像 | 逐字节相同（sha256 一致） |
| inode 表 / superblock / 条目数 | 逐位不变（3432 / 5555 条） |
| 变化的文件 | 恰好只有被改的 `launcher.bin`（app 29、health 10 有实际差异） |
| UI 素材、负载、回滚在最终 .face 里的偏移 | 从 .face 里的 Lua 表读出来重新校验，逐条字节一致（`_tools/s5e_verify.py`，独立于构建脚本） |
| 两遍构建偏移漂移 | 0 |
| 480 页面圆屏切边 | 真实渲染像素测量，7 个页面全部 0 越界 |
| Lua 语法块平衡 | balanced |
| 预览图尺寸 | 326×326（Compiler.exe 对 462 设备强制，实测） |

---

## 7. 「环境预检查」通过意味着什么（**重要**）

预检查是**只读**的，所以它是**必要但不充分**条件：

| 预检查能证明 | 预检查证明不了 |
|---|---|
| `/dev/app`、`/dev/health` 两个节点存在且**可读** | **可写** —— 只有真正写第一条时才知道（这一步一个字节都不写） |
| 分区头是 `-rom1fs-`、卷名是 `app` / `health`、报出分区大小 | 表盘宿主的字体/界面能力 |
| 每分区抽 1 条对版：显示 `app 原厂✓` 或 `app 已替换✓` | 其余 46 条的偏移（这些在写入时逐条对版） |
| 负载表全部 4 对齐、不越界 | |

**为什么证明不了「可写」也敢点**：写入路径自带三重保护 ——

1. 每条写之前先读设备上 64 字节**对版**：等于「原厂字节」或「替换后字节」任一才动手；两者都不是就判「版本不符」，**该分区剩余记录全部跳过**，绝不往别人的文件里写
2. 写完整段 82,956 字节**回读比对**，不一致就计失败
3. 只做**等长原地覆盖**，不碰 inode 表 / superblock / 目录项 —— 最坏结果是「图标没变」，不会把分区写坏

**判断成功的唯一标准**：跑完显示 `> 成功 91 / 失败 0（共 91）` 和 `> app 63/63  health 28/28`。**不是 0 就先别重启**，点「回滚修改」再排查。

> 因为对版接受两种状态，**重复点「开始替换」或断电后半途重来都是安全的**（已经写入新图标的那部分不会被判成「版本不符」）。

---

## 8. 还没验证的（真机只能你来测）

1. **表盘宿主进程有没有权限写 `/dev/app` 和 `/dev/health`**
   S4 eSIM 上写 `/dev/app` 是实测通过的；这台同源平台但没测过。**请先点「环境预检查」**（只读，不写任何字节）。
2. **`lvgl.Font('MiSans-Medium' / 'MiSans-Semibold', size)` 在这台上的表现**
   `vela_font.bin` 里确实有 `MiSans-Semibold.ttf` / `MiSans-Medium.ttf`，S4 上这个 API 可用。界面文字依赖它；若不可用，文字会退回主题默认字体（中文可能缺字）。
3. **`/dev/health` 的写权限**。如果它不可写，app 的 33 条仍会成功，日志里 health 会全失败。
4. **安装通道**：和 `S5Icons.face` 一样走你的表盘安装方式（Compiler.exe 内部用的是 push 到 `/data/app/watchface/market/<id>/resource.bin`）。

输出怎么读（「正在替换」页）：

- 每 10 条一行 `> n/47 成 x 失 y`
- 结束：`> 成功 x / 失败 y（共 47）`，必要时 `> 版本不符跳过 n 条`，以及 `> app a/33  health b/14`
- **失败 0** 表示 47 条都写入并回读校验通过 → 点「重启手表」

---

## 9. 想改的话

```powershell
$py = "C:\\Users\\hi\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe"

# 只改界面/坐标：改 watchface_s5e/main.lua 与 _tools/s5e_pages.py，然后
& $py _tools\\s5e_render_ui.py        # 渲染 480 预览
& $py _tools\\s5e_check_clip.py       # 圆屏切边检查
& $py _tools\\s5e_build.py            # 两遍构建 -> _out\\faces\\S5eIcons.face
& $py _tools\\s5e_verify.py           # 独立校验

# 换图标来源 / 换固件版本
& $py _tools\\s5e_payload.py          # 重新生成负载 + 整分区镜像（自带证明）
& $py _tools\\s5e_ui_images.py        # 重新生成 UI 素材（改了素材时）
& $py _tools\\s5e_build.py
```

> `_build_s5e/`、`build_overlay_s5e/` 是产物，别手改；`watchface_s5e/main.lua` 才是源码。