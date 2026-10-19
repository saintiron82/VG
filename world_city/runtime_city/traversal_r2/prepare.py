#!/usr/bin/env python3
"""Prepare bounded actual-mesh r2 capsule diagnostics without changing city sources.

Routes are fixed before physics. Analytic H is spawn metadata only: the engine ray
finds the real compiled surface; no height-following or synthetic floor is used.
"""
from __future__ import annotations
import argparse, copy, hashlib, itertools, json, math
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
GROUND={'terrain','bridge','dock','dock_connector','terrain_macro','terrain_medium',
        'fine_walk_surface','fine_buried_buffer','fine_buried_support','building_foundation'}
OBSTACLES={'wall','fountain','bridge_pier','dock_support','building_retaining_interface',
           'outer_woodland_tree','orchard_tree','property_boundary','garden_bed','grave_marker','market_stall'}
FINE_BOUNDS=[-576.,-256.,-544.,-224.]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def height(regions,x,z):return max([0.]+[min(a*x+b*z+c for a,b,c in r['planes']) for r in regions])
def subtract_box(box,hole):
    lo=[max(box['min'][a],hole['min'][a]) for a in range(3)]
    hi=[min(box['max'][a],hole['max'][a]) for a in range(3)]
    if any(lo[a]>=hi[a] for a in range(3)):return [box]
    remainder=copy.deepcopy(box);pieces=[]
    for a in range(3):
        if remainder['min'][a]<lo[a]:
            p=copy.deepcopy(remainder);p['max'][a]=lo[a];pieces.append(p);remainder['min'][a]=lo[a]
        if remainder['max'][a]>hi[a]:
            p=copy.deepcopy(remainder);p['min'][a]=hi[a];pieces.append(p);remainder['max'][a]=hi[a]
    return pieces

def openings(instance):
    values=list(instance.get('gate_openings',[]))+list(instance.get('road_openings',[]))
    values += [instance[k] for k in ('gate_opening','road_opening') if k in instance]
    result=[]
    for v in values:
        b=v.get('local_bounds',v)
        if 'min' not in b or 'max' not in b:raise ValueError('Unknown opening '+instance['id'])
        if b not in result:result.append(b)
    return result

def transformed_bounds(bounds,placement):
    transform=placement.get('transform',{})
    if 'basis' in transform:basis=transform['basis']
    else:
        t=float(placement.get('yaw_rad',math.radians(placement.get('yaw_deg',0))))
        c,s=math.cos(t),math.sin(t);basis=[[c,0,s],[0,1,0],[-s,0,c]]
    pos=placement['position_m']
    points=[[sum(basis[i][j]*p[j] for j in range(3))+pos[i] for i in range(3)]
            for p in itertools.product(*zip(bounds['min'],bounds['max']))]
    return [min(p[0] for p in points),min(p[2] for p in points),max(p[0] for p in points),max(p[2] for p in points)]

def corridor_intersects(bounds,points,margin=4.):
    # Conservative union of segment AABBs; never culls a collider touching path.
    for p,q in zip(points,points[1:]):
        if bounds[0]<=max(p[0],q[0])+margin and bounds[2]>=min(p[0],q[0])-margin and bounds[1]<=max(p[2],q[2])+margin and bounds[3]>=min(p[2],q[2])-margin:return True
    return False

def route_record(id,xz,kind,regions,**extra):
    clean=[]
    for x,z in xz:
        p=[float(x),height(regions,x,z),float(z)]
        if not clean or math.dist(p,clean[-1])>1e-7:clean.append(p)
    if len(clean)<2:raise ValueError('Too few route points '+id)
    return {'id':id,'kind':kind,'points':clean,'length_m':sum(math.dist(a,b) for a,b in zip(clean,clean[1:])),
            'source_road_ids':[],'test_scope':'diagnostic_not_production_certification',**extra}

def approach_endpoint(instance,projection,stand_off=.8):
    """Stop .8m outside conservative shell, not inside a recessed doorway."""
    start=projection['road_connection_m'];door=projection['entrance_position_m']
    c,s=math.cos(instance['yaw_rad']),math.sin(instance['yaw_rad']);pos=projection['position_m']
    local=[]
    for p in (start,door):
        dx,dz=p[0]-pos[0],p[2]-pos[2];local.append([c*dx-s*dz,s*dx+c*dz])
    bounds=instance['local_bounds'];lo=[bounds['min'][0],bounds['min'][2]];hi=[bounds['max'][0],bounds['max'][2]]
    entry,leave=0.,1.
    for axis in (0,1):
        d=local[1][axis]-local[0][axis]
        if abs(d)<1e-10:
            if not lo[axis]<=local[0][axis]<=hi[axis]:return [door[0],door[2]]
        else:
            t1=(lo[axis]-local[0][axis])/d;t2=(hi[axis]-local[0][axis])/d
            entry=max(entry,min(t1,t2));leave=min(leave,max(t1,t2))
    length=math.dist([start[0],start[2]],[door[0],door[2]])
    t=max(0.,min(1.,entry)-stand_off/length)
    return [start[0]+(door[0]-start[0])*t,start[2]+(door[2]-start[2])*t]

