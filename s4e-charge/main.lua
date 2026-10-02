--[[----------------------------------------------------------------------------
  S4Chg —— S5 41mm(OS4) 充电动画 -> S4 eSIM

  界面按 CSS 设计稿 1:1 落地（本机用真 MiSans 字体渲染预览验证过）:
    * 页面底色纯黑（取自封面图四角）
    * rgba(255,255,255,0.6) -> #999999（白 60% 叠黑）
    * font-weight 600 -> MiSans-Semibold ; 500 -> MiSans-Medium
    * vertical-align:middle -> 手工算 y（LVGL 标签没有垂直居中样式）
    * 多色文本用 LVGL recolor："灰#ffffff 白#灰"
    * 圆屏安全区：实测所有页面 0 像素越界（大按钮全靠 40px 圆角收进圆内）

  真机已验证的底层能力:
    * 宿主不调用 ui.init -> 加载期建界面
    * SCRIPT_PATH 为空 -> 用 debug.getinfo 反推目录
    * .face 不解包，资源仍在 resource.bin 里 -> 按偏移读出来用
    * /dev/system 可写，dd 读写校验通过
    * 没有 utf8 标准库 -> 自带按位 UTF-8 解码（本文件未用到，留作提醒）
------------------------------------------------------------------------------]]

local lvgl = require("lvgl")

local W, H = 466, 466
local DEV, BLK = "/dev/system", 4
local TMPH = "/tmp/os4_head.bin"
local TMPR = "/tmp/os4_back.bin"

-- 等长覆盖只保证「偏移」512 对齐；RLE 素材的长度常常不是 4 的倍数（如 1635 / 3047），
-- 那种记录必须退化成 bs=1（偏移本身对齐，所以 bs=1 也精确），否则会多写相邻文件的字节。
local function ddBlk(off, len)
  if off % BLK == 0 and len % BLK == 0 then return BLK end
  return 1
end
local TMPB = "/tmp/os4_blob.bin"


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
-- UI 图片 { resource.bin 内偏移, 长度, 名字 }  —— 由 _tools/gen_ui_lua.py 回填
local UIIMG = {
__UIIMG__
}

-- 角色：'replace' = 只负责替换（写 q63 的帧）；'restore' = 只负责还原（写回原厂字节）
-- 两份盘共用同一个 watchface id，所以设备上只会占一份空间（见 README）
local ROLE = '__ROLE__'

-- 负载表 { resource 内偏移, ROMFS 目标偏移, 长度 } —— 由脚本回填
--   pay = 本盘要写进去的字节；rb = **另一侧字节的 64 B 指纹**（只给版本校验用）
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
      local p = "/tmp/ui_" .. e[3] .. ".bin"
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

local F_CLOCK = getFont('MiSans-Semibold', 28)
local F_TITLE = getFont('MiSans-Medium', 30)
local F_ITEM  = getFont('MiSans-Medium', 28)
local F_BODY  = getFont('MiSans-Medium', 24)
local F_VER   = getFont('MiSans-Medium', 20)

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
local job = { run = false, list = nil, i = 0, errs = 0, variant = 'replace' }
-- 从哪个入口进"开始替换"确认页，确认按钮就执行对应操作：
--   首页「开始替换」 -> 'replace'
--   帮助页「回滚修改」 -> 'rollback'（也要先过一遍警告确认，不直接开跑）
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

local function clockLabel(parent)
  -- 居中不用 text_align（它要的是 lv_text_align_t：LEFT=0/CENTER=1/RIGHT=2，
  -- 传 ALIGN.CENTER=9 越界会被忽略 -> 实测变成左对齐）。
  -- 改为按真字体量出的文本宽度手工算 x，并把 w 收紧，这样对齐方式就不影响结果。
  local l = lab(parent, { x = 195, y = 3, w = 86, h = 45, text = '--:--',
                          text_color = C_GRAY, font_size = 28, text_font = F_CLOCK })
  clocks[#clocks + 1] = l
  return l
end

local function pageTitle(parent, text, x, w)
  -- 标题 y：框 y=34 h=45，字号 30 行高约 41 -> 34 + (45-41)/2 = 36
  return lab(parent, { x = x, y = 36, w = w, h = 45, text = text,
                       text_color = C_WHITE, font_size = 30, text_font = F_TITLE })
end

local function backArrow(parent, x, onTap)
  local im = nil
  if IMG.back then
    pcall(function() im = parent:Image { src = IMG.back, x = x or 160, y = 43 } end)
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
    plate = parent:Object { x = 49, y = y, w = 368, h = 88, pad_all = 0,
                            bg_color = C_PLATE, border_width = 0, radius = 34 }
  end)
  if plate then
    if onTap then
      setClickable(plate)
      bindTap(plate, onTap)
    end
    pcall(function()
      plate:Object { x = 20, y = 19, w = 50, h = 50,
                     bg_color = C_CIRC, border_width = 0, radius = 25 }
    end)
    if IMG[iconkey] then
      pcall(function() plate:Image { src = IMG[iconkey], x = 30, y = 29 } end)
    end
    -- 标题框 h=54，字号 28 行高约 38 -> 垂直居中 y = 17 + 8 = 25（左对齐，不用 text_align）
    lab(plate, { x = 80, y = 25, w = 208, h = 54, text = title,
                 text_color = C_WHITE, font_size = 28, text_font = F_ITEM })
  end
  return plate
