--[[----------------------------------------------------------------------------
  S5Chg —— S5 41mm(q63) 充电动画 -> S5 eSIM 46mm(p62lte)

  写入目标：/dev/system（ROMFS，卷名 system）里的 charging/charge0..60.bin
    61 帧、480x480、I8 + RLE（cf=0x0a, flags=0x08），每帧槽位长度各不相同
    （143,832 ~ 213,511 B）—— 负载**逐字节等长**，所以 inode 表与后面所有文件的
    绝对偏移一个字节都不动。

  界面按 480x480 设计稿落地（tools/pages.py，本机用真 MiSans 渲染 + 真实像素判
  圆屏切边，17 个页面含 replace/restore 两套文案：0 越界、0 折行）。

  两份盘共用同一个 watchface id 462150103：
    S5Chg.face        只装"替换后"的 61 帧 + 原厂 64B 指纹
    S5ChgRestore.face 只装"原厂"的 61 帧 + 替换后 64B 指纹
  装其中一份就顶掉另一份，设备上始终只占一份空间。

  真机已验证的底层能力（沿用 S5->S4 那个表盘）:
    * 宿主不调用 ui.init -> 加载期建界面
    * SCRIPT_PATH 为空 -> 用 debug.getinfo 反推目录
    * .face 不解包，资源仍在 resource.bin 里 -> 按偏移读出来用
    * /dev/system 可写，dd 读写校验通过
    * 没有 utf8 标准库 -> 自带按位 UTF-8 解码（本文件未用到，留作提醒）
------------------------------------------------------------------------------]]

local lvgl = require("lvgl")

local W, H = 480, 480
local DEV, BLK = "/dev/system", 4
local TMPH = "/tmp/s5c_head.bin"        -- 版本校验读出的前 64 字节
local TMPR = "/tmp/s5c_back.bin"        -- 写完之后回读出来的那一份
local TMPB = "/tmp/s5c_blob.bin"        -- 待写入的负载（从 resource.bin 抠出来）

-- 等长覆盖只保证「偏移」512 对齐；RLE 素材的长度常常不是 4 的倍数，
-- 那种记录必须退化成 bs=1（偏移本身对齐，所以 bs=1 也精确），否则会多写相邻文件的字节。
local function ddBlk(off, len)
  if off % BLK == 0 and len % BLK == 0 then return BLK end
  return 1
end

--------------------------------------------------------------------- 自身目录
local SRC = ""
if debug and debug.getinfo then
  local info = debug.getinfo(1, "S")
  SRC = (info and info.source) or ""
end
if type(SRC) ~= "string" then SRC = "" end
if SRC:sub(1, 1) == "@" then SRC = SRC:sub(2) end
SRC = SRC:gsub("\\", "/")
local THIS_DIR = SRC:match("^(.*)/[^/]+$") or ""
local SP = THIS_DIR ~= "" and (THIS_DIR .. "/") or ""
local PARENT = SP:gsub("[^/]+/$", "")

local RES = nil
do
  local c = { PARENT .. "resource.bin", SP .. "../resource.bin", SP .. "resource.bin" }
  for i = 1, #c do
    local f = io.open(c[i], "rb")
    if f then f:close(); RES = c[i]; break end
  end
end

--------------------------------------------------------------------- 资源偏移
-- UI 图片 { resource.bin 内偏移, 长度, 名字 } —— 由 tools/gen_ui_lua.py 回填
local UIIMG = {
__UIIMG__
}

-- 角色：'replace' = 只负责替换（写 q63 的帧）；'restore' = 只负责还原（写回原厂字节）
-- 两份盘共用同一个 watchface id，所以设备上只会占一份空间（见 README）
local ROLE = '__ROLE__'

-- 负载表 { resource 内偏移, /dev/system 内偏移, 长度 } —— 由脚本回填
--   pay = 本盘要写进去的字节；rb = **另一侧字节前 64 B 的指纹**（只给版本校验用）
local PAYTBL = {
__PAY__
__RB__
}

