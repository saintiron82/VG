"""Compile bounded, source-authored r2 grade layers with the unchanged common pipeline.

No source XZ reservation, r1 file, common compiler, cell or exported mesh is edited.
Medium tile ownership is intentionally conservative: only road/precinct/work/entry
neighbourhoods are promoted, while a single 32 m castle sample has fine occupancy.
"""
from __future__ import annotations
import argparse
import collections
import copy
import gc
import hashlib
import itertools
import json
import math
import time
from pathlib import Path

from world_city.runtime_city.topography import author as a
from world_city.runtime_city.infrastructure import author as infrastructure

ROOT = a.ROOT
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "generated/r2_topography"
BASE_PLAN = HERE.parent / "generated/r2/scene.flat_property.json"
R1_INFRA = HERE.parent / "generated/r1/infrastructure.json"
FABRIC = HERE.parent / "urban_fabric/generated/urban_fabric.json"
FINE_BOUNDS = [-576., -256., -544., -224.]
MEDIUM_PITCH = .5
MEDIUM_DEPTH = 3.
COMMON_FILES = ["voxel_character/common/coordinate_planes.py", "voxel_character/common/core.py",
                "voxel_character/common/render_data.py", "voxel_character/tools/mesh.py"]
IDENTITY = [[1,0,0],[0,1,0],[0,0,1]]


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    temp.replace(path)


def relative(path):
    try: return str(Path(path).relative_to(ROOT))
    except ValueError: return str(path)


def polygon_bounds(poly):
    return [min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly)]


def overlap(left, right):
    return left[0] < right[2] - a.EPS and right[0] < left[2] - a.EPS and left[1] < right[3] - a.EPS and right[1] < left[3] - a.EPS


def clipped(poly, bounds):
    if not overlap(polygon_bounds(poly), bounds): return []
    return a._intersect(a._convex(poly), a._inside_planes(a._rect(bounds)))


def affected(poly, field):
    return any(a._eval(f["plane"], *v) > a.EPS for f in field.facets(poly) for v in f["polygon_xz_m"])


def placement_polygon(placement, spec=None):
    spec = spec or placement["spec"]
    x, _, z = placement["position_m"]
    angle = math.radians(placement.get("yaw_deg", 0))
    c, s = math.cos(angle), math.sin(angle)
    local = spec.get("polygons_xz_m")
    if local is None:
        w, length = spec["width_m"], spec.get("length_m", spec.get("depth_m"))
        local = [a._rect([-w/2, -length/2, w/2, length/2])]
    return [[[x+c*u+s*v, z-s*u+c*v] for u,v in poly] for poly in local]


def make_ground_master(bounds, owners, field, *, pitch=.5, depth=MEDIUM_DEPTH, top_offset=0., bottom=None, foundations=None):
    """One common composite owns each visible cell: grass, then source materials.

    Sequential source component compositing is the common compiler's existing
    behavior. All solids share the exact analytic top, pitch and absolute origin.
    There are no independently overlaid coplanar road/grass meshes.
    """
    fine = pitch <= a.WALK_PITCH + a.EPS
    a._bounds(bounds, 8. if fine else 32.)
    master = a._new_master(bounds, "walk_surface" if fine else "distant_ground", "grass", {
        "requested_pitch_m": pitch, "walk_collision_allowed": fine,
        "vertical_depth_m": depth, "top_offset_m": top_offset,
        "surface_owner": "single_common_composite_grass_then_source_materials",
        "draw_offset_y_m": 0., "visible_material_priority": [o["id"] for o in owners],
        "road_reservations_expanded": False})
    for facet in field.facets(a._rect(bounds)):
        a._add_facet(master, facet, "grass" if not top_offset else "earth", thickness=depth if bottom is None else None, bottom=bottom, top_offset=top_offset)
    if not top_offset:
        for owner in owners:
            q = clipped(owner["polygon_xz_m"], bounds)
            if not q: continue
            for facet in field.facets(q):
                a._add_facet(master, facet, owner["material"], thickness=depth if bottom is None else None, bottom=bottom)
    cuts=[]
    for projection in foundations or []:
        poly=clipped(projection["body_footprint_xz_m"],bounds)
        if poly:
            cuts.append({"id":"foundation_cut_"+projection["id"],
                "shape":a._prism(poly,projection["foundation"]["cut_top_y_m"],max(r["height_m"] for r in field.regions)+4),
                "transform":a.UP_EXTRUSION})
    if cuts: master["assembly_cuts"]=cuts
    return a._finish(master)