end

local function bigButton(parent, text)
  local b = nil
  pcall(function()
    b = parent:Object { x = 108, y = 365, w = 250, h = 80, pad_all = 0,
                        bg_color = C_PLATE, border_width = 0, radius = 40 }
  end)
  if b then setClickable(b) end
  -- 按钮文字：框 (65,13,120,54) 相对底板；字号 28 行高约 38 -> y = 13 + 8 = 21
  -- "确认替换"/"重启手表" 量得 112px -> 居中 x = 65 + (120-112)/2 = 69
  lab(b, { x = 69, y = 21, w = 122, h = 54, text = text,
           text_color = C_WHITE, font_size = 28, text_font = F_ITEM })
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
  if sh("dd if=" .. DEV .. " of=/tmp/os4_hdr.bin bs=1 count=48") ~= 0 then
    setDesc1('读取分区失败（dd 不可用或无权限）。', C_ERR)
    return false
  end
  local h = slurp("/tmp/os4_hdr.bin", 48)
  if not h or #h < 48 then
    setDesc1('读不到分区头。', C_ERR)
    return false
  end
  if h:sub(1, 8) ~= "-rom1fs-" then
    setDesc1('预检查失败：分区头不是 ROMFS。', C_ERR)
    return false
  end
  local z = h:find("\0", 17, true)
  local vol = h:sub(17, (z or 33) - 1)
  if vol ~= "system" then
    setDesc1('预检查失败：卷名是 ' .. vol .. '。', C_ERR)
    return false
  end
  local size = string.unpack("<I4", h, 9)
  local list = PAYTBL.pay or {}
  if #list == 0 then
    setDesc1('预检查失败：负载表为空。', C_ERR)
    return false
  end
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
  local f = io.open(RES, "rb")
  if f then
    f:seek("set", list[1][1])
    local probe = f:read(list[1][3])
    f:close()
    if not probe or #probe ~= list[1][3] then
      setDesc1('预检查失败：resource.bin 读取异常。', C_ERR)
      return false
    end
  end
  setDesc1(string.format('预检查通过 | %d 条 | %.2fMB\n您可以返回主页开始修改。',
                         #list, total / 1048576), C_OK)
  return true
end

--------------------------------------------------------------------- 替换
local logLabel = nil
local rebootBtn = nil
local logLines = {}

local function logOut(s)
  logLines[#logLines + 1] = s
  while #logLines > 8 do table.remove(logLines, 1) end
  if logLabel then
    pcall(function() logLabel:set { text = table.concat(logLines, "\n") } end)
  end
end

local function showReboot()
  if rebootBtn then pcall(function() rebootBtn:clear_flag(lvgl.FLAG.HIDDEN) end) end
end

local function readChunk(off, len, path, bsz)
  if os.remove then pcall(os.remove, path) end
  sh(string.format("dd if=%s of=%s bs=%d skip=%d count=%d",
                   DEV, path, bsz, off // bsz, len // bsz))
  return slurp(path, len)
end

-- 大块 + 尾块：偏移都是 512 对齐，RLE 素材的长度却常常不是 4/512 的倍数（4485 / 196005 …）。
-- 老写法对这种长度只能 bs=1 -> 一条 19 万字节要 38 万次单字节读写，慢到偶发失败。
-- 这里把它切成 ≤3 段：bs=512 的大块 + bs=4 的次块 + 最后 1~3 字节 bs=1，syscall 直接降两个数量级。
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

-- 每条三步：① 版本校验（设备上那段必须等于「原厂」或「替换后」）② 写入 ③ 整段回读比对
local function writeOne(rec, want)
  local f = io.open(RES, "rb")
  if not f then return 'err' end
  f:seek("set", rec[1])
  local data = f:read(rec[3])
  f:close()
  if not data or #data ~= rec[3] then return 'err' end
  local mismatch = false
  if want then
    local n = math.min(64, rec[3], want[3])
    local wf = io.open(RES, "rb")
    wf:seek("set", want[1])
    local wdata = wf:read(n)
    wf:close()
    local cur = readChunk(rec[2], n, TMPH, 1)
    if not cur or #cur ~= n or not wdata or #wdata ~= n then return 'err' end
    -- 设备上现在是「原厂」或「已改」都算正常；都不是（比如上次只写了一半）也**照样写**，
    -- 只记一笔 —— 跳过去反而修不好那种半截状态。
    if cur ~= data:sub(1, n) and cur ~= wdata then mismatch = true end
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
  return mismatch and 'warn' or 'ok'
end

local function startJob(variant)
  if job.run then return end
  local list = (variant == 'rollback') and PAYTBL.rb or PAYTBL.pay
  if not list or #list == 0 then
    setDesc1('负载表为空，已中止。', C_ERR)
    return
  end
  job.run, job.list, job.i, job.errs, job.variant = true, list, 0, 0, variant
  logLines = {}
  logOut(variant == 'rollback' and '> 开始回滚' or '> 开始替换')
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
    local s = (job.variant == 'rollback')
      and '> 回滚完毕，请重启手表。'
      or '> 替换完毕，请重启手表。若发现问题，请回滚修改。'
    logOut(s)
    logOut(string.format('> 共 %d 条，失败 %d 条%s', n, job.errs,
                         (job.vers or 0) > 0 and string.format('，写入前状态异常 %d 条（已照样写入）', job.vers) or ''))
    showReboot()
    return
  end
  local rb = (job.variant == 'rollback') and PAYTBL.pay or PAYTBL.rb
  local r = writeOne(job.list[job.i], rb and rb[job.i])
  if r == 'warn' then
    job.vers = (job.vers or 0) + 1
  elseif r ~= 'ok' then
    job.errs = job.errs + 1
  end
  if job.i % 4 == 0 or job.i == n then
    logOut(string.format('> 写入 %d/%d  失败 %d', job.i, n, job.errs))
  end
end

--------------------------------------------------------------------- 页面
local function buildHome()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  -- 盘内标题 = 显示名（不再用内部代号 S4Chg）；x 按真 MiSans 30px 量出的宽度居中：
  --   'S4e Pt.3' = 123 -> x = (466-123)/2 = 171.5 -> 172
  --   'S4e Pt.3 · 还原' = 220 -> x = (466-220)/2 = 123
  if ROLE == 'restore' then
    pageTitle(p, 'S4e Pt.3 · 还原', 123, 222)
  else
    pageTitle(p, 'S4e Pt.3', 172, 125)
  end
  listItem(p, 85, 'ic_help', '快速帮助', function() show(pages.help) end)
  listItem(p, 181, 'ic_replace', ROLE == 'restore' and '开始还原' or '开始替换', function()
    pendingVariant = 'replace'
    confirmFrom = 'home'
    show(pages.confirm)
  end)
  listItem(p, 277, 'ic_about', '关于', function() show(pages.about) end)
  return p
end

local function buildHelp()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  backArrow(p, 160, function() show(pages.home) end)
  local t = pageTitle(p, '快速帮助', 183, 130)
  setClickable(t)
  bind(t, function() show(pages.home) end)

  -- 竖排 4 个元素的 y：76 / 166 / 236 / 326。
  -- 原来 85 / 176 / 256 / 344 时，末尾那句 2 行块的**第 2 行**（y 377..410）已经越过圆边
  -- （仓库外 check_clip_real.py 实测：replace 盘 47 越界像素，s4e-PAnim 甚至 229 像素），
  -- 因为整页内容 88+66+88+66=308px，而 466 圆在 x=65 处最多只给到 y<=394。
  -- 4 个元素整体上移 9~22px 后：整页 replace/restore 都是 0 越界、0 溢框（最远像素 228.2 < 233）。
  listItem(p, 76, 'ic_check', '环境预检查', function() doCheck() end)
  desc1 = lab(p, { x = 65, y = 166, w = 338, h = 72,
                   text = '检查原始资源状态、分区可写情况等。',
                   text_color = C_GRAY, font_size = 24, text_font = F_BODY })

  -- 拆盘之后：本盘只装一份负载，「回滚/恢复」由另一份盘负责
  listItem(p, 236, 'ic_rollback', ROLE == 'restore' and '恢复修改' or '回滚修改', function()
    if ROLE == 'restore' then
      setDesc1('本盘是还原盘。要重新换回动画，请安装 S4e Pt.3。', C_GRAY)
    else
      setDesc1('本盘只负责替换。要还原原厂动画，请安装 S4e Pt.3 · 还原。', C_GRAY)
    end
  end)
  -- 换行写死成 2 行：24px 行高 33 -> 2 行 66 才放得进 h=72；
  -- 原来 w=334 时这句会被折成 3 行（第 3 行整个在圆外），所以框宽 334 -> 366
  -- （x=65 不动；实测行宽 360/306）。
  lab(p, { x = 65, y = 326, w = 366, h = 72,
           text = ROLE == 'restore' and '把充电动画写回原厂样式。'
                  or '本盘不含回滚数据（体积减半），\n还原请装 S4e Pt.3 · 还原。',
           text_color = C_GRAY, font_size = 24, text_font = F_BODY })
  return p
end

local function buildConfirm()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  -- 确认页的返回：回到进来时的那个页面（首页 或 快速帮助）
  local function goBack() show(pages[confirmFrom] or pages.home) end
  backArrow(p, 160, goBack)
  local t = pageTitle(p, '开始替换', 183, 130)
  setClickable(t)
  bind(t, goBack)

  -- 多色文本**不能**用 recolor：AP 里那几处 recolor 是图片重着色(bg_img_recolor)
  -- 和表盘编辑器的主题重着色，不是文本属性；实测标记会被原样显示出来。
  -- 改为拆成多个标签 + 手工算 x（宽度用真 MiSans 24px 量出）。
  -- 折行也显式写死：因为"替换图标包之前，请先确认自己"量得 336px，几乎等于 338px 框宽，
  -- 且型号那行 500px 必然折行，只有写死才能让多色片段位置确定。
  lab(p, { x = 64, y = 90, w = 338, h = 70,
           text = '替换充电动画之前，请先确认自己\n的系统版本号为 ',
           text_color = C_GRAY, font_size = 24, text_font = F_BODY })
  lab(p, { x = 241, y = 123, w = 104, h = 33, text = '3.202.79',
           text_color = C_WHITE, font_size = 24, text_font = F_BODY })
  lab(p, { x = 340, y = 123, w = 30, h = 33, text = '！',
           text_color = C_GRAY, font_size = 24, text_font = F_BODY })
  lab(p, { x = 64, y = 189, w = 338, h = 33, text = '请确认自己的手表型号为',
           text_color = C_GRAY, font_size = 24, text_font = F_BODY })
  lab(p, { x = 64, y = 222, w = 338, h = 70,
           text = 'Xiaomi Watch S4 eSIM（非\n15 周年纪念版）',
           text_color = C_WHITE, font_size = 24, text_font = F_BODY })
  lab(p, { x = 242, y = 255, w = 30, h = 33, text = '！',
           text_color = C_GRAY, font_size = 24, text_font = F_BODY })
  lab(p, { x = 64, y = 321, w = 338, h = 33, text = '搞机有风险，变砖后果自负。',
           text_color = C_GRAY, font_size = 24, text_font = F_BODY })

  local b = bigButton(p, '确认替换')
  bindTap(b, function() startJob(pendingVariant) end)
  return p
end

local function buildAbout()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  backArrow(p, 191, function() show(pages.home) end)
  local t = pageTitle(p, '关于', 214, 64)
  setClickable(t)
  bind(t, function() show(pages.home) end)

  -- 信息卡：底板 + 圆形 logo + 大标题 + 版本号
  pcall(function()
    p:Object { x = 52, y = 79, w = 362, h = 204, pad_all = 0,
               bg_color = C_PLATE, border_width = 0, radius = 30 }
  end)
  if IMG.logo then
    pcall(function() p:Image { src = IMG.logo, x = 194, y = 108 } end)
  end
  -- 28px 量得：'S4e Pt.3' = 114 -> 居中 x = 233 - 57 = 176
  --            'S4e Pt.3 · 还原' = 204 -> x = 233 - 102 = 131
  if ROLE == 'restore' then
    lab(p, { x = 131, y = 192, w = 206, h = 38, text = 'S4e Pt.3 · 还原',
             text_color = C_WHITE, font_size = 28, text_font = F_ITEM })
  else
    lab(p, { x = 176, y = 192, w = 116, h = 38, text = 'S4e Pt.3',
             text_color = C_WHITE, font_size = 28, text_font = F_ITEM })
  end
  -- "1.0.0" 20px 量得 45px -> 居中 x = 66 + (334-45)/2 = 210
  lab(p, { x = 210, y = 227, w = 45, h = 27, text = '1.0.0',
           text_color = C_GRAY, font_size = 20, text_font = F_VER })

  -- QQ 联系方式：结构与列表项一致（无动作，所以不给它绑点击）
  listItem(p, 291, 'ic_qq', '732681995', nil)
  return p
end

local function buildRunning()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  -- 本页没有返回图标（规格：顶栏同首页），所以标题要屏幕居中：
  -- "正在替换" 30px 量得 120px -> x = 233 - 120/2 = 173（不是帮助页的 183）
  pageTitle(p, '正在替换', 173, 130)
  logLabel = lab(p, { x = 64, y = 90, w = 338, h = 269, text = '',
                      text_color = C_WHITE, font_size = 24, text_font = F_BODY })
  rebootBtn = bigButton(p, '重启手表')
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
