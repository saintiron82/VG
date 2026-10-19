"""Assemble two landward gates using unchanged registered native assets.

Writes only this directory. Static occupancy proofs are reproduced with the
existing common compiler at each frozen render's own pitch. No new geometry,
cache, scene, controller, or source asset is authored by this program.
"""
from __future__ import annotations
import hashlib
import json
import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT))
from voxel_character.common.core import compile_master

BASE_SHA = '2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
BASE = ROOT / 'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json'
CONTEXT = HERE.parent / 'base_context.json'
BOUNDS = HERE.parent / 'asset_bounds.json'
HEADER = 'registered_main_gate_header'
TOWER = 'registered_fort_tower_10x34'
FOOTING = 'registered_tower_footing_south_tower_544'
EPS = 1e-8
S = json.loads(CONTEXT.read_text())
B = json.loads(BOUNDS.read_text())
I = {i['id']: i for i in S['common_instances']}
COMPILE_PROOFS = {}


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def ref(path):
    return {'path': relative(path), 'sha256': sha(path)}


def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def world(v, instance):
    c, s = math.cos(instance['yaw_rad']), math.sin(instance['yaw_rad'])
    p = instance['position_m']
    return [p[0] + c*v[0] + s*v[2], p[1] + v[1], p[2] - s*v[0] + c*v[2]]


def local(v, frame):
    c, s = math.cos(frame['yaw_rad']), math.sin(frame['yaw_rad'])
    p = frame['position_m']
    x, y, z = [v[j] - p[j] for j in range(3)]
    return [c*x - s*z, y, s*x + c*z]


def rect(x0, z0, x1, z1):
    return [[x0,z0], [x1,z0], [x1,z1], [x0,z1]]


def transform_poly(poly, instance, frame):
    result = [local(world([x,0,z], instance), frame) for x,z in poly]
    return [[p[0], p[2]] for p in result]


def area(poly):
    return abs(sum(p[0]*q[1] - p[1]*q[0] for p,q in zip(poly, poly[1:]+poly[:1])))/2 if poly else 0.0


def cross(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0])


def clip(subject, boundary):
    """Exact convex polygon intersection, with only a floating-point tolerance."""
    out = subject
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):
        source, out = out, []
        if not source:
            break
        for p,q in zip(source,source[1:]+source[:1]):
            dp,dq = cross(a,b,p), cross(a,b,q)
            ip,iq = dp >= -EPS, dq >= -EPS
            if ip:
                out.append(p)
            if ip != iq and abs(dp-dq) > 1e-14:
                t=dp/(dp-dq)
                out.append([p[k]+t*(q[k]-p[k]) for k in range(2)])
    return out


def overlap(a,b):
    return area(clip(a,b))


@lru_cache(None)
def compiled(key):
    asset = S['common_assets'][key]
    mp, rp = ROOT/asset['master_path'], ROOT/asset['render_path']
    assert sha(mp)==asset['master_sha256'], ('master identity',key)
    assert sha(rp)==asset['render_sha256'], ('render identity',key)
    master, render = json.loads(mp.read_text()), json.loads(rp.read_text())
    value = compile_master(master, {'pitch': render['pitch']})
    assert value['valid'] and value['payload_hash']==render['payload_hash'], ('occupancy identity',key)
    assert value['materials']==render['materials'], ('native materials',key)
    COMPILE_PROOFS[key] = {
        'master': ref(mp), 'render': ref(rp),
        'source_payload_sha256': render['payload_hash'],
        'reproduced_payload_sha256': value['payload_hash'],
        'pitch_m': value['pitch'], 'occupied_cells': len(value['cells']),
        'native_bounds_m': B[key], 'constraints': value['constraints'],
        'new_geometry_authored': False, 'source_and_render_unchanged': True,
    }
    return value


def bound_poly(instance, frame):
    b=B[instance['asset_key']]
    return transform_poly(rect(b['min'][0],b['min'][2],b['max'][0],b['max'][2]),instance,frame)