def make_retaining_master(projection,bounds,field):
    """Stone interface wholly inside realized body; explicit doorway remains open."""
    body=a._convex(projection["body_footprint_xz_m"])
    inset=a._intersect(body,[[p[0],p[1],p[2]-.5] for p in a._inside_planes(body)])
    strips=a._subtract_convex(body,a._inside_planes(inset)) if inset else [body]
    base=projection["position_m"][1]
    master=a._new_master(bounds,"retaining_interface","stone_dark",{
        "building_id":projection["id"],"requested_pitch_m":.5,
        "source_footprint_expanded":False,"inside_body_strip_width_m":.5,
        "doorway_source_clear_width_m":1.8,"walk_collision_allowed":False})
    for strip in strips:
        q=clipped(strip,bounds)
        if not q:continue
        for facet in field.facets(q):
            high=a._clip(facet["polygon_xz_m"],[facet["plane"][0],facet["plane"][1],facet["plane"][2]-base])
            if high and max(a._eval(facet["plane"],*v) for v in high)>base+a.EPS:
                a._add_facet(master,{**facet,"polygon_xz_m":high},"stone_dark",bottom=base-.5)
    if not master["components"]:return None
    master["assembly_cuts"]=[]
    doors=projection.get("all_entrance_contracts",[{"position_m":projection["entrance_position_m"],"yaw_rad":projection["yaw_rad"]}])
    for index,entry in enumerate(doors):
        x,floor,z=entry["position_m"];angle=entry["yaw_rad"];c,s=math.cos(angle),math.sin(angle)
        door=[[x+c*u+s*v,z-s*u+c*v] for u,v in [(-.9,-1.5),(.9,-1.5),(.9,1.5),(-.9,1.5)]]
        master["assembly_cuts"].append({"id":f"clear_authored_entrance_{index}","shape":a._prism(door,floor-.1,floor+2.5),"transform":a.UP_EXTRUSION})
    return a._finish(master)


def _owner(key, category, poly, material="stone", **extra):
    return {"id":key, "category":category, "polygon_xz_m":a._convex(poly), "material":material, **extra}


