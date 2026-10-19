"""Camera-only review copy, with a bounded density-block eye-height view."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];OUT=CITY/'evidence/visual_registered_common_r3'
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
p=OUT/'scene.json';d=json.loads(p.read_bytes());hashes={k:digest(d[k]) for k in ('surfaces','boxes','common_instances','common_assets')}
d['inspection_cameras'].update(
 estate_close=dict(position_m=[-70,115,-85],target_m=[-160,20,-240]),
 port_close=dict(position_m=[60,110,590],target_m=[-60,7,370]),
 bridge_closed=dict(position_m=[180,34,535],target_m=[129,6,491],bridge_state='ROAD_OPEN'),
 bridge_open=dict(position_m=[180,34,535],target_m=[129,6,491],bridge_state='NAVIGATION_OPEN'),
 market_close=dict(position_m=[175,78,145],target_m=[100,9,26]),
 cathedral_close=dict(position_m=[365,126,-8],target_m=[218,66,-180]),
 density_close=dict(position_m=[410,73,179],target_m=[334,4,90]),
 density_eye=dict(position_m=[319,4.15,100.3308028404],target_m=[336.129517807173,4.15,90.49240560983397],eye_height_m=1.65,source_route='B13_WEST_WELL_COURT:LINK',limits='Reserved source corridor, not a character traversal test.'),
 reservoir_close=dict(position_m=[85,76,-250],target_m=[-30,17,-365]),
 training_close=dict(position_m=[-195,95,-55],target_m=[-328,18,-175]))
assert hashes=={k:digest(d[k]) for k in hashes}
ledger=dict(parent_scene_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),geometry_hashes=hashes,views=['registered','bridge_closed','bridge_open','density_close','density_eye','market_close','cathedral_close','reservoir_close','training_close'],limits='Free inspection cameras; the eye-height view does not certify character traversal.')
d['camera_review_provenance']=ledger;(OUT/'camera_scene.json').write_text(json.dumps(d,separators=(',',':'))+'\n');(OUT/'camera_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n');print(ledger['parent_scene_sha256'])
