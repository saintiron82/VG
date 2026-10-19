"""Validate current resources and integrate the independently authored layers."""
from pathlib import Path
import json,sys,hashlib,collections
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.assemble_city import write,sha
from world_city.runtime_city.checks.placement import validate_placements
HERE=Path(__file__).resolve().parent;OUT=HERE/'generated/r1'

def main():
 scene=json.loads((OUT/'scene.json').read_text());plan=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text());inf=json.loads((OUT/'infrastructure.json').read_text())
 assert scene['catalog_complete']
 failures=[]
 for key,asset in scene['assets'].items():
  for lod,resource in asset.items():
   for path_key,hash_key in [('render_path','render_sha256'),('master_path','master_sha256')]:
    path=ROOT/resource[path_key]
    if not path.exists() or sha(path)!=resource[hash_key]:failures.append([key,lod,path_key])
 for key,resource in inf['assets'].items():
  if sha(ROOT/resource['render_path'])!=resource['render_sha256']:failures.append(['infrastructure',key])
 scene['infrastructure']=inf
 result=validate_placements(scene,plan);write(HERE/'evidence/placement_final.json',result)
 summary={'resource_failures':failures,'building_instances':len(scene['instances']),'building_masters':len(scene['assets']),'fine_resources':sum('fine' in a for a in scene['assets'].values()),'infrastructure_instances':len(inf['placements']),'infrastructure_render_resources':len(inf['assets']),'coarse_unique_cells':sum(a['coarse']['cell_count'] for a in scene['assets'].values()),'coarse_unique_quads':sum(a['coarse']['quad_count'] for a in scene['assets'].values()),'geometry_checks_pass':result['passed'],'entrance_verification_complete':result['verification_complete'],'vertical_access_status':result['vertical_access_status'],'district_counts':dict(collections.Counter(i['district_id'] for i in scene['instances'])),'source_layout_sha256':sha(ROOT/'world_city/data/city_brief.v2.json')}
 write(HERE/'evidence/resource_validation.json',summary)
 scene['status']='structural_pass_pending_visual_and_traversal' if result['passed'] and not failures else 'structural_fail'
 scene['structural_evidence']='world_city/runtime_city/evidence/resource_validation.json';write(OUT/'scene.json',scene)
 print(json.dumps(summary,ensure_ascii=False,indent=2)); print('Placement failures:',json.dumps(result['failures'],ensure_ascii=False)[:8000]);print('Unverified:',json.dumps(result['unverified'],ensure_ascii=False)[:2000])
 return int(bool(failures) or not result['passed'])
if __name__=='__main__':raise SystemExit(main())
