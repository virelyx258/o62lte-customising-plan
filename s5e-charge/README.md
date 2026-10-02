# S5Chg —— 把 S5 41mm(q63) 的充电动画搬到 S5 eSIM 46mm

把 **Xiaomi Watch S5 41mm（q63）** `vela_system.bin` 里的 `charging/charge0..60.bin`（**464×464**），
逐帧**等长覆盖**写进 **Xiaomi Watch S5 eSIM 46mm（p62lte）** `/dev/system` 的同名 61 个槽位
（**480×480**，I8 + RLE）。

> 关系：`s4e-charge` 是「S5 41mm → S4 eSIM」的母项目（只读参考）。本项目沿用它的全部结构
> （两遍构建回填偏移、指纹表拆盘、逐字节等长覆盖、独立校验），只把目标换成 S5 eSIM、
> 帧数改成 61→61、界面重做成 480×480、放大从"同尺寸"改成"464→480 放大"。

## 改了什么

| | |
|---|---|
| 目标 | `inputs/target/vela_system.bin`（S5 eSIM 46mm `/dev/system`）→ `charging/charge0..60.bin`，**61 帧 480×480** I8+RLE，槽位 143,832 ~ 213,511 B（**各不相同**） |
| 源 | `inputs/source/vela_system.bin`（q63 S5 41mm）→ `charging/charge0..60.bin`，**61 帧 464×464** |
| 映射 | **帧号 1:1（n → n）**。两边都是 61 帧，**没有** S4e 那版的 `round(n/56*60)` 比例重采样 |
| 放大 | 源帧 RGB 用 **Lanczos** 放大到 480×480，再把每个像素**吸附回源帧自己的 256 色调色板**（最近的欧氏距离）→ 颜色零新增、零量化，空间上比最近邻放大平滑 |
| 本次 | **61/61 全换**，**每一帧都是"原调色板 + Lanczos"**（没有一帧被降级：没有暗区合并、没有降色数、没有留原厂） |
| 编码 | 压缩 8.69 MB，槽位共 11.27 MB → **还剩 2.57 MB 余量**（最紧的一帧 `charge47` 也余 10,488 B） |
| 校验 | 61/61 回解**逐像素**等于计划图、RLE 恰好解出 usize、inode 表/superblock 逐位不变、槽位外 0 字节变化、回放一致 |

等长的做法（硬约束，一步都不能省）：`解码源帧 → Lanczos 放大 480×480 → 吸附回源调色板 →
LVGL RLE 压缩 → 用合法空指令补齐到原 csize`。补齐用 `00 00`（重复 0 次）这类**产出 0 像素**
的指令；另外 `usize_tail()` 会在解码长度比 `usize` 少时**重复最后一个字节**补足
（踩过的坑：RLE 输出比 `usize` 少 1 个像素，设备端整帧不画）。

## 交付物

| 文件 | 字节数 | id / b5 | sha256 |
|---|---|---|---|
| `dist/S5Chg.face` | **11,986,752** | `462150103` / b5=0 | `577147341d363811965b51f46088ed98ea62c946cc8b7d205264577fab4d8066` |
| `dist/S5ChgRestore.face` | **11,986,752** | `462150103` / b5=0 | `8dbfc87acde8b54543fa7f2b54c1b0d7360634c83d6cf139a78df762ff078f2c` |

两份盘**共用同一个表盘 id**（`462150103`）：装其中一份就会顶掉另一份，设备上始终只占一份空间。
- `S5Chg.face`：`pay` = 替换后的 61 帧，`rb` = **原厂**前 64 B 指纹（只给版本校验用）
- `S5ChgRestore.face`：`pay` = **原厂**61 帧（逐字节），`rb` = 替换后前 64 B 指纹

预览与报告：
- `docs/decode_preview.png` —— **直接从交付物 .face 里解出来的 61 帧**总览（最硬的证据）
- `docs/face_before_after.png` —— 抽样 5 帧：上排 q63 原帧（464），下排交付物解出的帧（480）
- `docs/before_after.png` —— 生成负载时的对照图（上=源帧，下=磁盘上改后镜像解出的帧）
- `docs/ui_*.png` / `docs/ui_all.png` —— 480×480 界面（9 个规格页 + 8 个还原盘文案变体）
- `docs/selfcheck_report.txt` —— `tools/verify_all.py` 的完整输出（33/33）
- `docs/selfcheck_run.txt` —— **整条重建流水线的原始输出**（8 步，逐步 EXIT=0）

