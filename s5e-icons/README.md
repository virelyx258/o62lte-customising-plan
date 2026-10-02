# S5 图标包 → Xiaomi Watch S5 eSIM 46mm（图标修改器 · Lua 表盘）

把 **Xiaomi Watch S5 41mm（q63, v4.101.020）的 OS4 图标包**写进 **Xiaomi Watch S5 eSIM 46mm（p62lte, v3.112.035）** 的 `/dev/app` 与 `/dev/health` 两个分区。

- **153 条**负载：47 个 launcher 图标（app 33 + health 14）+ **44 个系统 UI 素材**（8 个锁屏/通知/免打扰小图标 + 22 张控制中心磁贴 + **14 张压力 App 小表情**）+ **160 张对讲机素材**（`walkie_talkie/**`）→ 全部等长覆盖，inode 表与后面所有偏移一个字节都不动
- **长宽比不一致的素材一律不替换**（保持原厂）：源图与槽位长宽比相差 >0.5% 就跳过 —— 拉伸会把方块变长方形、裁切会切掉按钮两端。所以 `walkie_talkie/image/stop.bin`（176×96 vs 144×96）与 `walkie_talkie/guidance/finish_guidance.bin`（176×96 vs 160×96）**保持原厂**（本机逐字节确认）
- **对讲机那一组是 I8+RLE 压缩槽位**（固件里 `flags=0x08`，长度不是 4 的倍数）→ `iconpack.encode_into_slot()`：量化（颜色数从 256 逐级往下试）→ RLE → 用 `ctrl=0` 的 2 字节空指令补齐到原 `csize`，做到逐字节等长；设备端写入这类记录自动退化成 `dd bs=1`
- 界面按 **480×480** 重做（设计稿在 `tools/s5e_pages.py`，本机用真 MiSans 渲染 + 真实像素判圆屏切边，7 页 0 越界）
- **压力 App 小表情也搬了 14 张**（`pressure/icon/`）：4 档情绪 48px（relax/mild/mid/severe）+ 32px 三张 + `press_grade1..4` 等级徽标 + `presure_icon` + 两张表情底版（`pressure_eomji_bg` / `_widbg`）；96px 那四张两边本来就一样（自动跳过）。没搬的：整屏背景（`pressure_bg`/`success_bg`/`success_arc`/`press_widget_bg*`/`press_chart_bg`）、`reminder.bin`、`pressure/measure/*` 动画帧（体积大）
- **系统 UI 素材整套一起搬**：8 个锁屏/通知/免打扰小图标 + 22 张控制中心磁贴（q63 磁贴是 116×116 浅色主题，缩放到 S5 eSIM 的 128×128）。白盘放在深色控制中心上的观感已在 S4 eSIM 上实测，效果可以
- 只读预检查 + 每条写入前后对版/回读校验 + 一键回滚

---

## 1. 交付物与安装

| 文件 | 说明 |
|---|---|
| `dist/S5eIcons.face` | **主交付物** 10,852,268 B（sha256 50da912734a5db48…），表盘 id `462150101`，b5=0（与固件自带表盘一致） |
| `dist/S5eIcons_toolchain.face` | 官方工具链原样产物（b5=10）；上面那个装不上时换这个 |
| `.work/s5e_from_os4/vela_app_os4.bin` | 重建后得到的整分区镜像（可直接刷机，绕开设备侧脚本） |
| `.work/s5e_from_os4/vela_health_os4.bin` | 同上（health 分区） |
| `docs/说明.md` | 完整说明：固件事实、47 条偏移表、验证结果、待实测项 |
| `docs/s5e_before_after.png` | 47 个 launcher 图标：原厂 → 替换后 对照图 |
| `docs/s5e_sysicons.png` | 44 个系统 UI 素材（22 控制中心 + 14 压力表情 + 8 其他）：原厂 → 从 S5 41mm 搬过来的 对照图 |
| `docs/s5e_pressure.png` | 14 张压力 App 小表情：原厂 → q63 对照图 |
| `docs/s5e_ui_all.png` | 480×480 七个页面预览 |

装法与普通 Lua 表盘相同（`resource.bin` 推到 `/data/app/watchface/market/<id>/`）。装好后在表盘上操作：

```
首页 →「快速帮助」→「环境预检查」   只读，一个字节都不写
首页 →「开始替换」→ 确认 → 自动写入 153 条 →「重启手表」
       快速帮助 →「回滚修改」→ 确认 → 写回原厂图标
```

输出怎么读（「正在替换」页）：每 10 条一行 `> n/153 成 x 失 y`；结束时 `> 成功 x / 失败 y（共 153）`、必要时 `> 版本不符跳过 n 条`，以及 `> app/health 分区分条统计`。

