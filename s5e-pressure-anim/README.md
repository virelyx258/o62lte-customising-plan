# S5ePAnim —— 把 S5 41mm(q63) 的压力检测动画搬到 S5 eSIM 46mm

把 **Xiaomi Watch S5 41mm（q63, v4.101.020）** 压力检测的 **100 帧 480×480** 动画，
逐帧**等长覆盖**写进 **Xiaomi Watch S5 eSIM 46mm（p62lte, v3.112.035）** `/dev/health` 里
`pressure/measure/Measuring1..119.bin` 的 **119 个槽位**（**464×464** I8 + LVGL RLE）。

> 关系：`s4e-pressure-anim` 是「S5 41mm → S4 eSIM（466×466）」的母项目（只读参考）。
> 本项目沿用它的全部结构（两遍构建回填偏移、指纹表拆盘、逐字节等长覆盖、独立校验），
> 只把目标换成 S5 eSIM、界面重做成 480×480、写入节点换成 `/dev/health`。

## 交付物

| 文件 | 字节数 | id / b5 | sha256 |
|---|---|---|---|
| `dist/S5ePAnim.face` | **16,450,844** | `462150102` / b5=0 | `d0bb012a364fd46eb4bb27db26ead72ae3166060c72c08ec5a76670dc06a3b1c` |
| `dist/S5ePAnimRestore.face` | **16,450,844** | `462150102` / b5=0 | `13cafae4bf2b03db82f2c17f9d3af7c7e8c01d0c26275feda301753a76ebda69` |

两份盘**共用同一个表盘 id**（`462150102`）：装其中一份就会顶掉另一份，设备上始终只占一份空间
（合在一张盘要 ~31 MB，超体积 —— 这是当初拆盘的原因）。

* `S5ePAnim.face`：`pay` = 替换后的 119 条（q63 的帧），`rb` = **原厂**前 64 B 指纹（只给版本校验用）
* `S5ePAnimRestore.face`：`pay` = **原厂** 119 条（逐字节），`rb` = 替换后前 64 B 指纹

两张盘除了负载/指纹与 Lua 里的两张表以外没有任何差别（头 50 B、8 张界面素材、资源基址逐字节相同）。

装法与普通 Lua 表盘相同（把生成的 `resource.bin` 推到表盘目录，例如
`/data/app/watchface/market/462150102/`）。装好后在表盘上操作：

```
首页 →「快速帮助」→「环境预检查」          只读，一个字节都不写
首页 →「开始替换」→ 确认页 →「确认替换」     写入 119 条 → 「重启手表」
还原：装 dist/S5ePAnimRestore.face（同 id 顶掉替换盘）→「开始还原」→ 重启
```

## 源 / 目标

| | 分区 | 槽位 | 尺寸 / 格式 | 单条大小 / 合计 |
|---|---|---|---|---|
| **目标** S5 eSIM 46mm（p62lte v3.112.035） | `inputs/target/vela_health.bin`（`/dev/health`，卷名 `health`） | `pressure/measure/Measuring1..119.bin` | 464×464 I8 **RLE**，`usize` **216,321 = 1024 + 464×464 + 1** | 4,485 ~ 196,538 B，共 **15.49 MB** |
| **源** S5 41mm（q63 v4.101.020） | `inputs/source/vela_app.bin` | `pressure/measure/Measuring1..100.bin` | 480×480 I8 **RLE**，`usize` 231,424 = 1024 + 480×480（**没有**尾巴字节） | ~182 KB / 帧 |

* 目标镜像 sha256 `489752c8a3fb24fff3e167610964795f0faaf830f142223b63be6ac2f57e67aa`
  （206,924,800 B，sb_size 206,924,736，superblock cksum `b804503a`）—— **偏移锁死这一版固件**。
* 改后镜像 `.work/anim/vela_health_anim.bin` sha256 `b11b72fcb38ad75a643d93d7db4dd366477ac33bfed93ef91096e04a73d67479`。

**映射**：第 k 个槽位(k=1..119) ← q63 第 `round((k-1)/(119-1)*(100-1))+1` 帧(1..100)。
119 与 100 不是整数倍关系，所以有 19 帧被连续两个槽位复用（`119↔100` 比例重采样，**不是** 1:1），
帧号顺序与速度与原动画一致。

