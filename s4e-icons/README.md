# S5 图标包 → Xiaomi Watch S4 eSIM（图标修改器 · Lua 表盘）

把 **Xiaomi Watch S5 41mm（q63, v4.101.020）的 OS4 图标包**写进 **Xiaomi Watch S4 eSIM（o62lte, 3.202.79）** 的 `/dev/app` 分区。

- **149 条**负载 = **37 个** launcher 图标 + **11 个控制中心顶栏状态 + 10 张合成图** + **8 个系统 UI 素材**（锁屏锁 / 状态栏系统锁 / 免打扰小图标 / 通知默认图 / 通知空状态 / 设置-通知 / 米家免打扰×2）+ **12 张压力 App 小表情** + **160 张对讲机素材**（`walkie_talkie/**`），全部等长替换（144×144 图标 / 128×128 磁贴 / 32~176 小图；图标是 I8 索引色需复用原调色板）
- **长宽比不一致的素材一律不替换**（保持原厂）：源图与槽位长宽比相差 >0.5% 就跳过 —— 拉伸会把方块变长方形、裁切会切掉按钮两端，宁可留原厂。所以 `walkie_talkie/image/stop.bin`（源 176×96 vs 槽位 144×96）和 `walkie_talkie/guidance/finish_guidance.bin`（176×96 vs 160×96）**保持原厂**（本机逐字节确认过）
- **对讲机那一组是 I8+RLE 压缩槽位**（固件里 `flags=0x08`，长度都不是 4 的倍数）→ 用 `iconpack.encode_into_slot()`：量化（颜色数从 256 逐级往下试）→ RLE → 用 `ctrl=0` 的 2 字节空指令补齐到原 `csize`，做到**逐字节等长**；设备端写入时这类记录自动退化成 `dd bs=1`
- 界面 466×466（设计稿在 `tools/pages.py`，本机真 MiSans 渲染 + 真实像素判圆屏切边）
- 只读预检查 + 写入 + 一键回滚；另外还有一个**不依赖表盘**的 `flash.sh` / `rollback.sh`（有 shell 时直接跑）

---

## 1. 交付物与安装

| 文件 | 说明 |
|---|---|
| `dist/S5Icons.face` | **主交付物** 8,024,916 B（sha256 b371a40e8eed53a0…），表盘 id `362150101`，b5=0 |
| `dist/S5Icons_toolchain.face` | 官方工具链原样产物（b5=10）；上面那个装不上时换这个 |
| `.work/s4_from_s5/vela_app_s5icons.bin` | 重建后得到的整分区镜像（265 MB，可直接刷机，绕开设备侧脚本） |
| `flash.sh` / `rollback.sh` | 有 nsh shell 时不用表盘：把脚本和 `payload/` 复制到 `/data/s5icons/` 再 `sh flash.sh` |
| `docs/分析报告-S4eSIM.md` | 固件结构 / 为什么必须等长 / 为什么锁版本 的完整分析 |
| `docs/图标命名对照表.md` | 39 个槽位的名字、偏移、格式对照表 |
| `docs/ui_all_466.png` | 466×466 七个页面预览 |
| `docs/s4e_sysicons.png` | 42 张系统素材（22 控制中心 + 8 锁屏/通知/设置/米家 + 12 压力表情）：S4 原厂 → 从 S5 41mm 搬来的 对照图 |
| `docs/s4e_pressure.png` | 12 张压力 App 小表情：S4 原厂 → q63 对照图 |

装法与普通 Lua 表盘相同（`resource.bin` 推到 `/data/app/watchface/market/<id>/`）。装好后在表盘上操作：

```
首页 →「快速帮助」→「环境预检查」   只读，不写任何字节
首页 →「开始替换」→ 确认 → 自动写入 149 条 →「重启手表」
       快速帮助 →「回滚修改」→ 确认 → 写回原厂图标
```

---

## 2. 目录

```
main.lua                 表盘源码（含 __UIIMG__ / __PAY__ / __RB__ 占位符，构建时回填）
payload/                 80 个负载 .bin（NNN_名字.bin）+ payload.lua 清单
payload_rollback/        同结构，内容是原厂字节（回滚用）
ui_images/               界面素材（LVGL v9 .bin，8 张）
assets/                  设计素材（Mdi 图标、返回箭头、QQ、封面）
assets/override/         3 张 112×112 自制 PNG（activities / sports_course / interconnect），优先级高于固件来源
tools/                   全部脚本（见下表）
dist/                    交付的 .face
docs/                    说明、分析报告、预览图
inputs/                  要你自己放固件分区镜像（见第 4 节，不进仓库）
vendor/                  放第三方 LuaDevTemplate-main（不进仓库）
.work/                   构建工作区（产物，可删）
```

