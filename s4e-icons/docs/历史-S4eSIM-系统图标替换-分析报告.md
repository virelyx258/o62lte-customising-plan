# Xiaomi Watch S4 eSIM（o62lte）系统应用图标替换 —— 固件包分析报告

分析对象：`c53475a6c7367c3583c6882665fd85ae_upd_mijia.watch.o62lte.bin`
固件标识：`ro.build.version=3.202.79, build.time=2026-07-03 19:58:07, model=o62lte`
机型字符串：`Xiaomi Watch S4 eSIM`
包大小：199,385,001 字节

---

## 1. 固件包是什么

外层就是一个 **ZIP（Android SignApk 签名包）**，开头即 `PK\x03\x04`，第一个条目是 `ota.sh`。

```
ota.sh                4524
vela_app.bin     265684992      <- 应用资源分区（图标在这里）
vela_watchface.bin 92967936
vela_system.bin   72366080
vela_font.bin     36146176
vela_misc.bin     35799040
vela_vendor.bin   17909760
vela_ap.bin       11141120
vela_quickapp.bin  5840896
vela_i18n.bin      4399104
vela_cp.bin        3174400
vela_audio.bin     2730024
vela_ota.bin       1441792
vela_tee.bin       1048576
META-INF/CERT.RSA / CERT.SF / MANIFEST.MF
```

`ota.sh` 的全部动作就是逐分区裸写：

```sh
dd if=/ota/vela_app.bin    of=/dev/app       bs=32768 verify
dd if=/ota/vela_vendor.bin of=/dev/vendor    bs=32768 verify
dd if=/ota/vela_system.bin of=/dev/system    bs=32768 verify
... (vendor/i18n/app/quickapp/cp/misc/audio/tee/system/font/ap/watchface)
```

签名信息：`CERT.SF` 里 `Created-By: 1.0 (Android SignApk)`、`X-Android-APK-Signed: 2, 3`，`MANIFEST.MF` 对每个分区镜像记录 SHA1。

> **结论：这份 OTA 包无法自行重新打包。** 改一个字节就过不了签名校验。

`vela_*.bin` 是 **Linux `romfs` 镜像**（magic `-rom1fs-`）：

| 镜像 | 卷名 | 条目数 | romfs 大小 |
|---|---|---|---|
| vela_app.bin | app | 7834 | 265,684,928 |
| vela_watchface.bin | watchface | 312 | 92,967,424 |
| vela_system.bin | system | 1525 | 72,365,728 |
| vela_font.bin | font | 15 | 36,145,776 |
| vela_misc.bin | mcmisc | 1341 | 35,798,176 |
| vela_vendor.bin | vendor | 58 | 17,909,328 |
| vela_quickapp.bin | quickapp | 46 | 5,840,544 |
| vela_i18n.bin | i18n | 277 | 4,399,072 |

在盘上它们挂到 `/resource/<卷名>`，所以 AP 二进制里出现的是 `/resource/app/...` 这样的绝对路径。

### ROMFS 结构（关键）

```
super : "-rom1fs-" | u32 size | u32 checksum | name(NUL, 补齐16)
inode : u32 next | u32 spec | u32 size | u32 checksum | name(NUL, 补齐16) | 文件数据紧跟其后
        next 低 4 位 = 类型：0=硬链接(spec=目标inode偏移) 1=目录(spec=首个子项偏移) 2=普通文件 8=可执行
```

**目录项与文件数据是严格顺序紧密排布的**，每一项的偏移完全由它前面所有内容的长度决定。

---

## 2. 系统自带应用的图标在哪里（已定位）

AP 二进制里写死了一批路径，直接给出答案：

```
/resource/app/alarm/launcher.bin
/resource/app/activities/launcher.bin
/resource/app/calendar/launcher.bin
/resource/app/heartrate/launcher.bin
... 共 39 个
```

精确统计：**38 个 `<app>/launcher.bin`** 加 **1 个 `phone/contacts_launcher.bin`**（联系人图标），共 39 个。

即 **每个系统应用目录下都有一个 `launcher.bin`，它就是"应用列表/启动器"里显示的那个图标**。全部位于 `vela_app.bin`（=`/dev/app` 分区，265 MB）。