def build_source_plan(brief=None, infrastructure_plan=None, building_plan=None, fabric=None):
    brief = brief or json.loads(a.BRIEF.read_text())
    infrastructure_plan = infrastructure_plan or json.loads(R1_INFRA.read_text())
    building_plan = building_plan or json.loads(BASE_PLAN.read_text())
    fabric = fabric or json.loads(FABRIC.read_text())
    field = a.field_from_brief(brief)
    nodes = {n["id"]:[n["position_m"][0],n["position_m"][2]] for n in brief["road_nodes"]}
    owners = []; replacement = set(); uf_replacement = []
    road_ids = set(); affected_nodes = set()
    for road in brief["roads"]:
        if road["kind"] == "wall_walk" or road["id"].startswith("WALL_ACCESS"): continue
        poly = infrastructure._ribbon(nodes[road["from_node"]], nodes[road["to_node"]], road["width_m"])
        if affected(poly, field):
            road_ids.add(road["id"]); affected_nodes.update([road["from_node"], road["to_node"]])
            owners.append(_owner(road["id"], "road", poly, source_road_id=road["id"], source_width_m=road["width_m"]))
    for p in infrastructure_plan["placements"]:
        if p["category"] == "road" and p.get("source_road_id") in road_ids: replacement.add(p["id"])
        if p["category"] == "road_join_draw_only" and (p.get("source_node_id") in affected_nodes or field.height(p["position_m"][0],p["position_m"][2]) > a.EPS):
            replacement.add(p["id"])
        if p["category"] == "plaza":
            polys = placement_polygon(p)
            if any(affected(poly,field) for poly in polys):
                replacement.add(p["id"])
                owners[0:0] = [_owner(p["id"]+f":{i}","precinct",poly,p["spec"].get("material","stone"),source_feature_id=p.get("source_feature_id")) for i,poly in enumerate(polys)]
    for p in fabric["placements"]:
        if p["category"] != "flush_work_surface" or not affected(p["footprint_xz_m"],field): continue
        uf_replacement.append(p["id"])
        spec=fabric["master_specs"][p["asset_key"]]
        owners.insert(0,_owner(p["id"],"flush_work_surface",p["footprint_xz_m"],spec.get("material","stone")))
    projections=[]
    for i in building_plan["instances"]:
        projection=a.project_instance(i,building_plan["asset_specs"][i["asset_key"]],field)
        if projection["foundation"]["terrain_max_y_m"] > a.EPS:
            projection["foundation_grid_origin_m"]=[0.,projection["position_m"][1],0.]
            projection["foundation"]["bottom_y_m"]=min(projection["foundation"]["bottom_y_m"],math.floor(projection["foundation"]["cut_top_y_m"]/2)*2-2)
            projection["all_entrance_contracts"]=[]
            spec=building_plan["asset_specs"][i["asset_key"]]
            for local in i.get("all_entrances_local_m",[i["entrance"]["local_position_m"]]):
                angle=i["yaw_rad"];c,s=math.cos(angle),math.sin(angle)
                x=projection["position_m"][0]+c*local[0]+s*local[2]
                z=projection["position_m"][2]-s*local[0]+c*local[2]
                floor=projection["position_m"][1]+local[1]
                # Normal follows nearest realized exterior facade; inner/court doors
                # do not intersect the outside retaining strip.
                side=min(abs(local[0]-spec["width_m"]/2),abs(local[0]+spec["width_m"]/2))
                front=min(abs(local[2]-spec["depth_m"]/2),abs(local[2]+spec["depth_m"]/2))
                projection["all_entrance_contracts"].append({"local_position_m":local,"position_m":[x,floor,z],
                    "source_ground_y_m":field.height(x,z),"floor_minus_ground_m":floor-field.height(x,z),
                    "yaw_rad":angle+(math.pi/2 if side<front else 0.),
                    "status":"primary_anchor_or_unmodified_rigid_secondary_door; medium_collision_unverified"})
            projection["retaining_treatment"]={"material":"stone_dark","strip_width_m":.5,
                "scope":"inside realized body perimeter where H exceeds entrance-anchored body base",
                "entry_clear_width_m":1.8,"coverage":"compiled source retaining strip; .5m distant occupancy, not fine collision certification"}
            projection["integration_exceptions"]=["Entrance approach and threshold remain medium0.5m distant LOD; no fine player passage claim."]
            if any(abs(e["floor_minus_ground_m"])>.1+1e-8 for e in projection["all_entrance_contracts"]):
                projection["integration_exceptions"].append("At least one rigid secondary doorway differs from terrain by more than0.1m; needs a source-authored threshold/approach before traversal.")
            if projection["foundation"]["terrain_max_y_m"]-projection["position_m"][1] > 2.:
                projection["integration_exceptions"].append("Uphill retaining interface exceeds2m; lower wall visibility changes and needs visual review.")
            projections.append(projection)
        p,q=projection["road_connection_m"],projection["entrance_position_m"]
        if math.dist([p[0],p[2]],[q[0],q[2]]) > a.EPS:
            poly=infrastructure._ribbon([p[0],p[2]],[q[0],q[2]],1.5)
            if affected(poly,field):owners.append(_owner(i["id"]+":entrance","entrance_approach",poly,source_building_id=i["id"]))
    owner_boxes = [(o, polygon_bounds(o["polygon_xz_m"])) for o in owners]
    chunks=[]
    for p in infrastructure_plan["placements"]:
        if p["category"] != "terrain": continue
        bounds=polygon_bounds(placement_polygon(p)[0])
        positive_grade=affected(a._rect(bounds),field)
        # Four metre tile-selection collar includes both road and owned shoulder.
        nearby=[o for o,b in owner_boxes if overlap([b[0]-4,b[1]-4,b[2]+4,b[3]+4],bounds)]
        visible=[o["id"] for o in nearby if clipped(o["polygon_xz_m"],bounds)]
        fine=all(abs(x-y)<1e-8 for x,y in zip(bounds,FINE_BOUNDS))
        foundation_ids=[b["id"] for b in projections if clipped(b["body_footprint_xz_m"],bounds)]
        if not positive_grade and not visible and not foundation_ids:continue
        replacement.add(p["id"])
        chunks.append({"id":p["id"],"bounds_xz_m":bounds,"medium_surface":bool(nearby) or fine or bool(foundation_ids),
                       "fine_sample":fine,"boundary_transition_only":not positive_grade,"owner_ids":visible,"selection_owner_ids":[o["id"] for o in nearby],"foundation_ids":foundation_ids})
    if sum(c["fine_sample"] for c in chunks)!=1:raise ValueError("the fine sample must match exactly one existing terrain tile")
    if any(clipped(p["source_footprint_xz_m"],FINE_BOUNDS) for p in projections):
        raise ValueError("fine test sample unexpectedly intersects a building reservation")
    return {"schema":"riverstone.city.topography.source_layers.v1","revision":"r2_topography",
        "source_hashes":{"brief":a._hash(brief),"r1_infrastructure":a._hash(infrastructure_plan),
                         "building_plan":a._hash(building_plan),"urban_fabric":a._hash(fabric)},
        "regions":field.regions,"chunks":chunks,"owners":owners,"building_footing_contracts":projections,
        "replace_r1_placement_ids":sorted(replacement),"replace_urban_fabric_placement_ids":sorted(uf_replacement),
        "budgets":{"macro_pitch_m":2.,"medium_pitch_m":.5,"fine_pitch_m":.1,
                   "macro_chunk_count":len(chunks),"medium_chunk_count":sum(c["medium_surface"] for c in chunks),
                   "flat_boundary_transition_chunk_count":sum(c["boundary_transition_only"] for c in chunks),
                   "flat_boundary_transition_area_m2":sum((c["bounds_xz_m"][2]-c["bounds_xz_m"][0])*(c["bounds_xz_m"][3]-c["bounds_xz_m"][1]) for c in chunks if c["boundary_transition_only"]),
                   "fine_active_area_m2":1024.,"fine_active_area_cap_m2":1024.,"fine_patch_count":64,
                   "fine_patch_span_m":4.,"maximum_candidate_cells_per_master":2000000,
                   "maximum_retained_cells_per_master":250000,"whole_city_fine_fill":False,
                   "owner_counts":dict(collections.Counter(o["category"] for o in owners))},
        "fine_sample":{"bounds_xz_m":FINE_BOUNDS,"route_id":"RT_CASTLE_CLIMB",
                       "walk_test_scope":"interior of sample; outer mixed-LOD seam is not traversable certified",
                       "full_grass_and_source_road_ownership":True},
        "ground_ownership_policy":"Affected r1 terrain tiles replaced atomically; promoted neighbourhoods use a recessed macro base plus one medium grass/source-material composite. Fine sample substitutes same-origin .1 cap, .2 buried buffer and .5 support.",
        "building_contract_scope":"Source body cuts, stone foundations and uphill retaining interfaces compiled here. Parent applies exact returned Y anchors; fine doorway/physics and visual clearance remain unverified.",
        "unwalkable_distant_lod_scope":"All macro2m and medium0.5m surfaces, wall access, gates and outer fine/medium seam remain outside the verified walk domain."}


