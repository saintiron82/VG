#!/usr/bin/env python3
"""Bounded source-owned coplanar subdivision; does not write source render/mesh."""
import os,sys
os.environ['PYTHONDONTWRITEBYTECODE']='1'
from pathlib import Path
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT.parent/'normal_diagnostic_r01'))
from derive_normal_diagnostic import *
R3=OUT.parent
R3PIN='c5354c21ca7a12589f6a8ee0bd73ca9046c120a43914b0502b1fc88d96c120ca'
SEALED='dbd7994bc11353b841aed5423c03292c41858767800adfdfc5103d88b9fec0ae'
SCHEMA='riverstone.roof.normal_split_sidecar.v1'
def output(name,obj):
 (OUT/name).write_text(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n')
def qspec(q):
 g=[[round(v/P) for v in p] for p in q];lo=[min(p[i] for p in g) for i in range(3)];hi=[max(p[i] for p in g) for i in range(3)];axis=next(i for i in range(3) if lo[i]==hi[i]);n=cross(sub(g[1],g[0]),sub(g[2],g[0]));sign=1 if n[axis]>0 else -1;u,v=[i for i in range(3) if i!=axis];return lo,hi,axis,sign,u,v

def rect(q,spec,a0,b0,a1,b1):
 lo,hi,axis,sign,u,v=spec;new=[]
 for p in q:
  c=list(p);c[u]=(a0 if round(p[u]/P)==lo[u] else a1)*P;c[v]=(b0 if round(p[v]/P)==lo[v] else b1)*P;new.append(c)
 return new

def faces(spec):
 lo,hi,axis,sign,u,v=spec
 for a in range(lo[u],hi[u]):
  for b in range(lo[v],hi[v]):
   c=[0,0,0];c[axis]=lo[axis]-(sign>0);c[u]=a;c[v]=b;yield a,b,tuple(c)

def main():
 started=time.monotonic();render=R3/'roof_repaired.render.json.gz';assert sha(render)==R3PIN
 sealed=R3/'normal_diagnostic_r01/normal_sidecar.json';assert sha(sealed)==SEALED
 inputpaths=[render,sealed,R3/'upper_union_arrays.npz',R3/'delta_ownership_arrays.npz',R3/'compile.json',R2/'roof_patch.master.json.gz',R2/'plan.json',R2/'compile.json'];pins={str(p.relative_to(ROOT)):sha(p) for p in inputpaths}
 master=read(R2/'roof_patch.master.json.gz');ops={op['id']:op for c in master['components'] for op in c['operations']};links={l['operation']:l for l in read(R2/'plan.json')['tile_source_links']};tiles={s:SourceTile(ops[s],links[s]) for s in SELECTED}
 x0=min(t.x0 for t in tiles.values());x1=max(t.x1 for t in tiles.values());z0=min(t.z0 for t in tiles.values());z1=max(t.z1 for t in tiles.values());meta={};candidates={};specs={};needs=set()
 for gi,qi,mat,q in stream_quads(render,meta):
  if not mat.startswith('top_tile_') or max(p[0] for p in q)<x0-P or min(p[0] for p in q)>x1+P or max(p[2] for p in q)<z0-P or min(p[2] for p in q)>z1+P:continue
  key=(gi,qi);candidates[key]=(mat,q);sp=qspec(q);specs[key]=sp
  for a,b,c in faces(sp):needs.add(c)
 union=np.load(R3/'upper_union_arrays.npz');arr=union['materials'];origin=union['origin_cell_xyz'].tolist();names=union['material_names'].tolist();ids={n:i for i,n in enumerate(names)}
 def material(c):
  x,y,z=c;return int(arr[y-origin[1],x-origin[0],z-origin[2]])
 owners={};zmin=min(c[2] for c in needs);zmax=max(c[2] for c in needs);loaded=[]
 for rec in read(R2/'compile.json')['chunks']:
  low,high=rec['owned_z_cells']
  if high<=zmin or low>zmax:continue
  p=ROOT/rec['compiled']['path'];assert sha(p)==rec['compiled']['sha256'];pins[str(p.relative_to(ROOT))]=sha(p);c=read(p);loaded.append(rec['index'])
  for row in c['cells']:
   cell=tuple(row[:3])
   if cell in needs and material(cell)==ids[row[5]]:owners[cell]=row[6]
  del c;gc.collect()
 delta=read(R3/'compile.json')['delta'];dp=ROOT/delta['path'];assert sha(dp)==delta['sha256'];pins[str(dp.relative_to(ROOT))]=sha(dp);dc=read(dp)
 for row in dc['cells']:
  cell=tuple(row[:3])
  if cell in needs and material(cell)==ids[row[5]]:
   assert owners.get(cell) not in SELECTED,'R3 delta overwrites selected measured source';owners[cell]=row[6]
 del dc;gc.collect()
 patches=[];splits=[];expected={};patch_expected={};proof=[];whole_face_count=split_safe_faces=split_cardinal_faces=original_split_faces=0;sourcecounts=collections.Counter();preservedcounts=collections.Counter();skipcounts=collections.Counter();untouched_selected_quads=0
 for key,(mat,q) in candidates.items():
  sp=specs[key];lo,hi,axis,sign,u,v=sp;fs=list(faces(sp));fids={owners.get(c) for a,b,c in fs}
  if not fids.intersection(SELECTED):continue
  for a,b,c in fs:
   nc=list(c);nc[axis]+=sign;assert material(c)==ids[mat] and material(nc)<0,'Face not current exact exterior'
  if len(fids)==1:
   fid=next(iter(fids));res,why=tiles[fid].classify(q,[c for a,b,c in fs],axis,sign)
   if res:
    n,seg=res;patch={'group_index':key[0],'quad_index':key[1],'normals':[[round(t,10) for t in n] for _ in range(4)],'source_tile_id':fid,'classification':'analytic_top_staircase'};patches.append(patch);patch_expected[key]=patch;whole_face_count+=len(fs);sourcecounts[fid]+=len(fs);continue
  else:why='mixed_or_unproven_tile_ownership'
  labels={};safe=0;cn=[0,0,0];cn[axis]=sign
  for a,b,c in fs:
   fid=owners.get(c,'unknown_current_union_owner');source_normal=None
   if fid in SELECTED:
    uq=rect(q,sp,a,b,a+1,b+1);res,reason=tiles[fid].classify(uq,[c],axis,sign)
    if res:source_normal,seg=res
   if source_normal is None:label=(fid,'preserved_cardinal',tuple(cn));preservedcounts[fid]+=1
   else:label=(fid,'analytic_top_staircase',tuple(round(t,10) for t in source_normal));safe+=1
   labels[(a,b)]=label
  if not safe:skipcounts[why]+=1;untouched_selected_quads+=1;continue
  expected[key]=labels;used=set();out=[];safe_rects=0
  for a,b,c in fs:
   if (a,b) in used:continue
   label=labels[(a,b)];b1=b+1
   while b1<hi[v] and (a,b1) not in used and labels[(a,b1)]==label:b1+=1
   a1=a+1
   while a1<hi[u] and all((a1,x) not in used and labels[(a1,x)]==label for x in range(b,b1)):a1+=1
   used.update((x,y) for x in range(a,a1) for y in range(b,b1));fid,classification,n=label
   out.append({'corners':rect(q,sp,a,b,a1,b1),'normals':[list(n) for _ in range(4)],'source_tile_id':fid,'classification':classification});safe_rects+=classification=='analytic_top_staircase'
  assert len(used)==len(fs)
  splits.append({'group_index':key[0],'quad_index':key[1],'material':mat,'quads':out});split_safe_faces+=safe;split_cardinal_faces+=len(fs)-safe;original_split_faces+=len(fs)
  for (a,b),label in labels.items():
   if label[1]=='analytic_top_staircase':sourcecounts[label[0]]+=1
  proof.append({'group_index':key[0],'quad_index':key[1],'original_skip_reason':why,'original_unit_faces':len(fs),'safe_unit_faces':safe,'preserved_unit_faces':len(fs)-safe,'replacement_subquads':len(out),'analytic_subquads':safe_rects})
 side={'schema':SCHEMA,'render_sha256':R3PIN,'patches':patches,'splits':splits,'diagnostic_only':True,'production_gate_open':False,'geometry_invariant':'exact coplanar area-preserving lattice partition; vertex/index representation changes; no displacement','unchanged_materials_sha256':hashlib.sha256(json.dumps(meta['materials'],sort_keys=True,separators=(',',':')).encode()).hexdigest()}
 side['grid_pitch']=P
 raw=(json.dumps(side,separators=(',',':'),allow_nan=False)+'\n').encode();newquads=sum(len(s['quads']) for s in splits)
 def validate(obj):
  assert obj['schema']==SCHEMA,'schema';assert obj['render_sha256']==R3PIN,'render_sha256';assert obj['grid_pitch']==P,'grid_pitch';seen=set()
  for p in obj['patches']:
   key=(p['group_index'],p['quad_index']);assert key in patch_expected,'unsafe_complete_quad';assert p==patch_expected[key],'unsafe_patch';assert key not in seen,'duplicate_target';seen.add(key)
  for s in obj['splits']:
   key=(s['group_index'],s['quad_index']);assert key in expected,'unknown_split_index';assert key not in seen,'duplicate_target';seen.add(key);mat,oldq=candidates[key];assert s['material']==mat,'wrong_material';sp=specs[key];lo,hi,axis,sign,u,v=sp;covered=set()
   for q in s['quads']:
    corners=q['corners'];assert len(corners)==4 and all(len(p)==3 and all(type(x)in(int,float) and math.isfinite(x) for x in p) for p in corners),'finite_corners'
    assert all(abs(p[axis]/P-lo[axis])<1e-9 for p in corners),'off_plane'
    nq=qspec(corners);nl,nh,na,ns,nu,nv=nq;assert na==axis and ns==sign,'winding';assert all(lo[i]<=nl[i]<=nh[i]<=hi[i] for i in range(3)),'outside_original_rectangle'
    assert corners==rect(oldq,sp,nl[u],nl[v],nh[u],nh[v]),'not_exact_rectangle'
    normals=q['normals'];assert len(normals)==4,'normal_count'
    for n in normals:
     assert len(n)==3 and all(type(x)in(int,float) and math.isfinite(x) for x in n) and abs(dot(n,n)-1)<1e-9,'unit_normal';assert n[axis]*sign>0,'inward_normal'
    for a,b,c in faces(nq):
     uv=(a,b);assert uv not in covered,'overlap';covered.add(uv);fid,classification,normal=expected[key][uv]
     assert q['source_tile_id']==fid,'wrong_feature';assert q['classification']==classification,'unsafe_classification';assert all(max(abs(x-y) for x,y in zip(n,normal))<1e-10 for n in normals),'unsafe_normal'
   assert covered==set(expected[key]),'split_gap'
  return True
 assert validate(side)
 report={'schema':'riverstone.roof.normal_split_audit.v1','render_sha256':R3PIN,'complete_quad_patches':len(patches),'complete_patch_unit_faces':whole_face_count,'split_original_quads':len(splits),'new_subquads':newquads,'new_analytic_subquads':sum(q['classification']=='analytic_top_staircase' for s in splits for q in s['quads']),'new_preserved_cardinal_subquads':sum(q['classification']=='preserved_cardinal' for s in splits for q in s['quads']),'newly_treated_unit_faces':split_safe_faces,'preserved_unit_faces_inside_splits':split_cardinal_faces,'original_split_unit_faces':original_split_faces,'total_treated_unit_faces':whole_face_count+split_safe_faces,'source_feature_count':len(sourcecounts),'per_source_treated_unit_faces':dict(sourcecounts),'untouched_selected_quads':untouched_selected_quads,'untouched_skip_counts':dict(skipcounts),'all_coplanar_no_displacement':True,'all_partitions_exact_integer_unit_face_cover':True,'all_partition_overlaps':0,'all_partition_holes':0,'all_partition_wrong_materials':0,'all_normals_finite_unit_outward':True,'source_inputs':pins,'sealed_sidecar_unchanged':sha(sealed)==SEALED,'frozen_inputs_unchanged':all(sha(ROOT/p)==h for p,h in pins.items()),'expected_json_bytes':len(raw),'prospective_replacement_unindexed_triangle_vertices':newquads*6,'old_replaced_unindexed_triangle_vertices':len(splits)*6,'vertex_count_delta':(newquads-len(splits))*6,'AS_limit_mib':256,'CPU_hard_limit_seconds':45,'requested_CPU_bound_seconds':60,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-started,'compiler_calls':0,'sampler_calls':0,'mesher_calls':0,'GUI_calls':0,'mode':'author' if '--author' in sys.argv else 'audit_only'}
 assert report['frozen_inputs_unchanged']
 output('audit.json',report)
 if '--author' not in sys.argv:
  print(json.dumps({k:v for k,v in report.items() if k not in ('source_inputs','per_source_treated_unit_faces','untouched_skip_counts')},sort_keys=True));return
 assert newquads<3000 or '--approved-count' in sys.argv,'Subquad count requires explicit approval';assert len(raw)<1000000,'Raw sidecar exceeds 1MB'
 tests=[];fixtures=[]
 def negative(name,change,wanted):
  sample={'schema':SCHEMA,'render_sha256':R3PIN,'grid_pitch':P,'patches':[],'splits':[json.loads(json.dumps(splits[0]))]};change(sample);message=None
  try:validate(sample)
  except AssertionError as e:message=str(e)
  assert message==wanted,(name,message,wanted);tests.append({'name':name,'rejected':True,'reason':message});fixtures.append({'name':name,'candidate':sample,'expected_rejection':wanted})
 negative('swapped_render_sha',lambda o:o.update(render_sha256='0'*64),'render_sha256')
 negative('invalid_split_gap',lambda o:o['splits'][0]['quads'].pop(),'split_gap')
 negative('invalid_split_overlap',lambda o:o['splits'][0]['quads'].append(o['splits'][0]['quads'][0]),'overlap')
 axis=specs[(splits[0]['group_index'],splits[0]['quad_index'])][2]
 negative('invalid_split_offplane',lambda o:o['splits'][0]['quads'][0]['corners'][0].__setitem__(axis,o['splits'][0]['quads'][0]['corners'][0][axis]+P),'off_plane')
 negative('wrong_material',lambda o:o['splits'][0].update(material='not_the_original_material'),'wrong_material')
 def unsafe(o):
  q=next(q for q in o['splits'][0]['quads'] if q['classification']=='preserved_cardinal');q['classification']='analytic_top_staircase'
 negative('unsafe_classification',unsafe,'unsafe_classification')
 (OUT/'normal_split_sidecar.json').write_bytes(raw);assert validate(read(OUT/'normal_split_sidecar.json'))
 output('split_partition_proof.json',{'splits':proof,'exact_integer_unit_face_cover':True,'holes':0,'overlaps':0})
 output('rejection_fixtures.json',{'tests':tests,'fixtures':fixtures});report['negative_tests']=tests;report['sidecar_sha256']=sha(OUT/'normal_split_sidecar.json');report['status']='PASS_SOURCE_BOUND_COPLANAR_SPLIT_DIAGNOSTIC';report['sidecar_roundtrip_validated']=True;output('validation.json',report)
 print(json.dumps({'status':report['status'],'sidecar':str(OUT/'normal_split_sidecar.json'),'sidecar_sha256':report['sidecar_sha256'],'new_subquads':newquads,'patches':len(patches),'splits':len(splits),'sidecar_bytes':len(raw),'negative_fixtures_passed':len(tests)},sort_keys=True))
if __name__=='__main__':main()
