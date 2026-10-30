"""Functional component placement for the audio interface board.

Board: 200 x 130 mm, 4 layers. y = 0 is the rear edge (power / USB),
y = 130 the front panel (jacks, pots, switches, LEDs).

Floorplan (mm):
  rear  ┌──────────────┬──────────┬────────┬───────────────────┐
        │ switchers    │ digital  │ USB/PD │ XMOS + clocks     │
        │ (SEPIC, Cuk, │ supplies │        ├───────────────────┤
        │  +50 V)      │          │        │ DAC               │
        ├──────────────┴──────────┼────────┴───────────────────┤
        │ LDOs (buffer between    │ I/V + output stage         │
        │ switchers and analog)   │                            │
        ├──────────────┬──────────┼────────────────────────────┤
        │ mic input,   │ ADC      │ headphone amp, protection  │
        │ phantom feed │          │                            │
  front └──────────────┴──────────┴────────────────────────────┘

Inside each region the ICs are spread out first, then every two-pin part
is put as close as possible to the IC pin it connects to (decoupling caps
to their supply pins, feedback parts to their feedback pins). Panel parts
are fixed to the board edges, facing outwards. Placement is a first pass to
review and refine, not a finished layout.
"""
import math

import pcbnew

BOARD_W, BOARD_H = 200.0, 130.0
CLEAR = 0.4          # mm between courtyards
CORNER = 7.0         # mm keep-out in each corner for M3 mounting holes

# region per sheet: (x0, y0, x1, y1) in mm
REGIONS = {
    'pwr_input':   (2, 2, 46, 52),
    'pwr_neg':     (46, 2, 82, 52),
    'pwr_phantom': (2, 52, 46, 80),
    'pwr_digital': (82, 2, 108, 40),
    'usb_pd':      (108, 2, 136, 38),
    'xmos':        (136, 2, 198, 34),
    'clocks':      (136, 34, 198, 50),
    'dac':         (150, 50, 198, 72),
    'pwr_ldo':     (46, 52, 98, 80),
    'dac_iv':      (98, 40, 150, 80),
    'mic':         (2, 80, 76, 128),
    'adc':         (76, 80, 104, 116),
    'hpamp':       (104, 72, 198, 108),
    'hp_protect':  (104, 108, 198, 128),
}

# panel parts: ref -> (x, edge) ; the part's outward face goes to that edge
EDGE = {
    'J101': (14, 'rear'), 'J201': (122, 'rear'),
    'J501': (21, 'front'), 'RV501': (54, 'front'), 'SW501': (70, 'front'),
    'D501': (78, 'front'), 'D510': (84, 'front'), 'D201': (90, 'front'), 'D202': (96, 'front'),
    'RV301': (124, 'front'), 'SW401': (143, 'front'), 'J402': (158, 'front'),
    'J401': (182, 'front'),
}

GROUND_LIKE = {'GND', 'CHASSIS'}


def mm(v):
    return pcbnew.FromMM(v)


def tomm(v):
    return pcbnew.ToMM(v)


def courtyard_bbox(f):
    """Courtyard bounding box (mm) of a footprint at its current position."""
    f.BuildCourtyardCaches()
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        cy = f.GetCourtyard(layer)
        if cy.OutlineCount():
            bb = cy.BBox()
            return (tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom()))
    bb = f.GetBoundingBox(False, False)
    return (tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom()))


def move_to(f, x, y):
    f.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))