## 真机怎么做

1. 装 `dist/S5Chg.face`
2. 表盘「快速帮助 → 环境预检查」（**只读**，一个字节都不写）：确认 `/dev/system` 可读、
   卷名是 `system`、61 条负载不越界，并对首/中/尾三条做抽样版本校验（`原厂✓` / `已替换✓`）
3. 首页「开始替换」→ 确认页 → **确认替换** → 等 `成功 61 失败 0`（61 条 ≈ 11.3 MB）
4. 「重启手表」→ 插上充电器看整段动画
5. 还原：装 `dist/S5ChgRestore.face` →「开始还原」→ 重启

输出怎么读（「正在替换」页）：每 10 条一行 `> 写入 n/61 成功 x 失败 y`；结束时
`> 共 61 条，成功 x 失败 y`。

**判断成功的唯一标准是 `成功 61 / 失败 0`**；如果出现 `> 版本不符跳过 n 条`，说明设备上的
`/dev/system` 不是算偏移时用的那一版固件 —— 此时**不要重启**，装对应版本的盘或先还原。

写入前每条都做版本校验：读设备上该偏移的前 64 B，必须等于「原厂前 64 B」或「替换后前 64 B」，
**两边都不是就判「版本不符」并跳过 `/dev/system` 剩余记录**（绝不把字节写进别人的文件里）。
写入后整条回读比对，失败自动重试 3 次 + 退化成整条一次 dd。

## 重建

```powershell
# 需要 Python 3 + Pillow + numpy；inputs/ 与 vendor/ 要自己准备（见下）
python tools\make_charge_payload.py all      # 61 帧负载 + 整分区镜像（自带 4 项镜像级自证）
python tools\make_dd_payload.py replace      # 负载 + 指纹 + blob_replace/
python tools\gen_ui_lua.py replace           # 两遍构建 -> dist\S5Chg.face（0 漂移校验）
python tools\verify_anim.py replace          # 逐盘校验（11 项）
python tools\make_dd_payload.py restore
python tools\gen_ui_lua.py restore           # -> dist\S5ChgRestore.face
python tools\verify_anim.py restore
python tools\verify_all.py                   # 独立总校验（33 项）+ 预览图 + selfcheck_report.txt
```

或者一条命令跑完全部 8 步（逐步校验、任一步失败即中止，输出留档到 `docs/selfcheck_run.txt`）：

```powershell
& ".\tools\selfcheck.ps1"
```

`make_charge_payload.py` 不加 `all` 时只跑 `[0,14,28,42,56]` 这 5 帧（轻量试跑）。

界面相关（改了 `tools/pages.py` / `main.lua` 之后）：

```powershell
python tools\make_ui_images.py               # assets/ -> ui_images/*.bin（480 档尺寸）
python tools\render_ui.py                    # 480×480 预览（有标签溢框会直接报出来）
python tools\check_clip.py                   # 真实渲染像素判圆屏切边（0 越界才算过）
```

### `inputs/` 与 `vendor/` 不进仓库

`.gitignore` 里已经排除（本项目 `.gitignore` 原样沿用，未改动）：

| 路径 | 是什么 |
|---|---|
| `inputs/target/vela_system.bin` | 目标固件 p62lte 的 system 分区镜像（84,429,824 B） |
| `inputs/source/vela_system.bin` | 源固件 q63 的 system 分区镜像（100,630,528 B） |
| `inputs/fonts/MiSans-*.ttf` | 可选；只用于本机渲染预览（缺了就退回系统字体，只影响预览） |
| `vendor/LuaDevTemplate-main/` | 官方模板（含 `Compiler.exe`）—— 用默认路径即可，**不要设 `ICON_EDIT_VENDOR`** |

固件分区镜像就是官方 OTA 包（ZIP）里的 `vela_system.bin` 条目，解压出来放到上表位置即可。

## 自证输出（全部真实执行过）

**① 61 条负载长度逐条 == 原槽位长度**
```
目标 S5 eSIM(p62lte) 61 帧（0..60，槽位合计 11.27 MB）
源   S5 41mm(q63)    61 帧（0..60，10.63 MB）
映射：n -> n（1:1）   输出分辨率：480x480（源 464x464 -> Lanczos 放大后吸附回源调色板）
   帧 47  <- q63 第 47  帧  槽位 144563 B  编码 134051 B（留白 10488）  ...  原调色板+Lanczos
回解自检通过 61 / 61（解码长度恰好 usize 且逐像素等于计划图）
编码方式分布：{'原调色板+Lanczos': 61}
```
`tools/verify_all.py`：`[OK] replace：61 条长度 == 原厂槽位长度  不符 0 条` /
`[OK] restore：61 条长度 == 原厂槽位长度  不符 0 条`；
`tools/verify_anim.py`：`pay 检查 61 条：长度全对 True`