### 目标固件的事实（从固件包里查出来的）

| 项 | 结论 | 证据 |
|---|---|---|
| 写入分区 | `vela_health.bin`，**卷名 `health`**，设备节点 `/dev/health` | ROMFS superblock 卷名 = `health`；206,924,800 B |
| 压力动画槽位 | `pressure/measure/Measuring1.bin … Measuring119.bin`，**119 帧** | 逐条枚举 ROMFS；编号连续 1..119 |
| 槽位格式 | 464×464，`cf=0x0a`(I8)，`flags=0x08`(RLE)，`method=1`，`stride=464` | 每条 12 B 图像头 + 12 B 压缩头；119 条的 `usize` 全是 216,321 |
| 槽位长度 | 4,485 ~ 196,538 B（差 40 倍），合计 15.49 MB | 逐条统计；`槽位长度 = 24 B 头 + csize` |
| 源素材 | q63 的 `vela_app.bin` 里 `pressure/measure/Measuring1..100.bin` | q63 的 `vela_health.bin` 里**没有** `pressure/measure/` |
| 源格式 | 480×480 I8 + RLE，`usize` 231,424，约 182 KB/帧 | 底噪是接近黑的 `#1a1a1a` 抖动 |
| 表盘宿主 | Lua 5.4，480×480 圆屏；`Compiler.exe` 对 DeviceType 462 强制 326×326 预览 | 同 `s5e-icons` 的实测结论 |

## 怎么做到「等长覆盖」

ROMFS 里每个文件的数据长度是硬编码的（后面所有文件的偏移都是绝对值），所以槽位必须**逐字节等长**替换：
`槽位长度 = 24 B 头（12 B 图像头 + 12 B 压缩头）+ csize 字节 RLE 流`。而两边尺寸不同、还都是 RLE，
压缩后长度各不相同。流水线（`tools/s5e_anim.py`）：

1. **暗部归零**（能不能塞进去的前提）：q63 的"黑"其实是一条接近黑的抖动底噪，熵极高；
   阈值（亮度 < 40，部分帧 < 56）以下的像素一律钉成纯黑之后，背景塌成整行单游程，
   RLE 体积掉到约 1/4。球体最暗的实体像素远高于阈值，所以只吃底噪、不动画面。
2. **缩放 + 量化**：480×480 → 464×464，在一条 34 档的阶梯上挑一档
   （256 色@1.00 → … → 32 色@0.70 → … → 2 色@0.05）。
3. **平滑**：以各帧"还能保住 ≥32 色"的最大缩放为上限，从峰值向两侧取**运行最小值**，
   得到单峰、单调的曲线，避免相邻帧忽大忽小（S4e 真机反馈过"忽大忽小"）。
4. **编码**：LVGL RLE（`tools/lvgl_bin.py: rle_compress`）。
5. **补齐**：`pad_rle_safe` 用两类**产出 0 像素**的合法指令把流补到 csize
   （`00 00` = 重复 0 次；`80` = 原样 0 个，用来修奇偶）。
6. **usize 尾巴**：解码长度必须**恰好**等于 header 里的 `usize`。
   目标槽位的 `usize = 216,321 = 1024 + 464×464 + **1**` —— 像素区之后还有 1 个字节；
   我们编码时也补出这 1 个字节（`usize_tail`），否则设备端 RLE 解码器认为流不完整，
   **整帧直接不画**（S4e 真机上就是这个现象：黑屏、只偶尔闪一下原版帧）。
   `s5e_anim.py` 里对这条有显式断言（源世代是 0 字节尾巴、目标世代是 1 字节，两者不同）。

### 编码期的三条就地自证（每条负载都跑）

1. `len(decode(stream)) == usize`（少一字节设备端就不画）
2. 解出来的像素 == 量化结果（逐点）
3. 量化结果的**形状**（非黑像素数 + bbox）与源图一致

> 第 3 条是被真 bug 逼出来的：早期版本量化时按 472 宽取像素、却读成 464 宽，整幅图被剪成
> **斜条纹** —— RLE 流完全正确、解出来也和"量化结果"逐点一致，只有比形状才抓得住。

