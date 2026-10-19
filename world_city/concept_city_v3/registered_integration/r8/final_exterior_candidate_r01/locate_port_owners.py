"""Locate the exact port retirement triangles in existing producer inputs."""
import pathlib,json,hashlib,time,collections,sys
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a,merge_patches as m
D=pathlib.Path(__file__).resolve().parent

def main(request_name="ownership_requests.json",output_name="port_source_location_r01.json"):
 start=time.monotonic();bp=D/'noble_cap_bridge_binding.json';b=a.load(bp);rp=a.CITY/'assemblies/waterworks/registered_bridge/port_approach_r01'/request_name;r=a.load(rp);wanted={tuple(tuple(v)for v in q['source_triangle_xyz_m']):q for q in r['current_top_retirement_requests']};found=collections.defaultdict(list)
 def visit(t,location):
  key=tuple(tuple(v)for v in t)
  if key in wanted:
   q=wanted[key];assert m.canonical_sha(t)==q['source_triangle_sha256'];found[q['source_triangle_sha256']].append(location)
 base=a.load(a.ROOT/b['base_scene']['path'],b['base_scene']['sha256'])
 for mat,flat in base['surfaces'].items():
  for i in range(0,len(flat),3):visit(flat[i:i+3],dict(kind='base',material=mat,triangle_index=i//3,source=b['base_scene']))
 for pi,ref in enumerate(b['patches']):
  p=a.load(a.ROOT/ref['path'],ref['sha256'])
  for mat,flat in p.get('appended_surfaces',{}).items():
   for i in range(0,len(flat),3):visit(flat[i:i+3],dict(kind='append',producer_index=pi,material=mat,triangle_index=i//3,source=ref))
  for ei,e in enumerate(p.get('surface_edits',[])):
   for i,t in enumerate(e['replacement_triangles_xyz_m']):visit(t,dict(kind='replacement',producer_index=pi,edit_index=ei,material=e['material'],base_triangle_index=e['triangle_index'],replacement_index=i,source=ref))
 rows=[dict(request_index=i,triangle_sha256=q['source_triangle_sha256'],locations=found[q['source_triangle_sha256']])for i,q in enumerate(r['current_top_retirement_requests'])]
 report=dict(schema='riverstone.port_exact_source_location.v1',binding=dict(path=a.rel(bp),sha256=a.sha(bp)),requests=dict(path=a.rel(rp),sha256=a.sha(rp)),rows=rows,unique=sum(len(q['locations'])==1 for q in rows),missing=[q['request_index']for q in rows if not q['locations']],ambiguous=[q['request_index']for q in rows if len(q['locations'])>1],seconds=time.monotonic()-start)
 out=D/output_name;assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k!='rows'},flush=True)
if __name__=='__main__':main(*sys.argv[1:])