def fixture_routes(scene,layer,plan):
    regions=plan['regions'];streets={r['id']:r for r in scene['infrastructure']['street_routes']};routes=[]
    def add(id,xz,kind,**extra):routes.append(route_record(id,xz,kind,regions,**extra))
    fine=[[-553.92,-235.88],[-546.36,-251.64]]
    add('FINE_SOURCE_CASTLE_UP',fine,'fine_interior',source_road_ids=['RT_CASTLE_CLIMB.023'],test_scope='fine_0p1m_sample')
    add('FINE_SOURCE_CASTLE_DOWN',fine[::-1],'fine_interior',source_road_ids=['RT_CASTLE_CLIMB.023'],test_scope='fine_0p1m_sample')
    add('FINE_INTERNAL_X_SEAMS',[[-574,-240],[-546,-240]],'fine_interior',test_scope='fine_0p1m_sample')
    add('FINE_INTERNAL_X_SEAMS_REVERSE',[[-546,-240],[-574,-240]],'fine_interior',test_scope='fine_0p1m_sample')
    add('FINE_INTERNAL_Z_SEAMS',[[-552,-254],[-552,-226]],'fine_interior',test_scope='fine_0p1m_sample')
    add('FINE_INTERNAL_Z_SEAMS_REVERSE',[[-552,-226],[-552,-254]],'fine_interior',test_scope='fine_0p1m_sample')
    add('FINE_ROAD_TO_GRASS_SHOULDER',[[-550.14,-243.76],[-557.35,-247.22]],'fine_interior',test_scope='fine_0p1m_sample')
    add('OUTER_MEDIUM_TO_FINE_SEAM',[[-552,-220],[-552,-230]],'mixed_lod_seam')
    add('OUTER_FINE_TO_MEDIUM_SEAM',[[-552,-230],[-552,-220]],'mixed_lod_seam')
    castle=streets['RT_CASTLE_CLIMB'];cathedral=streets['RT_CATHEDRAL_APPROACH']
    add('CASTLE_ZERO_TO_GRADE',castle['polyline_xz_m'][3:8],'medium_grade_transition',source_road_ids=castle.get('road_ids',[])[3:7])
    add('CATHEDRAL_ZERO_TO_GRADE',cathedral['polyline_xz_m'][5:10],'medium_grade_transition',source_road_ids=cathedral.get('road_ids',[])[5:9])
    for id in ('D01-B001','D02-B001'):
        p=next(p for p in layer['building_footing_contracts'] if p['id']==id)
        b=next(b for b in scene['instances'] if b['id']==id)
        start=p['road_connection_m'];end=approach_endpoint(b,p)
        add(id+'_ENTRY_APPROACH',[[start[0],start[2]],end],'medium_entry_approach',building_id=id,
            endpoint_policy='0.8m outside conservative building envelope; actual recessed door/threshold and interior excluded',
            declared_entrance_position_m=p['entrance_position_m'])
    for id in ('A01','A04','L13','RT_BRIDGE'):
        r=streets[id];add('BASELINE_'+id,r['polyline_xz_m'],'unchanged_flat_baseline',source_road_ids=r.get('road_ids',[]))
    add('NEGATIVE_RIVER_HAS_NO_INFINITE_FLOOR',[[-700,490],[-698,490]],'negative_control',expected_failure='spawn_not_grounded')
    add('NEGATIVE_CASTLE_WALL_IS_SOLID',[[-440,-325],[-440,-345]],'negative_control',expected_failure='blocked',expected_contact_id='D01-B001')
    return routes

