"""Camera-only evidence manifest; geometry and placements remain byte-equivalent data."""
import hashlib,json
from pathlib import Path
from world_city.concept_city_v3.registered_topography.revisions.r03_external_interfaces import review as terrain
ROOT=Path(__file__).resolve().parents[3];CITY=ROOT/'world_city/concept_city_v3'
def digest(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    folder=CITY/'evidence/visual_registered_common_r1_cached';source=folder/'scene.json';d=json.loads(source.read_bytes());before={k:digest(d[k]) for k in ('surfaces','boxes','common_instances','common_assets')}
    plan=json.loads((CITY/'registered_source/plan.json').read_bytes());road=next(r for r in plan['roads'] if r['id']=='BLOCK_014:ALLEY');a,b=road['polyline_xz_m'][:2]
    pos=[a[k]+(b[k]-a[k])*.69 for k in (0,1)];target=[a[k]+(b[k]-a[k])*.93 for k in (0,1)]
    d['inspection_cameras'].update(
        market_close=dict(position_m=[175,78,145],target_m=[100,9,26]),
        cathedral_close=dict(position_m=[365,126,-8],target_m=[218,66,-180]),
        alley_eye=dict(position_m=[pos[0],terrain.road_height_at(road['id'],*pos)+1.65,pos[1]],target_m=[target[0],terrain.road_height_at(road['id'],*target)+1.65,target[1]]),
        castle_close=dict(position_m=[-105,145,-70],target_m=[-290,45,-245]))
    d['camera_review_provenance']=dict(parent_scene_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),geometry_hashes=before,alley_eye_rule='1.65m above analytic registered road center; free camera only, not capsule traversal',alley_road_id=road['id'])
    after={k:digest(d[k]) for k in before};assert before==after
    (folder/'camera_scene.json').write_text(json.dumps(d,separators=(',',':'))+'\n');(folder/'camera_ledger.json').write_text(json.dumps(d['camera_review_provenance'],indent=2)+'\n')
    print(json.dumps({'camera_only_geometry_unchanged':True,'views':['market_close','cathedral_close','alley_eye','castle_close']}))
if __name__=='__main__':main()