**② 每条负载解出来都是 480×480（不能解码失败）**
```
[OK] replace：61 条都解出 480x480 且 RLE 恰好 usize  不符 0 条
[OK] restore：61 条都解出 480x480 且 RLE 恰好 usize  不符 0 条
```
（`usize` 必须**恰好** 231,424 = 1024 + 480×480，多一字节设备端 INVALID、少一字节不画）

**③ 改后整分区镜像的 inode 表 / superblock 逐位不变**
```
inode 表逐位不变：True（2150 条）
superblock 一致：True（sb_size=84429200 / 84429200，sb_cksum=3275251810 / 3275251810）
逐字节差异：共 11585280 字节，全部落在 61 个槽位内：True（槽位外 0 字节）
[OK] inode 表逐位不变（2150 条） / [OK] superblock 逐位不变 / [OK] 除 61 个槽位外没有任何字节变化
```

**④ 独立校验脚本全绿**
```
=== tools/verify_all.py（只读 dist/*.face + inputs/*/vela_system.bin，不读 .work/）===
61 帧平均差：mean 0.189  max 0.260（第 17 帧）      <- 与"独立做的 Lanczos 放大"比对
最像的源帧号与自身不一致的帧：0 个                  <- 证明第 n 帧就是 q63 第 n 帧
[OK] replace 盘 rb == 原厂前 64 B（对固件镜像比对）  不符 0 条
[OK] restore 盘 pay == 原厂整条字节（逐字节）        不符 0 条
[OK] restore 盘 rb == replace 盘 pay 前 64 B（两份交付物互证）  不符 0 条
RESULT: 全部通过 —— 33 项通过，0 项失败

=== tools/verify_anim.py replace / restore ===
S5Chg：pay 61 条，rb 61 条      pay 检查：长度全对 True，可解码 True，字节一致 True
全部通过 —— 11 项通过，0 项失败            （restore 同样 11/11）

=== tools/check_clip.py（480×480 圆屏，含 replace/restore 两套文案）===
检查了 17 个页面（含 replace/restore 两套文案）：越界页面 0
RESULT: PASS（0 越界、0 折行）
```

**⑤ 两张 .face 的 sha256**
```
S5Chg.face         11986752  b4=0 b5=0 id=b'462150103\x00'  sha256[:16]=577147341d363811
S5ChgRestore.face  11986752  b4=0 b5=0 id=b'462150103\x00'  sha256[:16]=8dbfc87acde8b545
S5Chg.face         sha256=577147341d363811965b51f46088ed98ea62c946cc8b7d205264577fab4d8066
S5ChgRestore.face  sha256=8dbfc87acde8b54543fa7f2b54c1b0d7360634c83d6cf139a78df762ff078f2c
```
完整重建 + 自证的原始输出（8 步全部 EXIT=0）留档在 `docs/selfcheck_run.txt`，
显式自证清单在 `docs/selfcheck_report.txt`（33/33）。重跑整条流水线：

```powershell
& ".\tools\selfcheck.ps1"        # = 上面 8 条命令，逐步校验，任一步失败即中止
```

## 已知边界 / 没做的部分

1. **没有一帧颜色数被降级**，也没有一帧保留原厂：61/61 都是「原调色板 + Lanczos」。
   全帧色数 251~256（即源调色板的实际用量），吸附误差 0.189/255（最大 0.260，第 17 帧）。
2. **没做锐化**：放大只用 Lanczos + 调色板吸附。这是刻意的 —— 锐化会增加索引噪点、
   直接吃掉 RLE 余量（最紧的 `charge47` 只剩 10,488 B）。
3. **真机未验证 S5 eSIM 的 `/dev/system` 可写**：这一点在 S4 eSIM 上实测通过（同源平台、
   同一套 dd 流程），S5 eSIM 上只能先靠只读的「环境预检查」确认可读 + 偏移对版。
   `system/drain/*`、`ota/anim*`、`setupwizard/*` 同理可改，但同样未在本机验证。