39 个图标全部是 **LVGL v9 二进制图片**：

```
u8 magic=0x19 | u8 color_format | u16 flags | u16 w | u16 h | u16 stride | u16 reserved
cf=0x10 ARGB8888 : 12 + 144*144*4          = 82956 字节
cf=0x0a I8       : 12 + 256*4 + 144*144    = 21772 字节
```

已全部解码验证（38/39，`voice/alexa/launcher.bin` 是 6005 字节的特例，`flags=0x0008`，格式待定）。

### 图标清单（偏移为 `vela_app.bin` 内绝对偏移，固件 3.202.79 专用）

| 应用 | 数据偏移 | 长度 | 尺寸 | 格式 |
|---|---|---|---|---|
| wxpay | 0x0000bc00 | 21772 | 144x144 | I8 |
| womenhealth | 0x00047a00 | 82956 | 144x144 | ARGB8888 |
| weather | 0x017de200 | 82956 | 144x144 | ARGB8888 |
| walkie_talkie | 0x02d45600 | 82956 | 144x144 | ARGB8888 |
| voice/alexa | 0x032fa000 | 6005 | 144x144 | I8(特例) |
| voice/aivs | 0x0341c400 | 82956 | 144x144 | ARGB8888 |
| todolist | 0x03aa9000 | 82956 | 144x144 | ARGB8888 |
| timer | 0x03ad3c00 | 82956 | 144x144 | ARGB8888 |
| sports/training | 0x0466b000 | 82956 | 144x144 | ARGB8888 |
| sports/record | 0x04a63000 | 82956 | 144x144 | ARGB8888 |
| sports | 0x04baee00 | 82956 | 144x144 | ARGB8888 |
| sports/course | 0x05132400 | 82956 | 144x144 | ARGB8888 |
| sleep | 0x05156400 | 82956 | 144x144 | ARGB8888 |
| settings | 0x052e8000 | 82956 | 144x144 | ARGB8888 |
| remote_camera | 0x06593a00 | 21772 | 144x144 | I8 |
| recorder | 0x067a4600 | 82956 | 144x144 | ARGB8888 |
| pressure | 0x07908400 | 82956 | 144x144 | ARGB8888 |
| phone | 0x07a4d000 | 82956 | 144x144 | ARGB8888 |
| phone/contacts_launcher | 0x07a82200 | 82956 | 144x144 | ARGB8888 |
| perpetual_calendar | 0x07b3be00 | 21772 | 144x144 | I8 |
| oxygen | 0x08f08c00 | 82956 | 144x144 | ARGB8888 |
| nfccard | 0x093f2c00 | 82956 | 144x144 | ARGB8888 |
| mijia | 0x09599200 | 82956 | 144x144 | ARGB8888 |
| media | 0x0968e200 | 82956 | 144x144 | ARGB8888 |
| lua | 0x096b5200 | 21772 | 144x144 | I8 |
| interconnect | 0x096d8000 | 82956 | 144x144 | ARGB8888 |
| innovation_research | 0x096efa00 | 82956 | 144x144 | ARGB8888 |
| heartrate | 0x09fea800 | 82956 | 144x144 | ARGB8888 |
| health_today | 0x0a223a00 | 82956 | 144x144 | ARGB8888 |
| flashlight | 0x0b6dba00 | 82956 | 144x144 | ARGB8888 |
| find_phone | 0x0b6f0000 | 82956 | 144x144 | ARGB8888 |
| esimsms | 0x0b762200 | 82956 | 144x144 | ARGB8888 |
| debug | 0x0b81a200 | 21772 | 144x144 | I8 |
| compass | 0x0b8a1400 | 21772 | 144x144 | I8 |
| chronograph | 0x0ba47e00 | 82956 | 144x144 | ARGB8888 |
| calendar | 0x0bc4b200 | 82956 | 144x144 | ARGB8888 |
| breath | 0x0bd54c00 | 82956 | 144x144 | ARGB8888 |
| barometer | 0x0e825c00 | 82956 | 144x144 | ARGB8888 |
| alarm | 0x0f3a7e00 | 82956 | 144x144 | ARGB8888 |

---

## 3. 疑问一：为什么"一个 Lua 表盘点一下就替换成功了"

