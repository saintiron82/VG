"""Bounded city infrastructure authoring using the unchanged common master schema.

This module authors source shapes/placements only. Sampling, sparse-cell authority,
meshing and runtime loading remain in voxel_character/common. It is not a terrain
engine, a new mesher, or a claim that the brief's candidate elevations are built.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRIEF = ROOT / "world_city/data/city_brief.v2.json"
WALL_REPORT = ROOT / "world_city/checks/wall_crossings_v2.json"
SCHEMA = "riverstone.voxel.master.v1"
PALETTE = {
    "earth": "77765a", "grass": "6f7959", "stone": "9e9b88",
    "stone_light": "aaa794", "stone_dark": "888a7d", "mortar": "777b71",
    "water": "427a83", "timber": "796047", "timber_light": "8c7255",
}
IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _num(spec, key, default, minimum=0):
    value = float(spec.get(key, default))
    if not math.isfinite(value) or value <= minimum:
        raise ValueError(f"{key} must be finite and > {minimum}")
    return value


def _box(lo, hi):
    return {"kind": "box", "min": list(lo), "max": list(hi)}


def _yaw(degrees):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def _poly_shape(polygon, y0, y1):
    # Common extrusion is along local Z; this proper rotation maps it to +Y.
    return {"kind": "extrusion", "polygon": [[x, -z] for x, z in polygon],
            "z_min": y0, "z_max": y1}


def make_master(spec):
    """Return numeric/declarative common master JSON, never sampled geometry.

    kind: terrain_tile, water_tile, road_paver, curb, wall_panel, battlement,
          bridge_deck, bridge_pier, dock, surface_patch.
    terrain/water tile: width_m X, length_m Z, centered XZ, top Y=0/-2.
    road/deck/dock: width_m X, length_m Z, walking top Y=0.
    wall: width_m X (longitudinal), depth_m Z, height_m Y; base Y=0.
    All transforms are ordinary proper rotations understood by common/core.py.
    """
    spec = copy.deepcopy(spec)
    kind = spec.get("kind", spec.get("type"))
    if not kind:
        raise ValueError("infrastructure spec requires kind")
    operations, planes = [], []

    def op(shape, material="stone", action="paint", transform=None, feature=None):
        item = {"id": f"op_{len(operations):04d}", "part": "solid", "action": action, "shape": shape}
        if action == "paint": item["material"] = material
        if transform: item["transform"] = transform
        if feature: item["feature"] = feature
        operations.append(item)

    def box(lo, hi, material="stone", **kw):
        op(_box(lo, hi), material, **kw)

    def polygon(poly, low, high, material="stone", action="paint"):
        op(_poly_shape(poly, low, high), material, action,
           {"basis": [[1, 0, 0], [0, 0, 1], [0, -1, 0]]})

    if kind in ("terrain_tile", "water_tile"):
        w, l = _num(spec, "width_m", 32), _num(spec, "length_m", 32)
        if max(w, l) > 32.00001: raise ValueError("terrain/water tiles are bounded to 32 m")
        if kind == "terrain_tile":
            planes = [{"id": "grade", "axis": 1, "value": 0, "snap": "none"},
                      {"id": "base", "axis": 1, "relative_to": "grade", "offset": -2}]
            box([-w/2, {"plane": "base"}, -l/2], [w/2, {"plane": "grade"}, l/2], spec.get("material", "grass"))
            for poly in spec.get("river_polygons_xz_m", []):
                polygon(poly, -3, 1, action="cut")
        else:
            # The same clipped shoreline as terrain cut: never a painted cap over land.
            for poly in spec.get("river_polygons_xz_m", []): polygon(poly, -4, -2, "water")
            if not operations: box([-w/2, -4, -l/2], [w/2, -2, l/2], "water")
    elif kind == "surface_patch":
        w, l = _num(spec, "width_m", 32), _num(spec, "length_m", 32)
        if max(w, l) > 32.00001: raise ValueError("surface patches are bounded to 32 m")
        material = spec.get("material", "stone")
        if material not in PALETTE: raise ValueError("unknown infrastructure material")
        for poly in spec.get("polygons_xz_m", []): polygon(poly, -.25, 0, material)
        if not operations: box([-w/2, -.25, -l/2], [w/2, 0, l/2], material)
    elif kind in ("road_paver", "bridge_deck", "dock"):
        w, l = _num(spec, "width_m", 6), _num(spec, "length_m", 8)
        if l > 32.00001 or w > 32.00001: raise ValueError("surface modules are bounded to 32 m")
        thickness = _num(spec, "thickness_m", .25 if kind == "road_paver" else .5)
        material = "timber" if kind == "dock" else "stone"
        planes = [{"id": "walk_grade", "axis": 1, "value": 0, "snap": "none"},
                  {"id": "paving_base", "axis": 1, "relative_to": "walk_grade", "offset": -thickness}]
        z0, z1 = -l/2, l/2
        if kind in ("bridge_deck", "dock"):
            # A source segment's modules share one longitudinal grid in world
            # distance. Internal boundaries choose the same nearest plane; only
            # the two outside ends grow outward. No post-sample cell repair.
            planes += [{"id":"deck_start","axis":2,"value":-l/2,"snap":spec.get("start_snap","floor")},
                       {"id":"deck_end","axis":2,"value":l/2,"snap":spec.get("end_snap","ceil")}]
            z0,z1 = {"plane":"deck_start"},{"plane":"deck_end"}
        box([-w/2, {"plane": "paving_base"}, z0], [w/2, {"plane": "walk_grade"}, z1], material)
        # Material-only stone courses. No relief, protruding curb, or raised road ridge.
        if spec.get("detail", True):
            stride = 2 if kind != "dock" else 1
            for i in range(int(math.ceil(l/stride))):
                z = -l/2 + i*stride
                end = min(z + .5, l/2)
                if end > z:
                    # Sparse broad accents avoid an expensive per-paver whole-city fill.
                    x0 = -w/2 if i % 2 else -.5
                    x1 = min(x0 + min(1, w), w/2)
                    if x1 > x0: box([x0, -min(thickness, .25), z], [x1, 0, end], "timber_light" if kind == "dock" else "stone_light")
    elif kind == "curb":
        w, l, h = _num(spec, "width_m", .25), _num(spec, "length_m", 8), _num(spec, "height_m", .25)
        box([-w/2, 0, -l/2], [w/2, h, l/2], "stone_dark")
    elif kind == "wall_panel":
        w = _num(spec, "width_m", spec.get("length_m", 16))
        d, h = _num(spec, "depth_m", 3), _num(spec, "height_m", 9)
        if w > 32.00001: raise ValueError("wall panels are bounded to 32 m")
        box([-w/2, 0, -d/2], [w/2, h, d/2], "stone")
        # Narrow colour courses are flush to the wall, not giant decorative relief.
        for y in range(2, int(h), 2):
            box([-w/2, y, -d/2], [w/2, min(h, y+.25), d/2], "stone_dark")
        if spec.get("battlements", True):
            height = _num(spec, "battlement_height_m", 1)
            pitch = _num(spec, "battlement_spacing_m", 2)
            for i in range(max(1, int(w//pitch))):
                center = -w/2 + (i+.5)*w/max(1,int(w//pitch))
                half = min(.5, w/2)
                box([center-half, h, -d/2], [center+half, h+height, -d/2+.75], "stone_light")
    elif kind == "battlement":
        w, d, h = _num(spec, "width_m", 1), _num(spec, "depth_m", .75), _num(spec, "height_m", 1)
        box([-w/2, 0, -d/2], [w/2, h, d/2], "stone_light")
    elif kind == "bridge_pier":
        w, l = _num(spec, "width_m", 2), _num(spec, "length_m", 4)
        base, top = float(spec.get("base_y_m", -4)), float(spec.get("top_y_m", -.5))
        if not math.isfinite(base+top) or base >= top: raise ValueError("bridge pier base must be below top")
        box([-w/2, base, -l/2], [w/2, top, l/2], "stone_dark")
    else:
        raise ValueError(f"unknown infrastructure kind: {kind}")

    return {
        "schema": SCHEMA, "id": f"city_{kind}_{_hash(spec)[:16]}", "revision": 1,
        "axes": {"up": "+Y", "front": "+Z", "right": "+X"},
        "grid_origin": [0, 0, float(spec.get("longitudinal_grid_origin_m", 0)) if kind in ("bridge_deck", "dock") else 0],
        "materials": dict(PALETTE), "coordinate_planes": planes,
        "components": [{"id": "module", "parts": [{"id": "solid", "pivot": [0,0,0]}], "operations": operations}],
        "instances": [{"id": "module_0", "component": "module"}],
        "metadata": {"authoring": "bounded_common_master_only", "spec": spec,
                     "datum": "walking surfaces Y=0; river surface Y=-2; candidate terrain elevations not realized"},
    }


def _dot(a, b): return sum(x*y for x,y in zip(a,b))
def _sub(a, b): return [x-y for x,y in zip(a,b)]
def _add(a, b): return [x+y for x,y in zip(a,b)]
def _mul(a, s): return [x*s for x in a]
def _cross(a,b): return a[0]*b[1]-a[1]*b[0]
def _lerp(a,b,t): return [x+(y-x)*t for x,y in zip(a,b)]
def _unit(a,b):
    d = _sub(b,a); length = math.hypot(*d)
    if length < 1e-8: raise ValueError("zero-length source segment")
    return [v/length for v in d], length


def _signed_area(poly): return sum(_cross(a,b) for a,b in zip(poly,poly[1:]+poly[:1]))/2


def _clip_polygon(poly, xmin,zmin,xmax,zmax):
    """Author a polygon clipped to one chunk; no cell sampling/meshing here."""
    out = [list(p) for p in poly]
    for axis, value, sign in [(0,xmin,1),(0,xmax,-1),(1,zmin,1),(1,zmax,-1)]:
        inp, out = out, []
        if not inp: break
        prev = inp[-1]; prev_in = sign*(prev[axis]-value) >= -1e-8
        for cur in inp:
            cur_in = sign*(cur[axis]-value) >= -1e-8
            if cur_in != prev_in:
                t = (value-prev[axis])/(cur[axis]-prev[axis]); out.append(_lerp(prev,cur,t))
            if cur_in: out.append(cur)
            prev, prev_in = cur, cur_in
    return out if len(out)>=3 and abs(_signed_area(out))>1e-7 else []


def _ribbon(a,b,width):
    u,_ = _unit(a,b); n = [-u[1]*width/2, u[0]*width/2]
    return [_add(a,n),_add(b,n),_sub(b,n),_sub(a,n)]


def _river_outline(points,width):
    """Mitered offset of the source river reservation, not a widened world plane."""
    units=[_unit(a,b)[0] for a,b in zip(points,points[1:])]
    offsets=[]
    for i in range(len(points)):
        if i==0: v=[-units[0][1],units[0][0]]
        elif i==len(points)-1: v=[-units[-1][1],units[-1][0]]
        else:
            n0=[-units[i-1][1],units[i-1][0]]; n1=[-units[i][1],units[i][0]]
            avg=_add(n0,n1); d=_dot(avg,n1)
            v=_mul(avg,1/d) if abs(d)>1e-8 else n1
        offsets.append(_mul(v,width/2))
    return [_add(p,v) for p,v in zip(points,offsets)]+[_sub(p,v) for p,v in reversed(list(zip(points,offsets)))]


def _point_inside(p, poly):
    inside=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>p[1]) != (b[1]>p[1]) and p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]: inside=not inside
    return inside


def _project(p,a,b):
    u,L=_unit(a,b); t=max(0,min(L,_dot(_sub(p,a),u)))
    q=_add(a,_mul(u,t)); return t,q,math.dist(p,q)


def _segment_convex_interval(a,b,poly):
    """Interval of source wall centerline inside a road's exact rectangular ribbon."""
    if _signed_area(poly)<0: poly=list(reversed(poly))
    lo,hi=0.,1.; v=_sub(b,a)
    for c,d in zip(poly,poly[1:]+poly[:1]):
        edge=_sub(d,c); num=_cross(edge,_sub(a,c)); den=_cross(edge,v)
        if abs(den)<1e-10:
            if num < -1e-7:return None
            continue
        t=-num/den
        if den>0:lo=max(lo,t)
        else:hi=min(hi,t)
        if lo>hi+1e-7:return None
    return [max(0,lo),min(1,hi)]


