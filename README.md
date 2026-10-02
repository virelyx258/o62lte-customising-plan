# 小米手表 系统图标修改器（Lua 表盘）

两个互相独立的项目，同一套机制：**用一个 Lua 表盘把系统应用图标「等长原地覆盖」进 ROMFS 资源分区**，重启生效；界面里带只读预检查、写入进度和一键回滚。

| 项目 | 目标机型 | 屏幕 | 写入分区 | 主交付物 |
|---|---|---|---|---|
| [`s4e-icons/`](s4e-icons/) | Xiaomi Watch S4 eSIM（o62lte, 3.202.79） | 466×466 | `/dev/app` | `dist/S5Icons.face` |
| [`s5e-icons/`](s5e-icons/) | Xiaomi Watch S5 eSIM 46mm（p62lte, 3.112.035） | 480×480 | `/dev/app` + `/dev/health` | `dist/S5eIcons.face` |

两个项目的**图标来源都是 Xiaomi Watch S5 41mm（q63, v4.101.020）的 OS4 图标包**。

每个项目内部结构：

```
README.md        项目说明（交付物 / 装法 / 边界）
main.lua         表盘源码（含 __PAY__ / __RB__ / __UIIMG__ 占位符，构建时回填）
tools/           全部 Python 脚本（ROMFS 解析、LVGL 编解码、负载生成、两遍构建、独立校验）
assets/          设计素材；assets/override/ 里的自制 PNG 优先级高于固件来源
inputs/          固件分区镜像（**要自己放，不进仓库**）
vendor/          第三方 LuaDevTemplate-main（含 Compiler.exe，**不进仓库**）
.work/           构建工作区（产物，可删）
dist/            交付的 .face
docs/            说明、分析报告、预览图
```

---

## 跑起来（全部在 `icon-editors/` 目录内完成）

前置：**Python 3 + Pillow**（`pip install pillow`）。

### 1) 放 `inputs/`（固件分区镜像）

官方 OTA 包（ZIP）里的 `vela_*.bin` 条目，解压后按下面的名字放（`ota.sh`、`CERT.*`、`MANIFEST.MF` 不需要）：

| 路径 | 是什么 | 字节 | sha256 前 16 |
|---|---|---:|---|
| `s4e-icons/inputs/target/vela_app.bin` | S4 eSIM 的 app 分区 | 265,684,992 | `caa66693f49477dd` |
| `s4e-icons/inputs/source/vela_app.bin` | S5 41mm q63 的 app 分区 | 206,000,128 | `161a8f7a5f0bd8af` |
| `s4e-icons/inputs/source/vela_health.bin` | q63 的 health 分区 | 233,939,968 | `12a3bd2f8b62e969` |
| `s5e-icons/inputs/target/vela_app.bin` | S5 eSIM 的 app 分区 | 103,043,072 | `9b41c5f5eb17c112` |
| `s5e-icons/inputs/target/vela_health.bin` | S5 eSIM 的 health 分区 | 206,924,800 | `489752c8a3fb24ff` |
| `s5e-icons/inputs/source/*` | 与 s4e 的 `source/` 是同一份 q63 镜像 | | |

### 2) 放 `vendor/`（第三方编译器）