**替换质量**：**119/119 全部替换**，`kept_stock = []`（没有一帧保留原厂）。
颜色分布：256 色 91 帧、192 色 1、128 色 2、96 色 1、64 色 7、48 色 3、32 色 6、
24 色 1、16 色 2、12 色 1、4 色 4。

* 开头 8 帧（`Measuring1..8`，4~24 色、缩放 0.16~0.65）是**设计如此**：动画从一个小点长起来，
  平滑曲线本身的目标档就在低端，不是被迫降级。
* **14 帧**（`Measuring106..119`）是**被迫退档**：平滑目标档（256 色@1.00）塞不进那 14 个偏小的槽位
  （槽位 19,025~77,823 B），退到 192/128/64/48/32 色 + 0.70~0.90 缩放；逐帧的 `(ci, target_ci, how)`
  都在 `.work/anim/manifest.json` 的 `records` / `degraded` 字段里。
* 预算利用率约 **49%**（编码 7.88 MB / 槽位 16.24 MB）：源帧本身是抖动过的 256 色图，
  去掉底噪后在 464×464 下的熵上限就是约 80 KB，而尾部槽位有 150~196 KB。
  想把预算填满只能把源图的**抖动颗粒**一起搬过去（背景会泛灰，也不是有效细节），
  权衡后选择保持画面干净 —— 这是**有意的取舍**，不是做不到。

## 真机怎么做

1. 装 `dist/S5ePAnim.face`
2. 表盘「快速帮助 → 环境预检查」（**只读**）：确认 `/dev/health` 可读、卷名是 `health`、
   119 条负载不越界（用 superblock 的**大端** size 判），并对首/中/尾三条做抽样版本校验
   （`原厂✓` / `已替换✓`）
3. 首页「开始替换」→ 确认页 → **确认替换** → 等 `成功 119 失败 0`（15.49 MB）
4. 「重启手表」→ 打开压力 App 开始检测，看整段动画
5. 还原：装 `dist/S5ePAnimRestore.face` →「开始还原」→ 重启

「正在替换」页每 10 条打一行 `> 写入 n/119  成功 x 失败 y`，结束打 `> 共 119 条，成功 x 失败 y`。
**判断成功的唯一标准是 `失败 0`**；若出现 `> 版本不符跳过 n 条`，说明设备上的 `/dev/health`
不是算偏移时用的那一版固件 —— **不要重启**，装对应版本的盘或先还原。

写入前每条都做版本校验：读设备上该偏移的前 64 B，必须等于「本盘要写的字节」或「另一侧的指纹」，
**两边都不是就判版本不符，并跳过 `/dev/health` 剩余记录**（绝不把字节写进别人的文件里）。
写入后用**内容比对**判成败（`os.execute` 的返回值在这台机器上不可靠），失败自动重试 3 次，
仍不过就退化成「整条一次 dd」。

### 为什么写入要分段（S4e 真机的教训）

119 个槽位**全部 512 对齐**，但 **97/119 条的长度不是 4 的倍数**（RLE 流长度随机）。
若按长度取块大小就只能退化成 `bs=1` —— 一条 19.6 万字节的记录要 ~40 万次单字节读写，
真机上慢到偶发失败。本项目按「`bs=512` 大块 + `bs=4` 次块 + 最后 1~3 字节 `bs=1`」切成 ≤3 段，
每条最多 3 个 dd 调用。

## 界面（480×480）

设计稿只有一处：`tools/s5e_pages.py`（`main.lua` 用的就是同一套坐标），
用真 MiSans 渲染到 `docs/ui_*.png`，并用**真实渲染像素**判圆屏切边（`tools/s5e_check_clip.py`）。

圆屏的硬约束：**在高度 y 处，屏幕的弦半宽 = √(240² − (y−240)²)**，越靠下越窄。所以：

* 列表底板 `radius=40` 不是审美：y=88 那行弦半宽只有 185.8，圆角不够时四个角会越过圆边
* 型号那一行拆成两行（`Xiaomi Watch S5` / `eSIM 46mm（p62lte）`）：整串 25px 真 MiSans 量得
  367px，而 y=243 处弦半宽只有 ~190px，放一行必被圆边切掉
* 说明文字每行都控制在 348px 以内（25px 下约 13 个中文字），否则折行后第 2 行会被圆边切
* 多色文本**不能**用 LVGL recolor（会被原样显示成 `#ffffff…`），一律拆成多个标签 + 手工算 x

