"""JSON-driven near-material authoring. Emits only existing common-master grammar.

No compile, runtime mutation, scaling, terrain adjustment, stairs or house-specific
Python dispatch. All bindings and physical dimensions are explicit input data.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))
from voxel_character.common import core
VERSION = "house-material-adapter-1"


class UnsupportedSurface(ValueError):
    def __init__(self, reason, details=None):
        super().__init__(reason)
        self.report = {"status": "coverage_pending", "reason": reason, "details": details or {},
                       "master_emitted": False, "silent_fallback": False}


def fail(condition, reason, details=None):
    if not condition:
        raise UnsupportedSurface(reason, details)


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stable(*parts):
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def box(name, lo, hi, material=None, part="solid", action="paint"):
    op = {"id": name, "part": part, "action": action,
          "shape": {"kind": "box", "min": list(lo), "max": list(hi)}}
    if action == "paint":
        op["material"] = material
    return op


def prism(name, poly, z0, z1, material, part="solid"):
    return {"id": name, "part": part, "action": "paint", "material": material,
            "shape": {"kind": "extrusion", "polygon": poly, "z_min": z0, "z_max": z1}}


def matches(op, selector):
    return (re.fullmatch(selector.get("id_regex", ".*"), op["id"]) is not None
            and all(op.get(k) == v for k, v in selector.items() if k in ("action", "part", "material"))
            and ("kind" not in selector or op["shape"]["kind"] == selector["kind"]))


def component_role(component, selectors):
    categories = {p.get("metadata", {}).get("source_category") for p in component["parts"]}
    roles = [name for name, value in selectors["components"].items()
             if categories.intersection(value["source_categories"])]
    fail(len(roles) <= 1, "ambiguous_component_role", {"component": component["id"], "roles": roles})
    return roles[0] if roles else None


def selected(component, role, selectors):
    return [op for op in component["operations"] if matches(op, selectors["surfaces"][role])]


def ensure_part(component, part):
    fail(any(p["id"] == part for p in component["parts"]), "missing_semantic_part", {"component": component["id"], "part": part})


def check_inputs(source, rules, selectors):
    fail(rules.get("schema") == "riverstone.surface_detail.rules.v2", "unsupported_rules_schema")
    fail(selectors.get("schema") == "riverstone.surface_detail.selectors.v1", "unsupported_selectors_schema")
    fail(rules.get("near_pitch_m") == .05, "near_pitch_contract_requires_005m")
    fail(type(rules.get("seed")) is int, "seed_must_be_integer")
    fail(rules["policy"].get("automatic_steps") is False, "automatic_steps_require_verified_city_support")
    core.validate_master(source, rules["near_pitch_m"])
    meta = source.get("metadata", {})
    for key in ("assembly_class", "style", "roof_form"):
        fail(meta.get(key) in selectors["support"][key], "unsupported_" + key,
             {"value": meta.get(key), "supported": selectors["support"][key]})
    for key in selectors["support"]["dimension_keys"]:
        fail(core.number(meta.get(key)) and meta[key] > 0, "missing_dimension_contract", {"key": key})
    for key in selectors["support"]["integer_keys"]:
        fail(type(meta.get(key)) is int and meta[key] > 0, "missing_integer_contract", {"key": key})
    for group in ("roof", "masonry", "window", "door"):
        fail(all(core.number(v) for v in rules[group].values()), "nonfinite_rule_parameter", {"group": group})
    for group, keys in {"roof": ["tile_run_m", "tile_width_m", "lateral_joint_m", "course_overlap_m", "lip_height_m", "tile_bed_depth_m", "underlay_recess_m"],
                        "masonry": ["course_height_m", "nominal_width_m", "joint_m", "recess_m", "foundation_skin_m"],
                        "window": ["glass_recess_m", "glass_thickness_m", "mullion_width_m", "shutter_width_m", "shutter_plank_m"],
                        "door": ["plank_width_m", "joint_m", "face_depth_m"]}.items():
        fail(all(rules[group][k] > 0 for k in keys), "nonpositive_rule_parameter", {"group": group})
    fail(rules["roof"]["lateral_joint_m"] < rules["roof"]["tile_width_m"], "roof_joint_exceeds_tile")
    fail(rules["masonry"]["joint_m"] < min(rules["masonry"]["course_height_m"], rules["masonry"]["nominal_width_m"]), "masonry_joint_exceeds_unit")
    fail(rules["door"]["joint_m"] < rules["door"]["plank_width_m"], "door_joint_exceeds_plank")
    slots = []
    for value in selectors["materials"].values():
        slots.extend(value if isinstance(value, list) else [value])
    fail(set(slots) <= set(source["materials"]), "missing_material_slots", {"missing": sorted(set(slots)-set(source["materials"]))})
    for component in source["components"]:
        role = component_role(component, selectors)
        if role:
            for op in component["operations"]:
                fail(not op.get("transform"), "operation_local_transform_pending", {"component": component["id"], "operation": op["id"]})
    return meta


def masonry_strip(prefix, x0, x1, y0, y1, z0, z1, rules, slots, seed, part="solid"):
    fail(x1 > x0 and y1 > y0 and z1-z0 > rules["recess_m"], "masonry_span_too_small")
    n = max(1, math.ceil((y1-y0)/rules["course_height_m"]))
    step = (y1-y0)/n
    fail(step > rules["joint_m"], "masonry_course_too_short")
    ops = [box(prefix+"__mortar", [x0, y0, z0], [x1, y1, z1-rules["recess_m"]], slots["mortar"], part)]
    for row in range(n):
        y = y0+row*step
        width = rules["nominal_width_m"]
        x = x0 - (width*.5 if row % 2 else 0)
        col = 0
        while x < x1-1e-9:
            a, b = max(x0, x+rules["joint_m"]/2), min(x1, x+width-rules["joint_m"]/2)
            if b > a:
                mat = slots["stone_variants"][stable(prefix, row, col, seed) % len(slots["stone_variants"])]
                ops.append(box(f"{prefix}__r{row}_c{col}", [a, y+rules["joint_m"]/2, z0],
                               [b, y+step-rules["joint_m"]/2, z1], mat, part))
            col += 1
            x += width
    return ops


def roof_geometry(op):
    s = op["shape"]
    p = s["polygon"]
    xs = sorted({v[0] for v in p})
    fail(len(p) == 4 and len(xs) == 2, "unsupported_roof_plane_polygon", {"operation": op["id"]})
    a, b = xs
    ys = [sorted(v[1] for v in p if v[0] == x) for x in xs]
    fail(all(len(v) == 2 for v in ys) and b > a, "invalid_roof_plane_endpoints")
    (la, ya), (lb, yb) = ys
    fail(abs((ya-la)-(yb-lb)) < 1e-8 and ya > la and abs(yb-ya) > 1e-8, "nonparallel_or_flat_roof_plane")
    return a, b, ya, yb, ya-la


def improve_roof(c, rules, selectors, counts, seed):
    r, slots = rules["roof"], selectors["materials"]
    planes = selected(c, "roof_plane", selectors)
    fail(bool(planes), "no_supported_roof_planes", {"component": c["id"]})
    fail(not any(o["action"] == "cut" for o in c["operations"]), "trimmed_roof_pending", {"component": c["id"]})
    out = []
    for old in c["operations"]:
        if old not in planes:
            out.append(old)
            continue
        a, b, ya, yb, thickness = roof_geometry(old)
        fail(thickness > r["underlay_recess_m"], "roof_underlay_recess_exceeds_skin")
        height = lambda x: ya+(yb-ya)*(x-a)/(b-a)
        under = copy.deepcopy(old)
        under["material"] = slots["roof_underlay"]
        under["shape"]["polygon"] = [[x, y-r["underlay_recess_m"] if abs(y-height(x)) < 1e-8 else y] for x,y in old["shape"]["polygon"]]
        out.append(under)
        n = max(1, math.ceil((b-a)/r["tile_run_m"]))
        step = (b-a)/n
        z0,z1 = old["shape"]["z_min"], old["shape"]["z_max"]
        for course in range(n):
            x0,x1 = a+course*step, a+(course+1)*step
            if yb > ya:
                x1 = min(b, x1+r["course_overlap_m"])
            else:
                x0 = max(a, x0-r["course_overlap_m"])
            z = z0-(r["tile_width_m"]*.5 if course % 2 else 0)
            col = 0
            while z < z1-1e-9:
                za,zb = max(z0,z+r["lateral_joint_m"]/2), min(z1,z+r["tile_width_m"]-r["lateral_joint_m"]/2)
                if zb > za:
                    ha = height(x0)+(r["lip_height_m"] if yb > ya else r["uphill_height_m"])
                    hb = height(x1)+(r["uphill_height_m"] if yb > ya else r["lip_height_m"])
                    mat = slots["roof_tiles"][stable(c["id"], old["id"], course, col, seed) % len(slots["roof_tiles"])]
                    out.append(prism(f"{old['id']}__near_tile_{course}_{col}", [[x0,height(x0)-r["tile_bed_depth_m"]],
                        [x1,height(x1)-r["tile_bed_depth_m"]],[x1,hb],[x0,ha]], za,zb,mat,old["part"]))
                    counts["roof_tiles"] += 1
                col += 1
                z += r["tile_width_m"]
        counts["roof_planes"] += 1
    c["operations"] = out


def improve_door(op, exterior, rules, slots):
    r = rules["door"]
    lo,hi = op["shape"]["min"], op["shape"]["max"]
    base = copy.deepcopy(op)
    base["material"] = slots["door_base"]
    base["shape"]["max"][2] = exterior
    fail(lo[2] < exterior, "door_base_depth_contract")
    out = [base]
    n = max(1, math.ceil((hi[0]-lo[0])/r["plank_width_m"]))
    width = (hi[0]-lo[0])/n
    fail(width > r["joint_m"], "door_plank_too_narrow")
    gap = r["joint_m"]/2
    for j in range(n):
        out.append(box(f"{op['id']}__near_plank_{j}", [lo[0]+j*width+gap,lo[1]+r["vertical_inset_m"],exterior],
                       [lo[0]+(j+1)*width-gap,hi[1]-r["vertical_inset_m"],exterior+r["face_depth_m"]],
                       slots["door_planks"][j % len(slots["door_planks"])],op["part"]))
    x = lo[0]+(hi[0]-lo[0])*r["latch_center_x_ratio"]
    y = lo[1]+(hi[1]-lo[1])*r["latch_center_y_ratio"]
    for label,w,h,back,front,mat in [("latch",r["latch_width_m"],r["latch_height_m"],r["latch_back_m"],r["latch_front_m"],slots["iron"]),
                                    ("handle",r["handle_width_m"],r["handle_height_m"],r["latch_front_m"],r["handle_front_m"],slots["handle"])]:
        out.append(box(op["id"]+"__near_"+label,[x-w/2,y-h/2,exterior+back],[x+w/2,y+h/2,exterior+front],mat,op["part"]))
    return out


def window_details(c, aperture, panel, old, rules, selectors, pending, window_record):
    r,slots = rules["window"], selectors["materials"]
    association = selectors["window_association"]
    name = aperture["id"][:-len(association["aperture_suffix"])]
    lo,hi = aperture["shape"]["min"],aperture["shape"]["max"]
    x0,y0 = lo[:2]
    x1,y1 = hi[:2]
    xm,ym = (x0+x1)/2,(y0+y1)/2
    surface = panel["shape"]["max"][2]
    wall0,wall1 = panel["shape"]["min"][0],panel["shape"]["max"][0]
    ensure_part(c,"windows")
    hw = r["mullion_width_m"]/2
    pre = name+"__near"
    out = [box(pre+"_mullion",[xm-hw,y0,surface+r["mullion_back_m"]],[xm+hw,y1,surface+r["mullion_front_m"]],slots["mullion"],"windows"),
           box(pre+"_transom",[x0,ym-hw,surface+r["mullion_back_m"]],[x1,ym+hw,surface+r["mullion_front_m"]],slots["mullion"],"windows")]
    for name_suffix,ext,ya,yb,front,mat in [("sill_bottom",r["sill_bottom_extension_m"],r["sill_bottom_y_m"],r["sill_middle_y_m"],r["sill_bottom_front_m"],slots["sill_lower"]),
                                         ("sill_top",r["sill_top_extension_m"],r["sill_middle_y_m"],r["sill_top_y_m"],r["sill_projection_m"],slots["sill_upper"])]:
        out.append(box(pre+"_"+name_suffix,[max(wall0,x0-ext),y0+ya,surface+r["sill_back_m"]],
                       [min(wall1,x1+ext),y0+yb,surface+front],mat,"windows"))
    frames = [o for o in old if o["id"] in [name+s for s in association["frame_suffixes"]]]
    fail(len(frames) == len(association["frame_suffixes"]), "missing_window_frame_association", {"component":c["id"],"window":name})
    frame0 = min(o["shape"]["min"][0] for o in frames)
    frame1 = max(o["shape"]["max"][0] for o in frames)
    # Available width is derived from actual wall bounds AND every other aperture.
    others = [o for o in old if o["action"] == "cut" and o != aperture and o["shape"]["kind"] == "box"]
    others += [o for o in old if o["id"] not in {f["id"] for f in frames} and o["part"] in ("windows","door_frame") and o["shape"]["kind"] == "box" and not matches(o,selectors["surfaces"]["old_shutter"])]
    shutters = []
    for side in (-1,1):
        edge = frame0-r["shutter_frame_clearance_m"] if side < 0 else frame1+r["shutter_frame_clearance_m"]
        boundary = wall0 if side < 0 else wall1
        for other in others:
            a,b = other["shape"]["min"],other["shape"]["max"]
            if b[1] <= y0 or a[1] >= y1:
                continue
            if side < 0 and b[0] <= edge:
                boundary = max(boundary,b[0]+r["shutter_frame_clearance_m"])
            elif side > 0 and a[0] >= edge:
                boundary = min(boundary,a[0]-r["shutter_frame_clearance_m"])
            elif a[0] < edge < b[0]:
                boundary = edge
        width = min(r["shutter_width_m"], max(0,(edge-boundary) if side < 0 else (boundary-edge)))
        if width < r["shutter_min_width_m"]:
            pending.append({"component":c["id"],"feature":name,"side":side,"reason":"shutter_clearance_below_contract", "available_width_m":width})
            continue
        a,b = (edge-width,edge) if side < 0 else (edge,edge+width)
        shutter = pre+f"_shutter_{side}"
        out.append(box(shutter,[a,y0,surface+r["shutter_back_m"]],[b,y1,surface+r["shutter_base_front_m"]],slots["shutter_base"],"windows"))
        n = max(1,math.ceil(width/r["shutter_plank_m"]-1e-9))
        step = width/n
        for j in range(n):
            gap = r["shutter_plank_joint_m"]/2
            out.append(box(shutter+f"_plank_{j}",[a+j*step+gap,y0+r["shutter_vertical_inset_m"],surface+r["shutter_base_front_m"]],
                           [a+(j+1)*step-gap,y1-r["shutter_vertical_inset_m"],surface+r["shutter_plank_front_m"]],slots["shutter_plank"],"windows"))
        for j,ratio in enumerate((r["shutter_strap_low_ratio"],r["shutter_strap_high_ratio"])):
            y = y0+(y1-y0)*ratio
            out.append(box(shutter+f"_strap_{j}",[a,y,surface+r["shutter_plank_front_m"]],[b,y+r["shutter_strap_height_m"],surface+r["shutter_strap_front_m"]],slots["iron"],"windows"))
        shutters.append({"side":side,"width_m":width,"x_range":[a,b]})
    window_record.append({"component":c["id"],"aperture":aperture["id"],"shutters":shutters})
    return out


def improve_wall(c,rules,selectors,counts,pending,window_record,seed):
    old = copy.deepcopy(c["operations"])
    panels = selected(c,"wall_panel",selectors)
    fail(len(panels)==1,"wall_panel_contract",{"component":c["id"]})
    panel = panels[0]
    surface = panel["shape"]["max"][2]
    apertures = selected(c,"window_aperture",selectors)
    glass = selected(c,"glass",selectors)
    assoc = selectors["window_association"]
    expect = {o["id"][:-len(assoc["aperture_suffix"])]+assoc["glass_suffix"] for o in apertures}
    fail({o["id"] for o in glass} == expect,"unmatched_glass_or_aperture",{"component":c["id"]})
    ops = []
    for original in old:
        op = copy.deepcopy(original)
        if matches(op,selectors["surfaces"]["masonry"]):
            lo,hi = op["shape"]["min"],op["shape"]["max"]
            r = rules["masonry"]
            # Recess original wall skin before cladding so joints remain geometric.
            top = surface+r["wall_projection_m"]
            ops.append(box(op["id"]+"__near_remove_skin",[lo[0],lo[1],top-r["wall_skin_m"]],[hi[0],hi[1],top],action="cut",part=op["part"]))
            ops.extend(masonry_strip(op["id"]+"__near",lo[0],hi[0],lo[1],hi[1],top-r["wall_skin_m"],top,r,selectors["materials"],seed,op["part"]))
            counts["masonry_strips"] += 1
        elif matches(op,selectors["surfaces"]["glass"]):
            op["shape"]["max"][2] = surface-rules["window"]["glass_recess_m"]
            op["shape"]["min"][2] = op["shape"]["max"][2]-rules["window"]["glass_thickness_m"]
            ops.append(op)
        elif matches(op,selectors["surfaces"]["old_shutter"]) or matches(op,selectors["surfaces"]["old_mullion"]):
            continue
        elif matches(op,selectors["surfaces"]["door_leaf"]):
            ops.extend(improve_door(op,surface,rules,selectors["materials"]))
            counts["door_leaves"] += 1
        else:
            ops.append(op)
    for aperture in apertures:
        ops.extend(window_details(c,aperture,panel,old,rules,selectors,pending,window_record))
        counts["windows"] += 1
    c["operations"] = ops


def improve_foundation(c,rules,selectors,counts,seed):
    bodies = selected(c,"foundation_body",selectors)
    thresholds = selected(c,"threshold",selectors)
    fail(len(bodies)==1 and bool(thresholds),"foundation_body_threshold_contract",{"component":c["id"]})
    body = bodies[0]
    lo,hi = body["shape"]["min"],body["shape"]["max"]
    body["material"] = selectors["materials"]["mortar"]
    preserved = copy.deepcopy(thresholds)
    c["operations"] = [o for o in c["operations"] if o not in thresholds]
    for face in ("front","back","left","right"):
        u0,u1 = (lo[0],hi[0]) if face in ("front","back") else (lo[2],hi[2])
        skin = rules["masonry"]["foundation_skin_m"]
        prefix = body["id"]+"__near_"+face
        ops = [box(prefix+"_remove_skin",[u0,lo[1],-skin],[u1,hi[1],0],action="cut",part=body["part"])]
        ops += masonry_strip(prefix,u0,u1,lo[1],hi[1],-skin,0,rules["masonry"],selectors["materials"],seed,body["part"])
        for op in ops:
            q = op["shape"]
            a,b = q["min"],q["max"]
            if face == "front":
                q["min"],q["max"] = [a[0],a[1],hi[2]+a[2]],[b[0],b[1],hi[2]+b[2]]
            elif face == "back":
                q["min"],q["max"] = [a[0],a[1],lo[2]-b[2]],[b[0],b[1],lo[2]-a[2]]
            elif face == "right":
                q["min"],q["max"] = [hi[0]+a[2],a[1],a[0]],[hi[0]+b[2],b[1],b[0]]
            else:
                q["min"],q["max"] = [lo[0]-b[2],a[1],a[0]],[lo[0]-a[2],b[1],b[0]]
        c["operations"].extend(ops)
        counts["masonry_strips"] += 1
    c["operations"].extend(preserved)
    counts["thresholds_preserved"] += len(preserved)


def estimate_candidates(master,pitch):
    """Exact compiler AABB candidate count, without enumerating any cells."""
    components,instances = core.validate_master(master,pitch)
    transforms = {}
    visiting = set()
    def world(key):
        if key in transforms:
            return transforms[key]
        fail(key not in visiting,"instance_hierarchy_cycle")
        visiting.add(key)
        i = instances[key]
        t = core.transform(i.get("transform"))
        if i.get("parent"):
            t = core.compose(world(i["parent"]),t)
        visiting.remove(key)
        transforms[key] = t
        return t
    origin = master.get("grid_origin",[0,0,0])
    total = 0
    paint_bound = 0
    rows = []
    for instance in instances.values():
        component = components[instance["component"]]
        row = {"instance":instance["id"],"component":component["id"],
               "source_categories":sorted({p.get("metadata",{}).get("source_category") for p in component["parts"] if p.get("metadata",{}).get("source_category")}),
               "operation_count":len(component["operations"]),"candidate_cells":0,
               "near_authored_candidate_cells":0,"retained_source_candidate_cells":0,"by_part":{}}
        rows.append(row)
        for op in components[instance["component"]]["operations"]:
            placement = core.compose(world(instance["id"]),core.transform(op.get("transform")))
            shape = core.prepare_shape(op["shape"],pitch)
            lo,hi = core.shape_bounds(shape)
            corners = [core.apply(placement,p) for p in itertools.product(*zip(lo,hi))]
            lows = [min(p[j] for p in corners) for j in range(3)]
            highs = [max(p[j] for p in corners) for j in range(3)]
            count = math.prod(math.ceil((b-o)/pitch-core.EPS)-math.floor((a-o)/pitch+core.EPS) for a,b,o in zip(lows,highs,origin))
            total += count
            row["candidate_cells"] += count
            row["by_part"][op["part"]] = row["by_part"].get(op["part"],0)+count
            row["near_authored_candidate_cells" if "__near" in op["id"] else "retained_source_candidate_cells"] += count
            if op["action"] == "paint":
                paint_bound += count
    extra_regions = master.get("assembly_cuts",[]) + [c for c in master.get("constraints",[]) if c["kind"] == "empty_region"]
    for op in extra_regions:
        shape = core.prepare_shape(op["shape"],pitch)
        lo,hi = core.shape_bounds(shape)
        corners = [core.apply(core.transform(op.get("transform")),p) for p in itertools.product(*zip(lo,hi))]
        total += math.prod(math.ceil((max(p[j] for p in corners)-origin[j])/pitch-core.EPS)-math.floor((min(p[j] for p in corners)-origin[j])/pitch+core.EPS) for j in range(3))
    return {"pitch_m":pitch,"operation_aabb_candidate_cells":total,
            "paint_aabb_cells_upper_bound":paint_bound,"actual_occupied_cells":None,
            "actual_quads":None,"full_compile_run":False,"by_component":rows,
            "method":"same core.prepare_shape/transform/AABB ranges as common compiler; not an occupied-cell or mesh prediction"}


def preservation_check(original,candidate,selectors):
    old = {c["id"]:c for c in original["components"]}
    new = {c["id"]:c for c in candidate["components"]}
    checks = {"instances_unchanged":original["instances"]==candidate["instances"],
              "component_ids_unchanged":list(old)==list(new),
              "materials_unchanged":original["materials"]==candidate["materials"],
              "assembly_cuts_unchanged":original.get("assembly_cuts",[])==candidate.get("assembly_cuts",[]),
              "constraints_unchanged":original.get("constraints",[])==candidate.get("constraints",[]),
              "entrance_unchanged":original["metadata"].get("entrance")==candidate["metadata"].get("entrance"),
              "all_source_cuts_unchanged":True,"thresholds_unchanged":True,"roof_horizontal_bounds_preserved":True}
    aperture_count = 0
    for key,c in old.items():
        newops = {o["id"]:o for o in new[key]["operations"]}
        for op in c["operations"]:
            if op["action"] == "cut":
                checks["all_source_cuts_unchanged"] &= newops.get(op["id"]) == op
                aperture_count += 1
            if matches(op,selectors["surfaces"]["threshold"]):
                checks["thresholds_unchanged"] &= newops.get(op["id"]) == op
            if component_role(c,selectors)=="roof" and matches(op,selectors["surfaces"]["roof_plane"]):
                a,b,_,_,_ = roof_geometry(op)
                tiles = [v for k,v in newops.items() if k.startswith(op["id"]+"__near_tile_")]
                for tile in tiles:
                    s = tile["shape"]
                    checks["roof_horizontal_bounds_preserved"] &= (min(p[0] for p in s["polygon"]) >= a-1e-8 and max(p[0] for p in s["polygon"]) <= b+1e-8 and s["z_min"] >= op["shape"]["z_min"]-1e-8 and s["z_max"] <= op["shape"]["z_max"]+1e-8)
    fail(all(checks.values()),"preservation_validation_failed",checks)
    return {"checks":checks,"source_cut_count":aperture_count}


def author(source,rules,selectors,source_info=None):
    meta = check_inputs(source,rules,selectors)
    candidate = copy.deepcopy(source)
    counts = {k:0 for k in ("roof_tiles","roof_planes","windows","door_leaves","masonry_strips","thresholds_preserved")}
    pending,windows = [],[]
    roles = {k:0 for k in selectors["components"]}
    for c in candidate["components"]:
        role = component_role(c,selectors)
        if role:
            roles[role] += 1
        if role == "roof":
            improve_roof(c,rules,selectors,counts,rules["seed"])
        elif role == "wall":
            improve_wall(c,rules,selectors,counts,pending,windows,rules["seed"])
        elif role == "foundation":
            improve_foundation(c,rules,selectors,counts,rules["seed"])
        elif role == "door_insert":
            leaves = selected(c,"door_leaf",selectors)
            fail(bool(leaves),"door_insert_without_leaf",{"component":c["id"]})
            ops = []
            for op in c["operations"]:
                if op in leaves:
                    ops.extend(improve_door(op,selectors["contracts"]["door_insert_surface_m"],rules,selectors["materials"]))
                    counts["door_leaves"] += 1
                else:
                    ops.append(op)
            c["operations"] = ops
    fail(roles["roof"] > 0 and roles["wall"] > 0 and roles["foundation"] == 1,"required_component_roles_missing",roles)
    expected_roofs = selectors["contracts"]["roof_components_by_form"][meta["roof_form"]]
    if isinstance(expected_roofs,str):
        expected_roofs = meta[expected_roofs]
    fail(roles["wall"] == meta["floors"]*selectors["contracts"]["walls_per_floor"],"wall_count_floor_contract",roles)
    fail(roles["roof"] == expected_roofs,"roof_component_count_contract",roles)
    fail(counts["roof_planes"] == expected_roofs*selectors["contracts"]["roof_planes_per_component"][meta["roof_form"]],"roof_plane_count_contract",counts)
    fail(counts["door_leaves"] == meta["row_units"],"door_count_row_units_mismatch",counts)
    identity = core.digest({"source":source,"rules":rules,"selectors":selectors,"engine":VERSION,"engine_sha256":sha(__file__)})[:16]
    candidate["id"] = source["id"]+"__near_"+identity
    candidate["revision"] = source["revision"]+1
    preservation = preservation_check(source,candidate,selectors)
    provenance = {"engine":VERSION,"engine_sha256":sha(__file__),"seed":rules["seed"],
                  "source_id":source["id"],"source_canonical_sha256":core.digest(source),
                  "rules_sha256":core.digest(rules),"selectors_sha256":core.digest(selectors),
                  "inputs":source_info or {},"reference_quality":"near_detail_r01 house.r04 physical material rules",
                  "geometry_scaling":False,"new_steps":0,"new_corbels":0,
                  "collision_reference":"unchanged original source; city support/contact not evaluated",
                  "counts":counts,"component_roles":roles}
    candidate.setdefault("provenance",{})["city_near_material"] = provenance
    candidate["metadata"]["city_near_material"] = {"rules_id":rules["id"],"selectors_id":selectors["id"],
        "seed":rules["seed"],"near_pitch_m":rules["near_pitch_m"],"status":"authored_not_visual_approved",
        "pending_features":pending,"roof_lip_delta_max_m":rules["roof"]["lip_height_m"],
        "collision":"original source unchanged","city_access_verified":False}
    core.validate_master(candidate,rules["near_pitch_m"])
    counts["source_operations"] = sum(len(c["operations"]) for c in source["components"])
    counts["output_operations"] = sum(len(c["operations"]) for c in candidate["components"])
    report = {"status":"structural_pass_feature_pending" if pending else "structural_pass_not_compiled",
              "source_id":source["id"],"output_id":candidate["id"],"preservation":preservation,
              "counts":counts,"pending_features":pending,"windows":windows,
              "estimate":estimate_candidates(candidate,rules["near_pitch_m"]),
              "full_compile":False,"visual_approval":False,"city_support_validation":False}
    return candidate,provenance,report


def author_files(source_path,rules_path,selectors_path,output_dir):
    output = Path(output_dir)
    info = {"source_path":str(source_path),"source_sha256":sha(source_path),
            "rules_path":str(rules_path),"rules_file_sha256":sha(rules_path),
            "selectors_path":str(selectors_path),"selectors_file_sha256":sha(selectors_path)}
    source = load(source_path)
    stem = source["id"]
    try:
        candidate,provenance,report = author(source,load(rules_path),load(selectors_path),info)
    except UnsupportedSurface as exc:
        report = dict(exc.report,source_id=stem,inputs=info)
        write(output/(stem+".validation.json"),report)
        return report
    write(output/(stem+".master.json"),candidate)
    write(output/(stem+".provenance.json"),provenance)
    write(output/(stem+".validation.json"),report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--rules",type=Path,required=True)
    parser.add_argument("--selectors",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args = parser.parse_args()
    report = author_files(args.source,args.rules,args.selectors,args.output_dir)
    print(json.dumps({k:v for k,v in report.items() if k not in ("windows","inputs")},ensure_ascii=False,indent=2))
    raise SystemExit(2 if report["status"] == "coverage_pending" else 0)
