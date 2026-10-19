"""Rebind immutable r08 boundary paths to the exactly coplanar r09 change."""
import json,shutil
from .build_corridors import H,ref,sha
P=H/'candidate_r08_boundary_routes_r01';C=H/'candidate_r09';O=H/'candidate_r09_boundary_routes_r01';O.mkdir();d=json.load(open(P/'routes.json'));original_routes=json.dumps(d['routes'],separators=(',',':'));main=json.load(open(C/'routes.json'))
for key in ['finite_patch','visual_index','producer_sources']:d[key]=main[key]
d['producer_sources']['boundary_original_request']=ref(P/'routes.json');d['supplements_request']=ref(C/'routes.json');assert json.dumps(d['routes'],separators=(',',':'))==original_routes
(O/'routes.json').write_text(json.dumps(d,separators=(',',':'))+'\n');shutil.copyfile(__file__,O/'producer.py');(O/'FROZEN.json').write_text(json.dumps(dict(request=ref(O/'routes.json'),producer=ref(O/'producer.py'),original=ref(P/'routes.json'),proof='Exact same boundary route arrays and fixture; only immutable geometry/index references updated after coplanar diagonal flip.'),separators=(',',':'))+'\n');print(json.dumps(ref(O/'routes.json')))
