#!/usr/bin/env python3
"""Build the starting PCB and a bundled footprint library from design.py.

Writes, next to the schematic in hardware/schematic/kicad/:
  aio.kicad_pcb   every part with its footprint and pad nets (unrouted),
                  grouped by sheet, inside a board outline
  aio.pretty/     copies of every footprint used, so the project is
                  self-contained (Altium's Import Wizard can turn this
                  folder into a PcbLib)

Run after design.py:  python3 hardware/schematic/pcb.py
Needs KiCad 7's pcbnew Python module and the kicad-footprints library.
"""
import os
import shutil
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design  # noqa: E402
from kigen import uid  # noqa: E402

FPDIR = os.environ.get('KICAD_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
OUT = design.OUT
GAP = 2.0          # mm between parts
ROW_W = 160.0      # mm, width of each sheet's block


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
    x0, y_block = 0.0, 0.0
    for s in design.d.sheets:
        x, y, rowh = 0.0, y_block, 0.0
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
            bb = f.GetBoundingBox(False, False)
            w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
            if x + w > ROW_W and x > 0:
                x, y, rowh = 0.0, y + rowh + GAP, 0.0
            # move so the bounding box's top-left lands on (x, y)
            dx = mm(x0 + x) - bb.GetX()
            dy = mm(y) - bb.GetY()
            f.Move(pcbnew.VECTOR2I(dx, dy))
            x += w + GAP
            rowh = max(rowh, h)
        y_block = y + rowh + 10.0
    # board outline around everything
    bb = board.ComputeBoundingBox(True)
    m = mm(5)
    rect = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetStart(pcbnew.VECTOR2I(bb.GetX() - m, bb.GetY() - m))
    rect.SetEnd(pcbnew.VECTOR2I(bb.GetRight() + m, bb.GetBottom() + m))
    board.Add(rect)
    path = os.path.join(OUT, 'aio.kicad_pcb')
    pcbnew.SaveBoard(path, board)
    print(f'wrote {path}: {len(board.GetFootprints())} footprints, {len(nets)} nets; '
          f'{len(os.listdir(lib_out))} footprints in aio.pretty')
    if skipped:
        print('no footprint (by design, see docs):', ' '.join(skipped))


if __name__ == '__main__':
    main()
