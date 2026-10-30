#!/usr/bin/env python3
"""Build the starting PCB and a bundled footprint library from design.py.

Writes, next to the schematic in hardware/schematic/kicad/:
  aio.kicad_pcb   every part on its footprint and nets, placed by function
                  on a 200 x 130 mm board (see place.py), unrouted
  aio.pretty/     copies of every footprint used, so the project is
                  self-contained (Altium's Import Wizard can turn this
                  folder into a PcbLib)

Run after design.py:  python3 hardware/schematic/pcb.py
Needs KiCad 7's pcbnew Python module and the kicad-footprints library.
"""
import json
import os
import shutil
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402
from kigen import uid  # noqa: E402
import place  # noqa: E402

FPDIR = os.environ.get('KICAD_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
OUT = design.OUT


def mm(v):
    return pcbnew.FromMM(v)


def load_fp(fp):
    lib, name = fp.split(':')
    path = os.path.join(FPDIR, lib + '.pretty')
    f = pcbnew.FootprintLoad(path, name)
    if f is None:
        raise SystemExit(f'footprint not found: {fp}')
    return f, os.path.join(path, name + '.kicad_mod')


def main():
    board = pcbnew.BOARD()
    nets = {}

    def net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    lib_out = os.path.join(OUT, 'aio.pretty')
    shutil.rmtree(lib_out, ignore_errors=True)
    os.makedirs(lib_out)
    root = uid('root')
    skipped = []
    for s in design.d.sheets:
        for p in s.parts:
            if not p.fp:
                skipped.append(p.ref)
                continue
            f, src = load_fp(p.fp)
            shutil.copy(src, lib_out)
            f.SetReference(p.ref)
            f.SetValue(p.value)
            unit = min(p.info.units)
            f.SetPath(pcbnew.KIID_PATH(f'{uid("sheet", s.name)}/{uid(s.name, p.ref, unit)}'))
            for pad in f.Pads():
                n = p.nets.get(pad.GetNumber())
                if n:
                    pad.SetNet(net(n))
            board.Add(f)
    overflow = place.Placer(board, design.d).run()
    place.outline(board)
    place.region_labels(board, design.d.sheets)
    bad = place.overlaps(board)
    if bad:
        raise SystemExit(f'courtyard overlaps: {bad[:10]}')
    if overflow:
        print('placed outside their region (region full):', ' '.join(overflow))
    path = os.path.join(OUT, 'aio.kicad_pcb')
    # let KiCad write a complete .kicad_pro (importers such as Altium's read
    # it), then list the schematic sheets in it the way eeschema does
    pro = os.path.join(OUT, 'aio.kicad_pro')
    if os.path.exists(pro):
        os.remove(pro)
    pcbnew.SaveBoard(path, board)
    with open(pro) as f:
        cfg = json.load(f)
    cfg['sheets'] = [[uid('root'), 'Root']] + [[uid('sheet', s.name), s.title] for s in design.d.sheets]
    with open(pro, 'w') as f:
        json.dump(cfg, f, indent=2)
        f.write('\n')
    prl = os.path.join(OUT, 'aio.kicad_prl')
    if os.path.exists(prl):
        os.remove(prl)    # per-user UI state, not part of the design
    print(f'wrote {path}: {len(board.GetFootprints())} footprints, {len(nets)} nets; '
          f'{len(os.listdir(lib_out))} footprints in aio.pretty')
    if skipped:
        print('no footprint (by design, see docs):', ' '.join(skipped))


if __name__ == '__main__':
    main()