**判断成功的唯一标准是 `失败 0`。**不是 0 就先别重启，点「回滚修改」。

---

## 2. 目录

```
main.lua                 表盘源码（含 __UIIMG__ / __PAY__ / __RB__ 占位符，构建时回填）
payload/                 payload.bin = MAGIC + 91 条顺序拼接；payload.lua = 逐条偏移表
payload_rollback/        原厂字节（回滚用）
ui_images/               界面素材（LVGL v9 .bin，8 张）
assets/                  设计素材 PNG（Mdi 图标、返回箭头、QQ、封面）
assets/override/         自制图覆盖（activities.png = 跑道图标，优先级高于固件源）
tools/                   全部脚本（见下表）
dist/                    交付的 .face
docs/                    说明与预览图
inputs/                  要你自己放固件分区镜像（见第 4 节，不进仓库）
vendor/                  放第三方 LuaDevTemplate-main（不进仓库）
.work/                   构建工作区（产物，可删）
```

| 脚本 | 作用 |
|---|---|
| `tools/paths.py` | 所有路径的唯一入口（inputs / vendor / .work / dist，支持环境变量覆盖） |
| `tools/s5e_payload.py` | 从两个分区镜像生成 91 条负载 + 回滚 + 整分区镜像（自带正反两个证明） |
| `tools/s5e_ui_images.py` | 设计素材 PNG → LVGL .bin + 圆形 logo |
| `tools/s5e_pages.py` | 480×480 页面规格（唯一的设计稿来源） |
| `tools/s5e_render_ui.py` | 用真 MiSans 渲染 7 页预览 |
| `tools/s5e_check_clip.py` | 用真实渲染像素判圆屏是否切边 |
| `tools/s5e_build.py` | 两遍构建 → `dist/S5eIcons.face`（自动回填偏移 + 0 漂移校验） |
| `tools/s5e_verify.py` | **独立校验**：从 .face 里反解 Lua 表与偏移，再与固件镜像逐字节比对 |
| `tools/romfs.py` `tools/lvgl_bin.py` `tools/iconpack.py` `tools/render_ui.py` `tools/lua_balance.py` | 共用底层（ROMFS 解析 / LVGL 图片编解码 / UI 渲染 / Lua 块平衡） |

---

## 3. 目标固件的事实（从固件包里查出来的）

| 项 | 结论 | 证据 |
|---|---|---|
| 机型 | Xiaomi Watch S5 eSIM 46mm | `vela_ap.bin` / `vela_cp_image.bin` 里的机型字符串 |
| 屏幕 | 480×480 | 自带表盘素材 `bigsun.bin`、`citymage1.bin` 都是 I8 480×480（231,436 B）；`complexzone.lua` 建 480×480 根对象 |
| Lua 宿主 | 有，Lua 5.4 | `vela_ap.bin` 里 `Lua 5.4`、`SCRIPT_PATH`、`watchface.db`、`luavgl`，以及同样的 7 个 C 模块 `luaopen_activity/dataman/miwear/navigator/screen/topic/vibrator` |
| 自带 Lua 表盘 | 7 个 | outdooradv / daynight / corona / complexzone / clearheart / circle / asymmetryzone |
| 图标槽位 | `/dev/app` 34 个 + `/dev/health` 15 个 | ROMFS `app` / `health` 卷里的 `*/launcher.bin` |
| 图标格式 | 全部 144×144 ARGB8888 = 82,956 B | 逐个解码确认；这台**没有 I8 槽位**（S4 eSIM 有 6 个），不存在量化损失 |
| 原厂画法 | 内容 136×136 居中（4px 透明边）；`launcher_*` 138@(3,3)；`debug` / `lua` / `voice_alexa` / `sports_game` 满幅 144 | 逐像素量 alpha 边界 |

## 4. 替换内容

- 能对上 **47** 个槽位（app 33 + health 14）；OS4 里没有对应的 2 个槽位**保持原厂**：`walkie_talkie`、`sports_game`
- 其中 **8 个**槽位的 OS4 图标与原厂逐字节相同（debug / esimsms / interconnect / lua / sports / sports_course / sports_record / sports_training），照样写入，保证整套一致
- **`activities` 用自制图覆盖**：`assets/override/activities.png`（112×112 红/绿/青同心环，即 S4 项目里那张跑道图标）优先于 q63 固件源。裁剪 = 取实心 bbox(100×100) → 放大到目标槽位画法(136×136，LANCZOS + 锐化) → 居中粘回 (4,4)；实测成品外径与原厂图标**完全对齐**（都是 (4,4)-(139,139)）
- **`voice_aivs`（小爱同学）同样用自制图覆盖**：`assets/override/voice_aivs.png`（用户给的 144×144 PNG，圆形白盘直径 140）→ 裁到实心 → 缩放到槽位画法 136×136 → 居中；编码后 82,956 B 与原槽位等长
- **尺寸归一化**：把 OS4 的满幅 144 图按目标槽位的画法缩放（多数 136、`launcher_*` 138）并居中到同一原点 —— 这样每条负载长度与原槽位完全相等
- 负载 4.41 MB（替换 + 回滚各一份），.face 共 8.98 MB