class Placer:
    def __init__(self, board, design):
        self.board, self.design = board, design
        self.fp = {f.GetReference(): f for f in board.GetFootprints()}
        self.boxes = {}          # ref -> placed courtyard bbox
        self.part = {p.ref: (s, p) for s in design.sheets for p in s.parts}

    # -- geometry ---------------------------------------------------------
    def free(self, box, region):
        x0, y0, x1, y1 = box
        rx0, ry0, rx1, ry1 = region
        if x0 < rx0 or y0 < ry0 or x1 > rx1 or y1 > ry1:
            return False
        for cx0, cy0 in ((0, 0), (BOARD_W - CORNER, 0), (0, BOARD_H - CORNER), (BOARD_W - CORNER, BOARD_H - CORNER)):
            if x1 > cx0 and x0 < cx0 + CORNER and y1 > cy0 and y0 < cy0 + CORNER:
                return False
        for b in self.boxes.values():
            if x0 < b[2] + CLEAR and x1 > b[0] - CLEAR and y0 < b[3] + CLEAR and y1 > b[1] - CLEAR:
                return False
        return True

    def try_place(self, ref, x, y, region, rotations=(0, 90)):
        """Put ref as close to (x, y) as possible inside region. Returns success."""
        f = self.fp[ref]
        best = None
        for rot in rotations:
            f.SetOrientationDegrees(rot)
            move_to(f, 0, 0)
            bx = courtyard_bbox(f)          # offsets of the courtyard from the origin
            for r in [i * 0.5 for i in range(0, 200)]:
                found = None
                steps = max(1, int(2 * math.pi * r / 0.5)) if r else 1
                for k in range(steps):
                    a = 2 * math.pi * k / steps
                    px, py = round(x + r * math.cos(a), 2), round(y + r * math.sin(a), 2)
                    box = (px + bx[0], py + bx[1], px + bx[2], py + bx[3])
                    if self.free(box, region):
                        found = (r, px, py, rot, box)
                        break
                if found:
                    if best is None or found[0] < best[0]:
                        best = found
                    break
        if best is None:
            return False
        _, px, py, rot, box = best
        f.SetOrientationDegrees(rot)
        move_to(f, px, py)
        self.boxes[ref] = box
        return True

    # -- panel parts --------------------------------------------------------
    def place_edge(self, ref, x, edge):
        """Rotate so the side of the courtyard that sticks out furthest past
        the pads (the mating face of a horizontal jack, pot or USB-C) faces
        the board edge, then put that side on the edge."""
        f = self.fp[ref]
        best = None
        for rot in (0, 90, 180, 270):
            f.SetOrientationDegrees(rot)
            move_to(f, 0, 0)
            pads = [(tomm(p.GetPosition().x), tomm(p.GetPosition().y)) for p in f.Pads()]
            x0, y0, x1, y1 = courtyard_bbox(f)
            reach = (y1 - max(py for _, py in pads)) if edge == 'front' else (min(py for _, py in pads) - y0)
            if best is None or reach > best[0] + 0.01:
                best = (reach, rot, (x0, y0, x1, y1))
        _, rot, (x0, y0, x1, y1) = best
        f.SetOrientationDegrees(rot)
        px = x - (x0 + x1) / 2
        py = (BOARD_H - y1) if edge == 'front' else -y0
        move_to(f, px, py)
        self.boxes[ref] = (px + x0, py + y0, px + x1, py + y1)

    # -- regions ------------------------------------------------------------
    def place_sheet(self, s):
        region = REGIONS[s.name]
        parts = [p for p in s.parts if p.ref in self.fp and p.ref not in self.boxes]
        multi = [p for p in parts if len(self.fp[p.ref].Pads()) > 2]
        two = [p for p in parts if len(self.fp[p.ref].Pads()) <= 2]
        # 1) ICs / multi-pin parts spread across the region, largest first
        multi.sort(key=lambda p: -self._area(p.ref))
        rx0, ry0, rx1, ry1 = region
        n = max(1, len(multi))
        cols = max(1, round(math.sqrt(n * (rx1 - rx0) / max(1, ry1 - ry0))))
        rows = math.ceil(n / cols)
        for i, p in enumerate(multi):
            cx = rx0 + (rx1 - rx0) * ((i % cols) + 0.5) / cols
            cy = ry0 + (ry1 - ry0) * ((i // cols) + 0.5) / rows
            self._must(p.ref, cx, cy, region)
        # 2) two-pin parts next to the IC pad they connect to
        anchors = {p.ref for p in multi} | {r for r in self.boxes}
        # big parts (bulk caps, inductors) first so they get room, then the
        # small ones in schematic order, so helpers follow the part they serve
        big = sorted([p for p in two if self._area(p.ref) > 40], key=lambda p: -self._area(p.ref))
        small = [p for p in two if p not in big]
        for p in big + small:
            x, y = self._target(p, anchors, region, s)
            self._must(p.ref, x, y, region)
            anchors.add(p.ref)       # lets RC chains form next to each other

    def _area(self, ref):
        x0, y0, x1, y1 = courtyard_bbox(self.fp[ref])
        return (x1 - x0) * (y1 - y0)

    def _must(self, ref, x, y, region):
        if self.try_place(ref, x, y, region):
            return
        # region full: allow the whole board as a fallback, reported later
        if not self.try_place(ref, x, y, (0, 0, BOARD_W, BOARD_H)):
            raise RuntimeError(f'cannot place {ref}')
        self.overflow.append(ref)

    def _target(self, p, anchors, region, sheet):
        """Point just outside the pad this part should sit next to.

        Signal parts go next to a pad on the same sheet that shares a signal
        net. Supply-only parts (decoupling caps) go next to the supply pin of
        the IC they are drawn with: the nearest preceding multi-pin part in
        the sheet that has a pad on that rail."""
        order = [q.ref for q in sheet.parts]
        here = order.index(p.ref)
        local = [r for r in anchors if r in self.boxes and r in order]
        nets = [n for n in p.nets.values() if n not in GROUND_LIKE]
        signal = [n for n in nets if not self._is_rail(n)]
        pick = None
        if signal:
            for ref in sorted(local, key=lambda r: abs(order.index(r) - here)):
                pad = next((q for q in self.fp[ref].Pads() if q.GetNetname() in signal), None)
                if pad:
                    pick = (pad, self.fp[ref])
                    break
        if pick is None and nets:
            ics = [q.ref for q in sheet.parts[:here][::-1]
                   if q.ref in self.boxes and len(self.fp[q.ref].Pads()) > 2]
            ics += [r for r in local if len(self.fp[r].Pads()) > 2 and r not in ics]
            for ref in ics:
                pads = [q for q in self.fp[ref].Pads() if q.GetNetname() in nets]
                if pads:
                    # the supply pin with the fewest parts already next to it
                    pad = min(pads, key=lambda q: self._crowd(q))
                    pick = (pad, self.fp[ref])
                    break
        if pick is None:
            rx0, ry0, rx1, ry1 = region
            return (rx0 + rx1) / 2, (ry0 + ry1) / 2
        pad, f = pick
        x, y = tomm(pad.GetPosition().x), tomm(pad.GetPosition().y)
        c = f.GetPosition()
        cx, cy = tomm(c.x), tomm(c.y)
        d = math.hypot(x - cx, y - cy) or 1
        return x + 2.0 * (x - cx) / d, y + 2.0 * (y - cy) / d     # just outside the pad

    @staticmethod
    def _is_rail(n):
        return n.startswith(('+', '-')) or n in ('VIN', 'VBUS', 'VBUS_SW', 'DCIN')

    def _crowd(self, pad):
        x, y = tomm(pad.GetPosition().x), tomm(pad.GetPosition().y)
        return sum(1 for b in self.boxes.values()
                   if abs((b[0] + b[2]) / 2 - x) < 4 and abs((b[1] + b[3]) / 2 - y) < 4)

    def run(self):
        self.overflow = []
        for ref, (x, edge) in EDGE.items():
            if ref in self.fp:
                self.place_edge(ref, x, edge)
        for s in self.design.sheets:
            self.place_sheet(s)
        return self.overflow


def outline(board):
    rect = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    rect.SetLayer(pcbnew.Edge_Cuts)
    rect.SetStart(pcbnew.VECTOR2I(0, 0))
    rect.SetEnd(pcbnew.VECTOR2I(mm(BOARD_W), mm(BOARD_H)))
    board.Add(rect)


def region_labels(board, sheets):
    for s in sheets:
        x0, y0, x1, y1 = REGIONS[s.name]
        box = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
        box.SetLayer(pcbnew.Cmts_User)
        box.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        box.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        box.SetWidth(mm(0.1))
        board.Add(box)
        t = pcbnew.PCB_TEXT(board)
        t.SetText(s.title)
        t.SetLayer(pcbnew.Cmts_User)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.2), mm(1.2)))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        t.SetPosition(pcbnew.VECTOR2I(mm(x0 + 0.5), mm(y0 + 1)))
        board.Add(t)


def overlaps(board):
    """Pairs of footprints whose courtyards overlap (bbox test)."""
    boxes = [(f.GetReference(), courtyard_bbox(f)) for f in board.GetFootprints()]
    bad = []
    for i, (ra, a) in enumerate(boxes):
        for rb, b in boxes[i + 1:]:
            if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
                bad.append((ra, rb))
    return bad