def _jobs(plan):
    field=a.GradeField(plan["regions"])
    owners={o["id"]:o for o in plan["owners"]}
    foundations={b["id"]:b for b in plan["building_footing_contracts"]}
    for chunk in plan["chunks"]:
        bounds=chunk["bounds_xz_m"];key=chunk["id"].replace(":","_")
        selected=[owners[o] for o in chunk["owner_ids"]]
        projected=[foundations[i] for i in chunk["foundation_ids"]]
        macro=a.make_terrain_master(bounds,field,surface_recess=chunk["medium_surface"],foundation_projections=projected)
        yield "macro_"+key,macro,2.,"terrain_macro",chunk
        if chunk["fine_sample"]:
            # Support top is buried1m. The .2 buffer bridges to the .4m fine cap.
            support=make_ground_master(bounds,[],field,pitch=.5,depth=3.,top_offset=-1.)
            yield "support_"+key,support,.5,"fine_buried_support",chunk
            for ix in range(8):
                for iz in range(8):
                    b=[bounds[0]+ix*4,bounds[1]+iz*4,bounds[0]+(ix+1)*4,bounds[1]+(iz+1)*4]
                    stem=f"{key}_{ix}_{iz}"
                    buffer=a.make_walk_buffer_master(b,field=field)
                    yield "buffer_"+stem,buffer,.2,"fine_buried_buffer",chunk
                    cap=make_ground_master(b,selected,field,pitch=.1,depth=a.SURFACE_DEPTH)
                    yield "fine_"+stem,cap,.1,"fine_walk_surface",chunk
        elif chunk["medium_surface"]:
            # Deep foundation excavation is filled by the same medium composite.
            bottom=min((p["foundation"]["cut_top_y_m"]-2 for p in projected),default=None)
            # Foundation-heavy chunks use16m surface pieces to bound candidate work.
            count=2 if projected else 1
            for ix in range(count):
                for iz in range(count):
                    step=(bounds[2]-bounds[0])/count;stepz=(bounds[3]-bounds[1])/count
                    sub=[bounds[0]+ix*step,bounds[1]+iz*stepz,bounds[0]+(ix+1)*step,bounds[1]+(iz+1)*stepz]
                    cover=make_ground_master(sub,selected,field,bottom=bottom,foundations=projected)
                    yield f"medium_{key}_{ix}_{iz}",cover,.5,"terrain_medium",chunk
        for projection in projected:
            footing=a.make_foundation_master(projection,bounds)
            footing["grid_origin"]=[0.,projection["position_m"][1],0.]
            footing["metadata"].update({"sampling_anchor":"rigid_body_base_exact_Y",
                "shared_boundary_policy":"same absolute XZ planes; same body-base Y origin across all footing chunks of this building",
                "required_sampled_top_y_m":projection["position_m"][1]})
            footing["id"]="pending";footing=a._finish(footing)
            yield "foundation_"+key+"_"+projection["id"],footing,.5,"building_foundation",chunk
            retaining=make_retaining_master(projection,bounds,field)
            if retaining:
                yield "retaining_"+key+"_"+projection["id"],retaining,.5,"building_retaining_interface",chunk


def candidate_budget(master,pitch):
    """Exact common candidate AABB count, without sampling any output cells."""
    from voxel_character.common import coordinate_planes,core
    numeric,_=coordinate_planes.resolve_master(master,{"pitch":pitch})
    components,instances=core.validate_master(numeric,pitch)
    origin=numeric.get("grid_origin",[0,0,0]);total=0
    def count(operation,placement):
        shape=core.prepare_shape(operation["shape"],pitch)
        lo,hi=core.shape_bounds(shape)
        corners=[core.apply(placement,p) for p in itertools.product(*zip(lo,hi))]
        low=[min(p[i] for p in corners) for i in range(3)]
        high=[max(p[i] for p in corners) for i in range(3)]
        return math.prod(max(0,math.ceil((b-o)/pitch-core.EPS)-math.floor((v-o)/pitch+core.EPS)) for v,b,o in zip(low,high,origin))
    for instance in instances.values():
        if instance.get("parent"):raise ValueError("integration sources must use identity world instances")
        placement=core.transform(instance.get("transform"))
        for operation in components[instance["component"]]["operations"]:
            total+=count(operation,core.compose(placement,core.transform(operation.get("transform"))))
    for operation in numeric.get("assembly_cuts",[]):total+=count(operation,core.transform(operation.get("transform")))
    return total


def validate_compiled_layer(compiled,master,field):
    pitch=compiled["pitch"];bounds=master["metadata"]["bounds_xz_m"]
    if not compiled["valid"]:raise ValueError("common validation failed")
    spans={}
    for x,y,z,*_ in compiled["cells"]:
        xx,yy,zz=(x+.5)*pitch,(y+.5)*pitch,(z+.5)*pitch
        if not bounds[0]-1e-7<=xx<=bounds[2]+1e-7 or not bounds[1]-1e-7<=zz<=bounds[3]+1e-7:
            raise ValueError("sample escaped bounded source chunk")
        spans[x,z]=max(spans.get((x,z),-math.inf),(y+1)*pitch)
    kind=master["metadata"]["kind"];offset=master["metadata"].get("top_offset_m",0.)
    maximum_error=-math.inf
    for (x,z),top in spans.items():
        if kind in {"building_foundation","wall_foundation"}:
            expected=master["metadata"].get("required_sampled_top_y_m")
            if expected is not None and abs(top+compiled["grid_origin"][1]-expected)>1e-7:
                raise ValueError("sampled foundation top does not match exact rigid body base")
            continue
        limit=field.height((x+.5)*pitch,(z+.5)*pitch)+offset+pitch/2
        if top>limit+1e-7:raise ValueError(f"{kind} visible top exceeds source-height quantization bound")
        maximum_error=max(maximum_error,top-(limit-pitch/2))
    return {"common_valid":True,"nonempty":bool(spans),"bounded_source_columns":True,
            "source_height_upper_bound_pass":True,"column_count":len(spans),
            "maximum_signed_source_top_error_m":maximum_error if math.isfinite(maximum_error) else None,
            "foundation_exact_base_top_pass":True if kind in {"building_foundation","wall_foundation"} else None}


