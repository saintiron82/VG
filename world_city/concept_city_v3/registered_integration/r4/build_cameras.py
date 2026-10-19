"""Camera-only r4 review; registration stays fixed to the approved concept."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1]
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 out=CITY/'evidence/visual_registered_common_r4';p=out/'scene.json';d=json.loads(p.read_bytes());before={k:digest(d[k]) for k in ('surfaces','boxes','common_instances','common_assets')}
 d['inspection_cameras'].update(
  density_close=dict(position_m=[410,73,179],target_m=[334,4,90]),
  density_eye=dict(position_m=[319,4.15,100.3308028404],target_m=[336.129517807173,4.15,90.49240560983397],eye_height_m=1.65,source_route='B13_WEST_WELL_COURT:LINK',limits='Source reserved corridor only; not character passage.'),
  density_b15=dict(position_m=[452,82,370],target_m=[346,4,246]),
  reservoir_north=dict(position_m=[30,70,-480],target_m=[-30,17,-365]),
  south_road=dict(position_m=[235,66,640],target_m=[134,2,548]),
  training_close=dict(position_m=[-195,95,-55],target_m=[-328,18,-175]),
  cathedral_close=dict(position_m=[365,126,-8],target_m=[218,66,-180]),
  bridge_closed=dict(position_m=[180,34,535],target_m=[129,6,491],bridge_state='ROAD_OPEN'),
  bridge_open=dict(position_m=[215,45,472],target_m=[129,7,491],bridge_state='NAVIGATION_OPEN'))
 assert before=={k:digest(d[k]) for k in before}
 d['camera_review_provenance']=dict(parent_scene_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),unchanged_geometry=before,eye_height_claim='Free camera only; no character pass')
 dest=out/'camera_scene.json';assert not dest.exists();dest.write_text(json.dumps(d,separators=(',',':'))+'\n');print(hashlib.sha256(dest.read_bytes()).hexdigest())
if __name__=='__main__':main()
