# 小米手表 S4 eSIM 系统图标 / 动画修改器（Lua 表盘）

三个独立的项目，同一套机制：**用一个 Lua 表盘把系统资源「等长原地覆盖」进 ROMFS 分区**，重启生效；界面里带只读预检查、写入进度和一键回滚。

| 项目 | 干什么 | 写入分区 | 表盘名 / id | 交付物 |
|---|---|---|---|---|
| [`s4e-icons/`](s4e-icons/) | 系统应用图标 + 控制中心顶栏状态 + 各 App 素材（同名全换） | `/dev/app` | **S4e Pt.1** / `362150101` | `dist/S5Icons.face`（替换 + 回滚在同一张盘里） |
| [`s4e-pressure-anim/`](s4e-pressure-anim/) | 压力检测动画（119 帧） | `/dev/app` | **S4e Pt.2** / `362150102` | `dist/S4PAnim.face` + `dist/S4PAnimRestore.face` |
| [`s4e-charge/`](s4e-charge/) | 充电动画（57 帧） | `/dev/system` | **S4e Pt.3** / `362150103` | `dist/S4Chg.face` + `dist/S4ChgRestore.face` |

目标机型：**Xiaomi Watch S4 eSIM（o62lte, 3.202.79），466×466**。
素材来源：**Xiaomi Watch S5 41mm（q63, v4.101.020）的 OS4 资源**。

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

## 交付物与当前校验状态

| 文件 | 字节 | 表盘名 | b5 | id | sha256 |
|---|---:|---|---:|---|---|
| `s4e-icons/dist/S5Icons.face` | 8,010,028 | S4e Pt.1 | 0 | 362150101 | `286a87ed41d636933dc4432b46b28aeb011f73004ddf2816d198c520613565fd` |
| `s4e-icons/dist/S5Icons_toolchain.face` | 8,010,028 | S4e Pt.1 | 10 | 362150101 | `5045e4adf803f61c2aef8324f08d56802e02db6f0e7e4a13942e0bcb1f65f032` |
| `s4e-pressure-anim/dist/S4PAnim.face` | 16,688,156 | S4e Pt.2 | 0 | 362150102 | `8492e2cb29f612caa3965014d0bf2e44bdb2f54cd08bad28087bd6c1bd80b214` |
| `s4e-pressure-anim/dist/S4PAnimRestore.face` | 16,688,156 | S4e Pt.2 | 0 | 362150102 | `cc9fe6e3d93efea0fa2f8ae5ff63641066cdefe06867dbc43736bdd5f2833e87` |
| `s4e-charge/dist/S4Chg.face` | 6,424,484 | S4e Pt.3 | 0 | 362150103 | `44b28b61200a03ac8c33333c051c4a395ca4f3c197012102229e2717cfbbd00b` |
| `s4e-charge/dist/S4ChgRestore.face` | 6,424,484 | S4e Pt.3 | 0 | 362150103 | `8c97bb1e87efefe58c91d560c2488677ba9d89107824712f09818893611a1dbb` |

- `*_toolchain.face` 是官方工具链的原样产物（b5=10）；主交付物是 **b5=0** 的那张，装不上时才换它。
- 每个项目的 replace / restore 用**同一个表盘 id**，装其中一张会顶掉另一张，设备上只占一份空间。
- 校验：`s4e_verify.py`（icons 全绿）、`verify_anim.py replace|restore`（两个动画项目各 11/11）。所有盘的两遍构建都是 **0 偏移漂移**，且 inode 表 / superblock 逐位不变。

---

## 跑起来（全部在仓库根目录内完成）

前置：**Python 3 + Pillow**（`pip install pillow`）。

### 1) 放 `inputs/`（固件分区镜像）

官方 OTA 包（ZIP）里的 `vela_*.bin` 条目，解压后按下面的名字放（`ota.sh`、`CERT.*`、`MANIFEST.MF` 不需要）：

| 路径 | 是什么 | 字节 | sha256 前 16 |
|---|---|---:|---|
| `s4e-icons/inputs/target/vela_app.bin` | S4 eSIM 的 app 分区（目标） | 265,684,992 | `caa66693f49477dd` |
| `s4e-icons/inputs/source/vela_app.bin` | q63 的 app 分区（素材来源） | 206,000,128 | `161a8f7a5f0bd8af` |
| `s4e-icons/inputs/source/vela_health.bin` | q63 的 health 分区 | 233,939,968 | `12a3bd2f8b62e969` |
| `s4e-pressure-anim/inputs/target/vela_app.bin` | 同上（app 分区） | 265,684,992 | `caa66693f49477dd` |
| `s4e-pressure-anim/inputs/source/vela_app.bin` | 同上（q63 app） | 206,000,128 | `161a8f7a5f0bd8af` |
| `s4e-charge/inputs/target/vela_system.bin` | S4 eSIM 的 system 分区（目标） | 72,366,080 | `bf631818f2ccbe48` |
| `s4e-charge/inputs/source/vela_system.bin` | q63 的 system 分区（素材来源） | 100,630,528 | `114c131821b39d71` |

### 2) 放 `vendor/`（第三方编译器）

