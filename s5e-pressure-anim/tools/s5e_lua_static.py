# -*- coding: utf-8 -*-
"""main.lua 的静态体检 —— 编译前把「真机上才会炸」的几类错抓出来。

S4e 那版的真机事故是：`segs/ddWrite/ddRead` 被放在 `slurp/sh` **之前**，
于是函数体里引用的 `sh` 不是那个 local，而是**全局 nil**，一调用就
`attempt to call a nil value (global 'sh')` —— 而且当时整条流水线全绿
（Compiler.exe 只打包 Lua、不解析它）。所以本文件专门查：

  ① 块配平（function/if/for/while/do/end/repeat/until）
  ② **先用后声明**：某个名字在文件里是 `local`，但第一次调用发生在它声明之前
  ③ 调用了既不是 local、也不在 Lua 标准库白名单里的名字（拼写错 / 忘了 local）
  ④ 模板约定：4 个占位符各 1 次、`--[[` 只在文件头、以 `return ui\\n` 结尾
     （tools/s5e_verify.py 会从 .face 里反解 Lua，这几条是它定位 Lua 的前提）

用法：python tools/s5e_lua_static.py [main.lua]
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PROJ
from lua_balance import strip

LUAC = os.path.join(PROJ, 'main.lua')

# Lua 5.4 标准库 + 本项目用到的宿主全局（都不是拼写错）
WHITELIST = set("""
require pcall xpcall type pairs ipairs next select tostring tonumber rawget rawset
rawequal rawlen setmetatable getmetatable error assert print unpack load
string table math io os coroutine utf8 debug collectgarbage
""".split())
KEYWORDS = set("""
and break do else elseif end false for function goto if in local nil not or
repeat return then true until while
""".split())
REQUIRED_PH = ('__UIIMG__', '__PAY__', '__RB__', '__ROLE__')

fail = 0


def bad(msg):
    global fail
    fail += 1
    print('  FAIL ' + msg)


def ck(cond, msg):
    print(('  OK   ' if cond else '  FAIL ') + msg)
    if not cond:
        global fail
        fail += 1


def lineno(src, idx):
    return src.count('\n', 0, idx) + 1


def decls(src, code):
    """名字 -> 它在 code 里第一次被 local 声明（或作为函数参数出现）的位置。"""
    out = {}
    for m in re.finditer(r'\blocal\s+function\s+([A-Za-z_]\w*)', code):
        out.setdefault(m.group(1), m.start(1))
    for m in re.finditer(r'\blocal\s+([A-Za-z_][\w,\s]*?)\s*(?:=|$)', code, re.M):
        base = m.start(1)
        for piece in m.group(1).split(','):
            nm = piece.strip()
            if re.fullmatch(r'[A-Za-z_]\w*', nm):
                out.setdefault(nm, base)
    # 函数参数也是 local（`function(a, b)` / `function f(a)`），否则会误报
    for m in re.finditer(r'\bfunction\b\s*[A-Za-z_.:]*\s*\(([^)]*)\)', code):
        for piece in m.group(1).split(','):
            nm = piece.strip()
            if re.fullmatch(r'[A-Za-z_]\w*', nm):
                out.setdefault(nm, m.start())
    return out


def calls(code):
    """所有函数调用点（排除 `function NAME(` 这种定义）。"""
    out = []
    for m in re.finditer(r'(?<![\w.:])([A-Za-z_]\w*)\s*\(', code):
        head = code[max(0, m.start(1) - 12):m.start(1)]
        if re.search(r'\bfunction\s+$', head):
            continue                      # 定义，不是调用
        out.append((m.group(1), m.start(1)))
    return out


def main():
    src = open(LUAC, encoding='utf-8').read()
    code = strip(src)
    print('=== tools/s5e_lua_static.py  %s  (%d B) ===' % (LUAC, len(src.encode('utf-8'))))

    print('\n[1] 块配平')
    def cnt(k):
        return len(re.findall(r'(?<![\w.])' + k + r'(?![\w])', code))
    do_standalone = cnt('do') - cnt('while') - cnt('for')
    openers = cnt('function') + cnt('if') + cnt('while') + cnt('for') + do_standalone
    ck(openers == cnt('end') and cnt('repeat') == cnt('until'),
       'openers=%d end=%d（function=%d if=%d for=%d while=%d do=%d）repeat=%d until=%d'
       % (openers, cnt('end'), cnt('function'), cnt('if'), cnt('for'), cnt('while'),
          do_standalone, cnt('repeat'), cnt('until')))

    print('\n[2] 先用后声明（真机上会变成 "call a nil value"）')
    d = decls(src, code)
    early, unknown = [], []
    for name, pos in calls(code):
        if name in KEYWORDS or name in WHITELIST:
            continue
        if name in d:
            if pos < d[name]:
                early.append((name, lineno(src, pos), lineno(src, d[name])))
        else:
            unknown.append((name, lineno(src, pos)))
    ck(not early, '没有"先调用后 local"：%s'
       % ('' if not early else ' / '.join('%s 调用@%d 声明@%d' % e for e in early)))
    ck(not unknown, '没有未声明的被调用名：%s'
       % ('' if not unknown else ' / '.join('%s@%d' % u for u in unknown)))

    print('\n[3] 模板约定（s5e_verify.py 靠这些从 .face 里反解 Lua）')
    for ph in REQUIRED_PH:
        ck(src.count(ph) == 1, '占位符 %s 出现 %d 次（要 1）' % (ph, src.count(ph)))
    ck(src.startswith('--[[--'), '文件以 --[[-- 开头')
    ck(src.count('--[[') == 1, '--[[ 只出现 %d 次（要 1，否则 verify 会从中间截 Lua）'
       % src.count('--[['))
    ck(src.endswith('return ui\n'), '以 return ui\\n 结尾')
    ck(src.count('return ui\n') == 1, 'return ui\\n 只出现 %d 次（要 1）' % src.count('return ui\n'))
    ck('local UIIMG = {' in src, '有 local UIIMG = {')

    print('\n[4] 与 s5e_verify.py 对齐的字面量')
    ck(re.search(r"local ROLE = '__ROLE__'", src) is not None, "local ROLE = '__ROLE__'")
    ck(re.search(r'local W, H = 480, 480', src) is not None, 'local W, H = 480, 480')
    m = re.search(r'local DEVS = \{([^}]*)\}', src)
    ck(m is not None and '/dev/health' in m.group(1),
       'DEVS 里有 health -> /dev/health：%s' % (m.group(1).strip() if m else None))
    ck("local DEV = DEVS.health" in src,
       'DEV 来自 DEVS.health（表里的键名真的被用于取节点，不是摆设）')
    paytbl = re.search(r'local PAYTBL = \{\n__PAY__\n__RB__\n\}', src)
    ck(paytbl is not None, 'PAYTBL 里只有 __PAY__ / __RB__ 两处占位符（没有硬编码节点名）')
    ck('466' not in src, '没有残留的 466（旧 S4e 尺寸）')

    print('\n=== %s ===' % ('全部通过' if not fail else '%d 项失败' % fail))
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
