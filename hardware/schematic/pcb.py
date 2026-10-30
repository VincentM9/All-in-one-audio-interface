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
import json
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
BLOCK_W = 70.0     # mm, max width of one sheet's cluster
BOARD_W = 300.0    # mm, max width of the packed clusters
BLOCK_GAP = 8.0    # mm between clusters


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
    # 1) pack each sheet's parts into its own block (parts in schematic
    #    order, so an IC sits next to the passives that belong to it)
    blocks = []
    for s in design.d.sheets:
        placed, x, y, rowh = [], 0.0, 0.0, 0.0
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
            if x + w > BLOCK_W and x > 0:
                x, y, rowh = 0.0, y + rowh + GAP, 0.0
            placed.append((f, x - pcbnew.ToMM(bb.GetX()), y - pcbnew.ToMM(bb.GetY())))
            x += w + GAP
            rowh = max(rowh, h)
        width = max([pcbnew.ToMM(f.GetBoundingBox(False, False).GetWidth()) + dx + pcbnew.ToMM(f.GetBoundingBox(False, False).GetX())
                     for f, dx, dy in placed] + [10])
        blocks.append((s, placed, width, y + rowh))
    # 2) shelf-pack the blocks, power sections first, audio last, each with
    #    its sheet title on the User.Comments layer
    bx, by, shelf = 0.0, 0.0, 0.0
    for s, placed, w, h in blocks:
        if bx + w > BOARD_W and bx > 0:
            bx, by, shelf = 0.0, by + shelf + BLOCK_GAP, 0.0
        for f, dx, dy in placed:
            f.Move(pcbnew.VECTOR2I(mm(bx + dx), mm(by + 4 + dy)))
        t = pcbnew.PCB_TEXT(board)
        t.SetText(s.title)
        t.SetLayer(pcbnew.Cmts_User)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetPosition(pcbnew.VECTOR2I(mm(bx), mm(by + 1)))
        board.Add(t)
        bx += w + BLOCK_GAP
        shelf = max(shelf, h + 4)
    # board outline around everything
    bb = board.ComputeBoundingBox(False)   # all items, not edges only
    m = mm(5)
    rect = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetStart(pcbnew.VECTOR2I(bb.GetX() - m, bb.GetY() - m))
    rect.SetEnd(pcbnew.VECTOR2I(bb.GetRight() + m, bb.GetBottom() + m))
    board.Add(rect)
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