实测：7 个页面越界像素 **0**（最远点 238.4 / 半径 240），标签溢框 0。

## 重建

```powershell
$env:PYTHONIOENCODING="utf-8"                # Windows 上必须，否则中文输出会炸
# 需要 Python 3 + Pillow (+ numpy)
python tools\s5e_anim.py all                 # 100 帧 -> 119 个等长槽位 + 改后整分区镜像（几分钟，几百 MB）
python tools\s5e_lua_static.py               # main.lua 静态体检（块配平 / 先用后声明 / 模板约定）

python tools\s5e_payload.py   replace        # 负载 + 指纹 -> payload/ + blob_replace/
python tools\s5e_overlay.py   replace        # 480x480 overlay（首页真渲染 -> 326x326 缩略图）
python tools\s5e_build.py     replace        # 两遍构建 -> dist\S5ePAnim.face（0 漂移校验）
python tools\s5e_verify.py    replace        # 逐盘校验（38 项）

python tools\s5e_payload.py   restore
python tools\s5e_overlay.py   restore
python tools\s5e_build.py     restore        # -> dist\S5ePAnimRestore.face
python tools\s5e_verify.py    restore

python tools\s5e_verify_indep.py             # 独立总校验（70 项，不读构建中间产物）
```

界面相关（改了 `tools/s5e_pages.py` / `main.lua` 之后）：

```powershell
python tools\s5e_ui_images.py                # assets/ -> ui_images/*.bin（8 张 LVGL v9 素材）
python tools\s5e_render_ui.py                # 480x480 预览 -> docs\ui_*.png + docs\ui_all.png（会报溢框）
python tools\s5e_check_clip.py               # 真实渲染像素判圆屏切边（0 越界才算过）
```

### 需要自己准备的输入（放进 `inputs/`，不进仓库）

| 路径 | 是什么 | 大小 |
|---|---|---|
| `inputs/target/vela_health.bin` | 目标固件（p62lte）health 分区 | 206,924,800 |
| `inputs/target/vela_app.bin` | 目标固件 app 分区（可选） | 103,043,072 |
| `inputs/target/vela_font.bin` | 目标固件 font 分区（可选：渲染预览时从里面取 MiSans） | 43,379,712 |
| `inputs/source/vela_app.bin` | 素材来源（S5 41mm q63）app 分区 | 206,000,128 |
| `inputs/fonts/MiSans-*.ttf` | 可选；不提供就自动从 `inputs/target/vela_font.bin` 里取 | — |
| `vendor/LuaDevTemplate-main/` | 官方模板（里面有 `Compiler.exe`） | — |

固件分区镜像就是官方 OTA 包（ZIP）里的 `vela_*.bin` 条目，解压出来即可。
**不要设 `ICON_EDIT_VENDOR`** —— 每个项目自带 `vendor/LuaDevTemplate-main/`。

## 自证输出（全部真实执行过，原始输出在 `docs/selfcheck_run.txt` / `docs/selfcheck_report.txt`）

**① 119 条负载长度逐条 == 原槽位长度**

```
OK   每条负载长度 == 原槽位长度（119 条）                        <- s5e_verify.py（两盘各一次）
OK   第 k 条负载的目标偏移 == Measuring{k}.bin 的偏移（0 处不符）  <- s5e_verify_indep.py：名字也对得上
OK   119 个目标偏移全部 512 对齐
     （97/119 条长度不是 4 的倍数 -> Lua 侧必须走 bs=512+4+1 分段写，否则退化成 bs=1）
```

**② 每条负载解出来都是 464×464，且 RLE 恰好 `usize`**

```
OK   每条负载都能按 LVGL RLE 解出正好 usize 字节、解成 464x464
OK   每条都是 I8(0x0a) + 压缩 + 464x464 + stride 464（0 条不符）
OK   每条 RLE 解出**恰好** usize=216321 且 1024+464*464 之后正好 1 字节尾巴（0 条不符）
```

**③ 改后镜像的 inode 表 / superblock 逐位不变、槽位外 0 字节变化**