| 脚本 | 作用 |
|---|---|
| `tools/paths.py` | 所有路径的唯一入口（inputs / vendor / .work / dist，支持环境变量覆盖） |
| `tools/make_s5_to_s4_inset.py` | S5 图标 → S4 槽位（尺寸归一化 + I8 调色板复用 + 自制 PNG 覆盖） |
| `tools/make_dd_payload.py` | 切分成逐条负载 + 回滚负载 + `flash.sh` / `rollback.sh` / `payload.json` |
| `tools/make_ui_images.py` | 设计素材 PNG → LVGL .bin + 圆形 logo |
| `tools/pages.py` | 466×466 页面规格（唯一的设计稿来源） |
| `tools/render_ui.py` | 用真 MiSans 渲染 7 页预览 |
| `tools/check_clip.py` | 用真实渲染像素判圆屏是否切边 |
| `tools/gen_ui_lua.py` | 两遍构建 → `dist/S5Icons.face`（自动回填偏移 + 0 漂移校验） |
| `tools/romfs.py` `tools/lvgl_bin.py` `tools/iconpack.py` `tools/lua_balance.py` | 共用底层（ROMFS 解析 / LVGL 图片编解码 / Lua 块平衡） |

---

## 3. 目标固件的事实

| 项 | 结论 |
|---|---|
| 机型 | Xiaomi Watch S4 eSIM（o62lte），屏幕 466×466 |
| Lua 宿主 | 有，Lua 5.4；7 个 C 模块 activity / dataman / miwear / navigator / screen / topic / vibrator + luavgl |
| 图标槽位 | 39 个 `launcher.bin`（38 个 `<app>/launcher.bin` + `phone/contacts_launcher.bin`），都在 `/dev/app`（265 MB ROMFS 分区） |
| 图标格式 | 33 个 ARGB8888（82,956 B）+ 6 个 I8（21,772 B）；144×144 画布 |
| 原厂画法 | 内容 136×136 居中（4px 透明边）；I8 槽位必须复用源图调色板，否则边缘锯齿 + 彩点 |

## 4. 替换内容

- **37 个**槽位真正被改写；`voice_alexa`、`wxpay` 与 S5 源逐字节相同，已从负载中剔除
- **另外搬了 22 张控制中心磁贴**（`control_center/icon/*`，S4 128×128 ← q63 116×116，缩放 + 复用源图 I8 调色板）：勿扰 / 静音 / 手电 / 设置 / 飞行 / 电池 / 移动网络 / 抬腕亮屏 / 排水 / 查找手机 / 蓝牙 / 耳机 / 取消 / 加号 / 网络开关。对照图见 `docs/s4e_sysicons.png`
  - ⚠ 说明：S4 原厂是**蓝色主题**（选中=实心蓝盘），q63 是**浅色主题**（白盘 + 浅色字形）——q63 那边看着「淡」是它的正常样子（OS4 的浅色控制中心）。
  - ✅ **已实测：效果可以**（用户确认）。
- **另外 8 个系统 UI 素材也一起搬了**（和 S5 eSIM 那份同一组）：`system/icon/lock_icon.bin`（锁屏锁）、`common/icon/system_lock.bin`（状态栏锁）、`common/icon/quiet_mode.bin`（免打扰小图标）、`notifications/no_message.bin`（通知空状态）、`settings/icon/notify.bin`（设置-通知，80→64）、`mijia/enable|disable_donot_disturb.bin`（米家免打扰，80→64）、`esimsms/icon/esim_sms_reminder.bin`（短信提醒）。对照图同 `docs/s4e_sysicons.png`。
- **压力 App 小表情也搬了 12 张**（S4 没有 health 分区，这些都在 `/dev/app` 的 `pressure/icon/`）：4 档情绪 48px（relax/mild/mid/severe）+ 32px 三张 + `press_grade1..4` + `presure_icon`。没搬：96px（两边本来就一样）、`pressure_eomji_bg/_widbg`（S4 没有这两张）、整屏背景与 `measure/*` 动画帧、`reminder.bin`。对照图 `docs/s4e_pressure.png`
- `walkie_talkie` 是 S4 独有、S5 没有，保持原厂
- `activities`、`sports_course`、`interconnect` 用 `assets/override/` 里的自制 112×112 PNG；`voice_aivs`（小爱同学）用 `assets/override/voice_aivs.png`（用户给的 144×144 PNG）—— 都会裁到实心范围、缩放到该槽位自己的画法（136×136）再归一化
- 编码策略：S5 文件长度 == S4 槽位长度 → 原样拷贝；否则解码后按 **S4 槽位的色彩格式**重新编码，保证长度逐字节相等