def prism_hits(instances, frame, lo=(-4,0,-3), hi=(4,4.5,3)):
    """Exhaustive positive-volume occupied-cell/prism test after rigid transforms."""
    query=rect(lo[0],lo[2],hi[0],hi[2]); hits=[]; candidates=[]
    for instance in instances:
        key=instance['asset_key']; b=B[key]; dy=instance['position_m'][1]-frame['position_m'][1]
        if min(hi[1],dy+b['max'][1])-max(lo[1],dy+b['min'][1]) <= EPS:
            continue
        if overlap(bound_poly(instance,frame),query) <= EPS:
            continue
        candidates.append(instance['id']); c=compiled(key); pitch=c['pitch']; origin=c['grid_origin']; count=0; volume=0.0
        for row in c['cells']:
            mn=[origin[k]+pitch*row[k] for k in range(3)]
            height=min(hi[1],dy+mn[1]+pitch)-max(lo[1],dy+mn[1])
            if height <= EPS:
                continue
            poly=transform_poly(rect(mn[0],mn[2],mn[0]+pitch,mn[2]+pitch),instance,frame)
            a=overlap(poly,query)
            if a > EPS:
                count+=1; volume+=a*height
        if count:
            hits.append({'id':instance['id'],'asset_key':key,'intersecting_occupied_cells':count,'intersection_volume_m3':round(volume,9)})
    # Analytic boxes are actual scene colliders, not native mesh instances.
    box_hits=[]
    for box in S['boxes']:
        p=box['position_m']; sz=box['size_m']; dy=p[1]-frame['position_m'][1]
        height=min(hi[1],dy+sz[1]/2)-max(lo[1],dy-sz[1]/2)
        if height <= EPS:
            continue
        poly=transform_poly(rect(-sz[0]/2,-sz[2]/2,sz[0]/2,sz[2]/2),box,frame)
        a=overlap(poly,query)
        if a > EPS:
            box_hits.append({'id':box['id'],'intersection_volume_m3':a*height})
    return {'bounds_gate_local_m':{'min':list(lo),'max':list(hi)},'bounds_candidates':candidates,'occupied_native_intersections':hits,'analytic_box_intersections':box_hits,'clear':not hits and not box_hits}


@lru_cache(None)
def layer_rects(key, local_y):
    """Merge occupied-cell cross sections without approximation."""
    c=compiled(key); p=c['pitch']; o=c['grid_origin']; iy=math.floor((local_y-o[1])/p); rows=defaultdict(list)
    for row in c['cells']:
        if row[1]==iy:
            rows[row[2]].append(row[0])
    spans=defaultdict(list)
    for z,xs in rows.items():
        xs=sorted(xs); start=end=xs[0]
        for x in xs[1:]:
            if x==end+1:
                end=x
            else:
                spans[(start,end+1)].append(z); start=end=x
        spans[(start,end+1)].append(z)
    rectangles=[]
    for (x0,x1),zs in spans.items():
        zs=sorted(zs); start=end=zs[0]
        for z in zs[1:]+[None]:
            if z is not None and z==end+1:
                end=z
            else:
                rectangles.append(rect(o[0]+x0*p,o[2]+start*p,o[0]+x1*p,o[2]+(end+1)*p))
                start=end=z
    return rectangles


def join_proof(tower, adjacent, frame):
    """Test every exact constant-occupancy Y slab over the full 4.5 m throat height."""
    levels={0.0,4.5}
    for instance in [tower]+adjacent:
        c=compiled(instance['asset_key']); dy=instance['position_m'][1]-frame['position_m'][1]
        for row in c['cells']:
            for offset in (0,1):
                y=dy+c['grid_origin'][1]+(row[1]+offset)*c['pitch']
                if EPS<y<4.5-EPS:
                    levels.add(y)
    levels=sorted(levels); slabs=[]
    for lo,hi in zip(levels,levels[1:]):
        mid=(lo+hi)/2
        tr=[transform_poly(p,tower,frame) for p in layer_rects(tower['asset_key'],mid+frame['position_m'][1]-tower['position_m'][1])]
        sources=[]
        for instance in adjacent:
            ar=[transform_poly(p,instance,frame) for p in layer_rects(instance['asset_key'],mid+frame['position_m'][1]-instance['position_m'][1])]
            a=sum(overlap(p,q) for p in tr for q in ar)
            if a>EPS:
                sources.append({'id':instance['id'],'occupied_overlap_area_m2':round(a,9)})
        slabs.append({'height_above_gate_floor_m':[lo,hi],'adjacent_solid_overlaps':sources,'closed':bool(sources)})
    assert all(r['closed'] for r in slabs), ('wall join open',tower['id'],slabs)
    return {'tower_id':tower['id'],'adjacent_ids':[i['id'] for i in adjacent], 'method':'Exhaustive compiled occupied-cell cross sections for every constant-occupancy Y slab; exact convex polygon intersections after rigid transforms, not bounding-box-only overlap.', 'tested_height_above_gate_floor_m':[0,4.5], 'all_slabs_have_positive_solid_overlap':True,'slabs':slabs}


