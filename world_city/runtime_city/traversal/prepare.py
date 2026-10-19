#!/usr/bin/env python3
"""Prepare independent, explicit capsule tests from the compiled city manifests.
No test points are rerouted around failures. Elevation remains the documented Y=0
milestone, not the source's unresolved terrain-height proposals.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
GROUND_CATEGORIES={'terrain','bridge','dock','dock_connector'}
OBSTACLE_CATEGORIES={'wall','fountain','bridge_pier','dock_support'}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())


def subtract_box(box, hole):
    """Exact AABB difference, <=6 disjoint boxes; accepts holes outside a box."""
    lo=[max(box['min'][a],hole['min'][a]) for a in range(3)]
    hi=[min(box['max'][a],hole['max'][a]) for a in range(3)]
    if any(lo[a]>=hi[a] for a in range(3)): return [box]
    remainder={'min':list(box['min']),'max':list(box['max'])}
    pieces=[]
    for a in range(3):
        if remainder['min'][a]<lo[a]:
            p={'min':list(remainder['min']),'max':list(remainder['max'])}
            p['max'][a]=lo[a];pieces.append(p);remainder['min'][a]=lo[a]
        if remainder['max'][a]>hi[a]:
            p={'min':list(remainder['min']),'max':list(remainder['max'])}
            p['min'][a]=hi[a];pieces.append(p);remainder['max'][a]=hi[a]
    return pieces


def openings(instance):
    values=list(instance.get('gate_openings',[]))+list(instance.get('road_openings',[]))
    for key in ('gate_opening','road_opening'):
        if key in instance:values.append(instance[key])
    result=[]
    for opening in values:
        bounds=opening.get('local_bounds',opening)
        if 'min' not in bounds or 'max' not in bounds:raise ValueError(f"Unrecognized opening: {instance['id']} {opening}")
        if bounds not in result:result.append(bounds)
    return result


def route_record(id,points,kind,source_ids,**extra):
    clean=[]
    for p in points:
        point=[float(p[0]),0.,float(p[1])]
        if not clean or math.dist(point,clean[-1])>1e-5:clean.append(point)
    if len(clean)<2:raise ValueError(f'Route {id} too short')
    return dict(id=id,kind=kind,points=clean,source_road_ids=source_ids,
                length_m=sum(math.dist(a,b) for a,b in zip(clean,clean[1:])),**extra)



def dock_access_points(dock, end_inset=.75):
    """Use authored runtime access when present; never route around a blocker."""
    if 'accessible_polyline_xz_m' in dock:
        points=[list(map(float,p)) for p in dock['accessible_polyline_xz_m']]
        if len(points)<2:raise ValueError('Dock access needs at least two points: '+dock['id'])
        tail=math.dist(points[-2],points[-1])
        if tail<=end_inset:raise ValueError('Dock final segment shorter than capsule inset: '+dock['id'])
        points[-1]=[points[-1][j]+(points[-2][j]-points[-1][j])*end_inset/tail for j in (0,1)]
        return points,'authored_accessible_polyline_xz_m'
    f=dock['source_footprint_xz_m'];x=sum(p[0] for p in f)/len(f)
    return [dock['quay_connection_xz_m'],[x,min(p[1] for p in f)],[x,max(p[1] for p in f)-end_inset]],'original_source_footprint_root'


def prepare(scene_path,infra_path,out_path):
    scene,infra=read(scene_path),read(infra_path)
    selected=[]
    for placement in infra['placements']:
        category=placement['category']
        if category not in GROUND_CATEGORIES|OBSTACLE_CATEGORIES:continue
        p={k:placement[k] for k in ('id','asset_key','position_m','yaw_deg','transform') if k in placement}
        p.update(category=category,collision_layer=1 if category in GROUND_CATEGORIES else 2)
        p['ignored_visual_offset_y_m']=placement.get('render_offset_y_m',0)
        selected.append(p)
    keys=sorted({p['asset_key'] for p in selected})
    assets={}
    for key in keys:
        asset=infra['assets'][key]
        actual_hash=digest(ROOT/asset['render_path'])
        if actual_hash!=asset['render_sha256']:raise ValueError('Hash mismatch '+key)
        assets[key]={'render_path':asset['render_path'],'render_sha256':actual_hash}
    buildings=[]
    for instance in scene['instances']:
        boxes=[instance['local_bounds']]
        holes=openings(instance)
        for hole in holes:boxes=[piece for box in boxes for piece in subtract_box(box,hole)]
        buildings.append(dict(id=instance['id'],asset_key=instance['asset_key'],position_m=instance['position_m'],
                              yaw_rad=instance['yaw_rad'],boxes=boxes,opening_count=len(holes)))
    streets={r['id']:r for r in infra['street_routes']}
    routes=[route_record(r['id'],r['polyline_xz_m'],r['kind'],r.get('road_ids',[]),width_m=r['width_m']) for r in streets.values()]
    bridge=streets['RT_BRIDGE'];south=streets['RT_SOUTH_MARKET']
    routes.append(route_record('COMBINED_SOUTH_BRIDGE_TO_MARKET',list(reversed(bridge['polyline_xz_m']))+south['polyline_xz_m'][1:],
                               'continuous_landmark_connection',bridge['road_ids']+south['road_ids']))
    approaches={a['route_id']:a for a in infra.get('external_gate_approaches',[])}
    for gate in ('WEST','EAST','NORTH'):
        r=streets[f'RT_{gate}_MARKET'];p=r['polyline_xz_m']
        if r['id'] in approaches:
            approach=approaches[r['id']];access=approach['polyline_xz_m']
            if math.dist(access[-1],p[0])>.01:raise ValueError('External approach does not meet canonical route: '+r['id'])
            points=access+p[1:];policy='authored_external_gate_approaches; canonical source street unchanged'
        else:
            a,b=p[0],p[1];length=math.dist(a,b)
            outside=[a[j]+(a[j]-b[j])/length*15 for j in (0,1)]
            points=[outside]+p;policy='15m straight continuation of first source road segment outside gate'
        routes.append(route_record(f'GATE_{gate}_OUTSIDE_TO_MARKET',points,'extended_gate_entry',r['road_ids'],extension_policy=policy))
    for dock in infra['docks']:
        points,origin=dock_access_points(dock)
        routes.append(route_record(dock['id']+'_QUAY_TO_PIER',points,'quay_to_dock',[],
                                  path_origin=origin,end_policy='0.75m before actual dock edge'))
    deferred=infra.get('walls',{}).get('deferred_wall_routes',[])
    manifest=dict(schema='riverstone.city.capsule_suite.v1',repo_root=str(ROOT),
                  sources={'scene_path':str(scene_path),'scene_sha256':digest(scene_path),'infrastructure_path':str(infra_path),'infrastructure_sha256':digest(infra_path)},
                  assumptions={'capsule_radius_m':.3,'capsule_height_m':1.8,'walking_speed_mps':4.,'physics_hz':60,
                               'within_route_teleport':False,'independent_route_reset':True,'ground':'exact compiled render quads; no infinite plane',
                               'buildings':'conservative local envelope minus explicit authored opening boxes',
                               'render_offset_y_m':'visual only, not applied to collision','terrain_grade':'flat_y0_initial_exterior_milestone',
                               'not_validated':['actual game controller','NPCs','navigation mesh','unrealized terrain grades','interiors','elevated wall walks']},
                  ground_categories=sorted(GROUND_CATEGORIES),obstacle_categories=sorted(OBSTACLE_CATEGORIES),
                  assets=assets,placements=selected,buildings=buildings,routes=routes,
                  coverage={'source_street_routes':len(streets),'source_ground_segments':len(infra['routes']),
                            'extra_continuous_routes':len(routes)-len(streets),'deferred_wall_routes':len(deferred),
                            'buildings':len(buildings),'openings_subtracted':sum(b['opening_count'] for b in buildings),
                            'collision_placements_by_category':dict(Counter(p['category'] for p in selected)),
                            'route_length_total_m':sum(r['length_m'] for r in routes)})
    out_path=Path(out_path);out_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'prepared':str(out_path),'coverage':manifest['coverage'],'unique_collision_assets':len(assets)},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scene',type=Path,default=ROOT/'world_city/runtime_city/generated/r1/scene.json')
    parser.add_argument('--infrastructure',type=Path,default=ROOT/'world_city/runtime_city/generated/r1/infrastructure.json')
    parser.add_argument('--output',type=Path,default=HERE/'prepared.json');a=parser.parse_args();prepare(a.scene,a.infrastructure,a.output)