local function prepImages()
  local paths = {}
  if not RES then return paths end
  local f = io.open(RES, "rb")
  if not f then return paths end
  for i = 1, #UIIMG do
    local e = UIIMG[i]
    f:seek("set", e[1])
    local d = f:read(e[2])
    if d and #d == e[2] then
      -- 直接写到 /tmp 根下：不能写子目录（目录不存在，且这台机器的 Lua 没有 mkdir）
      local p = "/tmp/s5c_ui_" .. e[3] .. ".bin"
      local o = io.open(p, "wb")
      if o then o:write(d); o:close(); paths[e[3]] = p end
    end
  end
  f:close()
  return paths
end

local IMG = prepImages()

--------------------------------------------------------------------- 颜色与字体
local C_GRAY, C_WHITE = '#999999', '#ffffff'
local C_OK, C_ERR = '#43cf7c', '#d43030'
local C_PLATE, C_CIRC = 0x002927, 0x4f4f4f

local function getFont(name, size)
  local f = nil
  pcall(function() f = lvgl.Font(name, size) end)
  return f
end

local F_CLOCK = getFont('MiSans-Semibold', 29)
local F_TITLE = getFont('MiSans-Medium', 31)
local F_ITEM  = getFont('MiSans-Medium', 29)
local F_BODY  = getFont('MiSans-Medium', 25)
local F_VER   = getFont('MiSans-Medium', 21)

--------------------------------------------------------------------- 按下高亮
-- onPressed / onClicked 是真实的 LVGL 对象方法（就在 onevent 旁边，属性表里可查）
local HL = 0x005149              -- 按下高亮色（比底板 0x002927 明显亮）
local pressed = nil              -- { obj = , t = }
local tickCount = 0

local function setBg(obj, c)
  pcall(function() obj:set { bg_color = c } end)
end

local function pressRelease()
  if pressed then
    setBg(pressed.obj, C_PLATE)
    pressed = nil
  end
end

--------------------------------------------------------------------- 基础
local ui = {}
local built = false
local pages = {}
local clocks = {}
local job = { run = false, list = nil, i = 0, ok = 0, errs = 0, vers = 0,
              skipRest = false, variant = 'replace' }
-- 从哪个入口进"开始替换"确认页，确认按钮就执行对应操作：
--   首页「开始替换」 -> 'replace'
--   帮助页「回滚修改」 -> 'tip'（拆盘后本盘没有回滚数据，只提示装另一份盘）
local pendingVariant = 'replace'
-- 确认页是从哪进来的，返回就回哪：
--   首页「开始替换」 -> 'home' ; 帮助页「回滚修改」 -> 'help'
local confirmFrom = 'home'

local function newPage()
  local p = nil
  pcall(function()
    p = lvgl.Object(nil, { x = 0, y = 0, w = W, h = H, bg_color = 0x000000,
                           bg_opa = 255, border_width = 0, pad_all = 0 })
    p:clear_flag(lvgl.FLAG.SCROLLABLE)
    p:add_flag(lvgl.FLAG.EVENT_BUBBLE)
  end)
  return p
end

local function show(p)
  if not p then return end
  pressRelease()                 -- 切页时清掉可能残留的高亮
  for k, v in pairs(pages) do
    pcall(function() v:add_flag(lvgl.FLAG.HIDDEN) end)
  end
  pcall(function() p:clear_flag(lvgl.FLAG.HIDDEN) end)
end

local function bind(obj, fn)
  if not obj then return end
  -- 成品样本用的是 onevent(lvgl.EVENT.SHORT_CLICKED, fn)（CLICKED 这个常量
  -- 在这台机器上不存在），所以按 SHORT_CLICKED -> onClicked -> CLICKED 依次试
  local ev = lvgl.EVENT
  if ev and ev.SHORT_CLICKED then
    if pcall(function() obj:onevent(ev.SHORT_CLICKED, function() fn() end) end) then return end
  end
  if pcall(function() obj:onClicked(function() fn() end) end) then return end
  pcall(function() obj:onevent(ev and ev.CLICKED, fn) end)