4. **偏移锁固件版本**：换固件必须重跑 `make_charge_payload.py all` → `make_dd_payload.py` →
   `gen_ui_lua.py`。用错版本时表盘会判「版本不符」并跳过 `/dev/system` 剩余记录，
   不会把字节写进别人的文件里。
5. **`Compiler.exe` 的设备表里没有 480 档**（枚举 DeviceType 只有 17 个已知值，圆表且预览
   326×326 的只有 362 / 462）→ 这里用 `DeviceType=462` + 326×326 预览图，预览只是表盘列表
   里的缩略图，与实际 480×480 画面无关（界面尺寸由 `main.lua` 与 `.fprj` 的 480 决定）。
6. **负载文件必须原样连续放在 resource.bin 里**，偏移才等于 `文件基址 + 魔数长度 + 相对偏移`；
   `gen_ui_lua.py` 会断言这一点并做两遍 0 漂移校验。魔数长度是 15 B（曾把 15 写成 16 导致全部偏移差 1）。
7. **写入速度**：偏移都是 512 对齐，所以 195 KB 的记录按 `bs=512` + `bs=4` + `bs=1` 三段写，
   不是逐字节；`sync` + 整条回读比对，失败重试 3 次后改用整条一次 dd。
8. **没动的**：`inode` 表、目录项、superblock、任何非 `charging/charge*.bin` 的文件；
   仓库里其它项目（`s4e-*`、`s5e-icons`、`s5e-pressure-anim`）与 git（未 commit、未改 `.gitignore`）。

## 目录

```
main.lua                 表盘源码（含 __UIIMG__ / __PAY__ / __RB__ / __ROLE__ 占位符，构建时回填）
tools/                   全部脚本（见下表）
ui_images/               界面素材（LVGL v9 .bin，8 张，480 档尺寸）
assets/                  设计素材 PNG
dist/                    交付的 .face
docs/                    预览图、对照图、selfcheck_report.txt
inputs/                  固件分区镜像 + 字体（不进仓库，见上）
vendor/                  LuaDevTemplate-main（含 Compiler.exe，不进仓库）
.work/                   构建工作区（产物，可删）
```

| 脚本 | 作用 | 相对 s4e-charge |
|---|---|---|
| `tools/paths.py` | 所有路径的唯一入口 | 沿用（未改） |
| `tools/romfs.py` | ROMFS 分区解析 | 沿用（未改） |
| `tools/lvgl_bin.py` | LVGL v9 RLE 编解码 + `pad_rle_safe` | 沿用（未改） |
| `tools/iconpack.py` | ARGB8888/I8 图片编码（界面素材用） | 沿用（未改） |
| `tools/lua_balance.py` | Lua 块配平检查 | 沿用（未改） |
| `tools/make_charge_payload.py` | **改**：目标/源换成 S5e + q63，61→61（n→n），输出 480×480，Lanczos+调色板吸附 | 重写 |
| `tools/make_dd_payload.py` | **改**：魔数 `S5C-PAYv1` / `S5C-FPv1`，脚本文案与设备名 | 小改 |
| `tools/make_overlays.py` | **改**：DeviceType 462 / Screen 480 / 预览 326（按首页规格真渲染） | 改 |
| `tools/build_faces.py` | **改**：盘名 S5Chg / S5ChgRestore，id 462150103 | 小改 |
| `tools/finalize_faces.py` | **改**：同上（b5=0 的忠实产物 + 改 id） | 小改 |
| `tools/gen_ui_lua.py` | **改**：盘名/角色名 | 小改 |
| `tools/verify_anim.py` | **改**：盘名 + 480×480 判据 | 小改 |
| `tools/verify_all.py` | **新增**：独立总校验（33 项，不读 `.work/`）+ 预览图 + 报告 | 新增 |
| `tools/selfcheck.ps1` | **新增**：一条命令跑完上面 8 步（逐步校验、失败即中止、输出留档） | 新增 |
| `tools/pages.py` | **改**：480×480 页面规格（含还原盘文案变体） | 重写 |
| `tools/render_ui.py` | **改**：画布 466→480，输出到 `docs/`，报标签溢框 | 小改 |
| `tools/check_clip.py` | **改**：圆屏 240/240，两套文案都过一遍 | 改 |
| `tools/make_ui_images.py` | **改**：素材尺寸换 480 档（31/18×29/80） | 改 |
| `main.lua` | **改**：480 几何、S5Chg 文案、版本不符**跳过分区剩余记录** | 重写 |