```
OK   inode 表（路径/偏移/next/spec/size/cksum）5555 条逐位不变
OK   superblock 与卷名不变（size 206924736 / cksum b804503a / 'health'）
OK   分区长度不变（206924800 B）
OK   除 119 个槽位外，其余 5275 个文件的字节**逐字节**不变（0 处不符）
OK   变化区间 0x2c18618..0x3b9d384 完全落在槽位区间 0x2c18600..0x3b9d385 内
OK   119 个槽位全部被改写（未变的：无）
```

**④ `.face` 里 Lua 表反解出的偏移与镜像一致（0 漂移）＋ 两张盘互证**

```
OK   两张表的偏移自洽：首条紧跟魔数，之后逐条紧邻（0 处不连续）
OK   Lua 表里的 119 条偏移 == 文件基址 + 魔数长度 + 相对偏移      <- s5e_verify.py
偏移校验：全部吻合，0 漂移                                      <- s5e_build.py（两遍构建）
OK   replace 的负载前 64 B == restore 的指纹；restore 的负载前 64 B == replace 的指纹
OK   119/119 条负载在两张盘里都不一样
```

**总账**

```
s5e_lua_static.py      : 全部通过（块配平 202/202；无先用后声明；4 个占位符各 1 次）
s5e_verify.py replace  : 38 项通过，0 项失败
s5e_verify.py restore  : 38 项通过，0 项失败
s5e_verify_indep.py    : 70 项通过，0 项失败
s5e_check_clip.py      : 7 个页面，越界 0（最远 238.4 / 半径 240）
```

## 构建期的两个坑（都在 `tools/s5e_build.py` 里修掉了）

**① 交付物的 b5 曾经是 10（必须和固件自带表盘一样是 0）**
两遍构建走的是 vendor 的 `scripts/build_face.ps1`，它编完之后会调
`scripts/internal/set_face_id.ps1`，里面有一句 `$bytes[5] = [byte]$faceIdSize`（= 10）——
把 id 字符串长度写进了头里第 5 字节。现在最终产物取自**裸 `Compiler.exe -b`** 的输出
（b5 由编译器给出，实测 0），只覆盖 40..49 = id；并断言「裸产物与 toolchain 产物只差
b5 + id 这 8 个字节」，否则拒绝交付。

**② 第二遍曾经编的还是占位符版 Lua**
`main.lua` 是带 `__UIIMG__ / __PAY__ / __RB__ / __ROLE__` 的模板：第一遍编模板、量出资源偏移；
第二遍必须把**回填后的 Lua 写回编译工作区**再编。之前只把回填结果写到了
`.work/overlay/...`（给人看的副本），编译工作区里还是模板 → 交付物里的 Lua 带着占位符，
表盘在设备上会直接"负载表为空"。现在第二遍前会 `write_lua(resolved)`。

## 已知边界 / 没做的部分

1. **真机未验证 S5 eSIM 的 `/dev/health` 可写**：同源平台的 S4 eSIM 上 dd 读写流程实测通过，
   S5 eSIM 上只能先靠只读的「环境预检查」确认可读 + 偏移对版。整条 119 条的写入路径在本机
   **无法**端到端验证（没有设备），本机只验证了字节、长度、偏移、头、镜像完整性。
2. **偏移锁固件版本**：换固件必须重跑 `s5e_anim.py all` → 4 步流水线。用错版本时表盘会判
   「版本不符」并跳过 `/dev/health` **剩余**记录（`job.skipRest`），不会把字节写进别人的文件里。
3. **开头 8 帧与结尾 14 帧的画质**：开头 8 帧只有 4~24 色（它们是"一个小点"，槽位预算
   4.5~17.5 KB）；结尾 14 帧被预算逼到 32~192 色 + 0.70~0.90 缩放。这是等长覆盖的硬约束
   （464×464 的 I8 图光全黑背景就要 ~3.7 KB），不是编码 bug；要更大就得上「非等长写」，
   那会动 inode 表和后面所有文件的偏移（本项目刻意不做）。
4. **`Compiler.exe` 的设备表里没有 480 档**：圆表且预览 326×326 的只有 362 / 462，
   所以用 `DeviceType=462` + 326×326 预览图。预览只是表盘列表里的缩略图，
   实际画面尺寸由 `main.lua` 与 `.fprj` 的 480 决定。