def prepare(scene_path,layer_path,out_path,fine_only=False):
    scene,layer=read(scene_path),read(layer_path)
    if layer['status']!='compiled_structural_only' and not fine_only:raise ValueError('Layer compilation incomplete')
    plan_path=ROOT/layer['source_plan_path']
    if digest(plan_path)!=layer['source_plan_sha256']:raise ValueError('Layer source plan hash mismatch')
    plan=read(plan_path);routes=fixture_routes(scene,layer,plan)
    if fine_only:routes=[r for r in routes if r['kind']=='fine_interior']
    infra=scene['infrastructure'];assets=dict(infra['assets']);placements=list(infra['placements'])
    replaced=set(layer['replace_r1_placement_ids'])|set(layer['replace_urban_fabric_placement_ids'])
    placements=[p for p in placements if p['id'] not in replaced]
    existing={p['id'] for p in placements}
    for p in layer['placements']:
        if p['id'] in existing:continue
        placements.append(p)
    for k,a in layer['assets'].items():
        if k in assets and assets[k]['render_sha256']!=a['render_sha256']:raise ValueError('Asset collision '+k)
        assets[k]=a
    footing={p['id']:p for p in layer['building_footing_contracts']}
    buildings=[];overridden=[]
    for instance in scene['instances']:
        p=copy.deepcopy(instance)
        if p['id'] in footing and p['position_m']!=footing[p['id']]['position_m']:
            overridden.append({'id':p['id'],'from':p['position_m'],'to':footing[p['id']]['position_m']})
            p['position_m']=footing[p['id']]['position_m']
        holes=openings(p);boxes=[p['local_bounds']]
        for h in holes:boxes=[piece for box in boxes for piece in subtract_box(box,h)]
        buildings.append({'id':p['id'],'position_m':p['position_m'],'yaw_rad':p['yaw_rad'],'boxes':boxes,
                          'opening_count':len(holes),'world_bounds_xz_m':transformed_bounds(p['local_bounds'],p)})
    selected=[]
    for p in placements:
        cat=p['category']
        if cat not in GROUND|OBSTACLES:continue
        p=copy.deepcopy(p);p['world_bounds_xz_m']=transformed_bounds(assets[p['asset_key']]['bounds'],p)
        p['collision_layer']=1 if cat in GROUND else 2
        p['physics_test_override_disabled_lod']=p.get('collision_enabled') is False
        p['ignored_visual_offset_y_m']=p.get('render_offset_y_m',0)
        selected.append(p)
    byplacement={p['id']:p for p in selected};bybuilding={b['id']:b for b in buildings};used=set();usedbuildings=set()
    for route in routes:
        route['placement_ids']=[p['id'] for p in selected if corridor_intersects(p['world_bounds_xz_m'],route['points'])]
        route['building_ids']=[b['id'] for b in buildings if corridor_intersects(b['world_bounds_xz_m'],route['points'])]
        used.update(route['placement_ids']);usedbuildings.update(route['building_ids'])
    selected={k:byplacement[k] for k in sorted(used)};buildings={k:bybuilding[k] for k in sorted(usedbuildings)}
    keys={p['asset_key'] for p in selected.values()};chosen={}
    for key in sorted(keys):
        a=assets[key];path=ROOT/a['render_path'];sha=digest(path)
        if sha!=a['render_sha256']:raise ValueError('Compiled render hash mismatch '+key)
        chosen[key]={k:a[k] for k in ('render_path','render_sha256','bounds','pitch_m','quad_count') if k in a}
    sources={name:{'path':str(Path(path).resolve()),'sha256':digest(path)} for name,path in [('scene',scene_path),('topography',layer_path),('topography_source',plan_path)]}
    implementation={str(p.relative_to(ROOT)):digest(p) for p in [HERE/'prepare.py',HERE/'Traversal.gd',HERE/'project.godot',ROOT/'voxel_character/common/preview/RenderData.gd']}
    out={'schema':'riverstone.city.r2_capsule_suite.v1','repo_root':str(ROOT),'sources':sources,
         'implementation_hashes':implementation,'assets':chosen,'placements':selected,'buildings':buildings,'routes':routes,
         'scene_anchor_overrides_from_tested_layer':overridden,'fine_bounds_xz_m':FINE_BOUNDS,
         'assumptions':{'capsule_radius_m':.3,'capsule_height_m':1.8,'walking_speed_mps':4,'physics_hz':60,
           'actual_ground':'unmodified compiled common render triangles; no added floor/ramp; no vertex editing',
           'within_route_teleport':False,'independent_route_reset':True,'spawn':'ray to actual layer1 collision; analytic H never drives movement',
           'building_collision':'conservative envelopes minus only existing explicit openings',
           'test_collision_policy':'force actual macro/medium geometry on for diagnostic tests; production collision_enabled flags unchanged',
           'scope':'fixed sampled routes only; no whole-city, production controller, navmesh, NPC, interior or door-threshold guarantee',
           'collision_selection':'per-route conservative segment AABB union +4m; static world rebuilt only between independent cases'},
         'coverage':{'route_count':len(routes),'route_kinds':dict(Counter(r['kind'] for r in routes)),
                     'selected_collision_assets':len(chosen),'selected_placements':len(selected),'selected_buildings':len(buildings),
                     'collision_categories':dict(Counter(p['category'] for p in selected.values())),
                     'source_scene_buildings':len(scene['instances']),'sampled_only':True}}
    write(out_path,out);return out

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--scene',type=Path,default=ROOT/'world_city/runtime_city/generated/r2/scene.json')
    ap.add_argument('--layers',type=Path,default=ROOT/'world_city/runtime_city/generated/r2_topography/layer_manifest.json')
    ap.add_argument('--output',type=Path,default=HERE/'prepared.json');ap.add_argument('--fine-only',action='store_true');a=ap.parse_args();o=prepare(a.scene,a.layers,a.output,a.fine_only)
    print(json.dumps({'prepared':str(a.output),'sources':o['sources'],'coverage':o['coverage'],'anchor_overrides':len(o['scene_anchor_overrides_from_tested_layer'])},indent=2))
