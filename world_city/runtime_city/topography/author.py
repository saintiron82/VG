"""Bounded terrain grade authoring through the existing common master compiler.

This is CSG source authoring, not a mesher, physics engine, or live r1 patch.
All XZ coordinates remain in the recovered plan. Absolute world coordinates and
one common grid origin are intentional: moving a returned master is forbidden.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BRIEF = ROOT / "world_city/data/city_brief.v2.json"
SCENE = ROOT / "world_city/runtime_city/generated/r1/scene.json"
HISTORY = ROOT / "world_city/city_history.json"
GRADE_LIMIT = .125
MACRO_PITCH = 2.
WALK_PITCH = .1
SURFACE_DEPTH = .4
FOUNDATION_EMBED = 2.5
BUFFER_PITCH = .2
BUFFER_TOP_OFFSET = -.2
BUFFER_DEPTH = 1.3
BURIED_TOP_OFFSET = -1.
FINE_SHOULDER = 2.
MEDIUM_SHOULDER = 4.
MACRO_GUARD = 2.
RECESS_DEPTH = 2.
MAX_SURFACE_SPAN = 8.
EPS = 1e-8


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _finite(*values):
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        raise ValueError("finite numeric coordinates required")


def _area(poly):
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly, poly[1:]+poly[:1])) / 2


def _convex(poly):
    p = [list(v) for v in poly]
    if len(p) < 3 or any(len(v) != 2 for v in p):
        raise ValueError("at least three XZ vertices required")
    for v in p: _finite(*v)
    if abs(_area(p)) < EPS: raise ValueError("degenerate polygon")
    if _area(p) < 0: p.reverse()
    for a,b,c in zip(p, p[1:]+p[:1], p[2:]+p[:2]):
        if (b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]) < -EPS:
            raise ValueError("convex source polygon required; do not silently alter its footprint")
    return p


def _clean(poly):
    out = []
    for p in poly:
        if not out or math.dist(p, out[-1]) > EPS: out.append(p)
    if len(out)>1 and math.dist(out[0], out[-1]) <= EPS: out.pop()
    return out if len(out)>=3 and abs(_area(out))>EPS else []


def _eval(plane, x, z):
    return plane[0]*x + plane[1]*z + plane[2]


def _clip(poly, plane):
    """Clip a convex source polygon to ax+bz+c >= 0; no sampled output cells."""
    if not poly: return []
    out=[]; prev=poly[-1]; pv=_eval(plane,*prev)
    for cur in poly:
        cv=_eval(plane,*cur)
        if (pv >= -EPS) != (cv >= -EPS):
            t=pv/(pv-cv)
            out.append([prev[i]+t*(cur[i]-prev[i]) for i in (0,1)])
        if cv >= -EPS: out.append(list(cur))
        prev,pv=cur,cv
    return _clean(out)


def _inside_planes(poly):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        length=math.dist(a,b)
        if length<=EPS: raise ValueError("duplicate polygon vertex")
        nx,nz=-(b[1]-a[1])/length,(b[0]-a[0])/length
        result.append([nx,nz,-nx*a[0]-nz*a[1]])
    return result


def _intersect(poly, planes):
    for plane in planes:
        poly=_clip(poly,plane)
        if not poly: break
    return poly


def _subtract_convex(poly, planes):
    """Disjoint convex source pieces of poly outside a convex reservation."""
    outside=[]; inside=poly
    for plane in planes:
        if not inside: break
        q=_clip(inside,[-v for v in plane])
        if q: outside.append(q)
        inside=_clip(inside,plane)
    return outside


def _bounds(bounds, max_span=32.):
    if len(bounds)!=4: raise ValueError("bounds are [xmin,zmin,xmax,zmax]")
    x0,z0,x1,z1=map(float,bounds);_finite(x0,z0,x1,z1)
    if not 0<x1-x0<=max_span+EPS or not 0<z1-z0<=max_span+EPS:
        raise ValueError(f"positive XZ span bounded to {max_span:g} m required")
    return [x0,z0,x1,z1]


def _rect(bounds):
    x0,z0,x1,z1=bounds
    return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]]


class GradeField:
    """A continuous piecewise-affine, globally Lipschitz two-precinct field.

    Per precinct: max(0, min(plateau_height, height + grade * inward_distance
    to each original precinct edge)). The two positive supports must not overlap.
    Their max with zero is continuous and has grade <= max(region.grade).
    """
    def __init__(self, regions):
        self.regions=copy.deepcopy(regions)
        for region in self.regions:
            _finite(region["height_m"],region["grade"])
            if not 0<region["grade"]<=GRADE_LIMIT or region["height_m"]<=0:
                raise ValueError("positive height and grade <= configured walk limit required")
            region["plateau_polygon_xz_m"]=_convex(region["plateau_polygon_xz_m"])
            h,s=region["height_m"],region["grade"]
            region["planes"]=[[0.,0.,h]]+[[s*a,s*b,h+s*c] for a,b,c in _inside_planes(region["plateau_polygon_xz_m"])]
            # The bounding square only constructs a finite convex support polygon.
            p=region["plateau_polygon_xz_m"];reach=4*h/s
            support=_rect([min(v[0] for v in p)-reach,min(v[1] for v in p)-reach,
                           max(v[0] for v in p)+reach,max(v[1] for v in p)+reach])
            region["support_polygon_xz_m"]=_intersect(support,region["planes"][1:])
        for i,a in enumerate(self.regions):
            for b in self.regions[i+1:]:
                if _intersect(a["support_polygon_xz_m"],b["planes"][1:]):
                    raise ValueError("overlapping positive terrain supports need a new reviewed grade design")
        self.max_grade=max((r["grade"] for r in self.regions),default=0.)

    def height(self,x,z):
        _finite(x,z)
        return max([0.]+[min(_eval(p,x,z) for p in r["planes"]) for r in self.regions])

    def facets(self,polygon):
        """Convex source domains with their exact affine top, including lower city."""
        polygon=_convex(polygon);result=[];flat=[polygon]
        for region in self.regions:
            ps=region["planes"]
            for i,p in enumerate(ps):
                # p is active where it is nonnegative and no other plane is lower.
                q=_intersect(polygon,[p]+[[v[j]-p[j] for j in range(3)] for k,v in enumerate(ps) if k!=i])
                if q: result.append({"region_id":region["id"],"plane":list(p),"polygon_xz_m":q})
            flat=[q for f in flat for q in _subtract_convex(f,ps[1:])]
        result.extend({"region_id":"lower_city","plane":[0.,0.,0.],"polygon_xz_m":q} for q in flat)
        return result

    def profile(self,a,b):
        """Exact affine breakpoints along an unchanged source XZ segment."""
        _finite(*a,*b)
        length=math.dist(a,b)
        if length<EPS:
            return {"points_m":[[a[0],self.height(*a),a[1]]],"length_xz_m":0.,"max_grade":0.}
        lines=[[0.,0.]]
        for r in self.regions:
            for p in r["planes"]:
                ya,yb=_eval(p,*a),_eval(p,*b)
                lines.append([ya,yb-ya])
        ts={0.,1.}
        for i,(ya,da) in enumerate(lines):
            for yb,db in lines[i+1:]:
                if abs(da-db)>1e-12:
                    t=(yb-ya)/(da-db)
                    if EPS<t<1-EPS: ts.add(t)
        points=[]
        for t in sorted(ts):
            x,z=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
            points.append([x,self.height(x,z),z])
        # Remove redundant collinear source breakpoints; this is not voxel decimation.
        clean=[]
        for p in points:
            if clean and math.dist([p[0],p[2]],[clean[-1][0],clean[-1][2]])<EPS: continue
            while len(clean)>=2:
                q,r=clean[-2:];l1=math.hypot(r[0]-q[0],r[2]-q[2]);l2=math.hypot(p[0]-r[0],p[2]-r[2])
                if abs((r[1]-q[1])/l1-(p[1]-r[1])/l2)>1e-9: break
                clean.pop()
            clean.append(p)
        clean[0]=[a[0],self.height(*a),a[1]]
        clean[-1]=[b[0],self.height(*b),b[1]]
        slopes=[abs(q[1]-p[1])/math.hypot(q[0]-p[0],q[2]-p[2]) for p,q in zip(clean,clean[1:])]
        return {"points_m":clean,"length_xz_m":length,"max_grade":max(slopes,default=0.)}


def field_from_brief(brief):
    features={f["id"]:f for f in brief["site_features"]}
    return GradeField([
        {"id":"castle_hill","source_feature_id":"F_CASTLE_CLOSE","district_id":"D01",
         "height_m":24.,"grade":.12,"original_candidate_height_m":52.,
         "plateau_polygon_xz_m":features["F_CASTLE_CLOSE"]["footprint_xz_m"]},
        {"id":"cathedral_terrace","source_feature_id":"F_CATHEDRAL_CLOSE","district_id":"D02",
         "height_m":14.,"grade":.10,"original_candidate_height_m":28.,
         "plateau_polygon_xz_m":features["F_CATHEDRAL_CLOSE"]["footprint_xz_m"]},
    ])


@lru_cache(maxsize=1)
def default_field():
    return field_from_brief(json.loads(BRIEF.read_text()))


def height_at(x,z,field=None): return (field or default_field()).height(x,z)


def project_road(road,nodes,field=None):
    field=field or default_field()
    def xz(n):
        p=nodes[n]["position_m"] if isinstance(nodes[n],dict) else nodes[n]
        return [p[0],p[2]] if len(p)==3 else list(p)
    a,b=xz(road["from_node"]),xz(road["to_node"])
    deferred=road["kind"]=="wall_walk" or road["id"].startswith("WALL_ACCESS")
    return {"id":road["id"],"route_id":road.get("route_id"),"width_m":road["width_m"],
            "source_node_ids":[road["from_node"],road["to_node"]],"source_centerline_xz_m":[a,b],
            "grade_status":"deferred_wall_vertical_access" if deferred else "continuous_source_grade_authored",
            "projection":None if deferred else field.profile(a,b),
            "collision_pitch_m":None if deferred else WALK_PITCH,
            "crossfall_bound":None if deferred else field.max_grade,
            "crossfall_note":"follows terrain plane; no separately cambered/cart-certified carriageway"}


def _body_footprint(instance,spec):
    w,d=spec["width_m"],spec["depth_m"];yaw=instance["yaw_rad"];c,s=math.cos(yaw),math.sin(yaw)
    x,_,z=instance["position_m"]
    return [[x+c*a+s*b,z-s*a+c*b] for a,b in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]


def project_instance(instance,spec,field=None):
    """Entrance is the Y anchor; rigid body stays upright and its XZ does not move."""
    field=field or default_field();e=instance["entrance"];p=e["position_m"]
    local_y=e.get("local_position_m",[0,p[1]-instance["position_m"][1],0])[1]
    floor=field.height(p[0],p[2]);base=floor-local_y
    fp=_body_footprint(instance,spec)
    source_planes=_inside_planes(_convex(instance["source_footprint_xz_m"]))
    if min(_eval(p,*v) for p in source_planes for v in fp)<-.002:
        raise ValueError("realized foundation body extends beyond immutable source footprint")
    values=[_eval(f["plane"],*v) for f in field.facets(fp) for v in f["polygon_xz_m"]]
    connection=e["road_connection_m"];profile=field.profile([connection[0],connection[2]],[p[0],p[2]])
    # The endpoints must remain those of the source approach, even for very short spans.
    profile["points_m"][-1][1]=floor
    return {"id":instance["id"],"source_footprint_id":instance["source_footprint_id"],
            "position_m":[instance["position_m"][0],base,instance["position_m"][2]],
            "yaw_rad":instance["yaw_rad"],"source_footprint_xz_m":copy.deepcopy(instance["source_footprint_xz_m"]),
            "body_footprint_xz_m":fp,"entrance_position_m":[p[0],floor,p[2]],
            "road_connection_m":[connection[0],field.height(connection[0],connection[2]),connection[2]],
            "entrance_local_y_m":local_y,"approach":profile,
            "foundation":{"bottom_y_m":min(values)-FOUNDATION_EMBED,"top_y_m":base,
                          "terrain_min_y_m":min(values),"terrain_max_y_m":max(values),
                          "cut_top_y_m":base-RECESS_DEPTH,"required_cut_fill":True,
                          "macro_replacement_policy":"promote every intersecting chunk; recess the entire chunk below minimum foundation cut_top before adding fine cap and support",
                          "interface_support_required":True,
                          "policy":"cut only realized body footprint to cut_top; solid support to body base; preserve courtyard voids"},
            "entrance_contract":"source centerline reaches authored threshold continuously; width/obstacles/player collision still require integration",
            "passage_status":"needs_level_passage_patch_and_gate_clearance_check" if instance["functional_role"]=="gatehouse" else "exterior_approach_only"}


def _new_master(bounds,kind,material,metadata):
    from world_city.runtime_city.infrastructure.author import PALETTE
    if material not in PALETTE: raise ValueError("use an existing infrastructure material")
    planes=[]
    for axis,values in [(0,[bounds[0],bounds[2]]),(2,[bounds[1],bounds[3]])]:
        for value in values:
            planes.append({"id":f"boundary_{axis}_{float(value).hex()}","axis":axis,"value":value,"snap":"none"})
            if axis==2:
                planes.append({"id":f"boundary_neg_z_{float(value).hex()}","axis":2,"value":-value,"snap":"none"})
    return {"schema":"riverstone.voxel.master.v1","id":"pending","revision":1,
            "axes":{"up":"+Y","front":"+Z","right":"+X"},"grid_origin":[0,0,0],
            "materials":dict(PALETTE),"coordinate_planes":planes,"components":[],"instances":[],
            "metadata":{"authoring":"topography_next_revision_common_CSG_only","kind":kind,
                        "bounds_xz_m":list(bounds),"placement":"identity_world_coordinates_only",
                        "shared_boundary_policy":"same absolute planes, global grid origin, same pitch on both sides",
                        **metadata}}


def _plane_ref(master,name,axis,value):
    master["coordinate_planes"].append({"id":name,"axis":axis,"value":value,"snap":"none"})
    return {"plane":name}


def _prism(poly,low,high,master=None):
    # Canonicalize authored facet intersections to nanometres. Adjacent CSG
    # polygons then share identical endpoints instead of 1e-15 sliver cracks.
    # Source plan/road/footprint records are never rounded or rewritten.
    polygon=[]
    for x,z in poly:
        xx,zz=round(x,9),round(-z,9)
        if master is not None:
            bounds=master["metadata"]["bounds_xz_m"]
            for v in (bounds[0],bounds[2]):
                if abs(x-v)<1e-9:xx={"plane":f"boundary_0_{float(v).hex()}"}
            for v in (bounds[1],bounds[3]):
                if abs(z-v)<1e-9:zz={"plane":f"boundary_neg_z_{float(v).hex()}"}
        polygon.append([xx,zz])
    return {"kind":"extrusion","polygon":polygon,"z_min":low,"z_max":high}


UP_EXTRUSION={"basis":[[1,0,0],[0,0,1],[0,-1,0]]}


def _cut_wedge(master,cid,poly,plane,low,high,above):
    a,b,c=plane;g=math.hypot(a,b)
    if g<EPS:
        return {"kind":"box","min":[min(v[0] for v in poly)-1,c if above else low,min(v[1] for v in poly)-1],
                "max":[max(v[0] for v in poly)+1,high if above else c,max(v[1] for v in poly)+1]},None
    ux,uz=a/g,b/g;vs=[ux*x+uz*z for x,z in poly];ws=[-uz*x+ux*z for x,z in poly]
    s0,s1=min(vs)-1,max(vs)+1;w0,w1=min(ws)-1,max(ws)+1
    h0,h1=g*s0+c,g*s1+c
    edge0=_plane_ref(master,cid+"_h0",1,h0);edge1=_plane_ref(master,cid+"_h1",1,h1)
    if above:
        cap=max(high,h0,h1)+1;polygon=[[s0,edge0],[s1,edge1],[s1,cap],[s0,cap]]
    else:
        cap=min(low,h0,h1)-1;polygon=[[s0,cap],[s1,cap],[s1,edge1],[s0,edge0]]
    return {"kind":"extrusion","polygon":polygon,"z_min":w0,"z_max":w1}, {"basis":[[ux,0,-uz],[0,1,0],[uz,0,ux]]}


def _add_facet(master,facet,material,*,bottom=None,thickness=None,top_offset=0.):
    poly=facet["polygon_xz_m"];a,b,c=facet["plane"];top=[a,b,c+top_offset]
    heights=[_eval(top,*v) for v in poly];hi=max(heights)
    lo=bottom if thickness is None else min(heights)-thickness
    if lo>=hi-EPS: return
    cid=f"facet_{len(master['components']):03d}"
    # Flat domains use exact top/bottom directly, avoiding coincident CSG cuts.
    ops=[{"id":cid+"_solid","part":"solid","action":"paint","material":material,
          "shape":_prism(poly,lo,hi,master),"transform":UP_EXTRUSION}]
    if math.hypot(a,b)>EPS:
        shape,transform=_cut_wedge(master,cid+"_upper",poly,top,lo,hi,True)
        ops.append({"id":cid+"_top_cut","part":"solid","action":"cut","shape":shape,"transform":transform})
        if thickness is not None:
            shape,transform=_cut_wedge(master,cid+"_lower",poly,[a,b,c+top_offset-thickness],lo,hi,False)
            ops.append({"id":cid+"_bottom_cut","part":"solid","action":"cut","shape":shape,"transform":transform})
    master["components"].append({"id":cid,"parts":[{"id":"solid","pivot":[0,0,0]}],"operations":ops})
    master["instances"].append({"id":cid+"_0","component":cid})


def _finish(master):
    if not master["components"]: raise ValueError("requested source surface is empty")
    master["id"]="city_grade_"+_hash(master)[:20]
    return master


def make_terrain_master(bounds_xz,field=None,*,surface_recess=False,river_polygons=None,foundation_projections=None,recess_polygons=None):
    """A <=32 m master. surface_recess lowers its top 2 m for a fine cover.

    Supply source promotion polygons including their 2 m macro-voxel guard.
    Only those domains are recessed. A whole-tile recess remains an explicit
    bounded test option, never the proposed citywide fine-cover strategy.
    Fill recessed domains with buried support, medium collars and fine walk
    covers atomically. The unmodified r1 river is cut from land by default.
    """
    bounds=_bounds(bounds_xz);field=field or default_field();offset=-RECESS_DEPTH if surface_recess else 0.
    if recess_polygons is not None and not surface_recess:
        raise ValueError("recess polygons require surface_recess=True")
    master=_new_master(bounds,"recessed_terrain" if surface_recess else "macro_terrain","earth",
                       {"macro_pitch_m":MACRO_PITCH,"walk_collision_allowed":False,
                        "surface_recess_m":-offset,"replacement_cover_required":surface_recess})
    # Foundations may need deeper excavation than the ordinary 2 m cap recess.
    # A whole intersecting chunk is lowered, avoiding macro-cell side protrusions.
    # Fine cap ownership excludes the exact body footprint; no roads are widened.
    foundation_tops=[]
    for projection in foundation_projections or []:
        if _intersect(_convex(projection["body_footprint_xz_m"]),_inside_planes(_rect(bounds))):
            foundation_tops.append(projection["foundation"]["cut_top_y_m"])
    if foundation_tops and not surface_recess:
        raise ValueError("foundation excavation requires an atomic replacement surface tile")
    ceiling=min(foundation_tops) if foundation_tops else None
    master["metadata"]["foundation_excavation_ceiling_y_m"]=ceiling
    for f in field.facets(_rect(bounds)):
        remaining=[f["polygon_xz_m"]]
        if surface_recess and recess_polygons is not None:
            for reservation in recess_polygons:
                ps=_inside_planes(_convex(reservation));unowned=[]
                for poly in remaining:
                    q=_intersect(poly,ps)
                    if q:_add_facet(master,{**f,"polygon_xz_m":q},"earth",bottom=-4.,top_offset=offset)
                    unowned.extend(_subtract_convex(poly,ps))
                remaining=unowned
            for poly in remaining:_add_facet(master,{**f,"polygon_xz_m":poly},"earth",bottom=-4.)
        else:
            _add_facet(master,f,"earth",bottom=min(-4.,ceiling-2 if ceiling is not None else -4.),top_offset=offset)
    if ceiling is not None:
        master["assembly_cuts"]=[{"id":"foundation_chunk_excavation",
            "shape":{"kind":"box","min":[bounds[0],ceiling,bounds[1]],
                     "max":[bounds[2],max(r["height_m"] for r in field.regions)+4,bounds[3]]}}]
    if river_polygons is None:
        from world_city.runtime_city.infrastructure.author import _river_outline
        river=json.loads(BRIEF.read_text())["river_reservation"]
        river_polygons=[_river_outline(river["centerline_xz_m"],river["width_candidate_m"])]
    cuts=[]
    for i,poly in enumerate(river_polygons):
        # River outline can be non-convex; common extrusion preserves it unchanged.
        from world_city.runtime_city.infrastructure.author import _clip_polygon
        q=_clip_polygon(poly,*bounds)
        if q:
            cuts.append({"id":f"river_{i}","shape":_prism(q,-8.,max(r["height_m"] for r in field.regions)+2),"transform":UP_EXTRUSION})
    if cuts: master.setdefault("assembly_cuts",[]).extend(cuts)
    master["metadata"]["river_surface_y_m"]=-2.
    return _finish(master)


def make_surface_master(bounds_xz,polygons=None,field=None,*,material="stone",depth_m=SURFACE_DEPTH,exclude_polygons=None,_top_offset=0.,_max_span=MAX_SURFACE_SPAN):
    """Independent <=8 m source prism(s), H-depth..H, at walking pitch <=0.1 m.

    Road polygons retain their exact source reservation; separately owned 2 m
    shoulders use grass/earth at the same 0.1 m pitch. Do not fill residual fields
    with fine cells. A 0.2 m-pitch buried buffer bridges this thin 0.4 m cap to
    coarse 0.5 m support. Rendering grade is exact, with no draw-only Y offset.
    """
    bounds=_bounds(bounds_xz,_max_span);field=field or default_field();_finite(depth_m)
    if not SURFACE_DEPTH<=depth_m<=4: raise ValueError("surface depth must be .4 to 4 m for the declared overlap-safe layer bundle")
    master=_new_master(bounds,"walk_surface",material,
                       {"walk_collision_pitch_m":WALK_PITCH,"maximum_single_cell_rise_m":WALK_PITCH,
                        "vertical_depth_m":depth_m,"draw_offset_y_m":0.,
                        "layering":"0.4 m fine cap; buried 0.2 m-pitch buffer H-1.5..H-0.2; 0.5 m support below H-1.0; overlaps underground only",
                        "coplanar_surface_rule":"one visible material owner per XZ region; replace source ground cap, do not overlay a second coplanar mesh",
                        "hidden_face_removal":"not implemented; internal faces may remain in independent common exports"})
    clip_planes=_inside_planes(_rect(bounds))
    for p in (polygons if polygons is not None else [_rect(bounds)]):
        q=_intersect(_convex(p),clip_planes)
        owned=[q] if q else []
        for excluded in exclude_polygons or []:
            owned=[part for owner in owned for part in _subtract_convex(owner,_inside_planes(_convex(excluded)))]
        for owner in owned:
            for f in field.facets(owner): _add_facet(master,f,material,thickness=depth_m,top_offset=_top_offset)
    return _finish(master)


def make_walk_buffer_master(bounds_xz,polygons=None,field=None,*,exclude_polygons=None):
    """Buried 0.2 m transition shell under fine corridors; not field-wide fill."""
    master=make_surface_master(bounds_xz,polygons,field,material="earth",depth_m=BUFFER_DEPTH,
                               exclude_polygons=exclude_polygons,_top_offset=BUFFER_TOP_OFFSET)
    master["metadata"].update({"kind":"walk_buffer","requested_pitch_m":BUFFER_PITCH,
                               "walk_collision_allowed":False,"top_offset_m":BUFFER_TOP_OFFSET})
    master["metadata"].pop("walk_collision_pitch_m",None)
    master["metadata"].pop("maximum_single_cell_rise_m",None)
    master["id"]="city_grade_"+_hash(master)[:20]
    return master


def make_medium_shoulder_master(bounds_xz,polygons,field=None,*,exclude_polygons=None):
    """Non-walkable 0.5 m collar outside the fine 2 m road shoulder."""
    master=make_surface_master(bounds_xz,polygons,field,material="earth",depth_m=1.5,
                               exclude_polygons=exclude_polygons,_max_span=32.)
    master["metadata"].update({"kind":"medium_shoulder","requested_pitch_m":.5,
                               "walk_collision_allowed":False,"top_offset_m":0.})
    master["metadata"].pop("walk_collision_pitch_m",None)
    master["metadata"].pop("maximum_single_cell_rise_m",None)
    master["id"]="city_grade_"+_hash(master)[:20]
    return master


def make_interface_support_master(bounds_xz,bottom_y_m,field=None,*,exclude_polygons=None):
    """Buried <=32 m, 0.5 m-pitch support from deep foundation cut to fine cap.

    Use after a foundation lowers a whole macro chunk: it fills the surrounding
    subgrade so the fine surface shell never floats above the excavated terrain.
    Exclude realized foundation bodies, whose own flat support owns that volume.
    """
    bounds=_bounds(bounds_xz);field=field or default_field();_finite(bottom_y_m)
    master=_new_master(bounds,"buried_interface_support","earth",
                       {"requested_pitch_m":.5,"walk_collision_allowed":False,
                        "top_offset_m":BURIED_TOP_OFFSET,"purpose":"fill excavated subgrade below fine cap"})
    owners=[_rect(bounds)]
    for excluded in exclude_polygons or []:
        owners=[part for owner in owners for part in _subtract_convex(owner,_inside_planes(_convex(excluded)))]
    for owner in owners:
        for f in field.facets(owner):
            _add_facet(master,f,"earth",bottom=bottom_y_m,top_offset=BURIED_TOP_OFFSET)
    return _finish(master)


def make_foundation_master(projection,bounds_xz=None):
    """Solid body-footprint support. Mandatory terrain cut is returned separately."""
    p=projection["body_footprint_xz_m"];f=projection["foundation"]
    bounds=[min(v[0] for v in p),min(v[1] for v in p),max(v[0] for v in p),max(v[1] for v in p)]
    bounds=_bounds(bounds_xz if bounds_xz is not None else bounds)
    p=_intersect(_convex(p),_inside_planes(_rect(bounds)))
    if not p: raise ValueError("foundation does not intersect requested chunk")
    master=_new_master(bounds,"building_foundation","stone_dark",{"building_id":projection["id"],
                      "required_terrain_cut":{"polygon_xz_m":p,"top_y_m":f["cut_top_y_m"]},
                      "collision_verified":False})
    _add_facet(master,{"plane":[0,0,f["top_y_m"]],"polygon_xz_m":p},"stone_dark",bottom=f["bottom_y_m"])
    return _finish(master)


def compile_sample(master,pitch,*,max_candidate_cells=2_000_000,max_output_cells=600_000):
    """Only the unchanged common coordinate planes -> core -> render_data path."""
    from voxel_character.common import coordinate_planes,render_data
    kind=master["metadata"]["kind"]
    limits={"walk_surface":WALK_PITCH,"walk_buffer":BUFFER_PITCH,"medium_shoulder":.5,
            "buried_interface_support":.5,"building_foundation":.5}
    if kind in limits and pitch>limits[kind]+EPS:
        raise ValueError(f"{kind} sampling must be <= {limits[kind]} m; macro stairs cannot replace its declared layer")
    compiled=coordinate_planes.compile_master(master,{"pitch":pitch},max_candidate_cells=max_candidate_cells,
                                              max_output_cells=max_output_cells)
    if not compiled["valid"]: raise ValueError(compiled.get("validation"))
    # The common exporter correctly rejects empty geometry (e.g. all-water land tile).
    # No substitute mesh is generated; callers omit this empty land placement.
    return compiled,render_data.make_render_data(compiled) if compiled["cells"] else None


def promotion_budget(brief,building_projections,field=None):
    """Conservative polygon-area/cell estimates; never a city voxel compilation.

    Counts sum source reservations and therefore over-count overlapping junctions
    and footprints. They are safe coverage upper bounds, not measured union area.
    Only grade-affected roads/entries are newly promoted by this revision.
    """
    field=field or field_from_brief(brief)
    from world_city.runtime_city.infrastructure.author import _ribbon
    nodes={n["id"]:[n["position_m"][0],n["position_m"][2]] for n in brief["road_nodes"]}
    regions=[];junctions={}
    def envelope(p,q,width,pad):
        length=math.dist(p,q);u=[(q[i]-p[i])/length for i in (0,1)]
        start=[p[i]-u[i]*pad for i in (0,1)];end=[q[i]+u[i]*pad for i in (0,1)]
        return _ribbon(start,end,width+2*pad)
    def add(kind,key,p,q,width):
        if math.dist(p,q)<EPS:return False
        fine=envelope(p,q,width,FINE_SHOULDER)
        affected=any(_eval(f["plane"],*v)>EPS for f in field.facets(fine) for v in f["polygon_xz_m"])
        if not affected:return False
        medium=envelope(p,q,width,MEDIUM_SHOULDER)
        guard=envelope(p,q,width,MEDIUM_SHOULDER+MACRO_GUARD)
        regions.append({"id":key,"kind":kind,"source_walk_width_m":width,
                        "source_walk_polygon_xz_m":_ribbon(p,q,width),
                        "fine_cover_polygon_xz_m":fine,"medium_owner_outer_polygon_xz_m":medium,
                        "macro_recess_guard_polygon_xz_m":guard,
                        "medium_fill_outer_polygon_xz_m":guard,
                        "ownership":"subtract realized building bodies; fine shoulder subtracts road material; medium collar subtracts fine owners",
                        "road_reservation_expanded":False})
        return True
    for r in brief["roads"]:
        if r["kind"]=="wall_walk" or r["id"].startswith("WALL_ACCESS"):continue
        if add("road",r["id"],nodes[r["from_node"]],nodes[r["to_node"]],r["width_m"]):
            for nid in [r["from_node"],r["to_node"]]:junctions[nid]=max(junctions.get(nid,0),r["width_m"])
    for b in building_projections:
        p=b["road_connection_m"];q=b["entrance_position_m"]
        add("entrance_approach",b["id"],[p[0],p[2]],[q[0],q[2]],1.5)
    # These are ground owners beneath junctions, never enlarged road reservations.
    for nid,width in sorted(junctions.items()):
        x,z=nodes[nid];half=width/2
        def box(pad):return _rect([x-half-pad,z-half-pad,x+half+pad,z+half+pad])
        regions.append({"id":nid,"kind":"junction_ground","fine_cover_polygon_xz_m":box(FINE_SHOULDER),
                        "medium_owner_outer_polygon_xz_m":box(MEDIUM_SHOULDER),
                        "macro_recess_guard_polygon_xz_m":box(MEDIUM_SHOULDER+MACRO_GUARD),
                        "medium_fill_outer_polygon_xz_m":box(MEDIUM_SHOULDER+MACRO_GUARD),
                        "road_reservation_expanded":False})
    fine=sum(abs(_area(r["fine_cover_polygon_xz_m"])) for r in regions)
    medium=sum(abs(_area(r["medium_owner_outer_polygon_xz_m"])) for r in regions)
    guard=sum(abs(_area(r["macro_recess_guard_polygon_xz_m"])) for r in regions)
    # Volume/pitch^3 is an occupancy estimate, not a CSG candidate-cell guarantee.
    density=SURFACE_DEPTH/WALK_PITCH**3+BUFFER_DEPTH/BUFFER_PITCH**3
    return {"reservations":regions,"coverage_bound_kind":"sum of polygons, overlap and body exclusions not deducted",
            "affected_road_segments":sum(r["kind"]=="road" for r in regions),
            "affected_entrances":sum(r["kind"]=="entrance_approach" for r in regions),
            "junction_ground_owners":len(junctions),
            "fine_area_upper_bound_m2":fine,"medium_outer_area_upper_bound_m2":medium,
            "excavation_guard_area_upper_bound_m2":guard,
            "full_set_fine_occupancy_estimate_upper_bound":math.ceil(fine*SURFACE_DEPTH/WALK_PITCH**3),
            "full_set_buffer_occupancy_estimate_upper_bound":math.ceil(fine*BUFFER_DEPTH/BUFFER_PITCH**3),
            "all_at_once_allowed":False,"active_fine_area_cap_m2":1024.,
            "active_fine_plus_buffer_occupancy_estimate":math.ceil(1024*density),
            "per_compile_candidate_cell_limit":2_000_000,"per_compile_output_cell_limit":600_000,
            "candidate_budget_note":"volume estimates omit sampling-boundary rounding and CSG bounding-box work; unchanged compiler enforces candidate limit per bounded patch",
            "guard_fill_policy":"medium fill must cover medium_fill_outer_polygon (same as full excavation guard), minus fine/building owners; never leave the outer 2 m excavation ring empty",
            "compile_policy":"plan only; promote sparse nearby owned corridors on demand, never all hills or all reservations together",
            "edge_contract":"fine road and 2 m grass/earth shoulders share exact H and 0.1 m grid; <=0.1 m sampled rise at road edge; nonwalk medium seam is at least 2 m beyond source road edge",
            "flat_city_policy":"existing Y0 lower city and unwalked hills stay macro/medium; courts do not receive blanket fine fill"}


def build_grade_plan(brief=None,scene=None,history=None):
    brief=brief or json.loads(BRIEF.read_text());scene=scene or json.loads(SCENE.read_text());history=history or json.loads(HISTORY.read_text())
    field=field_from_brief(brief);nodes={n["id"]:n for n in brief["road_nodes"]}
    if {b["id"] for b in brief["building_plans"]}!={b["source_footprint_id"] for b in scene["instances"]}:
        raise ValueError("scene/source footprint identity mismatch")
    if not all(d["id"] in history["district_rules"] for d in brief["districts"]):
        raise ValueError("canonical history district binding missing")
    roads=[project_road(r,nodes,field) for r in brief["roads"]]
    buildings=[project_instance(i,scene["asset_specs"][i["asset_key"]],field) for i in scene["instances"]]
    active=[r for r in roads if r["projection"] is not None]
    max_road=max(r["projection"]["max_grade"] for r in active);max_entrance=max(b["approach"]["max_grade"] for b in buildings)
    if max(max_road,max_entrance)>GRADE_LIMIT+EPS: raise ValueError("source route/entrance grade budget exceeded")
    ingress={}
    for route in ("RT_CASTLE_CLIMB","RT_CASTLE_COURT","RT_CATHEDRAL_APPROACH","RT_CATHEDRAL_CLOSE"):
        rr=[r for r in active if r["route_id"]==route]
        ingress[route]={"segments":len(rr),"max_grade":max(r["projection"]["max_grade"] for r in rr),
                        "start_m":rr[0]["projection"]["points_m"][0],"end_m":rr[-1]["projection"]["points_m"][-1],
                        "centerline_continuous":all(math.dist(a["projection"]["points_m"][-1],b["projection"]["points_m"][0])<EPS for a,b in zip(rr,rr[1:])),
                        "source_xz_unchanged":True,"scope":"grade proof only; no collision/navigation pass"}
    return {"schema":"riverstone.city.grade.plan.v1","revision":"next_grade_r1","status":"source_authored_not_integrated",
            "source_hashes":{"brief":_hash(brief),"scene":_hash(scene),"history":_hash(history)},
            "regions":field.regions,"lower_city_y_m":0.,"river_surface_y_m":-2.,
            "height_contract":"H=max(0,min(region affine planes)); world XZ in metres; global grid origin [0,0,0]",
            "grade_proof":{"global_lipschitz_bound":field.max_grade,"limit":GRADE_LIMIT,
                           "reason":"all affine gradients have norm <=0.12; finite min/max preserve the bound",
                           "max_source_road_grade":max_road,"max_source_entrance_grade":max_entrance},
            "roads":roads,"buildings":buildings,"ingress":ingress,
            "promotion_budget":promotion_budget(brief,buildings,field),
            "preserved_reservations":{"building_footprints":len(buildings),"roads":len(roads),
                                      "courtyards":len([p for p in brief["plots"] if p.get("courtyard_xz_m")]),
                                      "policy":"XZ footprints, road ribbons, plot courts, river and feature outlines are read-only"},
            "sampling":{"macro_pitch_m":MACRO_PITCH,"interface_pitch_m":.5,"walk_pitch_m":WALK_PITCH,
                        "macro_chunk_span_m":32.,"surface_patch_span_m":MAX_SURFACE_SPAN,
                        "maximum_sampled_walk_step_m":WALK_PITCH,"macro_walk_collision_allowed":False,
                        "recess_depth_m":RECESS_DEPTH,"structural_cover_depth_m":SURFACE_DEPTH,
                        "buffer_pitch_m":BUFFER_PITCH,"buffer_depth_m":BUFFER_DEPTH,
                        "active_cover_policy":"only roads/entrances plus 2 m owned shoulders are fine; medium collar and 2 m excavation guard outside; atomically switch the layer bundle",
                        "fine_coverage_cap_m2":1024.,"max_active_full_8m_patches":16,
                        "surface_edge_policy":"road and owned 2 m shoulders share H and 0.1 m grid; no cliff at the road edge; medium/macro seam stays outside the walk domain",
                        "mixed_pitch_seam_policy":"promote both sides of a walkable seam to same pitch and grid; analytic continuity alone is not a mixed-LOD physics pass",
                        "whole_city_fine_fill":False},
            "departures":[{"district_id":"D01","candidate_y_m":52,"authored_y_m":24,"reason":"200 m normal run at 12% grade fits unchanged precinct approach"},
                          {"district_id":"D02","candidate_y_m":28,"authored_y_m":14,"reason":"140 m normal run at 10% grade; retain cathedral court and lower city"}],
            "limitations":["Not applied to r1, collision fixtures, infrastructure placements, or existing renders.",
                           "Building support masters and macro excavation are bounded source geometry; require atomic cap replacement and bounded foundation tile selection before city compilation.",
                           "Gate through-passages need level throat patches and clearance verification; wall walks remain deferred.",
                           "Exact entrance centerline grades are proven; approach widths, obstacle clearance and player traversal remain unverified.",
                           "Road crossfall follows terrain and may reach 12%; this is a game walk-slope bound, not a cart, wheelchair or civil drainage certification.",
                           "No independent-mesh hidden-face removal, whole-city compilation, mixed-LOD seam pass, or visual pass is claimed."]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=HERE/"generated/grade_plan.json")
    args=parser.parse_args()
    # This revision is deliberately incapable of overwriting the current scene.
    if not args.output.resolve().is_relative_to(HERE.resolve()):
        raise ValueError("next-grade authoring output must remain inside topography/")
    plan=build_grade_plan();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(plan,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
    summary={"status":plan["status"],"regions":[{"id":r["id"],"height_m":r["height_m"],"grade":r["grade"]} for r in plan["regions"]],
             "grade_proof":plan["grade_proof"],"ingress":plan["ingress"],"counts":plan["preserved_reservations"],"promotion_budget":{k:v for k,v in plan["promotion_budget"].items() if k!="reservations"},"output":str(args.output.relative_to(ROOT))}
    (args.output.parent/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