从这份固件包里能**确证**的事实：

1. 系统应用图标 = `vela_app.bin` 里的 `launcher.bin`，而 `vela_app.bin` 是**整个 265 MB 分区镜像**；
2. 官方通道 `ota.sh` 的写入方式是 `dd ... of=/dev/app`，**裸写分区**；
3. 官方 OTA 包是 **SignApk v2/v3 签名的**，因此**不可能**通过"重新打包 OTA"来替换图标；
4. 分区设备节点 `/dev/app`、`/dev/system` 等对用户态是**可打开的字符/块设备**（LoXe 文档也专门警告"不要直接试写未知设备，对分区节点 `dd`/重定向可能立即破坏系统"）。

把这四点连起来，社区图标包只能走一条路：**绕过签名校验，直接把图标字节写进分区**。

所以那个"Lua 表盘"的角色是**运载 + 执行载体**，而不是"表盘 API 能设置图标"：

```
图标包（做成表盘包的样子）
├── asset/*.bin      实际是一个"补丁表"：[(绝对偏移, 该长度字节), ...]
└── main.lua         ui.init / 按钮回调里做写入
        │  点击"立即替换"
        ▼
   按记录 seek+write 到 /dev/app（或整镜像 dd）
        ▼
   ROMFS 是只读挂载 + 有页缓存 → 必须重启才能重新读取
        ▼
   重启后应用列表图标变了
```

**"稍等片刻 + 重启"正是这条链路的指纹**：如果只是普通文件级改动，不需要重启；裸写分区必须重启，因为已经挂载的只读视图和缓存都是旧的。

> 这一节里，(1)(2)(3)(4) 是本次从固件包**实证**的；"表盘脚本直接写 `/dev/app`" 是**最符合全部观察的推断**，需要用那个图标包本身（看 `main.lua` 是否出现 `lvgl.fs.open_file`＋`/dev/app`＋`write`＋`seek`）或实机日志来最终确认。
> 另外一种可能是：表盘只是商店分类/容器格式，真正推送由工具箱的安装通道完成。区分方法同上——看包里有没有 Lua 写盘代码，以及 payload 是"几十 KB 的补丁表"还是"75 MB 的整分区镜像"。

---

## 4. 疑问二：为什么"只适用于特定固件版本"（例如 3.100.032）

先纠正一点：**锁版本的不是工具，是包里的那份 payload。** AstroBox 这类工具箱本身跨版本通用；写着"仅适用于 3.100.032"的是那份资源包。

原因有四层，前两层是技术必然，后两层是工程现实：

**① 绝对寻址 + 顺序排布（决定性原因）**
ROMFS 把所有 inode、文件名和文件数据**首尾相接顺序排布**。补丁表里存的是**绝对偏移**（例如 `0x0f3a7e00`）。只要前面对任何一个文件的长度变了 —— 新增一个图标、换一个字体、改一句文案、某个 `.bin` 从 I8 变 ARGB8888（长度差 61184 字节）—— **后面所有偏移全部平移**。此时旧补丁会把图标字节写进别的文件里，轻则图标错乱，重则损坏资源分区。

这跟"为什么这个 APK 版本的汉化补丁不能用到下一个版本"是同一类问题：**不是逻辑变了，是逐字节布局变了。**

**② 一致性**
资源分区与 AP/system 分区是配套发布的（资源清单、图标索引、字体/i18n 版本互相对应）。混搭会出现显示错乱，严重时起不来。所以包作者干脆要求"先降级到配套版本"。

**③ 官方 OTA 会整分区覆盖**
任何系统升级都执行 `dd ... of=/dev/app`，**你的图标会被整体重写回去**。所以"锁版本"同时意味着"OTA 之后失效"；如果升级后还拿旧偏移去写，就是往错误位置写数据。