---

## 5. 重建

### 5.1 需要自己准备的输入（放进 `inputs/`，不进仓库）

| 路径 | 是什么 | 大小 / sha256 前 16 位 |
|---|---|---|
| `inputs/target/vela_app.bin` | 目标固件（o62lte 3.202.79）app 分区 | 265,684,992 / caa66693f49477dd |
| `inputs/source/vela_app.bin` | 图标来源（S5 41mm q63）app 分区 | 206,000,128 / 161a8f7a5f0bd8af |
| `inputs/source/vela_health.bin` | 图标来源 health 分区 | 233,939,968 / 12a3bd2f8b62e969 |
| `inputs/fonts/MiSans-Medium.ttf`、`MiSans-Semibold.ttf` | 可选：渲染预览用；没有就退化成系统字体（只影响预览图） | — |
| `vendor/LuaDevTemplate-main/` | 官方模板（里面有 `Compiler.exe`） | — |

固件分区镜像就是官方 OTA 包（ZIP）里的 `vela_*.bin` 条目，解压出来即可。

### 5.2 步骤

```powershell
# 需要 Python 3 + Pillow
python tools/make_s5_to_s4_inset.py   # S5 图标 -> S4 槽位（产出 .work/s4_from_s5/vela_app_s5icons.bin）
python tools/make_dd_payload.py       # 切成逐条负载 + 回滚 + flash.sh/rollback.sh
python tools/make_ui_images.py        # 界面素材
python tools/gen_ui_lua.py            # 两遍构建 -> dist/S5Icons.face
python tools/render_ui.py             # 466 预览（可选）
python tools/check_clip.py            # 圆屏切边检查（可选）
```

### 5.3 只想换自定义图标？

把 144×144 PNG 按 `docs/图标命名对照表.md` 命名，然后：

```powershell
python tools/iconpack.py make inputs/target/vela_app.bin <你的PNG目录> .work/mypack --patched
```

---

## 6. 已知边界
- **对讲机素材默认不打包**（ICON_WALKIE=1 可打开）；160 条对讲机 PNG 仍在 ssets/walkie_talkie/。
- **控制中心的米家/融合中心那组：默认不打包**（用户 2026-10-02 决定不改；`ICON_MIJIA=1` 可打开）。已确认用户两台设备本来就装了同一个米家手表 App（`com.xiaomi.smarthome.watch.*.rpk`，129 张设备图标），128 张与 q63 **逐字节相同**，所以控制中心那套不需要移植；更多设备图标属于米家 App 内部素材，`/dev/app` 里没有对应槽位。


1. **偏移锁固件版本**：ROMFS 是绝对偏移顺序排布，跨版本套用旧偏移 = 往错误位置写。换固件要重跑上面的流程。
2. **等长是硬要求**：替换文件长度与原槽位不相等就会让后面所有偏移平移、镜像损坏；脚本对每条都断言长度相等。
3. **I8 槽位**（compass / debug / lua / perpetual_calendar / remote_camera / wxpay）必须复用源图调色板，否则边缘会出锯齿和彩点。
4. **真机能力**：`os.execute` / `dd` 可用；`io.popen` 捕获不到输出；`os.execute` 的返回值不可靠（成功也可能是 65280）→ 判据一律看内容。
5. 首次请只点「环境预检查」，看清输出再替换。

## 7. 第三方与风险

- 本仓库不含固件、OTA 包、字体；`.face` 由第三方 `Compiler.exe` 编译（见 [../README.md](../README.md)）
- 往分区节点写数据是危险操作；官方 OTA 升级会整分区覆盖，图标回到原厂
