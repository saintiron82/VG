"""Three finite, source-bound top tessellation corrections; no boundary moves."""
import json,math,copy
from .audit import HERE,ny,f32
from .neighbor_probe import plane
from .. import author as a
from ..coherent_final24_r02.prepare import ref
from ..final_profile_audit_r01 import exact_clip as e
from .classify import area

def run():
 src=HERE.parent/'coherent_final24_r02/top_scene_patch_r01.json';patch=json.loads(src.read_bytes());vs=patch['appended_surfaces']['ground_stone'];ts=[vs[i:i+3]for i in range(0,len(vs),3)];neighbor=json.loads((HERE/'neighbor_probe.json').read_bytes());sub=json.loads((HERE/'subdivision_probe.json').read_bytes());operations=[]
 for index in (1372,4204):
  opt=next(r for r in neighbor['appended']if r['index']==index)['options'][0];operations.append(dict(indices=sorted([index,opt['neighbor']]),new=opt['new'],method='SAME_PLANE_INTERNAL_DIAGONAL_RETRIANGULATION'))
 rec=next(r for r in sub['records']if r['source'].get('appended_triangle_index')==2533);operations.append(dict(indices=[2533],new=rec['replacement_triangles_xyz_m'],method='EXACT_PLANE_MIDPOINT_SUBDIVISION'))
 rows=[];replace={};removed=set()
 h=json.loads((HERE.parent/'coherent_final24_r02/physical_owner_handoff_r03.json').read_bytes());owner=[]
 for r in h['rendered_plane_owners']:
  if r['material']=='ground_stone':owner.extend([r]*len(list(a.fan_upward([[x,a.common.height(r['plane_y_xz_m'],[x,z]),z]for x,z in r['polygon_xz_m']]))))
 for op in operations:
  ids=op['indices'];old=[ts[i]for i in ids];new=op['new'];assert all(ny(t)>0 and ny([[f32(v)for v in x]for x in t])>0 for t in new);assert len({owner[i]['holding_id']for i in ids})==1
  source_area=sum(ny(t)for t in old)/2;new_area=sum(ny(t)for t in new)/2;missing=extra=0;signed=[]
  for i,t in zip(ids,old):
   poly=[[v[0],v[2]]for v in t];parts=[poly]
   for q in new:parts=[r for p in parts for r in e.difference(p,[[v[0],v[2]]for v in q])]
   missing+=sum(area(p)for p in parts)
   for q in new:
    qp=plane(q);clip=e.clip(poly,[[v[0],v[2]]for v in q]);signed.extend(a.common.height(qp,v)-a.common.height(owner[i]['plane_y_xz_m'],v)for v in clip)
  for t in new:
   parts=[[[v[0],v[2]]for v in t]]
   for q in old:parts=[r for p in parts for r in e.difference(p,[[v[0],v[2]]for v in q])]
   extra+=sum(area(p)for p in parts)
  assert max(missing,extra,abs(new_area-source_area))<1e-10
  assert max(abs(x)for x in signed)<1e-8
  replace[min(ids)]=new;removed.update(ids)
  rows.append(dict(method=op['method'],material='ground_stone',holding_id=owner[ids[0]]['holding_id'],source_indices=ids,source_triangles_xyz_m=old,source_triangle_hashes=[a.canonical_sha(t)for t in old],source_physical_owner_ids=[owner[i]['id']for i in ids],source_planes=[owner[i]['plane_y_xz_m']for i in ids],replacement_triangles_xyz_m=new,replacement_planes=[plane(t)for t in new],source_area_m2=source_area,replacement_area_m2=new_area,missing_source_area_m2=missing,outside_source_area_m2=extra,minimum_signed_height_deviation_m=min(signed),maximum_signed_height_deviation_m=max(signed),maximum_grade=max(math.hypot(*plane(t)[:2])for t in new),native_edge_policy='Original outer XZ vertices retained; only internal diagonal or exact source-edge midpoint changes.'))
 new=[]
 for i,t in enumerate(ts):
  if i in replace:new.extend(v for q in replace[i]for v in q)
  elif i not in removed:new.extend(t)
 patch['appended_surfaces']['ground_stone']=new;patch['precision_source_continuation']=dict(source=ref(src),ledger_path=str((HERE/'source_retriangulation_ledger.json').relative_to(a.ROOT)),scope='Only the three identified local precision cases and two same-owner coplanar neighbors.');report=dict(source=ref(src),operations=rows,passed=True,remaining_inversions=[])
 for i in range(len(new)//3):
  t=new[3*i:3*i+3]
  if ny([[f32(v)for v in x]for x in t])<0:report['remaining_inversions'].append(dict(material='ground_stone',appended_triangle_index=i,vertices_xyz_m=t,source_triangle_sha256=a.canonical_sha(t)))
 (HERE/'source_retriangulation_ledger.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False)+'\n');(HERE/'top_scene_patch_retriangulated.json').write_text(json.dumps(patch,separators=(',',':'),allow_nan=False)+'\n');print('Corrected3;',len(report['remaining_inversions']),'remaining appended flips; source remainder also remains.',flush=True)
 for r in rows:print(r['source_indices'],r['maximum_signed_height_deviation_m'],r['minimum_signed_height_deviation_m'],r['maximum_grade'],flush=True)
if __name__=='__main__':run()