5. **负载文件必须原样连续放在 resource.bin 里**，偏移才等于 `文件基址 + 魔数长度 + 相对偏移`；
   `s5e_build.py` 会逐条用生成时的 sha256 校验，并做两遍 0 漂移检查。魔数长度是 **15 B**
   （`S5P-PAYv1`），曾经写成 16 导致全部偏移差 1。
6. **分区键名 ≠ 节点路径**：Lua 表里存 `'health'`，运行期由 `DEVS['health']` 取到 `/dev/health`。
   把 `/dev/health` 直接存进表里，拼出来就是 `if=nil`。`s5e_verify.py` / `s5e_lua_static.py`
   都专门检查这一条。
7. **没动的**：inode 表、目录项、superblock、任何非 `pressure/measure/Measuring*.bin` 的文件；
   仓库里其它项目（`s4e-*`、`s5e-icons`、`s5e-charge`）与 git（未 commit、未改 `.gitignore`）。

## 第三方与风险

* 本仓库不含固件、OTA 包、字体；`.face` 由第三方 `Compiler.exe` 编译
* 往分区节点写数据是危险操作：写错偏移可能损坏资源分区。表盘自带版本校验与还原盘，
  但请自行确认设备所有权并承担后果
* 官方 OTA 升级会整分区覆盖，动画会回到原厂（等于自动还原）

## 目录

```
main.lua                 表盘源码（含 __UIIMG__ / __PAY__ / __RB__ / __ROLE__ 占位符，构建时回填）
tools/                   全部脚本（见下表）
ui_images/               界面素材（LVGL v9 .bin，8 张，480 档尺寸）
assets/                  设计素材 PNG（Mdi 图标、返回箭头、QQ、封面）
dist/                    交付的 .face
docs/                    界面预览 + selfcheck_run.txt / selfcheck_report.txt
inputs/                  固件分区镜像 + 字体（不进仓库，见上）
vendor/                  LuaDevTemplate-main（含 Compiler.exe，不进仓库）
.work/                   构建工作区（anim/ 改后镜像、overlay/、build/；可删）
payload/ payload_restore/     逐条目负载 + payload.lua（人肉 dd 用）
blob_replace/ blob_restore/   魔数 + 顺序拼接的 payload.bin / fp.bin / offsets.json
```

| 脚本 | 作用 |
|---|---|
| `tools/paths.py` | 所有路径的唯一入口（本项目事实：id / 480 / 464 / 119 都在这） |
| `tools/romfs.py` | ROMFS 分区解析（只读） |
| `tools/lvgl_bin.py` | LVGL v9 RLE 编解码 + `pad_rle_safe` |
| `tools/iconpack.py` | ARGB8888 / I8 图片编码（界面素材用） |
| `tools/lua_balance.py` | Lua 块配平（被 `s5e_lua_static.py` 调用） |
| `tools/s5e_anim.py` | **核心**：100 帧 → 119 个等长槽位 + 改后整分区镜像 + `manifest.json`（含三条就地自证） |
| `tools/s5e_payload.py` | 按角色切负载 + 指纹表 + `blob_*/`（含逐条 sha256） |
| `tools/s5e_overlay.py` | 生成可编译的 overlay（config / fprj / 预览图 / 资源） |
| `tools/s5e_build.py` | **两遍构建 + 裸编忠实产物（b5=0）+ 0 漂移校验** → `dist/*.face` |
| `tools/s5e_verify.py` | 逐盘校验（38 项）：头 / Lua / 偏移 / 逐条负载 / 指纹 / 镜像 / UI / 体积 |
| `tools/s5e_verify_indep.py` | 独立总校验（70 项）：不读构建中间产物的那一路 + 两张盘互证 |
| `tools/s5e_lua_static.py` | `main.lua` 静态体检（含 S4e 踩过的「先调用后声明」坑） |
| `tools/s5e_pages.py` | 480×480 页面规格（唯一的设计稿来源） |
| `tools/s5e_render_ui.py` | 用真 MiSans 渲染 7 页预览（会报标签溢框） |
| `tools/s5e_check_clip.py` | 用真实渲染像素判圆屏是否切边 |
| `tools/s5e_ui_images.py` | 设计素材 PNG → `ui_images/*.bin` + 圆形 logo |
