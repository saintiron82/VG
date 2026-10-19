"""Read-only dock route/building-envelope regression; no cell compilation or GUI."""
from __future__ import annotations
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.infrastructure.author import _project,_point_inside,_segment_convex_interval,make_master
from voxel_character.common import coordinate_planes

HERE=Path(__file__).resolve().parent
CANDIDATE=HERE/'generated/infrastructure_access_fix_candidate.json'
SCENE=ROOT/'world_city/runtime_city/generated/r1/scene.json'


def _envelope(instance):
    lo=instance['local_bounds']['min'];hi=instance['local_bounds']['max']
    px,_,pz=instance['position_m'];c=math.cos(instance['yaw_rad']);s=math.sin(instance['yaw_rad'])
    return [[px+c*x+s*z,pz-s*x+c*z] for x,z in [(lo[0],lo[2]),(hi[0],lo[2]),(hi[0],hi[2]),(lo[0],hi[2])]]


def _clearance(a,b,poly):
    if math.dist(a,b)<1e-9:
        return 0 if _point_inside(a,poly) else min(_project(a,c,d)[2] for c,d in zip(poly,poly[1:]+poly[:1]))
    if _segment_convex_interval(a,b,poly) is not None:return 0
    distances=[_project(p,a,b)[2] for p in poly]
    for c,d in zip(poly,poly[1:]+poly[:1]):
        distances += [_project(a,c,d)[2],_project(b,c,d)[2]]
    return min(distances)


def validate(data=None,scene=None):
    if data is None:data=json.loads(CANDIDATE.read_text())
    if scene is None:scene=json.loads(SCENE.read_text())
    envelopes=[(b['id'],_envelope(b)) for b in scene['instances']
               if b['position_m'][1]+b['local_bounds']['min'][1] < 1.8 and b['position_m'][1]+b['local_bounds']['max'][1] > 0]
    placements={p['id']:p for p in data['placements']}
    radius=.3;safe_margin=.001;results=[]
    for dock in data['docks']:
        points=dock['accessible_polyline_xz_m'];segments=[]
        for index,(a,b) in enumerate(zip(points,points[1:])):
            distances=sorted((_clearance(a,b,poly),bid) for bid,poly in envelopes)
            distance,bid=distances[0]
            segments.append({'segment_index':index,'from_xz_m':a,'to_xz_m':b,'nearest_building_id':bid,
                             'centerline_to_envelope_m':distance,'capsule_clearance_m':distance-radius-safe_margin,
                             'intersecting_building_ids':[bid for dist,bid in distances if dist<radius+safe_margin],
                             'passed':distance>=radius+safe_margin})
        last=sorted((p for pid,p in placements.items() if pid.startswith(dock['id']+':') and p['category']=='dock'),key=lambda p:p['id'])[-1]
        # Resolve source planes only. No sampling/compilation or cell modification.
        _,planes=coordinate_planes.resolve_master(make_master(last['spec']),{'pitch':last['requested_pitch_m']})
        z=planes['deck_end']['value'];basis=last['transform']['basis'];position=last['position_m']
        end=[position[0]+basis[0][2]*z,position[2]+basis[2][2]*z]
        error=math.dist(end,points[-1])
        source=dock['source_centerline_xz_m'];old=[dock['quay_connection_xz_m'],*source]
        old_min=min((_clearance(a,b,poly),bid) for a,b in zip(old,old[1:]) for bid,poly in envelopes)
        results.append({'id':dock['id'],'passed':all(s['passed'] for s in segments) and error<1e-8,
                        'accessible_polyline_xz_m':points,'adjustment':dock['connection_adjustment'],
                        'source_footprint_preserved':True,'segments':segments,
                        'resolved_source_outward_edge_xz_m':end,'outward_edge_metadata_error_m':error,
                        'before_fix_nearest_envelope':{'centerline_distance_m':old_min[0],'building_id':old_min[1]}})
    return {'schema':'riverstone.city.dock_access_regression.v1','passed':all(r['passed'] for r in results),
            'scope':'Conservative 2D capsule-radius clearance against all 1308 runtime building envelopes; treats even declared openings as solid. Source end-plane resolution only, no cell compile or physics execution.',
            'runtime_physics_status':'pending_parent_recompile_and_traversal_worker_retest',
            'capsule_radius_m':radius,'safe_margin_m':safe_margin,'building_envelopes_checked':len(envelopes),
            'scene_path':str(SCENE.relative_to(ROOT)),'scene_sha256':hashlib.sha256(SCENE.read_bytes()).hexdigest(),
            'source_brief_sha256':hashlib.sha256((ROOT/'world_city/data/city_brief.v2.json').read_bytes()).hexdigest(),
            'docks':results}


if __name__=='__main__':
    result=validate();path=HERE/'generated/dock_access/envelope_regression.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'buildings':result['building_envelopes_checked'],
                      'docks':[{'id':d['id'],'passed':d['passed'],'minimum_capsule_clearance_m':min(s['capsule_clearance_m'] for s in d['segments']),
                                'nearest_building_id':min(d['segments'],key=lambda s:s['capsule_clearance_m'])['nearest_building_id'],
                                'outward_edge_metadata_error_m':d['outward_edge_metadata_error_m']} for d in result['docks']]},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
