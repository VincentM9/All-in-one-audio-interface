"""Tiny KiCad 7 schematic writer driven by a netlist.

Parts are described by library symbol + pin-number -> net mapping. Each pin
gets a net label at its end (global label if the net crosses sheets, local
label otherwise); unused pins get a no-connect flag. Parts are packed in a
grid. Library symbols are copied from the installed KiCad libraries and
embedded in the schematic, so the output is self-contained (which is what
Altium's KiCad importer needs).
"""
import glob
import math
import os
import uuid as _uuid

from sexp import Sym, dump, find, first, parse

LIBDIR = os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')
GRID = 2.54
CHAR_W = 1.0           # mm per label character at 1.27 mm text
PROJECT = 'aio'

_ns = _uuid.UUID('6f1c1d1e-2b9a-4a51-9a7e-1d6c0a7b0f00')


def uid(*key):
    """Deterministic UUIDs so regenerating gives stable diffs."""
    return str(_uuid.uuid5(_ns, '/'.join(str(k) for k in key)))


# ---------------------------------------------------------------- symbols --
_libcache = {}


def _lib(name):
    if name not in _libcache:
        path = os.path.join(LIBDIR, name + '.kicad_sym')
        _libcache[name] = parse(open(path).read())
    return _libcache[name]


def _raw_symbol(lib, name):
    for s in find(_lib(lib), 'symbol'):
        if s[1] == name:
            return s
    raise KeyError(f'{lib}:{name}')


def _rename_units(body, old, new):
    out = []
    for x in body:
        if isinstance(x, list) and x and x[0] == 'symbol' and isinstance(x[1], str) \
                and x[1].startswith(old + '_'):
            x = ['symbol', new + x[1][len(old):]] + x[2:]
        out.append(x)
    return out


def load_symbol(lib_id):
    """Return a flattened symbol definition named lib_id (handles extends)."""
    lib, name = lib_id.split(':')
    s = _raw_symbol(lib, name)
    ext = first(s, 'extends')
    if ext:
        base = load_symbol(f'{lib}:{ext[1]}')
        base_name = base[1].split(':')[1]
        props = {p[1]: p for p in find(s, 'property')}
        body = []
        for x in base[2:]:
            if isinstance(x, list) and x and x[0] == 'property' and x[1] in props:
                x = props.pop(x[1])
            body.append(x)
        body = [x for x in body if not (isinstance(x, list) and x[0] == 'property')] + \
            [x for x in body if isinstance(x, list) and x[0] == 'property'] + list(props.values())
        body = _rename_units(body, base_name, name)
        # keep non-property flags of the base, then properties, then units
        flags = [x for x in body if isinstance(x, list) and x[0] in ('pin_numbers', 'pin_names', 'in_bom', 'on_board', 'power')]
        prop = [x for x in body if isinstance(x, list) and x[0] == 'property']
        units = [x for x in body if isinstance(x, list) and x[0] == 'symbol']
        return ['symbol', lib_id] + flags + prop + units
    s = ['symbol', lib_id] + s[2:]
    return s


