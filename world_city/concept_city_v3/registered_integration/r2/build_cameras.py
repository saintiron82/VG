import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];OUT=CITY/'evidence/visual_registered_common_r2'
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
p=OUT/'scene.json';d=json.loads(p.read_bytes());hashes={k:digest(d[k]) for k in ('surfaces','boxes','common_instances','common_assets')}
d['inspection_cameras'].update(estate_close=dict(position_m=[-70,115,-85],target_m=[-160,20,-240]),port_close=dict(position_m=[60,110,590],target_m=[-60,7,370]),bridge_close=dict(position_m=[220,45,592],target_m=[127,3,486]),market_close=dict(position_m=[175,78,145],target_m=[100,9,26]),cathedral_close=dict(position_m=[365,126,-8],target_m=[218,66,-180]))
assert hashes=={k:digest(d[k]) for k in hashes}
ledger=dict(parent_scene_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),geometry_hashes=hashes,views=['registered','estate_close','port_close','bridge_close','market_close','cathedral_close'],limits='Free cameras only, not character traversal.')
d['camera_review_provenance']=ledger;(OUT/'camera_scene.json').write_text(json.dumps(d,separators=(',',':'))+'\n');(OUT/'camera_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n');print(ledger['parent_scene_sha256'])
