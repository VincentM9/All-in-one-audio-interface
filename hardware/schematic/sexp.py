"""Minimal S-expression reader/writer for KiCad files."""
import re

_TOK = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    stack, cur = [], []
    pos = 0
    while pos < len(text):
        m = _TOK.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            cur.append(re.sub(r'\\(.)', lambda q: {'n': '\n'}.get(q.group(1), q.group(1)), m.group(3)[1:-1]))
        else:
            cur.append(Sym(m.group(4)))
    return cur[0] if len(cur) == 1 else cur


def _atom(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, bool):
        return 'yes' if a else 'no'
    if isinstance(a, (int, float)):
        s = f'{a:.4f}'.rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return '"' + str(a).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def dump(e, ind=0):
    if not isinstance(e, list):
        return _atom(e)
    if e and isinstance(e[0], str) and not isinstance(e[0], Sym):
        e = [Sym(e[0])] + e[1:]      # list heads are always keywords
    if all(not isinstance(x, list) for x in e):
        return '(' + ' '.join(_atom(x) for x in e) + ')'
    # keep element order (KiCad cares, e.g. "(pin_names (offset 1) hide)")
    out, inline = '(', True
    for i, x in enumerate(e):
        if isinstance(x, list):
            out += '\n' + '  ' * (ind + 1) + dump(x, ind + 1)
            inline = False
        else:
            out += (' ' if i and inline else ('' if not i else ' ')) + _atom(x)
    return out + '\n' + '  ' * ind + ')'


def find(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]


def first(e, key):
    r = find(e, key)
    return r[0] if r else None
