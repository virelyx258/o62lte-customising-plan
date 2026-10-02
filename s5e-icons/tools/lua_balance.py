"""Crude but effective Lua block-balance checker: strips comments and strings,
then counts block openers vs `end`."""
import sys, re

def strip(src):
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        # long bracket comment / string  --[[ ]] , --[==[ ]==]
        m = re.match(r'--\[(=*)\[', src[i:])
        if m:
            close = ']' + m.group(1) + ']'
            j = src.find(close, i)
            i = n if j < 0 else j + len(close)
            out.append(' ')
            continue
        if src.startswith('--', i):
            j = src.find('\n', i)
            i = n if j < 0 else j
            out.append(' ')
            continue
        m = re.match(r'\[(=*)\[', src[i:])
        if m:
            close = ']' + m.group(1) + ']'
            j = src.find(close, i)
            i = n if j < 0 else j + len(close)
            out.append('""')
            continue
        if c in '"\'':
            j = i + 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == c:
                    break
                j += 1
            i = j + 1
            out.append('""')
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def check(path):
    src = open(path, encoding='utf-8').read()
    code = strip(src)
    def cnt(k):
        return len(re.findall(r'(?<![\w.])' + k + r'(?![\w])', code))
    # every while/for consumes exactly one `do`, wherever it sits (may wrap lines)
    do_total = cnt('do')
    do_standalone = do_total - cnt('while') - cnt('for')
    openers = cnt('function') + cnt('if') + cnt('while') + cnt('for') + do_standalone
    enders = cnt('end')
    repeat_n, until_n = cnt('repeat'), cnt('until')
    print(f'{path}')
    print(f'  function={cnt("function")} if={cnt("if")} while={cnt("while")} '
          f'for={cnt("for")} do(standalone)={do_standalone} repeat={repeat_n}')
    print(f'  openers={openers}  end={enders}  until={until_n}')
    ok = (openers == enders) and (repeat_n == until_n)
    print(f'  BALANCED: {ok}')
    if not ok:
        print('  ^^^ 括号/块不匹配，需要检查')
    return ok


allok = True
for p in sys.argv[1:]:
    allok &= check(p)
print('\nALL OK' if allok else '\nPROBLEM')