def compile_layers(plan, out=DEFAULT_OUT, *, max_jobs=None, progress=True):
    out=Path(out)
    if (out/"layer_manifest.json").exists():
        previous=json.loads((out/"layer_manifest.json").read_text())
        previous["status"]="compiling_do_not_integrate"
        write(out/"layer_manifest.json",previous)
    write(out/"source_plan.json",plan)
    snapshot_path=out/"source_snapshots"/(a._hash(plan)+".json")
    write(snapshot_path,plan)
    common_hashes={p:sha(ROOT/p) for p in COMMON_FILES}
    assets={};placements=[];empty=[];fine_columns={};fine_buffers={};fine_support={};fine_macro={}
    building_resources=collections.defaultdict(lambda: {"foundation_asset_keys":[],"retaining_asset_keys":[]})
    started=time.monotonic();compiled_count=0;hit_count=0
    field=a.GradeField(plan["regions"])
    def column_spans(compiled):
        spans={};pitch=compiled["pitch"]
        for x,y,z,*_ in compiled["cells"]:
            lo,hi=spans.get((x,z),(math.inf,-math.inf))
            spans[x,z]=(min(lo,y*pitch),max(hi,(y+1)*pitch))
        return spans
    for index,(key,master,pitch,category,chunk) in enumerate(_jobs(plan)):
        if max_jobs is not None and index>=max_jobs:break
        mp=out/"masters"/(key+".json");rp=out/"renders"/(key+".json");cp=out/"cache"/(key+".json")
        write(mp,master)
        fingerprint={"master":sha(mp),"pitch":pitch,"common":common_hashes}
        cached=json.loads(cp.read_text()) if cp.exists() else None
        stat=None
        if cached and cached.get("key")==fingerprint and (cached.get("empty") or rp.exists() and cached.get("render_sha256")==sha(rp)):
            stat=cached;hit_count+=1
        if stat is None:
            candidates=candidate_budget(master,pitch)
            if candidates>2000000:raise ValueError(f"Source candidate budget exceeded before compile: {key}: {candidates}")
            compiled,render=a.compile_sample(master,pitch,max_candidate_cells=2000000,max_output_cells=250000)
            validation=validate_compiled_layer(compiled,master,field)
            if compiled["candidate_cells"]!=candidates:raise ValueError("candidate budget estimator drift")
            if render is None:stat={"key":fingerprint,"empty":True,"validation":validation}
            else:
                write(rp,render)
                stat={"key":fingerprint,"render_path":relative(rp),"render_sha256":sha(rp),
                      "master_path":relative(mp),"master_sha256":sha(mp),"bounds":render["bounds"],
                      "cell_count":render["cell_count"],"quad_count":render["quad_count"],"pitch_m":pitch,
                      "candidate_cells":compiled["candidate_cells"],"payload_hash":compiled["payload_hash"],"validation":validation}
                if chunk["fine_sample"]:
                    stat["column_spans"]=[[x,z,*v] for (x,z),v in sorted(column_spans(compiled).items())]
            write(cp,stat);compiled_count+=1
            del compiled,render
        if stat.get("empty"):empty.append(key);continue
        if chunk["fine_sample"]:
            target={"fine_walk_surface":fine_columns,"fine_buried_buffer":fine_buffers,
                    "fine_buried_support":fine_support,"terrain_macro":fine_macro}[category]
            for x,z,lo,hi in stat["column_spans"]:
                if (x,z) in target:raise ValueError("same-pitch chunk overlap")
                target[x,z]=(lo,hi)
        cleanstat={k:v for k,v in stat.items() if k!="column_spans"};assets[key]=cleanstat
        bounds=chunk["bounds_xz_m"]
        building_id=master["metadata"].get("building_id")
        if building_id:
            slot="foundation_asset_keys" if category=="building_foundation" else "retaining_asset_keys"
            building_resources[building_id][slot].append(key)
        placements.append({"id":"R2_GRADE:"+key,"asset_key":key,"position_m":[0,0,0],"yaw_deg":0,
            "transform":{"basis":IDENTITY,"translation":[0,0,0]},"category":category,
            "requested_pitch_m":pitch,"render_offset_y_m":0,"collision_enabled":category=="fine_walk_surface",
            "walk_surface_y_m":"source_H(x,z)","source_ground_id":chunk["id"],
            "chunk_xz":[math.floor(bounds[0]/32),math.floor(bounds[1]/32)],
            "stream_chunk_xz":[math.floor(bounds[0]/64),math.floor(bounds[1]/64)],
            "world_coordinate_geometry":True,**({"source_building_id":building_id} if building_id else {})})
        if progress and (index%20==0 or category=="fine_walk_surface"):
            print(json.dumps({"job":index+1,"asset":key,"cells":stat["cell_count"],"compiled":compiled_count,"cache_hits":hit_count,"elapsed_s":round(time.monotonic()-started,1)}),flush=True)
        gc.collect()
    complete=max_jobs is None
    validation=validate_fine_columns(plan,fine_columns,fine_buffers,fine_support,fine_macro) if fine_columns else {"status":"not_compiled"}
    footing_contracts=copy.deepcopy(plan["building_footing_contracts"])
    for projection in footing_contracts:
        projection["compiled_resources"]=building_resources.get(projection["id"],{"foundation_asset_keys":[],"retaining_asset_keys":[]})
        projection["foundation_source_cut_applied"]=complete and bool(projection["compiled_resources"]["foundation_asset_keys"])
    manifest={"schema":"riverstone.city.topography.layer_manifest.v1","revision":"r2_topography",
        "status":"compiled_structural_only" if complete else "partial_compile_do_not_integrate",
        "source_plan_path":relative(snapshot_path),"source_plan_sha256":sha(snapshot_path),
        "source_hashes":plan["source_hashes"],"common_source_hashes":common_hashes,
        "replace_r1_placement_ids":plan["replace_r1_placement_ids"],
        "replace_urban_fabric_placement_ids":plan["replace_urban_fabric_placement_ids"],
        "assets":assets,"placements":placements,"sampled_empty_keys":empty,
        "changed_ground_ownership":{"source_owners":plan["owners"],"chunks":plan["chunks"],"policy":plan["ground_ownership_policy"]},
        "building_footing_contracts":footing_contracts,"building_contract_scope":plan["building_contract_scope"],
        "tested_fine_region":{**plan["fine_sample"],"validation":validation},
        "unwalkable_distant_lod_scope":plan["unwalkable_distant_lod_scope"],
        "budgets":plan["budgets"],"execution":{"compiled":compiled_count,"cache_hits":hit_count,
            "wall_time_s":round(time.monotonic()-started,3),"aggregate_asset_cells":sum(v["cell_count"] for v in assets.values()),
            "aggregate_asset_quads":sum(v["quad_count"] for v in assets.values()),"peak_candidate_cells":max((v["candidate_cells"] for v in assets.values()),default=0),
            "memory_strategy":"one bounded common compiled cell payload at a time; retain only sampled fine-column spans for QA"},
        "preservation":{"r1_written":False,"common_written":False,"river_and_bridge_placements_replaced":False,
                        "source_xz_reservations_unchanged":True,"no_runtime_displacement":True,"no_infinite_plane":True},
        "limitations":["Headless common-source/occupancy validation only; no visual or full-city player traversal claim.",
                       "Medium and macro are distant LOD and never certified as fine walk collision.",
                       "Independent exports retain some underground overlapping/internal faces; there is no new meshing engine.",
                       "Parent must apply returned building anchors; medium foundations/retaining interfaces do not certify fine entrances, interiors or visual clearance."]}
    physics_path=HERE.parent/"traversal_r2/evidence/fine_results.json"
    if physics_path.exists():
        physics=json.loads(physics_path.read_text())
        manifest["fine_controller_traversal"]={"status":physics.get("status"),"summary":physics.get("summary"),
            "report_path":relative(physics_path),"report_sha256":sha(physics_path),
            "scope":"Independent actual-triangle generic capsule run. Occupancy seam pass does not imply walking pass."}
        manifest["limitations"].append("Independent generic capsule test fails uphill0.1m risers and has transient floor loss; fine occupancy is gap-free but not certified traversable with that controller.")
    write(out/"layer_manifest.json",manifest)
    write(out/"structural_validation.json",validation)
    write(out/"summary.json",{k:manifest[k] for k in ["status","budgets","execution","tested_fine_region","preservation","limitations"]})
    return manifest


