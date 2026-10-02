--[[----------------------------------------------------------------------------
  OS4 Icons (S5 eSIM) —— Xiaomi Watch S5 41mm(q63) 的 OS4 图标包 -> Xiaomi Watch S5 eSIM 46mm(p62lte)

  目标固件：miwear.watch.p62lte_v3.112.035_full（480x480，Lua 5.4 宿主）
  写入目标：两个 ROMFS 分区
      /dev/app     33 条（vela_app.bin  卷名 app    sb_size 103042192）
      /dev/health  14 条（vela_health.bin 卷名 health sb_size 206924736）
  47 条负载每条都恰好等于原槽位长度（144x144 ARGB8888 = 82956 B），
  所以 ROMFS 的 inode 表 / 后续所有偏移一个字节都不动。

  界面按 480x480 设计（_tools/s5e_pages.py 本机真字体渲染 + 圆屏切边检查 0 越界）。

  真机已验证的底层能力（沿用 S5->S4 那个表盘）:
    * 宿主不调用 ui.init -> 加载期建界面
    * SCRIPT_PATH 为空 -> 用 debug.getinfo 反推目录
    * .face 不解包，资源仍在 resource.bin 里 -> 按偏移读出来用
    * os.execute / dd 可用；os.execute 的返回值不可靠 -> 一律用内容比对判成败
------------------------------------------------------------------------------]]

local lvgl = require("lvgl")

local W, H = 480, 480
local BLK = 4

-- 等长覆盖只保证「偏移」512 对齐；RLE 素材的长度常常不是 4 的倍数（如 1635 / 3047），
-- 那种记录必须退化成 bs=1（偏移本身对齐，所以 bs=1 也精确）。
local function ddBlk(off, len)
  if off % BLK == 0 and len % BLK == 0 then return BLK end
  return 1
end
local DEVS = { app = "/dev/app", health = "/dev/health" }
local DEVLIST = { "app", "health" }        -- 顺序固定：app 先，health 后
local TMPH = "/tmp/s5e_head.bin"      -- 版本校验读出的 64 字节
local TMPW = "/tmp/s5e_wr.bin"        -- 待写入的负载（resource.bin 里抠出来的那一份）
local TMPB = "/tmp/s5e_back.bin"      -- 写完之后回读出来的那一份

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
-- UI 图片 { resource.bin 内偏移, 长度, 名字 } —— 由 _tools/s5e_build.py 回填
local UIIMG = {
__UIIMG__
}

-- 负载表：{ 设备, 分区内偏移, 长度, resource.bin 内偏移 } —— 同样由脚本回填
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
      local p = "/tmp/s5e_ui_" .. e[3] .. ".bin"
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
local HL = 0x005149
local pressed = nil
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
local job = { run = false, list = nil, i = 0, ok = 0, errs = 0, skipped = 0,
              variant = 'replace', bad = {}, done = {}, total = {} }
local pendingVariant = 'replace'
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
  pressRelease()
  for k, v in pairs(pages) do
    pcall(function() v:add_flag(lvgl.FLAG.HIDDEN) end)
  end
  pcall(function() p:clear_flag(lvgl.FLAG.HIDDEN) end)
end

local function bind(obj, fn)
  if not obj then return end
  local ev = lvgl.EVENT
  if ev and ev.SHORT_CLICKED then
    if pcall(function() obj:onevent(ev.SHORT_CLICKED, function() fn() end) end) then return end
  end
  if pcall(function() obj:onClicked(function() fn() end) end) then return end
  pcall(function() obj:onevent(ev and ev.CLICKED, fn) end)