def wall_intervals(plan, margin_m=.5, wall_depth_m=3):
    """Cut only six designated openings, accounting for all exact road crossings.

    Gate cuts include the projected gatehouse footprint plus 0.5 m. Road cuts
    include both the true road ribbon and wall-thickness swept clearance. No
    cuts are invented at undesignated intersections: those raise ValueError.
    """
    wall=plan["wall_outline_xz_m"]; edges=list(zip(wall,wall[1:]+wall[:1]))
    nodes={n["id"]:[n["position_m"][0],n["position_m"][2]] for n in plan["road_nodes"]}
    openings=[]
    for b in plan["building_plans"]:
        if b["functional_role"]=="gatehouse":
            openings.append({"id":b["id"],"name":b.get("name",b["id"]),"kind":"gatehouse",
                             "point_xz_m":b["road_access"]["connection_xz_m"],
                             "required_width_m":b["opening_required_m"]["width"],
                             "required_height_m":b["opening_required_m"]["height"],
                             "footprint_xz_m":b["footprint_xz_m"]})
    for f in plan["site_features"]:
        if f["kind"]=="water_postern":
            openings.append({"id":f["id"],"name":f["id"],"kind":"water_postern",
                             "point_xz_m":[f["position_m"][0],f["position_m"][2]],
                             "required_width_m":f["opening_required_m"]["width"],
                             "required_height_m":f["opening_required_m"]["height"],"footprint_xz_m":[]})
    for o in openings:
        wi,(a,b)=min(enumerate(edges),key=lambda e:_project(o["point_xz_m"],*e[1])[2])
        u,L=_unit(a,b); t,_,dist=_project(o["point_xz_m"],a,b)
        if dist>.02: raise ValueError(f"opening {o['id']} is not on source wall")
        values=[t-o["required_width_m"]/2,t+o["required_width_m"]/2]
        values += [_dot(_sub(p,a),u) for p in o["footprint_xz_m"]]
        o.update({"wall_edge":wi,"center_along_m":t,"interval_m":[max(0,min(values)-margin_m),min(L,max(values)+margin_m)],
                  "road_ids":[],"margin_m":margin_m,"cut_basis":"opening width + gate footprint projection + swept road clearance"})
    crossings=[]
    for r in plan["roads"]:
        if r["kind"]=="wall_walk" or r["id"].startswith("WALL_ACCESS"):continue
        ra,rb=nodes[r["from_node"]],nodes[r["to_node"]]
        for wi,(a,b) in enumerate(edges):
            interval=_segment_convex_interval(a,b,_ribbon(ra,rb,r["width_m"]))
            if interval is None:continue
            u,L=_unit(a,b); center=(interval[0]+interval[1])*L/2
            candidates=[o for o in openings if o["wall_edge"]==wi and abs(o["center_along_m"]-center)<30]
            if not candidates:raise ValueError(f"undesigned wall crossing: {r['id']} edge {wi}")
            opening=min(candidates,key=lambda o:abs(o["center_along_m"]-center))
            ru,_=_unit(ra,rb)
            # Project true road half-width through the complete 3 m wall slab.
            sine=abs(_cross(u,ru)); cosine=abs(_dot(u,ru))
            extra=(wall_depth_m/2)*cosine/max(sine,1e-6)+margin_m
            lo=max(0,interval[0]*L-extra);hi=min(L,interval[1]*L+extra)
            opening["interval_m"][0]=min(opening["interval_m"][0],lo)
            opening["interval_m"][1]=max(opening["interval_m"][1],hi)
            opening["road_ids"].append(r["id"])
            crossings.append({"road_id":r["id"],"route_id":r.get("route_id"),"wall_edge":wi,
                              "opening_id":opening["id"],"ribbon_interval_m":[interval[0]*L,interval[1]*L],
                              "required_clearance_interval_m":[lo,hi]})
    if any(not o["road_ids"] for o in openings):raise ValueError("designated opening has no road crossing")
    segments=[]
    for wi,(a,b) in enumerate(edges):
        _,L=_unit(a,b);cursor=0
        cuts=sorted((o for o in openings if o["wall_edge"]==wi),key=lambda o:o["interval_m"][0])
        for cut in cuts:
            lo,hi=cut["interval_m"]
            if lo>cursor:segments.append({"wall_edge":wi,"interval_m":[cursor,lo],"a_xz_m":_lerp(a,b,cursor/L),"b_xz_m":_lerp(a,b,lo/L)})
            cursor=max(cursor,hi)
        if cursor<L:segments.append({"wall_edge":wi,"interval_m":[cursor,L],"a_xz_m":_lerp(a,b,cursor/L),"b_xz_m":list(b)})
    return {"openings":openings,"segments":segments,"crossings":crossings,
            "wall_depth_m":wall_depth_m,"wall_height_m":9,"battlement_height_m":1,
            "unexplained_gaps":[],"crossing_count":len(crossings),
            "source_report":"world_city/checks/wall_crossings_v2.json"}