def make_instance(id, key, frame, dx=0):
    return {'id':id,'asset_key':key,'position_m':world([dx,0,0],frame),'yaw_rad':frame['yaw_rad'],'palette_id':'native_fortifications','palette_override':{},'scale':[1,1,1],'source_pack':'landward_gates_native_r9'}


def main():
    assert sha(BASE)==BASE_SHA, 'Frozen base identity changed'
    additions=[]; removals=[]; frames={}; gates={}
    for side,wall_id,floor,neighbors in [
        ('EAST','FORT_CURTAIN_12_0_05',4.0,['FORT_CURTAIN_12_0_04','FORT_CURTAIN_12_0_06']),
        ('WEST','FORT_CURTAIN_26_0_00',21.0,['FORT_CURTAIN_25_0_05','FORT_CURTAIN_26_0_01']),
    ]:
        old=I[wall_id]; frame={'position_m':[old['position_m'][0],floor,old['position_m'][2]],'yaw_rad':old['yaw_rad']}
        removed=[v for k,v in I.items() if k==wall_id or k.startswith(wall_id+':FOOTING:')]
        assert len(removed)==(3 if side=='EAST' else 4)
        removals.extend(i['id'] for i in removed)
        prefix='R9_LANDWARD_GATE:'+side
        header=make_instance(prefix+':HEADER',HEADER,frame)
        towers=[make_instance(prefix+':TOWER:'+name,TOWER,frame,dx) for name,dx in [('LEFT',-9.5),('RIGHT',9.5)]]
        feet=[make_instance(t['id']+':FOOTING',FOOTING,frame,dx) for t,dx in zip(towers,[-9.5,9.5])]
        new=[header]+towers+feet; additions.extend(new)
        kept=[i for i in S['common_instances'] if i['id'] not in {r['id'] for r in removed}]
        before=prism_hits(S['common_instances'],frame)
        after=prism_hits(kept+new,frame)
        extended=prism_hits(kept+new,frame,(-4,0,-6),(4,4.5,6))
        assert not before['clear'] and after['clear'] and extended['clear'], (side,before,after,extended)
        assert all(r['id'] in {i['id'] for i in removed} for r in before['occupied_native_intersections'])
        joins=[]
        for tower,neighbor in zip(towers,neighbors):
            adjacent=[i for k,i in I.items() if k==neighbor or k.startswith(neighbor+':FOOTING:')]
            joins.append(join_proof(tower,adjacent,frame))
        yaw=frame['yaw_rad']; c,s=math.cos(yaw),math.sin(yaw)
        frames[side.lower()]={
            'center_m':frame['position_m'],'position_m':frame['position_m'],'yaw_rad':yaw,
            'tangent_m':[c,0,-s],'inward_normal_m':[s,0,c],'outward_normal_m':[-s,0,-c],
            'local_axis_contract':{'x':'along wall toward RIGHT tower','y':'up from gate floor','z':'inward toward city'},
            'clear_native_aperture_local_m':{'min':[-4,0,-3],'max':[4,4.5,3]},
            'throat_faces_m':{'outside':world([0,0,-3],frame),'inside':world([0,0,3],frame)},
            'route_seed_m':{'outside':world([0,0,-6],frame),'inside':world([0,0,6],frame)},
            'removed_wall_id':wall_id,'header_id':header['id'],'tower_ids':[t['id'] for t in towers],
            'floor_elevation_m':floor,'route_support_status':'Terrain and road support are separate parent-owned source patches; these are geometry frame seeds, not traversal-certified waypoints.'}
        gates[side.lower()]={
            'source_wall_pose':old,'removed_instances':removed,'new_instance_ids':[v['id'] for v in new],
            'floor_m':floor,'native_aperture_minimum_width_m':8.0,'native_aperture_guaranteed_height_m':4.5,
            'native_aperture_depth_m':6.0,'static_native_collision_before':before,
            'static_native_collision_after':after,'static_native_clear_12m_crossing':extended,
            'actual_wall_geometry_removed':True,'remaining_copy_of_removed_wall_or_footing':False,
            'adjacent_wall_joins':joins,
            'header_tower_joins':{'left_shared_plane_local_x_m':-4.5,'right_shared_plane_local_x_m':4.5,'shared_face_area_each_m2_over_4_5m_height':27.0,'gap_m':0.0,'join_type':'Exact face contact of native header jamb with native tower inner shell.'},
            'tower_footing_contract':{'asset_key':FOOTING,'width_depth_m':[10,10],'local_y_bounds_m':[-1.5,0],'tower_local_bottom_m':-1,'tower_footing_overlap_m':1.0,'datum':'Same gate-floor root for tower and footing, as in original native placement.','terrain_bearing_verified':False},
            'new_closure_geometry_required':False,
        }
    for key in (HEADER,TOWER,FOOTING):
        compiled(key)
    header=compiled(HEADER); hp=header['pitch']; ho=header['grid_origin']
    bad=[r for r in header['cells'] if -4<ho[0]+(r[0]+.5)*hp<4 and 0<ho[1]+(r[1]+.5)*hp<4.5 and -3<ho[2]+(r[2]+.5)*hp<3]
    assert not bad
    fullwidth_ceiling=min(ho[1]+r[1]*hp for r in header['cells'] if -4<ho[0]+(r[0]+.5)*hp<4 and ho[1]+r[1]*hp>=0 and -3<ho[2]+(r[2]+.5)*hp<3)
    ids=set(I)
    assert len(set(removals))==7 and len(additions)==10
    assert len({v['id'] for v in additions})==10 and not(ids & {v['id'] for v in additions})
    assert all(v['scale']==[1,1,1] and v['palette_override']=={} for v in additions)
    pack={'schema':'riverstone.city.visual_addendum.v1','base_scene_sha256':BASE_SHA,'common_assets':{},'add_instances':additions,'remove_instance_ids':removals,'inspection_cameras':{},'provenance':{'purpose':'Two real landward wall entrances, with native headers and twin towers.','geometry_policy':'Reuse frozen registered native assets at rigid scale 1. No new meshes, materials, or closure geometry.','audit_path':relative(HERE/'audit.json'),'route_frame_path':relative(HERE/'route_frame.json')}}
    write('pack.json',pack)
    write('route_frame.json',{'schema':'riverstone.city.landward_gate_frames.v1','base_scene_sha256':BASE_SHA,'pack':ref(HERE/'pack.json'),'gates':frames})
    write('audit.json',{
        'schema':'riverstone.city.landward_gate_native_audit.v1','status':'PASS_STATIC_NATIVE_GEOMETRY_AND_SOURCE_IDENTITY',
        'base_scene_sha256':BASE_SHA,'inputs':{'base_context':ref(CONTEXT),'asset_bounds':ref(BOUNDS),'author':ref(Path(__file__))},
        'pack':ref(HERE/'pack.json'),'route_frame':ref(HERE/'route_frame.json'),
        'new_instances':10,'removed_instances':7,'new_assets':0,'new_closure_compiles':0,'source_assets_edited':0,'base_scene_edited':False,
        'scale_policy':'All added instances are rigid native scale [1,1,1].','native_material_overrides':0,
        'native_aperture':{'guaranteed_continuous_source_rectangle_m':[8,4.5],'source_arch_crown_height_m':8.5,'frozen_0_5m_voxel_full_width_clear_height_m':fullwidth_ceiling,'distinction':'4.5 m is the unchanged source arch springline guarantee; the frozen stepped native mesh has a taller 6 m full-width rectangular opening. No enlargement is authored.'},
        'native_asset_identity_and_reproduction':COMPILE_PROOFS,'gates':gates,
        'collision_composition_contract':{'remove_ids_before_add_instances':True,'rebuild_colliders_from_composed_native_instances':True,'do_not_retain_frozen_removed_wall_collision_shapes':True,'removed_source_colliders_are_part_of_scene_native_instances':True,'proof':'The same positive-volume prism intersects original wall/footing occupancy before removal and has zero intersections against every retained native instance plus added native instances and every analytic box afterward. The aperture is a physical hole in the composed source geometry, not a facade over a retained wall.'},
        'limits':['Static native occupancy and analytic-box geometry proof only; terrain triangle replacement and support proof belong to the parent-owned route/surface work.','No GUI or Godot runtime executed. Capsule/cart crossing requires the separately bound final source patch and runtime harness.','No claim about unchanged whole-city traversal results is made.']})
    print(json.dumps({'status':'PASS_STATIC_NATIVE_GEOMETRY_AND_SOURCE_IDENTITY','pack':relative(HERE/'pack.json'),'additions':10,'removals':7,'gates':{side:{'aperture_clear':g['static_native_collision_after']['clear'],'crossing_12m_clear':g['static_native_clear_12m_crossing']['clear'],'joined_sides':len(g['adjacent_wall_joins'])} for side,g in gates.items()}},indent=2))


if __name__=='__main__':
    main()