把 [FangAiden/LuaDevTemplate](https://github.com/FangAiden/LuaDevTemplate) 解压成
`<项目>/vendor/LuaDevTemplate-main/`（里面必须有 `watchface/tools/Compiler.exe`）。每个项目一份。
没有它只能生成负载，不能编译 `.face`。

（路径定义集中在各项目 `tools/paths.py`，可用
`ICON_EDIT_INPUTS / ICON_EDIT_VENDOR / ICON_EDIT_WORK / ICON_EDIT_DIST` 覆盖。）

### 3) 构建

```powershell
# 图标（S4e Pt.1）
cd s4e-icons
python tools/make_s5_to_s4_inset.py     # q63 素材 -> S4 槽位（尺寸归一化 / 格式转换 / I8 调色板复用）
python tools/make_dd_payload.py         # 逐条负载 + 回滚负载 + flash.sh / rollback.sh + payload.json
python tools/gen_ui_lua.py              # 两遍构建 -> dist/S5Icons.face（回填偏移，断言 0 漂移）
python tools/s4e_verify.py              # 独立校验

# 压力动画（S4e Pt.2）
cd ../s4e-pressure-anim
python tools/make_anim_payload.py       # 帧 -> 等长槽位 + 改后镜像（自带逐像素回解自证）
python tools/make_dd_payload.py replace ; python tools/gen_ui_lua.py replace ; python tools/verify_anim.py replace
python tools/make_dd_payload.py restore ; python tools/gen_ui_lua.py restore ; python tools/verify_anim.py restore

# 充电动画（S4e Pt.3）
cd ../s4e-charge
python tools/make_charge_payload.py all # 57 帧全量
python tools/make_dd_payload.py replace ; python tools/gen_ui_lua.py replace ; python tools/verify_anim.py replace
python tools/make_dd_payload.py restore ; python tools/gen_ui_lua.py restore ; python tools/verify_anim.py restore
```

### 4) 内容开关（只影响 `s4e-icons`）

默认打进表盘的是「应用图标 + 控制中心顶栏状态 + 系统 UI + 通知 / 电话 / 录音机 / 计时器 / 待办（同名全换）」。下面两组**默认关闭**：

| 环境变量 | 作用 |
|---|---|
| `ICON_MIJIA=1` | 控制中心里的米家 / 融合中心设备图标（实测目标机本来就装了同一个米家表 App，129 张设备图标里 128 张与 q63 逐字节相同，一般不需要） |
| `ICON_WALKIE=1` | 对讲机素材 `walkie_talkie/**`（160 条；素材来自用户提供的 PNG） |
| `ICON_SKIP_WALKIE=1` / `ICON_ONLY_WALKIE=1` | 要分组出表盘时用（一个大表盘拆两张） |

---

## 为什么必须等长

ROMFS 把 inode、文件名、文件数据首尾相接顺序排布，所有 `next` / `spec` 都是**绝对偏移**。替换文件只要长度差一个字节，它后面所有文件的偏移就整体平移 —— 轻则图标错乱，重则资源分区损坏。

所以三个项目都保证 **每条负载的长度 == 原槽位长度**，只动数据、不碰 inode 表 / superblock / 目录项。RLE 压缩的槽位（`flags=0x08`）用「量化 → RLE → 用合法空指令补齐到原 csize」做到逐字节等长；压缩流必须**恰好**解出 `usize`（差 1 个像素整帧就不画）。

## 表盘到底做了什么

Lua 表盘不能「设置图标」。系统资源住在 ROMFS 分区镜像里，必须写分区 + 重启。表盘只做运载 + 执行：

```
每条记录三步（只用官方存在的 dd，判据全看内容，不看 os.execute 的返回值 —— 它不可靠）：
  1 对版   读出设备上该偏移处 64 字节，与「原厂字节」或「替换后字节」比对
           两者都不是 -> 判「版本不符」，该分区剩余记录全部跳过（绝不往别人的文件里写）
  2 写入   dd if=/tmp/xxx of=<分区> bs=512 + bs=4 + bs=1 分段（长度不保证 4 对齐）
  3 回读   整段读回来逐字节比对

回滚 = 同一套流程，只是写入的字节换成原厂字节
最后 sync + reboot（ROMFS 是只读挂载 + 有页缓存，不重启看不到新内容）
```

偏移都在**构建时两遍测量回填**：先编一遍，在 .face 里搜负载定位，量出真实偏移写回 Lua，再编第二遍并逐条校验 0 漂移。

## 只安装、不重建

拿 `dist/*.face`，和普通 Lua 表盘一样安装（`resource.bin` 推到 `/data/app/watchface/market/<表盘id>/`）。装到手表后在表盘上操作：

```
首页 →「快速帮助」→「环境预检查」   只读，一个字节都不写
首页 →「开始替换」→ 确认 → 自动写入（看「失败 0」）→「重启手表」
       快速帮助 →「回滚修改」→ 确认 → 写回原厂
```

**环境预检查是只读的**，它只能证明「分区可读 + 抽样偏移对版」，证明不了「可写」；但写入路径每条都自带对版 + 回读校验，最坏结果是「内容没变」，不会把分区写坏。

## 已知边界

1. **偏移锁固件版本**：ROMFS 绝对偏移排布，换固件版本必须拿新镜像重跑，旧偏移会写错位置。
2. **等长是硬要求**：长度不等会让后面所有偏移平移；脚本对每条断言长度相等。
3. **I8 槽位**必须复用源图调色板，否则边缘锯齿 + 彩点。
4. **真机能力**：`os.execute` / `dd` 可用；`io.popen` 捕获不到输出；`os.execute` 返回值不可靠（成功也可能是 65280），判据一律看内容读回。
5. 首次请只点「环境预检查」，看清输出再替换。
6. 盘内显示名存在 `.face` 头部 `offset 104..167`（64 字节），由构建时的 `projectName` 决定；官方 `build_face.ps1` 会把工作区里唯一的 `.fprj` 改名并把 `<Screen Title>` 覆盖成它 —— 所以显示名要改就改 `projectName`，并且编译后把 `.fprj` 名字归一回去（本项目脚本已含断言）。

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
- **改系统分区有风险**：写错偏移可能损坏资源分区。三个项目都自带版本校验和回滚，但请自行确认设备所有权并承担后果
