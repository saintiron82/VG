"""Bounded source-native detail adapters using the existing shared crop author.
No collision creation; arbitrary native-cell boundary support is explicit opt-in.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,resource,sys,time
H=Path(__file__).resolve().parent;U=H.parent;R=U.parents[3]
sys.path.insert(0,str(U/'surface_modules/edge_trims'));import author_edge_trims as edge
common=edge.common
LIMIT=20_000_000

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,d):common.write_exact(p,common.payload(d))
def test():
 spec=importlib.util.spec_from_file_location('old_edge',U/'surface_modules/edge_trims/author_edge_trims.pre_native_quantum_r01.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 safe=read(U/'surface_modules/inputs/safe_offset_rules.v1.json');results=[]
 for kind in ['paving','planks']:
  q=copy.deepcopy(safe);q['trim']={'width_m':.5,'height_m':.25,'offset_m':[.25,.5]}
  prior=old.compile_exact_crop(q,kind,41873);now=edge.compile_exact_crop(q,kind,41873)
  assert all(common.payload(a)==common.payload(b)for a,b in zip(prior,now));results.append(kind+':default_byte_identical')
  full=copy.deepcopy(safe);full['trim']={'width_m':1,'height_m':1,'offset_m':[0,0]};m,_=common.author(full,kind,41873)
  c=common.compile_master(m,{'pitch':.0125});original={tuple(row[:3]):row[3:]for row in c['cells']}
  for trim in [{'width_m':.2,'height_m':.3,'offset_m':[.05,.1]},{'width_m':.075,'height_m':.125,'offset_m':[.9125,.875]},{'width_m':1,'height_m':.2,'offset_m':[0,.8]}]:
   q=copy.deepcopy(safe);q['trim']=trim;crop=edge.compile_exact_crop(q,kind,41873,boundary_quantum_m=.0125)
   ox,oy=trim['offset_m'];w,h=trim['width_m'],trim['height_m'];low=[round(ox/.0125),round(oy/.0125)];hi=[round((ox+w)/.0125),round((oy+h)/.0125)]
   expected={k:v for k,v in original.items() if all(low[a]<=k[a]<hi[a]for a in range(2))};actual={tuple(row[:3]):row[3:]for row in crop[1]['cells']}
   assert actual==expected;results.append(kind+':exact_full_source_crop:'+str(trim))
  for bad in [.02,.1,0,-.0125]:
   try:edge.author_exact_crop(q,kind,41873,boundary_quantum_m=bad)
   except ValueError:results.append(kind+':reject_quantum:'+str(bad))
   else:raise AssertionError('bad quantum accepted')
  q['trim']['offset_m'][0]=.003
  try:edge.author_exact_crop(q,kind,41873,boundary_quantum_m=.0125)
  except ValueError:results.append(kind+':reject_unaligned')
  else:raise AssertionError('unaligned accepted')
 from author_native_access import top_rectangle,patches
 valid=[[0,0,0],[0,0,1],[1,0,1],[1,0,0]]
 assert top_rectangle(valid)==[0,-80,80,0]
 for bad in [valid[::-1],[[0,0,0],[0,0,1],[.9,0,.8],[1,0,0]],[[0,0,0],[0,.1,1],[1,0,1],[1,0,0]]]:
  try:top_rectangle(bad)
  except ValueError:results.append('reject_source_non_top_rectangle')
  else:raise AssertionError('invalid support accepted')
 for rect in [[-13,-91,44,-65],[-80,-80,80,80],[0,0,2,80]]:
  for p in patches(rect):
   b=p['low_uv']+p['high_uv'];r=[x*.0125 for x in rect];assert r[0]-1e-8<=b[0]<b[2]<=r[2]+1e-8 and r[1]-1e-8<=b[1]<b[3]<=r[3]+1e-8
 results.append('negative_and_partial_source_bounds_contained')
 save(H/'validation/crop_regression_r01.json',{'all_pass':True,'tests':results,'default_old_author_sha256':sha(Path(old.__file__)),'current_author_sha256':sha(Path(edge.__file__)),'original_core_sha256':sha(R/'voxel_character/common/core.py')});return results

def build():
 start=time.perf_counter();results=test();plan=read(H/'generated/source_plan.json');safe=read(U/'surface_modules/inputs/safe_offset_rules.v1.json');out=H/'generated/modules_r01';rows=[];total=0
 frozen={str(p.relative_to(R)):sha(p)for p in [R/'voxel_character/common/core.py',R/'voxel_character/common/render_data.py',U/'surface_modules/author_surfaces.py',Path(edge.__file__),H/'generated/source_plan.json']}
 for i,demand in enumerate(plan['module_demand']):
  spec=copy.deepcopy(safe);spec['trim']=demand['trim'];master,c,render,contract,checks=edge.compile_exact_crop(spec,demand['kind'],demand['seed'],boundary_quantum_m=.0125)
  data=common.payload(render);source=common.payload(master);total+=len(data)+len(source);assert total<LIMIT
  rp=out/(demand['id']+'.render.json');mp=out/(demand['id']+'.master.json');common.write_exact(rp,data);common.write_exact(mp,source)
  rows.append({**demand,'render_path':str(rp.relative_to(R)),'render_sha256':sha(rp),'master_path':str(mp.relative_to(R)),'master_sha256':sha(mp),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':render['quad_count'],'checks':checks})
  if i%10==0:print(json.dumps({'done':i+1,'of':len(plan['module_demand']),'bytes':total}),flush=True)
 assert frozen=={p:sha(R/p)for p in frozen}
 save(out/'catalog.json',{'schema':'riverstone.native_access_detail.module_catalog.v1','source_plan_sha256':sha(H/'generated/source_plan.json'),'source_dependencies':frozen,'modules':rows,'runtime_activation':False,'original_collision_unchanged':True,'maximum_visual_offset_m':.0375})
 report={'all_pass':True,'modules':len(rows),'tests':len(results),'generated_bytes':total,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'seconds':time.perf_counter()-start,'runtime_activation':False,'no_new_collision':True}
 (H/'validation/build_r01.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':build()
