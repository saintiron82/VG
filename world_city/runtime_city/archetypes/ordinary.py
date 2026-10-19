"""Dimension-authored ordinary buildings in the established common master grammar.

This module authors continuous source geometry, never samples cells or scales an
existing house. All sampling/rendering belongs to common/core.py and render_data.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

STYLES = ("merchant", "old_timber", "port", "artisan", "garden", "institutional")
ROOF_FORMS = ("gable", "steep_gable", "hip", "shed", "flat", "twin_gable_z", "twin_gable_x")
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "voxel_character/common/assets/house/master.json"
SCHEMA = "riverstone.voxel.master.v1"
IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
ROTATIONS = {
    "front": IDENTITY,
    "back": [[-1, 0, 0], [0, 1, 0], [0, 0, -1]],
    "right": [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
    "left": [[0, 0, -1], [0, 1, 0], [1, 0, 0]],
}


@lru_cache(maxsize=1)
def _source():
    raw = SOURCE.read_bytes()
    master = json.loads(raw)
    return master, hashlib.sha256(raw).hexdigest()


def _finite(spec, key, default=None):
    value = spec.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    return float(value)


def _box(lo, hi):
    # No pitch-dependent exterior expansion: the authoring envelope is strict.
    if not all(a < b for a, b in zip(lo, hi)):
        raise ValueError(f"degenerate authored box: {lo}, {hi}")
    return {"kind": "box", "min": list(lo), "max": list(hi)}


def _extrusion(polygon, z0, z1):
    return {"kind": "extrusion", "polygon": [list(p) for p in polygon], "z_min": z0, "z_max": z1}


class _Assembly:
    def __init__(self):
        self.components = []
        self.instances = []

    def component(self, name, category):
        c = {"id": name, "parts": [{"id": "solid", "pivot": [0, 0, 0],
             "metadata": {"source_category": category, "dynamic": False}}], "operations": []}
        self.components.append(c)
        return c

    def paint(self, c, name, shape, material, part="solid"):
        if not any(p["id"] == part for p in c["parts"]):
            c["parts"].append({"id": part, "pivot": [0, 0, 0]})
        c["operations"].append({"id": name, "part": part, "action": "paint", "shape": shape, "material": material})

    def cut(self, c, name, shape):
        c["operations"].append({"id": name, "part": "solid", "action": "cut", "shape": shape})

    def instance(self, c, name=None, position=(0, 0, 0), side="front"):
        self.instances.append({"id": name or c["id"], "component": c["id"],
            "transform": {"translation": list(position), "basis": deepcopy(ROTATIONS[side])}})


def _window(a, c, name, x, y, width, height, shutter=False):
    """A real wall aperture, closed glazing and separately authored timber frame."""
    l, r, b, t = x-width/2, x+width/2, y, y+height
    a.cut(c, name+"_aperture", _box((l, b, -.65), (r, t, .25)))
    a.paint(c, name+"_glass", _box((l, b, -.5), (r, t, .02)), "glass", "windows")
    frame = .22
    for suffix, lo, hi in (
        ("left", (l-frame, b-frame, -.5), (l+frame, t+frame, .14)),
        ("right", (r-frame, b-frame, -.5), (r+frame, t+frame, .14)),
        ("sill", (l-frame, b-frame, -.5), (r+frame, b+frame, .20)),
        ("lintel", (l-frame, t-frame, -.5), (r+frame, t+frame, .14)),
    ):
        a.paint(c, name+"_"+suffix, _box(lo, hi), "timber_light", "windows")
    if width >= 1.6:
        a.paint(c, name+"_mullion", _box((x-.12, b, -.5), (x+.12, t, .15)), "timber", "windows")
    if shutter:
        sw = .35
        a.paint(c, name+"_shutter", _box((l-frame-sw, b, -.15), (l-frame, t, .22)), "door", "windows")


def _door(a, c, x, y, width, height, double=False):
    l, r, t = x-width/2, x+width/2, y+height
    a.cut(c, "door_aperture", _box((l, y, -.65), (r, t, .25)))
    if double:
        a.paint(c, "closed_left_leaf", _box((l, y, -.52), (x, t, .04)), "door", "door")
        a.paint(c, "closed_right_leaf", _box((x, y, -.52), (r, t, .04)), "door_dark", "door")
    else:
        a.paint(c, "closed_door_leaf", _box((l, y, -.52), (r, t, .04)), "door", "door")
    for suffix, lo, hi in (
        ("left", (l-.20, y, -.55), (l+.05, t+.25, .20)),
        ("right", (r-.05, y, -.55), (r+.20, t+.25, .20)),
        ("head", (l-.20, t-.05, -.55), (r+.20, t+.25, .20)),
    ):
        a.paint(c, "door_frame_"+suffix, _box(lo, hi), "timber_dark", "door_frame")
    for k, yy in enumerate((y+height*.25, y+height*.73)):
        a.paint(c, f"door_iron_strap_{k}", _box((l+.05, yy-.09, -.02), (r-.05, yy+.09, .16)), "iron", "door")


def _wall(a, name, span, floor_h, style, floor, front=False, era="rebuilt"):
    c = a.component(name, "wall_bay_assembly")
    half = span/2
    material = "stone" if style == "institutional" and floor == 0 else "plaster"
    if style == "garden":
        material = "plaster_light"
    if style == "port" and floor == 0:
        material = "stone_dark"
    a.paint(c, "wall_panel", _box((-half, 0, -.5), (half, floor_h, 0)), material)
    if floor == 0 and style not in ("institutional", "port"):
        base_h = {"early": .40, "rebuilt": .70, "late": 1.00}[era]
        a.paint(c, "era_stone_dado", _box((-half, 0, -.5), (half, base_h, .02)), "stone")
    # Stable broad material fields rather than stochastic grain or individual bricks.
    for suffix, y0, y1 in (("sill", 0, .35), ("head", floor_h-.35, floor_h)):
        a.paint(c, "beam_"+suffix, _box((-half, y0, -.5), (half, y1, .10)), "timber")
    bay_positions = [-half+.22, half-.22]
    if style == "old_timber":
        bay_positions += [-span*.17, span*.24]
    elif style not in ("garden", "institutional") and span >= 7:
        bay_positions += [-span*.22, span*.22]
    if era == "early" and span > 5 and style not in ("old_timber", "institutional"):
        bay_positions.append(-span*.13)
    for k, x in enumerate(bay_positions):
        a.paint(c, f"post_{k}", _box((x-.20, 0, -.5), (x+.20, floor_h, .12)), "timber")
    if style == "old_timber" and floor > 0:
        # Unequal, triangular-braced bays, kept inside the continuous envelope.
        for k, (x0, x1) in enumerate(((-half+.45, -span*.17-.25), (span*.24+.25, half-.45))):
            if x1-x0 > .45:
                a.paint(c, f"diagonal_brace_{k}", _extrusion(
                    [(x0, .45), (x0+.24, .45), (x1, floor_h-.40), (x1-.24, floor_h-.40)], -.5, .13), "timber")
    window_y = max(.8, floor_h*.34)
    window_h = min(1.35, floor_h-window_y-.45)
    centers = []
    if front and floor == 0:
        special = style in ("merchant", "artisan") and span >= 4.2
        door_x = -span*.28 if special else 0
        door_w = min(2.8, span*.48) if style == "port" else min(1.35, span*.31)
        door_h = min(2.65 if style == "port" else 2.15, floor_h-.45)
        _door(a, c, door_x, 0, door_w, door_h, style == "port")
        if special:
            # The shop/work bay is physically cut through plaster and glazed.
            width = min(2.5, span*.35)
            _window(a, c, "shop_opening" if style == "merchant" else "work_bay", span*.20,
                    .70, width, min(1.65, floor_h-1.2))
        elif style != "port" and span >= 5.5:
            centers = [-span*.31, span*.31]
    elif style == "port":
        # Storehouses intentionally have far fewer, higher openings.
        centers = [0] if floor > 0 or not front else []
        window_y = max(.85, floor_h*.55)
        window_h = min(.95, floor_h-window_y-.40)
    else:
        count = max(1, min(5, int(span/(2.7 if era == "late" else 3.2 if era == "early" else 3.0))))
        centers = [(i-(count-1)/2)*min(3.0, span/(count+.5)) for i in range(count)]
        if style == "old_timber" and len(centers) > 1:
            centers[0] += .20
    for i, x in enumerate(centers):
        width = min(1.45, span*.35)
        # Leave generous margins for shutters so nothing escapes the side envelope.
        _window(a, c, f"window_{i}", x, window_y, width, window_h,
                shutter=style in ("old_timber", "garden") and span >= 5 and abs(x)+width/2+.7 < half)
    return c


def _roof(a, form, w, z0, z1, eave, peak, name="roof", position=(0,0,0), placement_side="front"):
    c = a.component(name, "roof_surface")
    half = w/2
    if form == "hip":
        # A continuously authored six-course hipped roof, not a sampled LOD.
        courses = 6
        shrink_x = max(.1, half-.55)
        shrink_z = min((z1-z0)/2-.55, half*.82)
        dy = (peak-eave)/courses
        for i in range(courses):
            f, next_f = i/courses, (i+1)/courses
            x0, x1 = -half+shrink_x*f, half-shrink_x*f
            zz0, zz1 = z0+shrink_z*f, z1-shrink_z*f
            y0, y1 = eave+dy*i, eave+dy*(i+1)
            sx, sz = shrink_x/courses+.50, shrink_z/courses+.50
            mat = "slate_light" if i == 3 else "slate"
            if i == courses-1:
                a.paint(c, f"hip_cap_{i}", _box((x0, y0, zz0), (x1, y1, zz1)), mat)
            else:
                for side, lo, hi in (
                    ("left", (x0,y0,zz0), (min(x0+sx,x1),y1,zz1)),
                    ("right", (max(x1-sx,x0),y0,zz0), (x1,y1,zz1)),
                    ("back", (x0,y0,zz0), (x1,y1,min(zz0+sz,zz1))),
                    ("front", (x0,y0,max(zz1-sz,zz0)), (x1,y1,zz1)),
                ):
                    a.paint(c, f"hip_course_{i}_{side}", _box(lo,hi), mat)
    elif form == "flat":
        a.paint(c, "flat_slate_deck", _box((-half, peak-.50, z0), (half, peak, z1)), "slate")
        for side in (-1,1):
            x0 = -half if side < 0 else half-.40
            a.paint(c, f"flat_edge_{side}", _box((x0, peak-.65, z0), (x0+.40, peak, z1)), "stone")
    else:
        sections = [(-half, eave, half, peak)] if form == "shed" else [(-half,eave,0,peak),(0,peak,half,eave)]
        for side, (xa,ya,xb,yb) in enumerate(sections):
            for band in range(3):
                fa, fb = band/3, (band+1)/3
                x0,y0 = xa+(xb-xa)*fa, ya+(yb-ya)*fa
                x1,y1 = xa+(xb-xa)*fb, ya+(yb-ya)*fb
                poly = [(x0,y0-.55),(x1,y1-.55),(x1,y1),(x0,y0)]
                mat = "slate_light" if band == 1 and side == 0 else "slate"
                a.paint(c, f"slope_{side}_band_{band}", _extrusion(poly,z0,z1), mat)
        if form != "shed":
            a.paint(c, "ridge_line", _box((-.25,peak-.35,z0),(.25,peak,z1)), "slate_dark")
    a.instance(c, position=position, side=placement_side)
    return c


def make_master(spec: Mapping) -> dict:
    """Return a fresh common master with a strict total authoring envelope.

    Required: asset_id, width_m, depth_m, floors, style. Optional: roof_form,
    height_m. ``lod``/``detailed`` are accepted compatibility hints and have no
    effect at all: source geometry, metadata and source hash remain identical.
    Positive-Y is up, positive-Z is the closed entrance, and ground is Y=0.
    """
    if not isinstance(spec, Mapping):
        raise TypeError("spec must be a mapping")
    asset_id = spec.get("asset_id")
    if not isinstance(asset_id, str) or not asset_id:
        raise ValueError("asset_id must be a nonempty string")
    w, d = _finite(spec, "width_m"), _finite(spec, "depth_m")
    if w < 3 or d < 3.5 or w > 80 or d > 100:
        raise ValueError("ordinary building envelope requires 3 <= width <= 80 and 3.5 <= depth <= 100 metres")
    floors = spec.get("floors")
    if type(floors) is not int or not 1 <= floors <= 8:
        raise ValueError("floors must be an integer from 1 to 8")
    style = spec.get("style")
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    form = spec.get("roof_form", "gable")
    form = {"hipped":"hip", "pitched":"gable", "steep":"steep_gable", "gable_steep":"steep_gable"}.get(form,form)
    if form not in ROOF_FORMS:
        raise ValueError(f"roof_form must be one of {ROOF_FORMS}")
    era = spec.get("construction_era", "rebuilt")
    if era not in ("early", "rebuilt", "late"):
        raise ValueError("construction_era must be early, rebuilt, or late")
    roof_cross = w/2 if form == "twin_gable_z" else (d-.30)/2 if form == "twin_gable_x" else w
    roof_rise = min(4.5, max(1.5, roof_cross*.28))
    if form == "steep_gable":
        roof_rise = min(6.0, max(2.4,w*.42))
    elif form == "shed":
        roof_rise = min(2.4, max(1.0,w*.16))
    elif form == "flat":
        roof_rise = .6
    height = _finite(spec, "height_m", .5+floors*3.0+roof_rise+.5)
    if height < .5+floors*2.25+1.0:
        raise ValueError("height_m does not leave usable storeys and a roof")
    roof_rise = min(roof_rise, height-.5-floors*2.25-.5)
    peak = height-.5
    eave = peak-roof_rise
    fh = (eave-.5)/floors
    source, source_hash = _source()
    a = _Assembly()
    reserve = min(1.50 if style in ("merchant","artisan") else 1.10, d*.27)
    bx = w/2-.50
    back, front = -d/2+.50, d/2-reserve
    center_z = (back+front)/2
    overhang = .28 if style == "old_timber" and floors > 1 else 0
    base = a.component("foundation", "stone_foundation")
    a.paint(base, "stone_plinth", _box((-bx,0,back),(bx,.50,front)), "stone_dark")
    # Low stone doorstep is the only structure in the reserved entrance strip.
    door_x = -(2*bx-2*overhang)*.28 if style in ("merchant","artisan") and 2*bx-2*overhang >= 4.2 else 0
    step_w = min(2.8 if style == "port" else 1.8, w-1)
    a.paint(base, "front_threshold", _box((door_x-step_w/2,0,front-.1),(door_x+step_w/2,.50,d/2)), "stone_light")
    a.instance(base)
    for floor in range(floors):
        y = .5+floor*fh
        inset = overhang if floor == 0 else 0
        x = bx-inset
        z0, z1 = back+inset, front-inset
        floor_c = a.component(f"floor_{floor}", "structural_floor")
        a.paint(floor_c, "floor_slab", _box((-x,y-.05,z0),(x,y+.40,z1)), "timber_dark")
        a.instance(floor_c)
        for side, span, pos in (
            ("front",2*x,(0,y,z1)), ("back",2*x,(0,y,z0)),
            ("right",z1-z0,(x,y,(z0+z1)/2)), ("left",z1-z0,(-x,y,(z0+z1)/2)),
        ):
            wall = _wall(a, f"wall_{floor}_{side}",span,fh,style,floor,side=="front",era)
            a.instance(wall, position=pos, side=side)
    attic = a.component("attic_support", "roof_support")
    a.paint(attic,"ceiling",_box((-bx,eave-.25,back),(bx,eave,front)),"timber_dark")
    if form in ("gable","steep_gable","shed"):
        poly = [(-bx,eave-.15),(bx,eave-.15),(bx,peak-.45)] if form == "shed" else [(-bx,eave-.15),(bx,eave-.15),(0,peak-.45)]
        # Separate front/back infill, not a solid triangular house volume.
        for name,z0,z1 in (("front",front-.5,front),("back",back,back+.5)):
            a.paint(attic,"gable_"+name,_extrusion(poly,z0,z1),"plaster")
    if form == "twin_gable_z":
        for ridge, (x0,x1,cx) in enumerate(((-bx,0,-w/4),(0,bx,w/4))):
            poly = [(x0,eave-.15),(x1,eave-.15),(cx,peak-.45)]
            for name,z0,z1 in (("front",front-.5,front),("back",back,back+.5)):
                a.paint(attic,f"twin_{ridge}_{name}",_extrusion(poly,z0,z1),"plaster")
    elif form == "twin_gable_x":
        midpoint = (-d/2+d/2-.30)/2
        for ridge,(z0,z1,cz) in enumerate(((back,midpoint,-d/2+(d-.30)/4),(midpoint,front,-d/2+3*(d-.30)/4))):
            poly = [(-z1,eave-.15),(-z0,eave-.15),(-cz,peak-.45)]
            for name,x0,x1 in (("left",-bx,-bx+.5),("right",bx-.5,bx)):
                a.paint(attic,f"twin_{ridge}_{name}",_extrusion(poly,x0,x1),"plaster")
                attic["operations"][-1]["transform"] = {"basis":deepcopy(ROTATIONS["right"])}
    a.instance(attic)
    roof_z1 = d/2-.30
    if form == "twin_gable_z":
        for i,x in enumerate((-w/4,w/4)):
            _roof(a,"gable",w/2,-d/2,roof_z1,eave,peak,f"roof_{i}",(x,0,0))
    elif form == "twin_gable_x":
        roof_depth = d-.30
        for i,z in enumerate((-d/2+roof_depth/4,-d/2+3*roof_depth/4)):
            _roof(a,"gable",roof_depth/2,-w/2,w/2,eave,peak,f"roof_{i}",(0,0,z),"right")
    else:
        _roof(a,form,w,-d/2,roof_z1,eave,peak)
    if style in ("merchant","artisan") and 2*bx >= 4.2:
        canopy = a.component("shop_canopy", "shopfront_canopy")
        left,right = max(-bx+.25,door_x+.9),bx-.25
        if right-left > .6:
            canopy_y = .5+min(2.40,fh-.35)
            a.paint(canopy,"sloping_canopy",_extrusion(
                [(front,canopy_y),(d/2-.10,canopy_y-.25),(d/2-.10,canopy_y+.10),(front,canopy_y+.35)],
                left,right),"slate_light")
            # Extrusion's local X becomes world Z; local Z becomes world -X.
            # Reflect the x span through its placement to preserve a proper rotation.
            canopy["operations"][0]["shape"]["z_min"] = -right
            canopy["operations"][0]["shape"]["z_max"] = -left
            a.instance(canopy,side="left")
    chimney = a.component("chimney", "masonry_chimney")
    cx,cz = min(bx-.5,w*.20), max(back+.7,center_z-.6)
    ch_w = .9 if style == "artisan" else .65
    bottom = max(.5,eave-.6)
    a.paint(chimney,"shaft",_box((cx-ch_w/2,bottom,cz-ch_w/2),(cx+ch_w/2,height-.25,cz+ch_w/2)),"stone")
    a.paint(chimney,"cap",_box((cx-ch_w/2-.10,height-.35,cz-ch_w/2-.10),(cx+ch_w/2+.10,height,cz+ch_w/2+.10)),"stone_dark")
    if style == "artisan":
        # Taller external work-flue identity continues to the ground-floor workshop.
        a.paint(chimney,"workshop_flue",_box((cx-.45,.5,cz-.45),(cx+.45,bottom+.2,cz+.45)),"stone_dark")
    a.instance(chimney)
    # Exact source module, immutable and unscaled. Placed safely inside the envelope.
    rail = deepcopy(next(c for c in source["components"] if c["id"] == "eave_rail"))
    a.components.append(rail)
    rail_y = .5+min(2.15,fh-.45)+.42
    a.instance(rail,"entry_source_eave_rail",(door_x-.75,rail_y,front+.12))
    constraints = [
        {"id":"foundation_present","kind":"nonempty","selector":{"instance":"foundation"}},
        {"id":"roof_present","kind":"nonempty","selector":{"instance":["roof","roof_0","roof_1"]}},
        {"id":"closed_entrance_present","kind":"nonempty","selector":{"part":"door"}},
        {"id":"masonry_chimney_present","kind":"nonempty","selector":{"instance":"chimney"}},
        {"id":"walls_present","kind":"nonempty","selector":{"material":["plaster","plaster_light","stone","stone_dark"]}},
        {"id":"structural_floors_present","kind":"nonempty","selector":{"instance":"floor_0"}},
    ]
    return {
        "schema":SCHEMA,"id":asset_id,"revision":1,
        "axes":{"up":"+Y","front":"+Z","right":"+X"},"grid_origin":[0,0,0],
        "materials":deepcopy(source["materials"]),"components":a.components,"instances":a.instances,
        "assembly_cuts":[],"constraints":constraints,
        "metadata":{
            "authoring":"dimension_authored_modular_assembly_no_mesh_scaling",
            "style":style,"roof_form":form,"construction_era":era,"floors":floors,"floor_height_m":fh,
            "envelope":{"min":[-w/2,0,-d/2],"max":[w/2,height,d/2]},
            "body_bounds":{"min":[-bx,.5,back],"max":[bx,eave,front]},
            "entrance":{"front":"+Z","closed":True,"position":[door_x,.5,front],
                "threshold_bounds":{"min":[door_x-step_w/2,.5,front+.30],"max":[door_x+step_w/2,2.2,d/2]}},
            "sampling":"One continuous master; independently sample through common/core.py at each pitch.",
            "lod":"No authored geometry variants. LOD belongs to sampled render resources.",
            "continuous_envelope_strict":True,
            "sampled_bounds_note":"Center-sampled voxel faces may differ by at most half a cell from continuous bounds.",
        },
        "provenance":{
            "source_files":[{"path":"voxel_character/common/assets/house/master.json","sha256":source_hash}],
            "reused_exact_components":["eave_rail"],
            "palette":"Exact complete material map from the recovered approved common house master.",
            "new_geometry":"Dimension-authored floors, wall bays, apertures, closed doors, roof courses, chimney and optional canopy.",
            "framework":"voxel_character/common/core.py; voxel_character/common/render_data.py",
            "not_visual_approval":True,
        },
    }
