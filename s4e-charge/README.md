# S4Chg —— 把 S5 41mm(q63) 的充电动画搬到 S4 eSIM

**当前阶段：全量版已交付（57 帧全换）** —— 轻量测试（5 帧）已在真机确认生效：**`/dev/system` 可写 + 动画确实取自这 57 帧**。

## 改了什么

| | |
|---|---|
| 目标 | `inputs/target/vela_system.bin`（S4 eSIM `/dev/system`）→ `charging/charge0..56.bin`（57 帧 464×464 I8 RLE） |
| 源 | `inputs/source/vela_system.bin`（q63 S5 41mm）→ `charging/charge0..60.bin`（61 帧） |
| 映射 | 第 n 帧 ← q63 第 `round(n/56*60)` 帧（时间轴按比例映射） |
| 本次 | **57/57 全换**，**每帧都是 256 色**（槽位 79~119 KB 很宽裕；背景压平后 RLE 完全放得下） |
| 校验 | 57/57 回解逐像素一致、usize 长度一致、inode 表逐位不变、superblock 不变、回放一致 |

## 交付物

| 文件 | 说明 |
|---|---|
| `dist/S4Chg.face` | **替换盘**：6,422,844 B（6.1 MB），id `362150103`，b5=0，sha256 `687f600df38597e8…` |
| `dist/S4ChgRestore.face` | **还原盘**：同 id，sha256 `a243fb4734913280…`（装上即还原，也用来顶掉替换盘） |
| `docs/full_before_after.png` | 全量对照图（原厂 vs q63，采样 10 帧） |
| `docs/full_preview.mp4` | 换后整段 57 帧预览 |
| `docs/sample_before_after.png` / `sample_preview.mp4` | 轻量测试阶段（5 帧）的留档 |

## 真机怎么做

1. 装 `dist/S4Chg.face`（同 id 会自动顶掉测试盘）
2. 表盘「环境预检查」→「开始替换」→ 等 `失败 0`（57 条，约 6 MB；失败会打印 `> 失败 #N off=0x… len=… 首差@i 得AA期BB`）
3. 「重启手表」→ 插上充电器看整段动画
4. 还原：装 `dist/S4ChgRestore.face` →「开始还原」→ 重启

## 重建

```powershell
python tools/make_charge_payload.py all    # 全量 57 帧（不加 all = 只改 5 帧的轻量测试）
python tools/make_dd_payload.py replace    # 负载 + 指纹 + blob_replace/
python tools/gen_ui_lua.py replace         # 两遍构建 -> dist/S4Chg.face（0 漂移校验）
python tools/verify_anim.py replace        # 独立校验（只看交付物 + 原厂镜像）
python tools/make_dd_payload.py restore
python tools/gen_ui_lua.py restore         # -> dist/S4ChgRestore.face
python tools/verify_anim.py restore
```

`inputs/`（固件分区镜像）与 `vendor/`（LuaDevTemplate，含 Compiler.exe）不进仓库；`payload*/`、`blob_*/`、`.work/` 是可再生产物。

## 备注

- 本盘写的是 **`/dev/system`**（系统资源分区）：轻量测试证明它可 dd 写入，这是本轮最重要的发现 —— 以后 `system/drain/*`（排水）、`ota/anim*`（升级动画）、`setupwizard/*`（配对引导）都能用同一套办法改。
- ROMFS 的数据偏移是**结构性**的（`data_off = inode + 16 + align16(名字长度+1)`），所以只能逐帧等长覆盖，不能把数据指到别处、也不能跨分区。

# 编码 v2（2026-10-02）：画质问题的根因与修法

真机反馈「有点糊」。诊断后发现是**编码器**的问题，不是素材上限：

| | 旧方案 | 新方案 |
|---|---|---|
| 做法 | 整帧重新量化（MEDIANCUT 256 色）+ 把暗于 46 的像素压成纯黑 | **沿用 q63 原帧的调色板与索引**，只把接近黑的暗区归到一个索引，阈值按每帧预算取最小值（实测 4~40） |
| 圆环 | 亮部面积小，MEDIANCUT 按像素数分配颜色 → 圆环分不到颜色；阈值 46 还把环上的暗段啃成黑色缺口 | **逐像素与原帧完全一致** |
| 整帧 PSNR（57 帧） | 25.1 dB（最差 24.0） | **33.4 dB（最差 25.2）** |
| 接近黑区域均差 | 8.56 | 6.46 |

对照图见 docs/quality_v1_vs_v2.png（整帧 / 局部 2× / 与 q63 原帧的差异 ×4）。

**天花板在哪**：圆环已经到顶（逐像素一致，除非改尺寸或格式）；雾面暗区受**槽位字节预算**限制 —— q63 原帧是 135~201 KB/帧，S4e 槽位只有 79~119 KB，而暗区是噪点雾面、最吃 RLE。要连暗区也几乎无损，需要把 57 个槽位当总池重新分配，但总池 5.7 MB < 源 10.6 MB，仍然要取舍。

| 盘 | v2 体积 / sha256 | 校验 |
|---|---|---|
| dist/S4Chg.face | 6,422,844 B / 66640d3a869bbc29… | 11/11 通过 + 自检 57/57 |
| dist/S4ChgRestore.face | 6,422,844 B / 9652747f3c79402f… | 11/11 通过 |

**若之前装过 v1 全量版**（sha 687f600d…）：设备上是旧编码的帧，新盘替换时会提示「版本不符」（指纹表记的是**原厂**字节），但**它会照写**（版本不符只提示不阻止），写完重启即为 v2 画质。
