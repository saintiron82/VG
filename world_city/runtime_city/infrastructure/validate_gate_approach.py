"""Read-only full-width west approach audit against current runtime envelopes."""
import hashlib
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.infrastructure.author import _ribbon,_clip_polygon
from world_city.runtime_city.infrastructure.validate_dock_access import _envelope
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE/'generated/infrastructure_access_fix_candidate.json'
SCENE=ROOT/'world_city/runtime_city/generated/r1/scene.json'


def _overlap(a,b):
    for poly in (a,b):
        for p,q in zip(poly,poly[1:]+poly[:1]):
            normal=[-(q[1]-p[1]),q[0]-p[0]]
            av=[x[0]*normal[0]+x[1]*normal[1] for x in a]
            bv=[x[0]*normal[0]+x[1]*normal[1] for x in b]
            if max(av)<=min(bv)+1e-8 or max(bv)<=min(av)+1e-8:return False
    return True


def validate(data=None,scene=None):
    if data is None:data=json.loads(CANDIDATE.read_text())
    if scene is None:scene=json.loads(SCENE.read_text())
    results=[]
    for approach in data['external_gate_approaches']:
        points=approach['polyline_xz_m'];poly=_ribbon(points[0],points[-1],approach['width_m'])
        gate=next(b for b in scene['instances'] if b['id']==approach['gate_instance_id'])
        building_collisions=[b['id'] for b in scene['instances'] if b['id']!=gate['id'] and _overlap(poly,_envelope(b))]
        wall_collisions=[]
        for p in scene['infrastructure']['placements']:
            if p['category']!='wall':continue
            bounds=scene['infrastructure']['assets'][p['asset_key']]['bounds'];lo,hi=bounds['min'],bounds['max']
            basis=p['transform']['basis'];pos=p['position_m']
            wall=[[pos[0]+basis[0][0]*x+basis[0][2]*z,pos[2]+basis[2][0]*x+basis[2][2]*z]
                  for x,z in [(lo[0],lo[2]),(hi[0],lo[2]),(hi[0],hi[2]),(lo[0],hi[2])]]
            if _overlap(poly,wall):wall_collisions.append(p['id'])
        c=math.cos(gate['yaw_rad']);s=math.sin(gate['yaw_rad']);pos=gate['position_m']
        local=[]
        for x,z in poly:
            dx,dz=x-pos[0],z-pos[2];local.append([c*dx-s*dz,s*dx+c*dz])
        bounds=gate['local_bounds'];lo,hi=bounds['min'],bounds['max']
        overlap=_clip_polygon(local,lo[0],lo[2],hi[0],hi[2])
        main=gate['gate_openings'][0]['local_bounds'];mn,mx=main['min'],main['max']
        opening_clear=all(mn[0]-1e-8<=x<=mx[0]+1e-8 and mn[2]-1e-8<=z<=mx[2]+1e-8 for x,z in overlap)
        lateral_clearance=min((min(x-mn[0],mx[0]-x) for x,z in overlap),default=0)
        results.append({'id':approach['id'],'passed':not building_collisions and not wall_collisions and opening_clear,
                        'full_paved_width_m':approach['width_m'],'paved_polygon_xz_m':poly,
                        'building_envelope_intersections':building_collisions,'sampled_wall_bounds_intersections':wall_collisions,
                        'gate_local_corridor_polygon':local,'gate_envelope_overlap_polygon':overlap,
                        'entire_gate_overlap_inside_main_opening':opening_clear,'minimum_main_opening_lateral_clearance_m':lateral_clearance,
                        'canonical_source_route_unchanged':True})
    return {'schema':'riverstone.city.external_gate_approach_audit.v1','passed':all(r['passed'] for r in results),
            'scope':'Full 6.5 m authored paved rectangle, all current runtime building envelopes, and actual sampled wall-panel bounds. Main gate opening only; no tower removal or other new aperture.',
            'building_envelopes_checked':len(scene['instances']),'wall_panels_checked':sum(p['category']=='wall' for p in scene['infrastructure']['placements']),
            'scene_sha256':hashlib.sha256(SCENE.read_bytes()).hexdigest(),'approaches':results}


if __name__=='__main__':
    result=validate();(HERE/'generated/dock_access/west_approach_full_width_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