**④ 作者的取材边界**
那个包和它同一作者发布的[小米手环11固件](https://www.bandbbs.cn/resources/7955/)、[红米手表6固件](https://www.bandbbs.cn/resources/7243/)放在一起 —— 他是做固件 dump 的人，只为"手上有 dump 的那个版本"做偏移表。另外那份 S4 41mm 的包标的是 `3.100.032`，而你这台 eSIM 是 `3.202.79`，本来就不是同一条构建线。

**所以"难道每个版本都有不可替代的变化吗"——不是。** 是"按绝对偏移硬写"这个做法天生不能跨版本。**换一种做法就可以跨版本**（见下一节）。

---

## 5. 更好的做法：不重建 ROMFS，按名字原地替换（已实现并验证）

因为 144×144 的图标换成另一个 144×144、同色彩格式的图标时，**字节长度完全相同**，所以可以：

> **在设备上解析 ROMFS → 按路径找到 `<app>/launcher.bin` → 用等长的新图标覆盖它的数据 → inode 表、super block、后续所有偏移全部不动。**

这样：
- 不需要重建 ROMFS，不需要改 `size`/`checksum`/`next`；
- 不需要"每版本一份包"——偏移是**运行时从当前固件里算出来的**，所以**天然跨固件版本**；
- 传输量从"265 MB（或压缩 75 MB）整分区"降到"每个图标 83 KB / 22 KB"。

### 已验证的实现

工具：`_tools/romfs.py`（ROMFS 解析/遍历）、`_tools/iconpack.py`（make / apply / list）、`_tools/render_icons.py`（解码为 PNG）。

验证结果：

| 验证项 | 结果 |
|---|---|
| ARGB8888 编码器与原固件字节级一致（alarm 图标往返） | ✅ 完全一致（82956 字节） |
| I8 编码器长度一致 + 视觉误差 | ✅ 长度一致，平均绝对误差 0.22/255 |
| 原地替换后条目数 / 路径 / inode 表 / super block / 文件总长 | ✅ 全部**逐位不变**（7834 条，`inode table identical: True`） |
| 内容变化的文件 | ✅ 恰好只有被替换的那几个 `launcher.bin` |

用 4 个自制图标（alarm / timer / wxpay / settings）跑通了
`make → apply → 校验 → 回读渲染`全流程，见 `_out/patched_custom.png`。

---

## 6. 还缺的那一环：写入通道

到这里，"**改什么、改成什么、怎么做到版本无关**"都已经解决。**唯一未解决的是"怎么把这几万字节送进 `/dev/app`"**：

| 方式 | 说明 | 代价 |
|---|---|---|
| 实机 shell `dd` | 最直接，需要能拿到 shell（或 Recovery） | 需要相应工具/权限 |
| 表盘包 + 脚本写分区节点 | 社区现有做法，整链路已由本次分析解释清楚 | 属于滥用未公开行为，OTA 后失效；写错偏移会损坏分区 |
| 重打包 OTA zip | ❌ 签名校验过不去 | 不可行 |

要在你的机器上落地，下一步需要的是：**在真机上把 `/dev/app`（或至少 ROMFS 头与目标 inode）读出来**，用 `iconpack.py list` 得到你这一版固件的真实偏移，再生成补丁。这样就不再受"包只适用于某某版本"的限制。

---

## 7. 风险提示

- 对**分区节点**写数据是文档明确警告的危险操作；写错偏移会破坏资源分区，可能导致无法开机。
- 写之前**务必备份**原始分区（至少备份 ROMFS 头 + inode 表 + 你要改的 `launcher.bin` 原字节，能回滚）。
- 系统 OTA 会覆盖你的修改；跨版本套用旧补丁 = 往错误位置写数据。
- 修改系统资源分区可能影响保修；请自行确认设备所有权与当地法律。
- `voice/alexa/launcher.bin`（6005 字节，`flags=0x0008`）格式尚未确定，不要动它。

---

## 附：工作目录

```
_x/                       解包后的固件（含 13 个分区镜像）
_tools/romfs.py           ROMFS 解析与遍历
_tools/iconpack.py        list / make / apply 图标补丁
_tools/render_icons.py    把 launcher.bin 解码成 PNG
_tools/patch_demo.py      原地等长替换的概念验证
_tools/demo_icons.py      编码器自检 + 生成示例图标
_tools/verify_patch.py    补丁后元数据一致性校验
_out/icons/               从原厂固件导出的 38 个应用图标 PNG
_out/launcher_icons_sheet.png  全部图标总览
_out/before_after.png     原地替换前后对比
_out/patched_custom.png   自制图标写入后的回读结果
```