def validate_fine_columns(plan, fine, buffer, support, macro):
    bounds=plan["fine_sample"]["bounds_xz_m"];field=a.GradeField(plan["regions"])
    expected=round((bounds[2]-bounds[0])*(bounds[3]-bounds[1])/.01)
    if len(fine)!=expected:raise ValueError(f"fine cap holes: {len(fine)} != {expected}")
    max_step=0.;max_error=0.;minimum_buffer_overlap=math.inf;minimum_support_overlap=math.inf;minimum_macro_clearance=math.inf
    for (x,z),(lo,hi) in fine.items():
        xx,zz=(x+.5)*.1,(z+.5)*.1
        blo,bhi=buffer[math.floor(xx/.2),math.floor(zz/.2)]
        slo,shi=support[math.floor(xx/.5),math.floor(zz/.5)]
        mlo,mhi=macro[math.floor(xx/2),math.floor(zz/2)]
        if bhi < lo-1e-8 or shi < blo-1e-8 or mhi < slo-1e-8:raise ValueError("vertical layer gap")
        if bhi >= hi-1e-8 or shi >= hi-1e-8 or mhi >= hi-1e-8:raise ValueError("coarse support pokes through fine cap")
        minimum_buffer_overlap=min(minimum_buffer_overlap,bhi-lo)
        minimum_support_overlap=min(minimum_support_overlap,shi-blo)
        minimum_macro_clearance=min(minimum_macro_clearance,hi-mhi)
        max_error=max(max_error,abs(hi-field.height(xx,zz)))
        for k in [(x+1,z),(x,z+1)]:
            if k in fine:max_step=max(max_step,abs(hi-fine[k][1]))
    if max_step>.10000001:raise ValueError("fine cap exceeds one-cell rise")
    if max_error>.05000001:raise ValueError("fine cap deviates from source H by more than half pitch")
    return {"status":"passed","fine_column_count":len(fine),"fine_area_m2":len(fine)*.01,
        "maximum_neighbour_step_m":max_step,"maximum_sampled_top_error_m":max_error,
        "minimum_fine_buffer_overlap_m":minimum_buffer_overlap,"minimum_buffer_support_overlap_m":minimum_support_overlap,
        "minimum_macro_below_fine_top_m":minimum_macro_clearance,"same_pitch_internal_seams_gap_count":0,
        "missing_fine_columns":0,"support_poke_through_count":0,"vertical_layer_gap_count":0,
        "road_shoulder_policy":"One source-height common composite shares the entire 32m ground cap, including exact road material and surrounding grass.",
        "excluded_scope":"Outer sample/medium seam, buildings, gates, carts, physics and full-city traversal."}


