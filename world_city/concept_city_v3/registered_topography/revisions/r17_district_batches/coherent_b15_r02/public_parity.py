"""Confirm any finite reowned public pieces retain their exact source plane."""
import json,time
from .. import author as a
from .source_preflight import HERE,write

def run():
 scene=a.load_scene();patch=json.loads((HERE/'candidate_scene_patch.json').read_bytes());parts=json.loads((HERE/'composition_report.json').read_bytes())['rendered_owner_parts'];idx=a.geo._SpatialIndex(16)
 for i,o in enumerate(parts):idx.add(i,o['polygon_xz_m'])
 rows=[];fails=[]
 for e in patch['surface_edits']:
  if e['material']not in('road','alley'):continue
  t=scene['surfaces'][e['material']][e['triangle_index']*3:e['triangle_index']*3+3];p=[[v[0],v[2]]for v in t];plane=a.common.plane(t);delta=0.;area=0.
  for j in idx.candidates(p):
   o=parts[j];q=a.clip(p,o['polygon_xz_m'])
   if q:area+=a.geo.polygon_area(q);delta=max(delta,max(abs(a.common.height(plane,v)-a.common.height(o['plane_y_xz_m'],v))for v in q))
  row=dict(material=e['material'],triangle_index=e['triangle_index'],reowned_area_m2=area,maximum_height_change_m=delta);rows.append(row)
  if delta>1e-7:fails.append(row)
 result=dict(scene_patch_sha256=a.sha(HERE/'candidate_scene_patch.json'),public_original_faces=len(rows),rows=rows,failures=fails,maximum_height_change_m=max([r['maximum_height_change_m']for r in rows]+[0]),status='PASS'if not fails else'FAILED',activation=False);write('public_height_parity.json',result);print('public',len(rows),'fail',len(fails),'max',result['maximum_height_change_m'],flush=True)
if __name__=='__main__':run()