---

## 5. 重建

### 5.1 需要自己准备的输入（放进 `inputs/`，不进仓库）

| 路径 | 是什么 | 大小 / sha256 前 16 位 |
|---|---|---|
| `inputs/target/vela_app.bin` | 目标固件（p62lte）app 分区 | 103,043,072 / 9b41c5f5eb17c112 |
| `inputs/target/vela_health.bin` | 目标固件 health 分区 | 206,924,800 / 489752c8a3fb24ff |
| `inputs/target/vela_font.bin` | 目标固件 font 分区（可选：渲染预览时从里面取 MiSans） | 43,379,712 / 16cb803ac1bd74c5 |
| `inputs/source/vela_app.bin` | 图标来源（S5 41mm q63）app 分区 | 206,000,128 / 161a8f7a5f0bd8af |
| `inputs/source/vela_health.bin` | 图标来源 health 分区 | 233,939,968 / 12a3bd2f8b62e969 |
| `inputs/fonts/MiSans-Medium.ttf`、`MiSans-Semibold.ttf` | 可选；不提供就自动从 `inputs/target/vela_font.bin` 里取 | — |
| `vendor/LuaDevTemplate-main/` | 官方模板（里面有 `Compiler.exe`） | — |

固件分区镜像就是官方 OTA 包（ZIP）里的 `vela_*.bin` 条目，解压出来即可。

### 5.2 步骤

```powershell
# 需要 Python 3 + Pillow
python tools/s5e_payload.py      # 负载 + 整分区镜像（自己证明 正放=改后镜像 / 反放=原厂镜像）
python tools/s5e_ui_images.py    # 界面素材
python tools/s5e_render_ui.py    # 480 预览（可选）
python tools/s5e_check_clip.py   # 圆屏切边检查（可选）
python tools/s5e_build.py        # 两遍构建 -> dist/S5eIcons.face
python tools/s5e_verify.py       # 独立校验
```

只想改界面/坐标：改 `main.lua` 与 `tools/s5e_pages.py`，然后跑 `s5e_render_ui.py` + `s5e_check_clip.py` + `s5e_build.py` + `s5e_verify.py`。

---

## 6. 已知边界（踩过的坑）

0. **对讲机素材默认不打包**（ICON_WALKIE=1 可打开）；160 张 PNG 仍在 ssets/walkie_talkie/。

1. **偏移锁固件版本**：换固件要重跑 `s5e_payload.py` + 构建。用错版本时表盘会判「版本不符」整分区跳过，**不会把字节写进别人的文件里**。
2. **Compiler.exe 的设备表里没有 480 档**（枚举 DeviceType 1..1500 只有 17 个已知值，圆表且预览 326×326 的只有 362 / 462）→ 这里用 462 + 326×326 预览。预览只是表盘列表里的缩略图。
3. **表盘宿主能不能写 `/dev/app`、`/dev/health` 未在真机验证**（S4 eSIM 上写 `/dev/app` 是实测通过的，同源平台）。所以界面里第一步是只读的「环境预检查」。
4. **负载文件必须原样连续放在 .face 里**，偏移才等于 `文件基址 + 魔数长度 + 相对偏移`；`s5e_build.py` 会断言这一点。魔数长度**不要手写常量**（曾经把 15 写成 16，全部偏移差 1 字节）。
5. **独立校验不是摆设**：`tools/s5e_verify.py` 从 .face 里的 Lua 表反解偏移再与固件镜像比对，本项目开发时它抓出两个真 bug —— 魔数长度差 1；Lua 表里存的是 `/dev/app` 而不是运行时期望的 `app` 键（会让 dd 拼成 `if=nil`）。
6. 负载写入走 `/tmp` 中转（resource.bin 内的偏移不保证 4 字节对齐，不能直接 `dd skip`）。

## 7. 第三方与风险

- 本仓库不含固件、OTA 包、字体；`.face` 由第三方 `Compiler.exe` 编译（见 [../README.md](../README.md)）
- 往分区节点写数据是危险操作：写错偏移可能损坏资源分区。表盘自带版本校验与回滚，但请自行确认设备所有权并承担后果
- 官方 OTA 升级会整分区覆盖，图标会回到原厂（等于自动还原）