def build_wall_source_plan(infrastructure_plan=None,field=None):
    """Rigid curtain walls keep original XZ/yaw/gaps and receive stone footings."""
    infra=infrastructure_plan or json.loads(R1_INFRA.read_text());field=field or a.default_field()
    walls=[];affected_walls=[]
    for placement in infra["placements"]:
        if placement["category"]!="wall":continue
        asset=infra["assets"][placement["asset_key"]];b=asset["bounds"]
        local=a._rect([b["min"][0],b["min"][2],b["max"][0],b["max"][2]])
        x,_,z=placement["position_m"];angle=math.radians(placement["yaw_deg"]);c,s=math.cos(angle),math.sin(angle)
        poly=a._convex([[x+c*u+s*v,z-s*u+c*v] for u,v in local])
        heights=[a._eval(f["plane"],*v) for f in field.facets(poly) for v in f["polygon_xz_m"]]
        top=math.ceil(max(heights)/.5-1e-9)*.5 if max(heights)>a.EPS else 0.
        wall={"id":placement["id"],"source_asset_key":placement["asset_key"],
            "source_wall_edge":placement["source_wall_edge"],"source_interval_m":placement["source_interval_m"],
            "actual_compiled_body_footprint_xz_m":poly,"bounds_xz_m":polygon_bounds(poly),
            "position_m":[x,top,z],"yaw_deg":placement["yaw_deg"],
            "transform":{**placement["transform"],"translation":[x,top,z]},
            "terrain_min_y_m":min(heights),"terrain_max_y_m":max(heights),
            "support_bottom_y_m":min(heights)-2.5,"support_top_y_m":top,
            "wall_solid_height_m":placement["spec"]["height_m"],"source_xz_unchanged":True}
        walls.append(wall)
        if max(heights)>a.EPS:affected_walls.append(wall)
    adjacency=[];discontinuities=[]
    for index,left in enumerate(walls):
        for right in walls[index+1:]:
            same_edge=left["source_wall_edge"]==right["source_wall_edge"]
            adjacent=same_edge and (abs(left["source_interval_m"][1]-right["source_interval_m"][0])<1e-6 or abs(right["source_interval_m"][1]-left["source_interval_m"][0])<1e-6)
            if not adjacent and overlap(left["bounds_xz_m"],right["bounds_xz_m"]):
                adjacent=bool(a._intersect(left["actual_compiled_body_footprint_xz_m"],a._inside_planes(right["actual_compiled_body_footprint_xz_m"])))
            if not adjacent:continue
            lo=max(left["position_m"][1],right["position_m"][1])
            hi=min(left["position_m"][1]+left["wall_solid_height_m"],right["position_m"][1]+right["wall_solid_height_m"])
            record={"wall_ids":[left["id"],right["id"]],"base_step_m":abs(left["position_m"][1]-right["position_m"][1]),
                    "solid_body_vertical_overlap_m":hi-lo,"status":"continuous_vertical_overlap" if hi>lo else "discontinuous"}
            adjacency.append(record)
            if hi<=lo:discontinuities.append(record)
    opening_intersections=[]
    for wall in affected_walls:
        for opening in infra["walls"]["openings"]:
            poly=opening.get("footprint_xz_m")
            if poly and i_overlap(wall["actual_compiled_body_footprint_xz_m"],poly):
                opening_intersections.append({"wall_id":wall["id"],"opening_id":opening["id"]})
            if wall["source_wall_edge"]==opening["wall_edge"]:
                lo,hi=wall["source_interval_m"];a0,a1=opening["interval_m"]
                if min(hi,a1)-max(lo,a0)>1e-6:opening_intersections.append({"wall_id":wall["id"],"opening_id":opening["id"],"interval_overlap":True})
    if opening_intersections:raise ValueError(f"wall footing source intersects an intentional opening: {opening_intersections}")
    return {"schema":"riverstone.city.wall_grade.source.v1","source_infrastructure_sha256":sha(R1_INFRA),
            "wall_placement_updates":affected_walls,"adjacency_checks":adjacency,"discontinuities":discontinuities,
            "preserved_openings":copy.deepcopy(infra["walls"]["openings"]),"opening_intersection_count":0,
            "policy":"Only existing wall rigid Y changes; exact original wall XZ/yaw and gate gaps stay fixed. Stone support top equals half-metre-ceil of max H over actual compiled wall footprint.",
            "limits":{"pitch_m":.5,"max_candidate_cells":2000000,"max_retained_cells":250000},
            "exceptions":["Wall-walk access and tower-to-curtain walk connections remain unverified; this is vertical structural continuity only."]}


