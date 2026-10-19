from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[8];sys.path.insert(0,str(ROOT));C=ROOT/'world_city/concept_city_v3';SRC=C/'assemblies/landmarks/registered/precinct_r06_whole/primary_goals_completion_r01';sys.path.insert(0,str(SRC))
from audit_main_opening_diagnostics import *
O=Path(__file__).resolve().parent
scene=load(C/'evidence/r8_final110_runtime_r01/scene.json');p=next(x for x in scene['common_instances']if x['id']=='castle_registered:front_curtain');poly=b.xform(b.rect(-.3,.0,.3,2.5),p);ix=terrain.TriangleIndex(scene,[poly]);r=terrain.audit_polygon(ix,poly,None,grade_limit=1);print('terrain',r['area_m2'],r['missing_area_m2']);print([(s['material'],s['triangle_index'],s['min_y_m'],s['max_y_m'],s['polygon_xz_m'])for s in r['source_pieces']]);print('fields',r.keys())
near=[]
for pp in scene['common_instances']:
 a=scene['common_assets'][pp['asset_key']];m=load(ROOT/a['render_path']);bb=m['bounds'];foot=b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),pp)
 if geo.intersection_area(poly,foot)>1e-7 and bb['min'][1]+pp['position_m'][1]<26 and bb['max'][1]+pp['position_m'][1]>23:near.append({'id':pp['id'],'position':pp['position_m'],'bounds':bb})
print('near',near);(O/'gate_probe.json').write_text(json.dumps({'polygon':poly,'terrain':r,'nearby_native':near},indent=2)+'\n')