end

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
  -- 居中不用 text_align（它要的是 lv_text_align_t；传 ALIGN.CENTER 会越界被忽略）
  -- 改为按真字体量出的宽度手工算 x
  local l = lab(parent, { x = 201, y = 4, w = 78, h = 46, text = '--:--',
                          text_color = C_GRAY, font_size = 29, text_font = F_CLOCK })
  clocks[#clocks + 1] = l
  return l
end

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

-- 列表项：底板(整块可点) + 圆形遮罩 + 图标 + 标题（pad_all=0 必须，否则子元素右下偏移）
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
    lab(plate, { x = 82, y = 26, w = 214, h = 40, text = title,
                 text_color = C_WHITE, font_size = 29, text_font = F_ITEM })
  end
  return plate
end

local function bigButton(parent, text)
  local b = nil
  pcall(function()
    b = parent:Object { x = 111, y = 376, w = 258, h = 82, pad_all = 0,
                        bg_color = C_PLATE, border_width = 0, radius = 41 }
  end)
  if b then setClickable(b) end
  -- "确认替换"/"重启手表" 29px 量得 116px -> 居中 x = 111 + (258-116)/2 = 182
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

-- 从 resource.bin 里取一段（负载 / 原始字节）
local function slice(off, len)
  if not RES then return nil end
  local f = io.open(RES, "rb")
  if not f then return nil end
  f:seek("set", off)
  local d = f:read(len)
  f:close()
  return d
end

-- 读设备上某偏移处的 head 字节（不写，只读）
local function readBack(dev, off, len, tmp, bsz)
  if os.remove then pcall(os.remove, tmp) end
  sh(string.format("dd if=%s of=%s bs=%d skip=%d count=%d",
                   DEVS[dev], tmp, bsz or 1, bsz and (off // bsz) or off,
                   bsz and (len // bsz) or len))
  return slurp(tmp, len)
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
  local msg = {}
  for i = 1, #DEVLIST do
    local d = DEVLIST[i]
    local h = readBack(d, 0, 48, TMPH, 1)
    if not h or #h < 48 then
      msg[#msg + 1] = d .. ' 读不到'
    elseif h:sub(1, 8) ~= "-rom1fs-" then
      msg[#msg + 1] = d .. ' 头不是 ROMFS'
    else
      local z = h:find("\0", 17, true)
      local vol = h:sub(17, (z or 33) - 1)
      local size = string.unpack("<I4", h, 9)
      if vol ~= d then
        msg[#msg + 1] = d .. ' 卷名是 ' .. vol
      else
        msg[#msg + 1] = string.format('%s 可读 %.0fMB', d, size / 1048576)
      end
    end
  end
  local bad, total = 0, 0
  for i = 1, #list do
    local r = list[i]
    local b = ddBlk(r[2], r[3])
    if (r[2] % b) ~= 0 or (r[3] % b) ~= 0 then bad = bad + 1 end
    total = total + r[3]
  end
  local head = string.format('预检查 | %d 条 | %.2fMB', #list, total / 1048576)
  if bad > 0 then
    setDesc1(head .. string.format('\n%d 项未对齐！', bad), C_ERR)
    return false
  end
  local okAll = true
  for i = 1, #msg do
    if msg[i]:find('读不到') or msg[i]:find('不是 ROMFS') or msg[i]:find('卷名') then okAll = false end
  end
  -- 抽样版本校验：每个分区取第一条负载，比对设备上真实的 64 字节与原厂字节。
  -- 这一步能确认"负载偏移是给这一版固件算的"，而且只读、不写任何字节。
  for i = 1, #DEVLIST do
    local d = DEVLIST[i]
    local idx = nil
    for k = 1, #list do
      if list[k][1] == d then idx = k break end
    end
    if idx then
      local o = PAYTBL.rb[idx]
      local p = PAYTBL.pay[idx]
      local want = o and slice(o[4], 64) or nil
      local new = p and slice(p[4], 64) or nil
      local got = o and readBack(d, o[2], 64, TMPH, 1) or nil
      if want and got and #got >= 64 and got == want then
        msg[#msg + 1] = d .. ' 原厂✓'
      elseif new and got and #got >= 64 and got == new then
        msg[#msg + 1] = d .. ' 已替换✓'
      else
        msg[#msg + 1] = d .. ' 抽样×'
        okAll = false
      end
    end
  end
  setDesc1(head .. '\n' .. table.concat(msg, ' / '), okAll and C_OK or C_ERR)
  return okAll
end

--------------------------------------------------------------------- 替换 / 回滚 / 校验
local logLabel = nil
local rebootBtn = nil
local runningTitle = nil
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

-- 一条记录的动作（三条 dd：版本校验读 / 写 / 回读）：
--   mode='write'    : 先确认设备上现有 64B 等于原厂字节（版本对得上），写入新图标，整段回读比对
--   mode='rollback' : 反向 —— 先确认现有 64B 等于替换后的字节，再写回原厂字节并回读比对
-- 判据一律是内容比对，不看 os.execute 的返回值（这台机器上它不可靠）
local function runOne(i, mode)
  local srcname = (mode == 'rollback') and 'rb' or 'pay'
  local wantname = (mode == 'rollback') and 'pay' or 'rb'
  local rec = PAYTBL[srcname][i]
  local want = PAYTBL[wantname][i]
  if not rec or not want then return 'err' end
  local dev = rec[1]
  -- 现状认定：等于「原厂字节」（want）或等于「替换后字节」（rec）都算对版。
  -- 这样重复点替换、或断电后半途重来都不会被判成「版本不符」而卡住。
  local headW = slice(want[4], 64)
  local headO = slice(rec[4], 64)
  if not headW or not headO or #headW < 64 or #headO < 64 then return 'err' end
  local cur = readBack(dev, rec[2], 64, TMPH, 1)
  if not cur or #cur < 64 then return 'err' end
  if cur ~= headW and cur ~= headO then return 'ver' end
  local blob = slice(rec[4], rec[3])
  if not blob or #blob ~= rec[3] then return 'err' end
  -- 先把负载落到 /tmp（resource.bin 内的偏移不保证 4 对齐，所以不能用 dd 直接 skip）
  local wf = io.open(TMPW, "wb")
  if not wf then return 'err' end
  wf:write(blob)
  wf:close()
  local b = ddBlk(rec[2], rec[3])
  sh(string.format("dd if=%s of=%s bs=%d seek=%d count=%d",
                   TMPW, DEVS[dev], b, rec[2] // b, rec[3] // b))
  local back = readBack(dev, rec[2], rec[3], TMPB, b)
  if not back or #back ~= rec[3] or back ~= blob then return 'err' end
  return 'ok'
end

local function startJob(variant)
  if job.run then return end
  local pay = PAYTBL.pay or {}
  if #pay == 0 then
    setDesc1('负载表为空，已中止。', C_ERR)
    return
  end
  job.run, job.i, job.ok, job.errs, job.skipped = true, 0, 0, 0, 0
  job.variant, job.bad, job.done, job.total = variant, {}, {}, {}
  job.list = pay
  for k = 1, #pay do
    local d = pay[k][1]
    job.total[d] = (job.total[d] or 0) + 1
  end
  logLines = {}
  logOut((variant == 'rollback') and '> 开始回滚' or '> 开始替换')
  local _devs = {}
  for d in pairs(job.total) do _devs[#_devs + 1] = d end
  table.sort(_devs)
  local _parts = {}
  for i = 1, #_devs do
    _parts[#_parts + 1] = string.format('%s %d 条', _devs[i], job.total[_devs[i]])
  end
  logOut('> ' .. table.concat(_parts, ' / '))
  logOut('> 读取 resource.bin')
  if rebootBtn then pcall(function() rebootBtn:add_flag(lvgl.FLAG.HIDDEN) end) end
  if runningTitle then
    pcall(function()
      runningTitle:set { text = (variant == 'rollback') and '正在回滚' or '正在替换' }
    end)
  end
  show(pages.running)
end

local function tick()
  tickCount = tickCount + 1
  if pressed and (tickCount - pressed.t) > 40 then pressRelease() end
  if not job.run or not job.list then return end
  job.i = job.i + 1
  local n = #job.list
  if job.i > n then
    job.run = false
    logOut((job.variant == 'rollback') and '> 回滚完毕，请重启手表。'
                                     or '> 替换完毕，请重启手表。')
    logOut(string.format('> 成功 %d / 失败 %d（共 %d）', job.ok, job.errs, n))
    if job.skipped > 0 then
      logOut(string.format('> 版本不符跳过 %d 条', job.skipped))
    end
    logOut(string.format('> app %d/%d  health %d/%d',
                         job.done.app or 0, job.total.app or 0,
                         job.done.health or 0, job.total.health or 0))
    showReboot()
    return
  end
  local dev = job.list[job.i][1]
  if job.bad[dev] then
    job.skipped = job.skipped + 1
    job.errs = job.errs + 1
  else
    local r = runOne(job.i, (job.variant == 'rollback') and 'rollback' or 'write')
    if r == 'ok' then
      job.ok = job.ok + 1
      job.done[dev] = (job.done[dev] or 0) + 1
    elseif r == 'ver' then
      job.errs = job.errs + 1
      job.skipped = job.skipped + 1
      job.bad[dev] = true
      logOut('> ' .. dev .. ' 版本不符，已跳过')
    else
      job.errs = job.errs + 1
    end
  end
  if job.i % 10 == 0 or job.i == n then
    logOut(string.format('> %d/%d 成 %d 失 %d', job.i, n, job.ok, job.errs))
  end
end

--------------------------------------------------------------------- 页面
local function buildHome()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  -- 盘内标题 = 显示名：'S5e Pt.1' 31px 量得 121 -> x = (480-121)/2 = 179.5 -> 179
  pageTitle(p, 'S5e Pt.1', 179, 123)
  listItem(p, 88, 'ic_help', '快速帮助', function() show(pages.help) end)
  listItem(p, 186, 'ic_replace', '开始替换', function()
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
  desc1 = lab(p, { x = 67, y = 182, w = 348, h = 76,
                   text = '检查 app / health 两个分区\n与 47 条负载的完整性。',
                   text_color = C_GRAY, font_size = 25, text_font = F_BODY })

  listItem(p, 264, 'ic_rollback', '回滚修改', function()
    pendingVariant = 'rollback'
    confirmFrom = 'help'
    show(pages.confirm)
  end)
  lab(p, { x = 67, y = 355, w = 348, h = 36,
           text = '恢复 47 个图标的原始样式。',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  return p
end

local function buildConfirm()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  local function goBack() show(pages[confirmFrom] or pages.home) end
  backArrow(p, 167, goBack)
  local t = pageTitle(p, '开始替换', 188, 124)
  setClickable(t)
  bind(t, goBack)

  -- 多色文本不能用 recolor -> 拆成多个标签 + 手工算 x（宽度用真 MiSans 25px 量出）
  lab(p, { x = 60, y = 93, w = 360, h = 36,
           text = '替换图标包之前，请先确认自己', text_color = C_GRAY,
           font_size = 25, text_font = F_BODY })
  lab(p, { x = 60, y = 126, w = 360, h = 36,
           text = '的系统版本号为 ', text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  lab(p, { x = 244, y = 126, w = 120, h = 36, text = '3.112.035',
           text_color = C_WHITE, font_size = 25, text_font = F_BODY })
  lab(p, { x = 356, y = 126, w = 40, h = 36, text = '！',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  lab(p, { x = 60, y = 196, w = 360, h = 36, text = '请确认自己的手表型号为',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  lab(p, { x = 60, y = 229, w = 372, h = 36, text = 'Xiaomi Watch S5 eSIM 46mm',
           text_color = C_WHITE, font_size = 25, text_font = F_BODY })
  lab(p, { x = 427, y = 229, w = 40, h = 36, text = '！',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })
  lab(p, { x = 60, y = 331, w = 360, h = 36, text = '搞机有风险，变砖后果自负。',
           text_color = C_GRAY, font_size = 25, text_font = F_BODY })

  local b = bigButton(p, '确认替换')
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

  pcall(function()
    p:Object { x = 54, y = 81, w = 373, h = 210, pad_all = 0,
               bg_color = C_PLATE, border_width = 0, radius = 31 }
  end)
  if IMG.logo then
    pcall(function() p:Image { src = IMG.logo, x = 200, y = 111 } end)
  end
  -- 'S5e Pt.1' 29px 量得 114 -> 居中 x = 54 + (373-114)/2 = 183.5 -> 183
  lab(p, { x = 183, y = 198, w = 116, h = 40, text = 'S5e Pt.1',
           text_color = C_WHITE, font_size = 29, text_font = F_ITEM })
  lab(p, { x = 216, y = 234, w = 49, h = 28, text = '1.0.0',
           text_color = C_GRAY, font_size = 21, text_font = F_VER })

  listItem(p, 300, 'ic_qq', '732681995', nil)
  return p
end

local function buildRunning()
  local p = newPage()
  if not p then return nil end
  clockLabel(p)
  runningTitle = pageTitle(p, '正在替换', 178, 124)
  logLabel = lab(p, { x = 67, y = 93, w = 348, h = 277, text = '',
                      text_color = C_WHITE, font_size = 25, text_font = F_BODY })
  rebootBtn = bigButton(p, '重启手表')
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