def build_infrastructure(plan=None):
    """Return source-derived, chunk-ready placements and exact route metadata.

    This does not compile the city. Parent must cache make_master(spec) -> existing
    coordinate_planes.compile_master -> common render_data by master_key/pitch.
    `render_offset_y_m` is a draw-only anti-z-fighting offset, never walk grade.
    """
    if plan is None:plan=json.loads(BRIEF.read_text())
    placements=[]; specs={}
    source_nodes={n["id"]:n for n in plan["road_nodes"]}
    nodes={k:[n["position_m"][0],n["position_m"][2]] for k,n in source_nodes.items()}
    river=plan["river_reservation"];river_poly=_river_outline(river["centerline_xz_m"],river["width_candidate_m"])

    def place(pid,spec,pos=(0,0,0),yaw=0,pitch=.25,category="surface",**meta):
        spec=copy.deepcopy(spec);key=f"{spec['kind']}_{_hash(spec)[:16]}";specs.setdefault(key,spec)
        p={"id":pid,"master_key":key,"asset_key":key,"spec":spec,"position_m":list(pos),
           "yaw_deg":yaw,"transform":{"translation":list(pos),"basis":_yaw(yaw)},
           "requested_pitch_m":pitch,"category":category,
           "chunk_xz":[math.floor(pos[0]/32),math.floor(pos[2]/32)],
           "stream_chunk_xz":[math.floor(pos[0]/64),math.floor(pos[2]/64)],**meta}
        placements.append(p);return p

    def line(pid,a,b,width,kind="road_paver",category="road",pitch=.25,**meta):
        _,length=_unit(a,b);count=max(1,math.ceil(length/32));out=[]
        yaw=math.degrees(math.atan2(b[0]-a[0],b[1]-a[1]))
        # Exactly partition the source segment: no invented route widening or shifts.
        for i in range(count):
            p0,p1=_lerp(a,b,i/count),_lerp(a,b,(i+1)/count);mid=_lerp(p0,p1,.5)
            spec={"kind":kind,"width_m":width,"length_m":length/count}
            if kind in ("bridge_deck","dock"):
                spec.update({"longitudinal_grid_origin_m":-(i+.5)*length/count,
                             "start_snap":"floor" if i==0 else "nearest",
                             "end_snap":"ceil" if i==count-1 else "nearest"})
            out.append(place(f"{pid}:{i:03d}",spec,
                             [mid[0],0,mid[1]],yaw,pitch,category,
                             source_segment_xz_m=[p0,p1],walk_surface_y_m=0,
                             render_offset_y_m=.025,**meta))
        return out

    # Coarse terrain bounded to one source chunk per call. Partial shoreline tiles
    # share the exact cut polygon with water; open water is not covered with grass.
    bounds=plan["coordinate_system"]["bounds_m"];xmin,zmin=bounds[0][0],bounds[0][2];xmax,zmax=bounds[1][0],bounds[1][2]
    ground_tiles=water_tiles=0
    for ix,x0 in enumerate(range(math.floor(xmin/32)*32,math.ceil(xmax/32)*32,32)):
        for iz,z0 in enumerate(range(math.floor(zmin/32)*32,math.ceil(zmax/32)*32,32)):
            xa,xb=max(xmin,x0),min(xmax,x0+32);za,zb=max(zmin,z0),min(zmax,z0+32)
            if xa>=xb or za>=zb:continue
            cx,cz=(xa+xb)/2,(za+zb)/2;clip=_clip_polygon(river_poly,xa,za,xb,zb)
            local=[[round(p[0]-cx,7),round(p[1]-cz,7)] for p in clip]
            area=abs(_signed_area(clip)) if clip else 0;tile_area=(xb-xa)*(zb-za)
            base={"width_m":xb-xa,"length_m":zb-za}
            if area<tile_area-1e-5:
                spec={"kind":"terrain_tile",**base,"material":"earth" if _point_inside([cx,cz],plan["wall_outline_xz_m"]) else "grass"}
                if local:spec["river_polygons_xz_m"]=[local]
                place(f"ground:{ix:02d}:{iz:02d}",spec,[cx,0,cz],pitch=2,category="terrain")
                ground_tiles+=1
            if local:
                place(f"river:{ix:02d}:{iz:02d}",{"kind":"water_tile",**base,"river_polygons_xz_m":[local]},
                      [cx,0,cz],pitch=2,category="water",collision_enabled=False,water_surface_y_m=-2)
                water_tiles+=1

    # Paved source market/precinct footprints are separately tiled surface masters.
    # No large relief and no whole-city quarter-metre ground fill.
    plazas=[]
    for feature in plan["site_features"]:
        if feature["id"] not in ("F_MARKET_OPEN","F_CASTLE_CLOSE","F_CATHEDRAL_CLOSE"): continue
        poly=feature["footprint_xz_m"]
        minx,maxx=min(p[0] for p in poly),max(p[0] for p in poly)
        minz,maxz=min(p[1] for p in poly),max(p[1] for p in poly)
        ids=[]
        for xi,x0 in enumerate(range(math.floor(minx/32)*32,math.ceil(maxx/32)*32,32)):
            for zi,z0 in enumerate(range(math.floor(minz/32)*32,math.ceil(maxz/32)*32,32)):
                clip=_clip_polygon(poly,x0,z0,x0+32,z0+32)
                if not clip: continue
                cx,cz=x0+16,z0+16
                local=[[round(p[0]-cx,7),round(p[1]-cz,7)] for p in clip]
                p=place(f"plaza:{feature['id']}:{xi:02d}:{zi:02d}",
                        {"kind":"surface_patch","width_m":32,"length_m":32,"polygons_xz_m":[local],
                         "material":"stone" if feature["id"]=="F_MARKET_OPEN" else "stone_dark"},
                        [cx,0,cz],pitch=.25,category="plaza",source_feature_id=feature["id"],
                        walk_surface_y_m=0,render_offset_y_m=.018)
                ids.append(p["id"])
        plazas.append({"id":feature["id"],"footprint_xz_m":copy.deepcopy(poly),
                       "placement_ids":ids,"walk_surface_y_m":0,"status":"bounded_flat_common_surface_authored"})

    routes=[];bridges=[];deferred=[];road_node_widths={}
    for r in plan["roads"]:
        a,b=nodes[r["from_node"]],nodes[r["to_node"]]
        rec={**copy.deepcopy(r),"centerline_xz_m":[list(a),list(b)],"reserved_width_m":r["width_m"],
             "walk_surface_y_m":0,"source_node_y":[source_nodes[r["from_node"]]["position_m"][1],source_nodes[r["to_node"]]["position_m"][1]],
             "grade_status":"runtime_flat_accessibility_stage_not_authored_terrain_profile"}
        if r["kind"]=="wall_walk" or r["id"].startswith("WALL_ACCESS"):
            rec["realization_status"]="deferred_vertical_wall_access";deferred.append(rec);continue
        rec["ribbon_polygon_xz_m"]=_ribbon(a,b,r["width_m"])
        kind="bridge_deck" if r["kind"]=="bridge" else "road_paver"
        pp=line(r["id"],a,b,r["width_m"],kind,"bridge" if kind=="bridge_deck" else "road",source_road_id=r["id"],reserved_width_m=r["width_m"])
        rec["placement_ids"]=[p["id"] for p in pp];routes.append(rec)
        for nid in (r["from_node"],r["to_node"]):road_node_widths[nid]=max(road_node_widths.get(nid,0),r["width_m"])
        if kind=="bridge_deck":
            rec=copy.deepcopy(rec);rec["water_surface_y_m"]=-2;rec["deck_thickness_m"]=.5;rec["pier_ids"]=[]
            _,length=_unit(a,b)
            for i in range(1,math.ceil(length/18)):
                mid=_lerp(a,b,i/math.ceil(length/18))
                if _point_inside(mid,river_poly):
                    pier=place(f"{r['id']}:pier:{i}",{"kind":"bridge_pier","width_m":2,"length_m":4},
                               [mid[0],0,mid[1]],pp[0]["yaw_deg"],.5,"bridge_pier",source_road_id=r["id"])
                    rec["pier_ids"].append(pier["id"])
            bridges.append(rec)
    # Separate, draw-only join pads close sampled ribbon seam wedges. They are
    # explicitly not reserved road width, nav corridors, or collision expansion.
    for nid,width in sorted(road_node_widths.items()):
        p=nodes[nid]
        place(f"road_join:{nid}",{"kind":"road_paver","width_m":width,"length_m":width,"detail":False},
              [p[0],0,p[1]],pitch=.25,category="road_join_draw_only",render_offset_y_m=.023,
              collision_enabled=False,reservation_geometry=False,draw_only_overlap_join=True,
              source_node_id=nid,walk_surface_y_m=0)

    # Explicit runtime design inference: align a short exterior approach with the
    # west gate's main passage. Never extrapolate the diagonal canonical street
    # through the opposite intact tower or alter its source reservation.
    external_gate_approaches=[]
    west=next((b for b in plan["building_plans"] if b["id"]=="D09-B004"),None)
    if west:
        footprint=west["footprint_xz_m"]
        center=[sum(p[i] for p in footprint)/len(footprint) for i in (0,1)]
        entrance=west["entrance"]["position_xz_m"]
        face=min(zip(footprint,footprint[1:]+footprint[:1]),key=lambda e:_project(entrance,*e)[2])
        face_mid=_lerp(*face,.5)
        front,_=_unit(center,face_mid)
        approach_points=[_add(center,_mul(front,z)) for z in (-18,-7,0)]
        approach_id="INFERRED_WEST_GATE_APPROACH"
        parts=line(approach_id,approach_points[0],approach_points[-1],6.5,
                   source_opening_id=west["id"],design_inference=True,
                   authoritative_source_route=False)
        external_gate_approaches.append({"id":approach_id,"gate_instance_id":west["id"],
                    "route_id":"RT_WEST_MARKET","polyline_xz_m":approach_points,"width_m":6.5,
                    "placement_ids":[p["id"] for p in parts],"walk_surface_y_m":0,
                    "evidence":"design_inference",
                    "source_basis":"source gate footprint and entrance-facing axis; local X=0 and Z=-18,-7,0",
                    "canonical_route_policy":"append original RT_WEST_MARKET points[1:]; no source street extrapolation or source reservation edits",
                    "runtime_validation":"main-passage-aligned proposal verified by separate capsule traversal; full-width static audit stored separately"})

    # Source loading piers are joined to the quay by short at-grade connector decks.
    docks=[]
    quay=[r for r in routes if r.get("route_id")=="RT_QUAY"]
    for f in plan["site_features"]:
        if f["kind"]!="loading_pier":continue
        fp=f["footprint_xz_m"];xs=[p[0] for p in fp];zs=[p[1] for p in fp]
        source_start=[sum(xs)/len(xs),min(zs)];end=[source_start[0],max(zs)];width=max(xs)-min(xs)
        nearest=min((_project(source_start,*r["centerline_xz_m"])[1] for r in quay),key=lambda p:math.dist(source_start,p)) if quay else source_start
        station,projected,lateral_distance=_project(nearest,source_start,end)
        source_length=math.dist(source_start,end)
        trim=0 < station < source_length and lateral_distance <= width/2
        start=projected if trim else list(source_start)
        adjustment={"kind":"trim_landward_root_to_quay_projection" if trim else "source_root_retained",
                    "source_root_xz_m":list(source_start),"authored_root_xz_m":list(start),
                    "trimmed_landward_length_m":station if trim else 0,
                    "lateral_join_length_m":math.dist(nearest,start),
                    "reason":"quay already intersects source pier width; join laterally without a backwards landward detour" if trim else "quay does not project inside source pier length and width"}
        pp=line(f["id"],start,end,width,"dock","dock",source_feature_id=f["id"])
        connector=[]
        if math.dist(start,nearest)>.05:connector=line(f"{f['id']}:quay_link",nearest,start,width,"dock","dock_connector",source_feature_id=f["id"],design_inference="lateral quay-to-authored-pier-root connection" if trim else "short connection from planned pier to nearest quay centerline")
        # Shared deck grid is measured from the authored source-segment root.
        # The outer plane uses the existing ceil rule at 0.25 m, so expose its
        # actual edge to traversal consumers rather than the unsnapped source end.
        direction,authored_length=_unit(start,end)
        sampled_length=math.ceil(authored_length/.25-1e-9)*.25
        sampled_end=_add(start,_mul(direction,sampled_length))
        accessible=[]
        for point in (nearest,start,sampled_end):
            if not accessible or math.dist(accessible[-1],point)>1e-7:accessible.append(list(point))
        # Slender fixed supports under the timber deck, never through walk top.
        _,length=_unit(start,end)
        for i in range(1,math.ceil(length/12)+1):
            mid=_lerp(start,end,min(1,i*12/length))
            place(f"{f['id']}:support:{i}",{"kind":"bridge_pier","width_m":1,"length_m":1,"top_y_m":-.5},
                  [mid[0],0,mid[1]],pitch=.5,category="dock_support",source_feature_id=f["id"])
        docks.append({"id":f["id"],"source_footprint_xz_m":copy.deepcopy(fp),"walk_surface_y_m":0,
                      "source_centerline_xz_m":[list(source_start),list(end)],
                      "authored_centerline_xz_m":[list(start),list(end)],
                      "accessible_polyline_xz_m":accessible,
                      "accessible_polyline_endpoint_policy":"final point is actual outward sampled deck edge; consumers apply their own inward capsule stopping margin",
                      "authored_sampled_outward_edge_xz_m":sampled_end,
                      "connection_adjustment":adjustment,
                      "placement_ids":[p["id"] for p in pp+connector],"quay_connection_xz_m":nearest,
                      "connection_status":"authored_access_polyline_pending_runtime_capsule_retest"})

    walls=wall_intervals(plan)
    for si,s in enumerate(walls["segments"]):
        a,b=s["a_xz_m"],s["b_xz_m"];_,length=_unit(a,b);count=math.ceil(length/16)
        yaw=math.degrees(math.atan2(-(b[1]-a[1]),b[0]-a[0]))
        for i in range(count):
            mid=_lerp(a,b,(i+.5)/count)
            place(f"wall:{s['wall_edge']:02d}:{si:02d}:{i:03d}",
                  {"kind":"wall_panel","width_m":length/count,"depth_m":walls["wall_depth_m"],"height_m":walls["wall_height_m"]},
                  [mid[0],0,mid[1]],yaw,.5,"wall",source_wall_edge=s["wall_edge"],
                  source_interval_m=[s["interval_m"][0]+i*length/count,s["interval_m"][0]+(i+1)*length/count])
    walls["deferred_wall_routes"]=deferred

    # Validate source crossings are the exact ten recorded by the previous 2D check.
    source_report=json.loads(WALL_REPORT.read_text()) if WALL_REPORT.exists() else None
    report_match=None
    if source_report:
        expected={(r["road_id"],r["wall_edge"]) for r in source_report["checks"]}
        actual={(r["road_id"],r["wall_edge"]) for r in walls["crossings"]}
        report_match=expected==actual
        if not report_match:raise ValueError(f"wall crossing report mismatch: missing={expected-actual}; extra={actual-expected}")

    return {"schema":"riverstone.city.infrastructure.v1","id":plan["id"]+"_flat_infrastructure",
            "source_plan_id":plan["id"],"source_plan_revision":plan["revision"],
            "source_plan_sha256":_hash(plan),"placements":placements,"master_specs":specs,
            "routes":routes,"street_routes":copy.deepcopy(plan["street_routes"]),"bridges":bridges,"docks":docks,"plazas":plazas,
            "external_gate_approaches":external_gate_approaches,
            "river":{"source":copy.deepcopy(river),"outline_xz_m":river_poly,"water_surface_y_m":-2,
                     "ground_top_y_m":0,"bank_height_m":2,"shoreline_sampling_pitch_m":2,
                     "tile_count":water_tiles,"hydraulic_simulation":False},
            "walls":walls,"terrain":{"top_y_m":0,"base_y_m":-2,"macro_pitch_m":2,"chunk_span_m":32,
                     "tile_count":ground_tiles,"candidate_52m_elevation_realized":False,
                     "height_profiles_authored":False,"all_ground_routes_same_grade":True,
                     "whole_city_fine_fill":False},
            "checks":{"source_wall_report_matches":report_match,"wall_crossings":len(walls["crossings"]),
                      "designated_openings":len(walls["openings"]),"unexplained_wall_gaps":0,
                      "travel_road_segments":len(routes),"deferred_wall_access_segments":len(deferred)},
            "limitations":["Flat Y=0 accessibility stage. Candidate 52 m castle terrain and other district elevations are not realized.",
                           "River is a static lowered 2 m sampled ribbon, not hydraulic simulation.",
                           "Wall walks and access stair reservations remain deferred metadata; this is not a completed elevated wall navigation network.",
                           "Source route widths and centerlines are preserved; draw-only overlap pads do not widen road reservations.",
                           "Road render_offset_y_m is an anti-z-fighting draw offset, not a changed walking grade.",
                           "No cart swept-path, whole-city physics, or player navigation test is claimed by this authoring module."]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",type=Path,default=BRIEF)
    parser.add_argument("--output",type=Path,default=Path(__file__).parent/"generated/infrastructure.json")
    args=parser.parse_args();result=build_infrastructure(json.loads(args.plan.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n")
    summary={"path":str(args.output.relative_to(ROOT)),"placements":len(result["placements"]),"master_specs":len(result["master_specs"]),**result["checks"]}
    (args.output.parent/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