class SymInfo:
    """Pin geometry for a symbol: per unit list of pins."""

    def __init__(self, sym):
        self.sym = sym
        self.units = {}           # unit -> list of pins
        self.body = {}            # unit -> list of (x, y) points of graphics
        self.power = first(sym, 'power') is not None
        for u in find(sym, 'symbol'):
            unit = int(u[1].rsplit('_', 2)[-2])
            for p in find(u, 'pin'):
                at = first(p, 'at')
                pin = dict(num=first(p, 'number')[1], name=first(p, 'name')[1],
                           etype=str(p[1]), x=float(at[1]), y=float(at[2]),
                           a=int(float(at[3])) if len(at) > 3 else 0,
                           length=float(first(p, 'length')[1]) if first(p, 'length') else 0,
                           hidden='hide' in [str(t) for t in p])
                self.units.setdefault(unit, []).append(pin)
            for g in u[2:]:
                if not isinstance(g, list):
                    continue
                pts = []
                if g[0] == 'rectangle':
                    pts = [(float(first(g, 'start')[1]), float(first(g, 'start')[2])),
                           (float(first(g, 'end')[1]), float(first(g, 'end')[2]))]
                elif g[0] == 'polyline':
                    pts = [(float(q[1]), float(q[2])) for q in first(g, 'pts')[1:]]
                elif g[0] == 'circle':
                    c = first(g, 'center')
                    r = float(first(g, 'radius')[1])
                    pts = [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
                self.body.setdefault(unit, []).extend(pts)
        common = self.units.pop(0, [])
        cbody = self.body.pop(0, [])
        if not self.units:
            self.units[1] = []
        for u in self.units:
            self.units[u] = common + self.units[u]
            self.body[u] = cbody + self.body.get(u, [])
        props = {p[1]: p[2] for p in find(sym, 'property')}
        self.ref_prefix = props.get('Reference', 'U')

    def unit_of(self, num):
        return [u for u, ps in self.units.items() if any(p['num'] == num for p in ps)]


_infocache = {}


def info(lib_id, custom=None):
    if lib_id not in _infocache:
        _infocache[lib_id] = SymInfo(custom if custom is not None else load_symbol(lib_id))
    return _infocache[lib_id]


def make_ic_symbol(lib_id, left, right, top=(), bottom=(), ref='U', value='', fp='', desc=''):
    """Build a rectangular IC symbol. Pin lists are (number, name, etype)."""
    n = max(len(left), len(right), 1)
    # leave room inside the box for the (vertical) names of top/bottom pins
    pad_t = math.ceil(max([len(p[1]) for p in top] + [0]) * 1.27 / GRID + 1) * GRID if top else 0
    pad_b = math.ceil(max([len(p[1]) for p in bottom] + [0]) * 1.27 / GRID + 1) * GRID if bottom else 0
    h = (n + 1) * GRID + pad_t + pad_b
    w_chars = max([len(p[1]) for p in left] + [0]) + max([len(p[1]) for p in right] + [0])
    w = max(20.32, math.ceil((w_chars * 1.27 + 6) / GRID) * GRID)
    w = max(w, (max(len(top), len(bottom)) + 1) * GRID)
    w = math.ceil(w / (2 * GRID)) * 2 * GRID
    h = math.ceil(h / (2 * GRID)) * 2 * GRID
    x0, y0 = -w / 2, h / 2
    pins = []

    def pin(num, name, et, x, y, a):
        pins.append(['pin', Sym(et), Sym('line'), ['at', x, y, a], ['length', 2.54],
                     ['name', name, ['effects', ['font', ['size', 1.27, 1.27]]]],
                     ['number', num, ['effects', ['font', ['size', 1.27, 1.27]]]]])
    for i, (num, name, et) in enumerate(left):
        pin(num, name, et, x0 - 2.54, y0 - pad_t - (i + 1) * GRID, 0)
    for i, (num, name, et) in enumerate(right):
        pin(num, name, et, -x0 + 2.54, y0 - pad_t - (i + 1) * GRID, 180)
    for i, (num, name, et) in enumerate(top):
        pin(num, name, et, x0 + (i + 1) * GRID, y0 + 2.54, 270)
    for i, (num, name, et) in enumerate(bottom):
        pin(num, name, et, x0 + (i + 1) * GRID, -y0 - 2.54, 90)
    eff = ['effects', ['font', ['size', 1.27, 1.27]]]
    nm = lib_id.split(':')[1]
    return ['symbol', lib_id, ['in_bom', Sym('yes')], ['on_board', Sym('yes')],
            ['property', 'Reference', ref, ['at', 0, y0 + 1.27, 0], eff],
            ['property', 'Value', value or nm, ['at', 0, -y0 - 1.27, 0], eff],
            ['property', 'Footprint', fp, ['at', 0, 0, 0], ['effects', ['font', ['size', 1.27, 1.27]], Sym('hide')]],
            ['property', 'Datasheet', '', ['at', 0, 0, 0], ['effects', ['font', ['size', 1.27, 1.27]], Sym('hide')]],
            ['property', 'ki_description', desc, ['at', 0, 0, 0], ['effects', ['font', ['size', 1.27, 1.27]], Sym('hide')]],
            ['symbol', nm + '_0_1',
             ['rectangle', ['start', x0, y0], ['end', -x0, -y0],
              ['stroke', ['width', 0.254], ['type', Sym('default')]], ['fill', ['type', Sym('background')]]]],
            ['symbol', nm + '_1_1'] + pins]


# ----------------------------------------------------------------- sheets --
def rot(x, y, a):
    r = math.radians(a)
    return (round(x * math.cos(r) - y * math.sin(r), 4),
            round(x * math.sin(r) + y * math.cos(r), 4))


class Part:
    def __init__(self, sheet, lib_id, ref, value, nets, fp='', rot=0, mpn='', dnp=False,
                 custom=None, desc=''):
        self.sheet, self.lib_id, self.ref, self.value = sheet, lib_id, ref, value
        self.nets, self.fp, self.rot, self.mpn, self.dnp = dict(nets), fp, rot, mpn, dnp
        self.desc = desc
        self.info = info(lib_id, custom)
        self.custom = custom
        if not self.fp:     # fall back to the library symbol's default footprint
            self.fp = next((x[2] for x in find(self.info.sym, 'property') if x[1] == 'Footprint'), '')
        allnums = {p['num'] for ps in self.info.units.values() for p in ps}
        bad = set(self.nets) - allnums
        if bad:
            raise ValueError(f'{ref} {lib_id}: no pins {sorted(bad)}')


class Sheet:
    def __init__(self, name, title, prefix_num, notes=''):
        self.name, self.title, self.num = name, title, prefix_num
        self.parts, self.counters, self.notes = [], {}, notes
        self.flags = []

    def ref(self, prefix):
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f'{prefix}{self.num}{n:02d}'

    def add(self, lib_id, value, nets, prefix=None, **kw):
        inf = info(lib_id, kw.get('custom'))
        ref = self.ref(prefix or inf.ref_prefix.rstrip('?'))
        p = Part(self, lib_id, ref, value, nets, **kw)
        self.parts.append(p)
        return p

    # common passives -------------------------------------------------------
    def R(self, val, a, b, fp='Resistor_SMD:R_0603_1608Metric', **kw):
        return self.add('Device:R', val, {'1': a, '2': b}, fp=fp, rot=90, **kw)

    def C(self, val, a, b, fp='Capacitor_SMD:C_0603_1608Metric', **kw):
        return self.add('Device:C', val, {'1': a, '2': b}, fp=fp, rot=90, **kw)

    def CP(self, val, pos, neg, fp='Capacitor_SMD:CP_Elec_8x10', **kw):
        return self.add('Device:C_Polarized', val, {'1': pos, '2': neg}, fp=fp, rot=90, **kw)

    def L(self, val, a, b, fp='Inductor_SMD:L_Bourns_SRR1260', **kw):
        return self.add('Device:L', val, {'1': a, '2': b}, fp=fp, rot=90, **kw)

    def FB(self, val, a, b, fp='Inductor_SMD:L_0805_2012Metric', **kw):
        return self.add('Device:FerriteBead_Small', val, {'1': a, '2': b}, fp=fp, rot=90, **kw)

    def pwr_flag(self, net):
        self.flags.append(net)


class Design:
    def __init__(self, title, rev, date, company):
        self.title, self.rev, self.date, self.company = title, rev, date, company
        self.sheets = []

    def sheet(self, *a, **kw):
        s = Sheet(*a, **kw)
        self.sheets.append(s)
        return s

    # ---------------------------------------------------------------------
    def nets(self):
        """net -> list of (sheet, ref, pin)"""
        out = {}
        for s in self.sheets:
            for p in s.parts:
                for num, net in p.nets.items():
                    out.setdefault(net, []).append((s.name, p.ref, num))
        return out

    def write(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        netsheets = {}
        for s in self.sheets:
            for p in s.parts:
                for net in p.nets.values():
                    netsheets.setdefault(net, set()).add(s.name)
            for f in s.flags:
                netsheets.setdefault(f, set()).add(s.name)
        self.global_nets = {n for n, ss in netsheets.items() if len(ss) > 1}
        self._auto_flags()
        root_uuid = uid('root')
        for i, s in enumerate(self.sheets):
            self._write_sheet(s, outdir, root_uuid, i + 2)
        self._write_root(outdir, root_uuid)
        with open(os.path.join(outdir, PROJECT + '.kicad_pro'), 'w') as f:
            f.write('{\n  "meta": {"filename": "%s.kicad_pro", "version": 1},\n'
                    '  "sheets": [%s]\n}\n' % (PROJECT, ', '.join(
                        '["%s", "%s"]' % (uid('sheet', s.name), s.title) for s in self.sheets)))

    def _auto_flags(self):
        """Add PWR_FLAG to nets with power inputs but no power output."""
        types = {}
        for s in self.sheets:
            for p in s.parts:
                pins = {q['num']: q for ps in p.info.units.values() for q in ps}
                for num, net in p.nets.items():
                    types.setdefault(net, set()).add(pins[num]['etype'])
        have = {f for s in self.sheets for f in s.flags}
        for net, ts in types.items():
            if 'power_in' in ts and 'power_out' not in ts and net not in have:
                # put it on the first sheet that uses the net
                for s in self.sheets:
                    if any(net in p.nets.values() for p in s.parts):
                        s.flags.append(net)
                        break
        for s in self.sheets:
            s.flags = [f for f in s.flags if 'power_out' not in types.get(f, set())]

    # ---------------------------------------------------------------------
    def _write_sheet(self, s, outdir, root_uuid, page):
        sheet_uuid = uid('sheet', s.name)
        path = f'/{root_uuid}/{sheet_uuid}'
        items, libsyms = [], {}
        # one placement cell per (part, unit)
        cells = []
        for p in s.parts:
            units = sorted(p.info.units)
            for u in units:
                cells.append((p, u))
        if s.flags:
            for net in s.flags:
                cells.append(('FLAG', net))
        # measure cells
        meas = [self._measure(c) for c in cells]
        # pack into rows on the smallest paper that fits
        for paper, (W, H) in (('A3', (420, 297)), ('A2', (594, 420)), ('A1', (841, 594)), ('A0', (1189, 841))):
            pos = self._pack(meas, W - 40, H - 70)
            if pos is not None:
                break
        else:
            raise RuntimeError('sheet too big: ' + s.name)
        for (cell, m), (cx, cy) in zip(zip(cells, meas), pos):
            ox = round((20 + cx - m['x0']) / GRID) * GRID
            oy = round((25 + cy - m['y0']) / GRID) * GRID
            if cell[0] == 'FLAG':
                items += self._flag(s, cell[1], ox, oy, path, libsyms)
            else:
                items += self._place(s, cell[0], cell[1], ox, oy, path, libsyms, m)
        if s.notes:
            items.append(['text', s.notes, ['at', 20, H - 40, 0],
                          ['effects', ['font', ['size', 1.524, 1.524]], ['justify', Sym('left'), Sym('top')]],
                          ['uuid', uid(s.name, 'notes')]])
        doc = ['kicad_sch', ['version', 20230121], ['generator', Sym('eeschema')],
               ['uuid', sheet_uuid], ['paper', paper],
               self._title_block(s.title, page),
               ['lib_symbols'] + list(libsyms.values())] + items
        with open(os.path.join(outdir, s.name + '.kicad_sch'), 'w') as f:
            f.write(dump(doc) + '\n')

    def _title_block(self, title, page):
        return ['title_block', ['title', title], ['date', self.date], ['rev', self.rev],
                ['company', self.company], ['comment', 1, self.title]]

    def _label_len(self, net):
        return len(net) * CHAR_W + (4 if net in self.global_nets else 1.5)

    def _pins_world(self, p, u):
        out = []
        for q in p.info.units[u]:
            x, y = rot(q['x'], q['y'], p.rot)
            out.append(dict(q, wx=x, wy=-y, wa=(q['a'] + p.rot) % 360))
        return out

    def _measure(self, cell):
        if cell[0] == 'FLAG':
            return dict(x0=-3, y0=-8, x1=3 + self._label_len(cell[1]), y1=3)
        p, u = cell
        pts = [(rot(x, y, p.rot)) for x, y in p.info.body.get(u, [])]
        pts = [(x, -y) for x, y in pts]
        pins = self._pins_world(p, u)
        pts += [(q['wx'], q['wy']) for q in pins]
        x0 = min(x for x, _ in pts); x1 = max(x for x, _ in pts)
        y0 = min(y for _, y in pts); y1 = max(y for _, y in pts)
        bx0, bx1, by0, by1 = x0, x1, y0, y1
        for q in pins:
            net = p.nets.get(q['num'])
            ln = self._label_len(net) if net else 2
            d = (q['wa'] + 180) % 360        # label direction
            if d == 0: x1 = max(x1, q['wx'] + ln)
            elif d == 180: x0 = min(x0, q['wx'] - ln)
            elif d == 90: y0 = min(y0, q['wy'] - ln)
            else: y1 = max(y1, q['wy'] + ln)
        txt = max(len(p.ref), len(p.value)) * CHAR_W
        cx = (bx0 + bx1) / 2
        x0 = min(x0, cx - txt / 2); x1 = max(x1, cx + txt / 2)
        y0 -= 4; y1 += 4      # room for ref/value
        return dict(x0=x0 - 3, y0=y0 - 2, x1=x1 + 3, y1=y1 + 2, bx=(bx0, bx1, by0, by1))

    @staticmethod
    def _pack(meas, W, H):
        pos, x, y, rowh = [], 0, 0, 0
        for m in meas:
            w, h = m['x1'] - m['x0'], m['y1'] - m['y0']
            if x + w > W and x > 0:
                x, y, rowh = 0, y + rowh, 0
            pos.append((x, y))
            x += w
            rowh = max(rowh, h)
        return pos if y + rowh <= H else None

    def _label(self, net, x, y, d, key):
        eff_j = {0: ['justify', Sym('left')], 180: ['justify', Sym('right')],
                 90: ['justify', Sym('left')], 270: ['justify', Sym('right')]}[d]
        if net in self.global_nets:
            return ['global_label', net, ['shape', Sym('bidirectional')], ['at', x, y, d],
                    ['fields_autoplaced'],
                    ['effects', ['font', ['size', 1.27, 1.27]], eff_j], ['uuid', uid(*key)],
                    ['property', 'Intersheetrefs', '${INTERSHEET_REFS}', ['at', x, y, 0],
                     ['effects', ['font', ['size', 1.27, 1.27]], Sym('hide')]]]
        return ['label', net, ['at', x, y, d], ['fields_autoplaced'],
                ['effects', ['font', ['size', 1.27, 1.27]], eff_j], ['uuid', uid(*key)]]

    def _place(self, s, p, u, ox, oy, path, libsyms, m):
        lib = p.lib_id
        if lib not in libsyms:
            libsyms[lib] = p.custom if p.custom is not None else load_symbol(lib)
        items = []
        bx0, bx1, by0, by1 = m['bx']
        cx = ox + (bx0 + bx1) / 2
        hide = ['effects', ['font', ['size', 1.27, 1.27]], Sym('hide')]
        props = [
            ['property', 'Reference', p.ref, ['at', round(cx, 2), round(oy + m['y0'] + 4, 2), p.rot],
             ['effects', ['font', ['size', 1.27, 1.27]]]],
            ['property', 'Value', p.value, ['at', round(cx, 2), round(oy + m['y1'] - 4, 2), p.rot],
             ['effects', ['font', ['size', 1.27, 1.27]]]],
            ['property', 'Footprint', p.fp, ['at', ox, oy, 0], hide],
            ['property', 'Datasheet', '', ['at', ox, oy, 0], hide],
        ]
        if p.mpn:
            props.append(['property', 'MPN', p.mpn, ['at', ox, oy, 0], hide])
        if p.desc:
            props.append(['property', 'Description', p.desc, ['at', ox, oy, 0], hide])
        pins_all = [q for q in p.info.units[u]]
        sym = ['symbol', ['lib_id', lib], ['at', ox, oy, p.rot], ['unit', u],
               ['in_bom', Sym('yes')], ['on_board', Sym('yes')], ['dnp', Sym('yes' if p.dnp else 'no')],
               ['uuid', uid(s.name, p.ref, u)]] + props + \
            [['pin', q['num'], ['uuid', uid(s.name, p.ref, 'pin', q['num'])]] for q in pins_all] + \
            [['instances', ['project', PROJECT, ['path', path, ['reference', p.ref], ['unit', u]]]]]
        items.append(sym)
        # group pins by location so stacked pins share one label
        groups = {}
        for q in self._pins_world(p, u):
            groups.setdefault((q['wx'], q['wy']), []).append(q)
        for (wx, wy), qs in groups.items():
            nets = {p.nets[q['num']] for q in qs if q['num'] in p.nets}
            if len(nets) > 1:
                raise ValueError(f'{p.ref}: stacked pins {[q["num"] for q in qs]} on nets {nets}')
            x, y = round(ox + wx, 4), round(oy + wy, 4)
            if nets:
                d = (qs[0]['wa'] + 180) % 360
                items.append(self._label(nets.pop(), x, y, d, (s.name, p.ref, 'lbl', qs[0]['num'])))
            elif not all(q['hidden'] or q['etype'] == 'no_connect' for q in qs):
                items.append(['no_connect', ['at', x, y], ['uuid', uid(s.name, p.ref, 'nc', qs[0]['num'])]])
        return items

    def _flag(self, s, net, ox, oy, path, libsyms):
        lib = 'power:PWR_FLAG'
        if lib not in libsyms:
            libsyms[lib] = load_symbol(lib)
        ref = f'#FLG{s.num}{s.flags.index(net) + 1:02d}'
        hide = ['effects', ['font', ['size', 1.27, 1.27]], Sym('hide')]
        return [['symbol', ['lib_id', lib], ['at', ox, oy, 0], ['unit', 1],
                 ['in_bom', Sym('yes')], ['on_board', Sym('yes')], ['dnp', Sym('no')],
                 ['uuid', uid(s.name, 'flag', net)],
                 ['property', 'Reference', ref, ['at', ox, oy - 4, 0], hide],
                 ['property', 'Value', 'PWR_FLAG', ['at', ox, oy - 5.5, 0],
                  ['effects', ['font', ['size', 1.27, 1.27]]]],
                 ['property', 'Footprint', '', ['at', ox, oy, 0], hide],
                 ['property', 'Datasheet', '', ['at', ox, oy, 0], hide],
                 ['pin', '1', ['uuid', uid(s.name, 'flag', net, 'pin')]],
                 ['instances', ['project', PROJECT, ['path', path, ['reference', ref], ['unit', 1]]]]],
                self._label(net, ox, oy, 0, (s.name, 'flaglbl', net))]

    def _write_root(self, outdir, root_uuid):
        items = []
        x, y = 30, 40
        for i, s in enumerate(self.sheets):
            w, h = 60, 20
            su = uid('sheet', s.name)
            items.append(['sheet', ['at', x, y], ['size', w, h], ['fields_autoplaced'],
                          ['stroke', ['width', 0.1524], ['type', Sym('solid')]],
                          ['fill', ['color', 0, 0, 0, 0.0]], ['uuid', su],
                          ['property', 'Sheetname', s.title, ['at', x, y - 0.7116, 0],
                           ['effects', ['font', ['size', 1.27, 1.27]], ['justify', Sym('left'), Sym('bottom')]]],
                          ['property', 'Sheetfile', s.name + '.kicad_sch', ['at', x, y + h + 0.5846, 0],
                           ['effects', ['font', ['size', 1.27, 1.27]], ['justify', Sym('left'), Sym('top')]]],
                          ['instances', ['project', PROJECT, ['path', f'/{root_uuid}', ['page', str(i + 2)]]]]])
            x += 80
            if x > 300:
                x, y = 30, y + 40
        if getattr(self, 'root_notes', ''):
            items.append(['text', self.root_notes, ['at', 30, 130, 0],
                          ['effects', ['font', ['size', 1.524, 1.524]], ['justify', Sym('left'), Sym('top')]],
                          ['uuid', uid('root', 'notes')]])
        doc = ['kicad_sch', ['version', 20230121], ['generator', Sym('eeschema')],
               ['uuid', root_uuid], ['paper', 'A3'],
               self._title_block(self.title, 1), ['lib_symbols']] + items + \
            [['sheet_instances', ['path', '/', ['page', '1']]]]
        with open(os.path.join(outdir, PROJECT + '.kicad_sch'), 'w') as f:
            f.write(dump(doc) + '\n')


def write_bom(design, path):
    """Grouped CSV BOM: one line per value/footprint/MPN/DNP combination."""
    import csv
    groups = {}
    for s in design.sheets:
        for p in s.parts:
            key = (p.value, p.fp, p.mpn, p.dnp, p.lib_id)
            groups.setdefault(key, []).append(p.ref)

    def refkey(r):
        i = len(r.rstrip('0123456789'))
        return (r[:i], int(r[i:]))
    rows = sorted(groups.items(), key=lambda kv: refkey(sorted(kv[1], key=refkey)[0]))
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Qty', 'References', 'Value', 'MPN', 'Footprint', 'Symbol', 'DNP'])
        for (value, fp, mpn, dnp, lib), refs in rows:
            refs = sorted(refs, key=refkey)
            w.writerow([0 if dnp else len(refs), ' '.join(refs), value, mpn, fp, lib, 'DNP' if dnp else ''])