end

--------------------------------------------------------------------- 点按
-- 点按 = 按下高亮 + 抬起恢复 + 执行动作；带超时兜底（手指滑出时 click 不触发）
local function bindTap(obj, onTap)
  if not obj then return end
  local ok = pcall(function()
    obj:onPressed(function()
      setBg(obj, HL)
      pressed = { obj = obj, t = tickCount }
    end)
    obj:onClicked(function()
      pressRelease()
      if onTap then onTap() end
    end)
  end)
  if not ok then bind(obj, onTap) end
end

local function setClickable(o)
  if not o then return end
  pcall(function() o:add_flag(lvgl.FLAG.CLICKABLE) end)
end

local function lab(parent, o)
  o.text_font = o.text_font or F_BODY
  local l = nil
  pcall(function() l = parent:Label(o) end)
  return l
end

-- 时钟：居中不用 text_align（它要的是 lv_text_align_t，传 ALIGN.CENTER 越界会被忽略
-- -> 实测变成左对齐）。改为按真字体量出的宽度手工算 x：'10:24' 29px 量得 78
local function clockLabel(parent)
  local l = lab(parent, { x = 201, y = 4, w = 78, h = 46, text = '--:--',
                          text_color = C_GRAY, font_size = 29, text_font = F_CLOCK })
  clocks[#clocks + 1] = l
  return l
end

-- 标题：框 y=36 h=46，字号 31 行高 42 -> 从框顶画即可（LVGL 标签从框顶起排）
local function pageTitle(parent, text, x, w)
  return lab(parent, { x = x, y = 36, w = w, h = 46, text = text,
                       text_color = C_WHITE, font_size = 31, text_font = F_TITLE })
end

local function backArrow(parent, x, onTap)
  local im = nil
  if IMG.back then
    pcall(function() im = parent:Image { src = IMG.back, x = x or 167, y = 44 } end)
    setClickable(im)
    bind(im, onTap)
  end
  return im
end

-- 列表项：底板(整块可点) + 圆形遮罩 + 图标 + 标题
-- pad_all=0 是关键：LVGL 主题会给 Object 加内边距，不清零的话子元素会整体右下偏移
local function listItem(parent, y, iconkey, title, onTap)
  local plate = nil
  pcall(function()
    plate = parent:Object { x = 50, y = y, w = 379, h = 91, pad_all = 0,
                            bg_color = C_PLATE, border_width = 0, radius = 35 }
  end)
  if plate then
    if onTap then
      setClickable(plate)
      bindTap(plate, onTap)
    end
    pcall(function()
      plate:Object { x = 21, y = 20, w = 52, h = 52,
                     bg_color = C_CIRC, border_width = 0, radius = 26 }
    end)
    if IMG[iconkey] then
      pcall(function() plate:Image { src = IMG[iconkey], x = 31, y = 30 } end)
    end
    -- 标题 29px 行高 40，框高 40 -> 从框顶画就是垂直居中
    lab(plate, { x = 82, y = 26, w = 214, h = 40, text = title,
                 text_color = C_WHITE, font_size = 29, text_font = F_ITEM })
  end
  return plate
end

-- 大按钮 258x82 圆角 41：圆角把四角收进圆内（本机像素判据实测 0 越界）
local function bigButton(parent, y, text)
  local b = nil
  pcall(function()
    b = parent:Object { x = 111, y = y, w = 258, h = 82, pad_all = 0,
                        bg_color = C_PLATE, border_width = 0, radius = 41 }
  end)
  if b then setClickable(b) end
  -- 按钮文字：框 (71,22,126,40) 相对底板；'确认替换'/'重启手表' 29px 量得 116
  -- -> 居中 x = 111 + (258-116)/2 - 111 = 71
  lab(b, { x = 71, y = 22, w = 126, h = 40, text = text,
           text_color = C_WHITE, font_size = 29, text_font = F_ITEM })
  return b
end

local function clockTick()
  local t = '--:--'
  if os and type(os.date) == "function" then
    local ok, s = pcall(os.date, "%H:%M")
    if ok and type(s) == "string" then t = s end
  end
  for i = 1, #clocks do
    pcall(function() clocks[i]:set { text = t } end)
  end
end

--------------------------------------------------------------------- 外壳
local function slurp(p, n)
  local f = io.open(p, "rb")
  if not f then return nil end
  local d = f:read(n or "*a")
  f:close()
  return d
end

local function sh(cmd)
  if type(os.execute) ~= "function" then return -1 end
  local a, b, c = os.execute(cmd)
  if type(a) == "number" then return a end
  if a == true then return 0 end
  if type(c) == "number" then return c end
  if type(b) == "number" then return b end
  return -1
end

-- 从 resource.bin 里取一段（负载 / 另一侧指纹）
local function slice(off, len)
  if not RES then return nil end
  local f = io.open(RES, "rb")
  if not f then return nil end
  f:seek("set", off)
  local d = f:read(len)
  f:close()
  return d
end

-- 读设备上某偏移处的 len 字节（只读）。偏移 512 对齐时用分段大块，快两个数量级。
local BIG = 512

local function segs(off, len)
  local out = {}
  if off % BIG == 0 then
    local head = len - (len % BIG)
    if head > 0 then out[#out + 1] = { BIG, 0, head } end
    local rest = len - head
    local t4 = rest - (rest % 4)
    if t4 > 0 then out[#out + 1] = { 4, head, t4 } end
    if rest - t4 > 0 then out[#out + 1] = { 1, head + t4, rest - t4 } end
  else
    out[1] = { 1, 0, len }
  end
  return out
end

local function ddRead(off, len)
  local parts = {}
  for _, s in ipairs(segs(off, len)) do
    local b, rel, n = s[1], s[2], s[3]
    if os.remove then pcall(os.remove, TMPR) end
    sh(string.format("dd if=%s of=%s bs=%d skip=%d count=%d",
                     DEV, TMPR, b, (off + rel) // b, n // b))
    local d = slurp(TMPR, n)
    if not d or #d ~= n then return nil end
    parts[#parts + 1] = d
  end
  return table.concat(parts)
end

local function ddWrite(off, len, data)
  for _, s in ipairs(segs(off, len)) do
    local b, rel, n = s[1], s[2], s[3]
    -- 每段单独一个临时文件：这样 dd 只需要 seek（输出偏移），不依赖输入侧的 skip
    local o = io.open(TMPB, "wb")
    if not o then return false end
    o:write(data:sub(rel + 1, rel + n))
    o:close()
    sh(string.format("dd if=%s of=%s bs=%d seek=%d count=%d",
                     TMPB, DEV, b, (off + rel) // b, n // b))
  end
  return true
end

--------------------------------------------------------------------- 预检查
local desc1 = nil

local function setDesc1(txt, color)
  if not desc1 then return end
  pcall(function() desc1:set { text = txt, text_color = color } end)
end

local function doCheck()
  if not RES then
    setDesc1('找不到 resource.bin，无法操作。', C_ERR)
    return false
  end
  local list = PAYTBL.pay or {}
  if #list == 0 then
    setDesc1('预检查失败：负载表为空。', C_ERR)
    return false
  end
  local h = ddRead(0, 48)
  if not h or #h < 48 then
    setDesc1('预检查失败：/dev/system 读不到。', C_ERR)
    return false
  end
  if h:sub(1, 8) ~= "-rom1fs-" then
    setDesc1('预检查失败：设备节点不可读\n或分区头不是 ROMFS。', C_ERR)
    return false
  end
  local z = h:find("\0", 17, true)
  local vol = h:sub(17, (z or 33) - 1)
  if vol ~= "system" then
    setDesc1('预检查失败：卷名是 ' .. vol .. '。', C_ERR)
    return false
  end
  -- superblock 的 size 是**大端**（romfs 规范：__be32），所以这里必须用 ">I4"。
  -- （S4e 那版写成 "<I4"，读出来是个天文数字 -> 越界判断形同虚设；这里修正。）
  local size = string.unpack(">I4", h, 9)
  local bad, total = 0, 0
  for i = 1, #list do
    local r = list[i]
    local b = ddBlk(r[2], r[3])
    if (r[2] % b) ~= 0 or (r[3] % b) ~= 0 then bad = bad + 1 end
    if (r[2] + r[3]) > size then bad = bad + 1 end
    total = total + r[3]
  end
  if bad > 0 then
    setDesc1(string.format('预检查失败：%d 项越界或未对齐。', bad), C_ERR)
    return false
  end
  -- 顺带确认 resource.bin 第一条能读出来
  local probe = slice(list[1][1], list[1][3])
  if not probe or #probe ~= list[1][3] then
    setDesc1('预检查失败：resource.bin 读取异常。', C_ERR)
    return false
  end
  -- 抽样版本校验（只读）：首 / 中 / 尾三条，比对设备上真实的 64 字节与本盘的
  -- 「要写进去的字节」或「另一侧指纹」—— 能确认负载偏移就是给这一版固件算的。
  local marks = { 1, math.max(1, #list // 2), #list }
  local samp, okAll = {}, true
  for i = 1, #marks do
    local k = marks[i]
    local rec, oth = list[k], (PAYTBL.rb or {})[k]
    local got = ddRead(rec[2], 64)
    local mine = slice(rec[1], 64)
    local other = oth and slice(oth[1], 64) or nil
    if not got or #got < 64 then
      samp[#samp + 1] = '×'
      okAll = false
    elseif mine and got == mine then
      samp[#samp + 1] = '已替换✓'
    elseif other and got == other then
      samp[#samp + 1] = '原厂✓'
    else
      samp[#samp + 1] = '抽样×'
      okAll = false
    end
  end
  local head = string.format('预检查通过 | %d 条 | %.2fMB', #list, total / 1048576)
  setDesc1(head .. '\n/dev/system ' .. table.concat(samp, ' '), okAll and C_OK or C_ERR)
  return okAll
end

--------------------------------------------------------------------- 替换 / 还原
local logLabel = nil
local rebootBtn = nil
local runningTitle = nil
local logLines = {}

local function logOut(s)
  logLines[#logLines + 1] = s
  -- 日志框 h=277、行高 35 -> 最多显示 7 行；留 7 行保证最后一行完整可见
  while #logLines > 7 do table.remove(logLines, 1) end
  if logLabel then
    pcall(function() logLabel:set { text = table.concat(logLines, "\n") } end)
  end
end

local function showReboot()
  if rebootBtn then pcall(function() rebootBtn:clear_flag(lvgl.FLAG.HIDDEN) end) end
end

-- 一条记录三步：① 版本校验（设备上那段必须等于「原厂」或「替换后」的前 64 B）
--             ② 写入  ③ 整段回读比对
-- 版本两边都不是 -> 'ver'，并且**跳过 /dev/system 剩余记录**（换固件后最安全的行为：
-- 绝不把字节写进别人的文件里）。os.execute 的返回值在这台机器上不可靠，所以判据
-- 一律是内容比对。
local function writeOne(rec, want)
  local data = slice(rec[1], rec[3])
  if not data or #data ~= rec[3] then return 'err' end
  local n = 64
  if want then
    if want[3] < n then n = want[3] end
    local other = slice(want[1], n)
    local cur = ddRead(rec[2], n)
    if not cur or #cur ~= n or not other or #other ~= n then return 'err' end
    if cur ~= data:sub(1, n) and cur ~= other then return 'ver' end
  end
  local ok, lastBack = false, nil
  for attempt = 1, 3 do
    if not ddWrite(rec[2], rec[3], data) then return 'err' end
    sh("sync")
    lastBack = ddRead(rec[2], rec[3])
    if lastBack and #lastBack == rec[3] and lastBack == data then ok = true break end
    logOut(string.format('> 第 %d 条校验不过，重试 %d/3', job.i, attempt))
  end
  if not ok then
    -- 计划 B：常规「分段写」3 次不过时，改成整条一次 dd（bs=4 或 bs=1）。
    -- 有些驱动对「同一区域被拆成多次小写」比「一次大写」更敏感，换个写法常常就过了。
    local b = (rec[3] % 4 == 0) and 4 or 1
    local o = io.open(TMPB, "wb")
    if o then
      o:write(data)
      o:close()
      sh(string.format("dd if=%s of=%s bs=%d seek=%d count=%d",
                       TMPB, DEV, b, rec[2] // b, rec[3] // b))
      sh("sync")
      local back2 = ddRead(rec[2], rec[3])
      if back2 and #back2 == rec[3] and back2 == data then
        ok = true
        logOut(string.format('> 第 %d 条改用整条 bs=%d 写入后校验通过', job.i, b))
      end
    end
  end
  if not ok then
    -- 诊断：把「哪一条 / 目标偏移 / 长度 / 读回多少字节 / 第一个不同的字节」打出来
    local why = '读回 nil'
    if lastBack then
      if #lastBack ~= rec[3] then
        why = string.format('读回 %d 字节', #lastBack)
      else
        why = '内容全同?'
        for i = 1, #lastBack do
          if lastBack:byte(i) ~= data:byte(i) then
            why = string.format('首差@%d 得%02X 期%02X', i - 1, lastBack:byte(i), data:byte(i))
            break
          end
        end
      end
    end
    logOut(string.format('> 失败 #%d off=0x%X len=%d %s', job.i, rec[2], rec[3], why))
    return 'err'
  end
  return 'ok'
end

local function startJob(variant)
  if job.run then return end
  local list = PAYTBL.pay or {}
  if #list == 0 then
    setDesc1('负载表为空，已中止。', C_ERR)
    return
  end
  job.run, job.list, job.i, job.ok, job.errs, job.vers = true, list, 0, 0, 0, 0
  job.skipRest, job.variant = false, variant
  logLines = {}
  logOut('> 开始替换')
  logOut(string.format('> 61 帧充电动画 / 共 %d 条', #list))
  logOut('> 读取 resource.bin')
  if rebootBtn then pcall(function() rebootBtn:add_flag(lvgl.FLAG.HIDDEN) end) end
  show(pages.running)
end

local function tick()
  tickCount = tickCount + 1
  -- 兜底：按下超过 1.6s 没收到 click（手指滑出等）就恢复高亮
  if pressed and (tickCount - pressed.t) > 40 then pressRelease() end
  if not job.run or not job.list then return end
  job.i = job.i + 1
  local n = #job.list
  if job.i > n then
    job.run = false
    logOut('> 替换完毕，请重启手表。')
    logOut(string.format('> 共 %d 条，成功 %d 失败 %d', n, job.ok, job.errs))
    if job.vers > 0 then
      logOut(string.format('> 版本不符跳过 %d 条', job.vers))
      logOut('> 请勿重启，先装回匹配版本。')
    else
      logOut('> 若发现问题，请回滚修改。')
    end
    showReboot()
    return
  end
  if job.skipRest then
    job.vers = job.vers + 1
  else
    local rb = PAYTBL.rb and PAYTBL.rb[job.i]
    local r = writeOne(job.list[job.i], rb)
    if r == 'ver' then
      job.vers = job.vers + 1
      job.skipRest = true          -- 版本不符：跳过 /dev/system 剩余记录
      logOut('> /dev/system 版本不符，已跳过剩余记录')
    elseif r == 'ok' then
      job.ok = job.ok + 1
    else
      job.errs = job.errs + 1
    end
  end
  if job.i % 10 == 0 or job.i == n then
    logOut(string.format('> 写入 %d/%d  成功 %d 失败 %d', job.i, n, job.ok, job.errs))
  end
end

--------------------------------------------------------------------- 页面
local function buildHome()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  -- 盘内标题 = 显示名（不再用内部代号 S5Chg）；x 按真 MiSans 31px 量出的宽度居中：
  --   'S5e Pt.3' = 126 -> x = (480-126)/2 = 177
  --   'S5e Pt.3 · 还原' = 226 -> x = (480-226)/2 = 127
  if ROLE == 'restore' then
    pageTitle(p, 'S5e Pt.3 · 还原', 127, 228)
  else
    pageTitle(p, 'S5e Pt.3', 177, 128)
  end
  listItem(p, 88, 'ic_help', '快速帮助', function() show(pages.help) end)
  listItem(p, 186, 'ic_replace', ROLE == 'restore' and '开始还原' or '开始替换', function()
    pendingVariant = 'replace'
    confirmFrom = 'home'
    show(pages.confirm)
  end)
  listItem(p, 285, 'ic_about', '关于', function() show(pages.about) end)
  return p
end

local function buildHelp()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  backArrow(p, 167, function() show(pages.home) end)
  local t = pageTitle(p, '快速帮助', 188, 124)
  setClickable(t)
  bind(t, function() show(pages.home) end)

  listItem(p, 88, 'ic_check', '环境预检查', function() doCheck() end)
  desc1 = lab(p, { x = 60, y = 182, w = 372, h = 76,
                   text = '检查 /dev/system 分区与\n61 帧充电动画的完整性。',
                   text_color = C_GRAY, font_size = 25, text_font = F_BODY })

  -- 拆盘之后：本盘只装一份负载，「回滚/恢复」由另一份盘负责
  listItem(p, 264, 'ic_rollback', '回滚修改', function()
    if ROLE == 'restore' then
      setDesc1('本盘负责还原，换回动画\n请装 S5e Pt.3。', C_GRAY)
    else
      setDesc1('本盘只负责替换，请装\nS5e Pt.3 · 还原。', C_GRAY)
    end
  end)
  lab(p, { x = 60, y = 355, w = 372, h = 36,
           text = ROLE == 'restore' and '换回动画请装 S5e Pt.3。'
                  or '还原请装 S5e Pt.3 · 还原。',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  return p
end

local function buildConfirm()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  -- 确认页的返回：回到进来时的那个页面（首页 或 快速帮助）
  local function goBack() show(pages[confirmFrom] or pages.home) end
  backArrow(p, 167, goBack)
  local t = pageTitle(p, ROLE == 'restore' and '开始还原' or '开始替换', 188, 124)
  setClickable(t)
  bind(t, goBack)

  -- 多色文本**不能**用 recolor：AP 里那几处 recolor 是图片重着色(bg_img_recolor)
  -- 和表盘编辑器的主题重着色，不是文本属性；实测标记会被原样显示出来。
  -- 改为拆成多个标签 + 手工算 x（宽度用真 MiSans 25px 量出），框宽 ≥ 文本宽
  -- -> 保证不折行（折行会让手工算 x 的片段错位），并且整框都在圆内。
  lab(p, { x = 52, y = 93, w = 340, h = 36,
           text = '替换充电动画之前，请先确认',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  lab(p, { x = 52, y = 126, w = 380, h = 36,
           text = '自己的系统版本号为 3.112.035！',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  lab(p, { x = 52, y = 208, w = 280, h = 36, text = '请确认自己的手表型号为',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  lab(p, { x = 52, y = 241, w = 405, h = 36, text = 'Xiaomi Watch S5 eSIM 46mm ！',
           text_color = C_WHITE, font_size = 25, text_font = F_BODY })
  lab(p, { x = 52, y = 331, w = 330, h = 36, text = '搞机有风险，变砖后果自负。',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })

  local b = bigButton(p, 376, ROLE == 'restore' and '确认还原' or '确认替换')
  bindTap(b, function() startJob(pendingVariant) end)
  return p
end

local function buildAbout()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  backArrow(p, 198, function() show(pages.home) end)
  local t = pageTitle(p, '关于', 220, 62)
  setClickable(t)
  bind(t, function() show(pages.home) end)

  -- 信息卡：底板 + 圆形 logo + 大标题 + 版本号
  pcall(function()
    p:Object { x = 54, y = 81, w = 373, h = 210, pad_all = 0,
               bg_color = C_PLATE, border_width = 0, radius = 31 }
  end)
  if IMG.logo then
    pcall(function() p:Image { src = IMG.logo, x = 200, y = 111 } end)
  end
  -- 29px 量得：'S5e Pt.3' = 119 -> x = 54 + (373-119)/2 = 181
  --            'S5e Pt.3 · 还原' = 212 -> x = 54 + (373-212)/2 = 134.5 -> 134
  if ROLE == 'restore' then
    lab(p, { x = 134, y = 198, w = 214, h = 40, text = 'S5e Pt.3 · 还原',
             text_color = C_WHITE, font_size = 29, text_font = F_ITEM })
  else
    lab(p, { x = 181, y = 198, w = 121, h = 40, text = 'S5e Pt.3',
             text_color = C_WHITE, font_size = 29, text_font = F_ITEM })
  end
  -- '1.0.0' 21px 量得 49 -> 居中 x = 54 + (373-49)/2 = 216
  lab(p, { x = 216, y = 234, w = 49, h = 28, text = '1.0.0',
           text_color = C_GRAY, font_size = 21, text_font = F_VER })

  -- QQ 联系方式：结构与列表项一致（无动作，所以不给它绑点击）
  listItem(p, 300, 'ic_qq', '732681995', nil)
  return p
end

local function buildRunning()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  -- 本页没有返回图标（规格：顶栏同首页），所以标题要屏幕居中：
  -- '正在替换' 31px 量得 124 -> x = 240 - 124/2 = 178
  runningTitle = pageTitle(p, '正在替换', 178, 124)
  logLabel = lab(p, { x = 67, y = 93, w = 348, h = 277, text = '',
                      text_color = C_WHITE, font_size = 25, text_font = F_BODY })
  rebootBtn = bigButton(p, 376, '重启手表')
  -- 替换过程中不显示，替换完再显示
  if rebootBtn then pcall(function() rebootBtn:add_flag(lvgl.FLAG.HIDDEN) end) end
  bindTap(rebootBtn, function()
    logOut('> 正在重启…')
    sh("sync")
    sh("reboot")
  end)
  return p
end

--------------------------------------------------------------------- 组装
local function build()
  if built then return end
  built = true
  pages.home = buildHome()
  pages.help = buildHelp()
  pages.confirm = buildConfirm()
  pages.about = buildAbout()
  pages.running = buildRunning()
  if pages.home then show(pages.home) end
  clockTick()
  pcall(function()
    ui.timer = lvgl.Timer { period = 40, repeat_count = -1, cb = function() tick() end }
    if ui.timer and ui.timer.resume then ui.timer:resume() end
  end)
  pcall(function()
    ui.clockTimer = lvgl.Timer { period = 1000, repeat_count = -1,
                                 cb = function() clockTick() end }
    if ui.clockTimer and ui.clockTimer.resume then ui.clockTimer:resume() end
  end)
end

local okbuild, errbuild = pcall(build)
if not okbuild then
  pcall(function()
    local r = lvgl.Object(nil, { x = 0, y = 0, w = W, h = H, bg_color = 0x000000,
                                 bg_opa = 255, border_width = 0 })
    r:Label { x = 20, y = 20, w = W - 40, h = H - 40,
              text = 'BUILD FAILED:\n' .. tostring(errbuild),
              text_color = '#ffffff', font_size = 13, text_font = F_BODY }
  end)
end

ui.init = function()
  pcall(build)
  return ui.root
end

function pageOnPause()
  if ui.timer then pcall(function() ui.timer:pause() end) end
  if ui.clockTimer then pcall(function() ui.clockTimer:pause() end) end
end

function pageOnResume()
  if ui.timer then pcall(function() ui.timer:resume() end) end
  if ui.clockTimer then pcall(function() ui.clockTimer:resume() end) end
end

return ui