def i_overlap(left,right):
    return overlap(polygon_bounds(left),polygon_bounds(right)) and bool(a._intersect(a._convex(left),a._inside_planes(a._convex(right))))


def compile_wall_supplement(source=None,out=DEFAULT_OUT):
    source=source or build_wall_source_plan();out=Path(out);field=a.default_field()
    write(out/"wall_source_plan.json",source)
    common_hashes={p:sha(ROOT/p) for p in COMMON_FILES};assets={};placements=[]
    for wall in source["wall_placement_updates"]:
        bounds=a._bounds(wall["bounds_xz_m"])
        master=a._new_master(bounds,"wall_foundation","stone_dark",{
            "source_wall_id":wall["id"],"requested_pitch_m":.5,"walk_collision_allowed":False,
            "required_sampled_top_y_m":wall["support_top_y_m"],"intentional_openings_preserved":True})
        a._add_facet(master,{"plane":[0,0,wall["support_top_y_m"]],"polygon_xz_m":wall["actual_compiled_body_footprint_xz_m"]},
                     "stone_dark",bottom=wall["support_bottom_y_m"])
        master=a._finish(master);key="wall_support_"+wall["id"].replace(":","_")
        mp=out/"masters"/(key+".json");rp=out/"renders"/(key+".json");cp=out/"cache"/(key+".json")
        write(mp,master);fingerprint={"master":sha(mp),"pitch":.5,"common":common_hashes}
        stat=json.loads(cp.read_text()) if cp.exists() else None
        if not stat or stat.get("key")!=fingerprint or not rp.exists() or stat.get("render_sha256")!=sha(rp):
            candidates=candidate_budget(master,.5)
            if candidates>2000000:raise ValueError("wall support exceeds bounded candidate budget")
            compiled,render=a.compile_sample(master,.5,max_candidate_cells=2000000,max_output_cells=250000)
            if render is None:raise ValueError("wall support has no compiled occupancy")
            validation=validate_compiled_layer(compiled,master,field);write(rp,render)
            if abs(render["bounds"]["max"][1]-wall["support_top_y_m"])>1e-8:raise ValueError("wall support sampled top mismatch")
            stat={"key":fingerprint,"render_path":relative(rp),"render_sha256":sha(rp),"master_path":relative(mp),
                  "master_sha256":sha(mp),"bounds":render["bounds"],"cell_count":render["cell_count"],
                  "quad_count":render["quad_count"],"pitch_m":.5,"candidate_cells":compiled["candidate_cells"],"validation":validation}
            write(cp,stat);del compiled,render
        assets[key]=stat
        placements.append({"id":"R2_GRADE:"+key,"asset_key":key,"source_wall_id":wall["id"],
            "position_m":[0,0,0],"yaw_deg":0,"transform":{"basis":IDENTITY,"translation":[0,0,0]},
            "category":"wall_foundation","render_offset_y_m":0,"collision_enabled":False,
            "requested_pitch_m":.5,"world_coordinate_geometry":True,
            "stream_chunk_xz":[math.floor(wall["position_m"][0]/64),math.floor(wall["position_m"][2]/64)]})
    manifest={**source,"schema":"riverstone.city.wall_grade.layer_manifest.v1","status":"compiled_structural_only",
        "source_plan_path":relative(out/"wall_source_plan.json"),"source_plan_sha256":sha(out/"wall_source_plan.json"),
        "assets":assets,"placements":placements,"common_source_hashes":common_hashes,
        "wall_projection_contracts":[{"source_placement_id":w["id"],**w} for w in source["wall_placement_updates"]],
        "summary":{"wall_updates":len(source["wall_placement_updates"]),"support_assets":len(assets),
                   "support_cells":sum(v["cell_count"] for v in assets.values()),"support_quads":sum(v["quad_count"] for v in assets.values()),
                   "discontinuity_count":len(source["discontinuities"]),"opening_intersection_count":0,
                   "maximum_base_step_m":max((v["base_step_m"] for v in source["adjacency_checks"]),default=0),
                   "minimum_body_vertical_overlap_m":min((v["solid_body_vertical_overlap_m"] for v in source["adjacency_checks"]),default=None)}}
    write(out/"wall_supplement_manifest.json",manifest);return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUT)
    parser.add_argument("--source-only",action="store_true")
    parser.add_argument("--max-jobs",type=int)
    args=parser.parse_args();plan=build_source_plan();write(args.out/"source_plan.json",plan)
    print(json.dumps(plan["budgets"],indent=2),flush=True)
    if not args.source_only:
        result=compile_layers(plan,args.out,max_jobs=args.max_jobs)
        print(json.dumps({"status":result["status"],"assets":len(result["assets"]),"execution":result["execution"]},indent=2),flush=True)

if __name__=="__main__":main()