把 [FangAiden/LuaDevTemplate](https://github.com/FangAiden/LuaDevTemplate) 解压成
`<项目>/vendor/LuaDevTemplate-main/`（里面必须有 `watchface/tools/Compiler.exe`）。
两个项目各一份。没有它只能生成负载，不能编译 `.face`。

（本项目本来也支持 `ICON_EDIT_VENDOR=<目录>` 指向别处的模板，路径定义集中在
`tools/paths.py`，可用 `ICON_EDIT_INPUTS / ICON_EDIT_VENDOR / ICON_EDIT_WORK / ICON_EDIT_DIST` 覆盖。）

### 3) 构建

```powershell
cd icon-editors/s4e-icons
python tools/make_s5_to_s4_inset.py    # q63 素材 -> S4 槽位（含尺寸归一化、格式转换、I8 调色板复用）
python tools/make_dd_payload.py        # 逐条负载 + 回滚负载 + flash.sh / rollback.sh + payload.json
python tools/gen_ui_lua.py             # 两遍构建 -> dist/S5Icons.face（回填偏移，断言 0 漂移）
python tools/s4e_verify.py             # 独立校验（不复用构建代码，建议每次跑）

cd ../s5e-icons
python tools/s5e_payload.py            # q63 素材 -> S5e 槽位
python tools/s5e_build.py              # -> dist/S5eIcons.face
python tools/s5e_verify.py             # 独立校验
```

### 4) 内容开关

默认打进表盘的是「应用图标 + 控制中心顶栏状态 + 系统 UI + 通知 / 电话 / 录音机 / 计时器 / 待办」。
下面两组**默认关闭**：

| 环境变量 | 作用 |
|---|---|
| `ICON_MIJIA=1` | 控制中心里的米家 / 融合中心设备图标（实测目标机本来就装了同一个米家表 App，129 张设备图标里 128 张与 q63 逐字节相同，一般不需要） |
| `ICON_WALKIE=1` | 对讲机素材 `walkie_talkie/**`（160 条；S5 41mm 没有这个 App，素材来自用户提供的 PNG） |
| `ICON_SKIP_WALKIE=1` / `ICON_ONLY_WALKIE=1` | 要分组出表盘时用（一个大表盘拆两张） |

---

## 为什么必须等长

ROMFS 把 inode、文件名、文件数据首尾相接顺序排布，所有 `next` / `spec` 都是**绝对偏移**。替换文件只要长度差一个字节，它后面所有文件的偏移就整体平移 —— 轻则图标错乱，重则资源分区损坏。

所以两个项目都保证 **每条负载的长度 == 原槽位长度**，只动数据、不碰 inode 表 / superblock / 目录项。

## 表盘到底做了什么

Lua 表盘不能「设置图标」。系统图标住在 ROMFS 分区镜像里，必须写分区 + 重启。表盘只做运载 + 执行：

```
每条记录三步（只用官方存在的 dd，判据全看内容，不看 os.execute 的返回值 —— 它不可靠）：
  1 对版   读出设备上该偏移处 64 字节，与「原厂字节」或「替换后字节」比对
           两者都不是 -> 判「版本不符」，该分区剩余记录全部跳过（绝不往别人的文件里写）
  2 写入   dd if=/tmp/xxx of=<分区> bs=4 seek=<偏移/4> count=<长度/4>
  3 回读   整段读回来逐字节比对

回滚 = 同一套流程，只是写入的字节换成原厂字节
最后 sync + reboot（ROMFS 是只读挂载 + 有页缓存，不重启看不到新图标）
```

偏移都在**构建时两遍测量回填**：先编一遍，在 .face 里搜负载定位，量出真实偏移写回 Lua，再编第二遍并逐条校验 0 漂移。

## 只安装、不重建

直接拿 `s4e-icons/dist/S5Icons.face` 或 `s5e-icons/dist/S5eIcons.face`，和普通 Lua 表盘一样安装（`resource.bin` 推到 `/data/app/watchface/market/<id>/`）。装到手表后在表盘上操作：

```
首页 →「快速帮助」→「环境预检查」   只读，一个字节都不写
首页 →「开始替换」→ 确认 → 自动写入 → 「重启手表」
       快速帮助 →「回滚修改」→ 确认 → 写回原厂图标
```

**环境预检查是只读的**，它只能证明「两个分区可读 + 抽样偏移对版」，证明不了「可写」；但写入路径每条都自带对版 + 回读校验，最坏结果是「图标没变」，不会把分区写坏。

## 已知边界

1. **偏移锁固件版本**：ROMFS 绝对偏移排布，换固件版本必须拿新镜像重跑，旧偏移会写错位置。
2. **等长是硬要求**：长度不等会让后面所有偏移平移；脚本对每条断言长度相等。
3. **I8 槽位**必须复用源图调色板，否则边缘锯齿 + 彩点。
4. **真机能力**：`os.execute` / `dd` 可用；`io.popen` 捕获不到输出；`os.execute` 返回值不可靠（成功也可能是 65280），判据一律看内容读回。
5. 首次请只点「环境预检查」，看清输出再替换。

## 仓库里没有的东西（体积 / 版权）

| 不含 | 原因 | 怎么补 |
|---|---|---|
| `inputs/**/*.bin`（固件分区镜像） | 体积 + 版权 | 从官方 OTA 包解包，见上表 |
| `inputs/fonts/*.ttf`（MiSans） | 版权属小米 | 从固件 `vela_font.bin` 取；没有只影响预览图 |
| `vendor/LuaDevTemplate-main/` | 第三方 | 从 GitHub 取，见上 |

## 第三方与法律

- `.face` 由 [FangAiden/LuaDevTemplate](https://github.com/FangAiden/LuaDevTemplate) 的 `Compiler.exe` 编译；本仓库不含它，请自行放到 `vendor/LuaDevTemplate-main/`
- MiSans 字体版权属小米；本仓库不含字体文件，需要时从固件 `vela_font.bin` 里取
- 固件 / OTA 版权属小米，请从官方更新包里自行解包
- **改系统分区有风险**：写错偏移可能损坏资源分区。两个项目都自带版本校验和回滚，但请自行确认设备所有权并承担后果
