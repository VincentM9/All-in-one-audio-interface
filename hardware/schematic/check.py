#!/usr/bin/env python3
"""Check the generated KiCad schematic against the intended netlist.

1. Exports the netlist with kicad-cli (KiCad's own connectivity engine).
2. Compares it with design.py net by net (as sets of ref/pin), ignoring the
   path prefixes KiCad adds to local net names.
3. Runs a few electrical-rule checks of its own (KiCad 7's CLI has no ERC):
   single-pin nets, power inputs without a source, output-to-output shorts.

Run:  python3 hardware/schematic/check.py      (exit code 0 = all good)
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402
from sexp import find, first, parse  # noqa: E402


def exported_nets(root):
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, 'aio.net')
        r = subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr',
                            '-o', out, root], capture_output=True, text=True)
        if r.returncode:
            sys.exit('kicad-cli failed: ' + r.stdout + r.stderr)
        net = parse(open(out).read())
    nets = {}
    for n in find(first(net, 'nets'), 'net'):
        name = first(n, 'name')[1]
        nodes = frozenset((first(x, 'ref')[1], first(x, 'pin')[1]) for x in find(n, 'node'))
        nets[name] = nodes
    comps = {first(c, 'ref')[1] for c in find(first(net, 'components'), 'comp')}
    return nets, comps


def main():
    d = design.d
    d.write(design.OUT)
    want = {}
    pin_type = {}
    for s in d.sheets:
        for p in s.parts:
            pins = {q['num']: q for ps in p.info.units.values() for q in ps}
            for num, net in p.nets.items():
                want.setdefault(net, set()).add((p.ref, num))
                pin_type[(p.ref, num)] = pins[num]['etype']
    got, comps = exported_nets(os.path.join(design.OUT, 'aio.kicad_sch'))
    by_nodes = {nodes: name for name, nodes in got.items()}
    errors, warnings = [], []

    # 1. every intended net must exist exactly, with nothing extra on it
    for net, nodes in sorted(want.items()):
        nodes = frozenset(nodes)
        if nodes in by_nodes:
            continue
        hits = [(n, g) for n, g in got.items() if g & nodes]
        errors.append(f'net {net}: expected {sorted(nodes)}; KiCad has ' +
                      '; '.join(f'{n}={sorted(g)}' for n, g in hits))
    # 2. nothing KiCad connected that we did not intend
    intended = {frozenset(v) for v in want.values()}
    for name, nodes in got.items():
        if nodes in intended:
            continue
        real = {n for n in nodes if not n[0].startswith('#')}
        if name.startswith('unconnected-') and len(real) <= 1:
            continue
        if not real:
            continue
        if any(frozenset(real) == i for i in intended):
            continue
        errors.append(f'unexpected KiCad net {name}: {sorted(nodes)}')
    # 3. all parts present
    refs = {p.ref for s in d.sheets for p in s.parts}
    missing = refs - comps
    if missing:
        errors.append(f'parts missing from netlist: {sorted(missing)}')

    # 4. simple ERC
    for net, nodes in want.items():
        if len(nodes) == 1:
            errors.append(f'single-pin net {net}: {sorted(nodes)}')
        types = [pin_type[n] for n in nodes]
        outs = [n for n in nodes if pin_type[n] in ('output', 'power_out')]
        if len(outs) > 1 and not all(pin_type[n] == 'power_out' for n in outs):
            errors.append(f'outputs shorted on {net}: {sorted(outs)}')
        if 'input' in types and not any(t in ('output', 'power_out', 'passive', 'bidirectional',
                                              'open_collector', 'tri_state', 'power_in')
                                        for t in types):
            warnings.append(f'input with no driver on {net}')
    flagged = {f for s in d.sheets for f in s.flags}
    for net, nodes in want.items():
        types = {pin_type[n] for n in nodes}
        if 'power_in' in types and 'power_out' not in types and net not in flagged:
            errors.append(f'power input without source/PWR_FLAG on {net}')

    n_pins = sum(len(v) for v in want.values())
    print(f'{len(refs)} parts, {len(want)} nets, {n_pins} connected pins checked')
    for w in warnings:
        print('WARN ', w)
    for e in errors:
        print('ERROR', e)
    print('OK' if not errors else f'{len(errors)} error(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
