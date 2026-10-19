"""One unchanged common-master bounded evaluation plus exact exterior composition."""
import gzip,hashlib,json,resource,sys,time
from pathlib import Path
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(ROOT));from voxel_character.common import core,render_data
O=Path(__file__).resolve().parent;D=O.parent/'reconstruction_proof_r01';P=.125
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def save(p,o):
 assert not p.exists();b=json.dumps(o,separators=(',',':'),allow_nan=False).encode();p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)
def clip(q,y0,y1):
 if max(p[1] for p in q)-min(p[1] for p in q)<1e-9:
  normal=np.cross(np.array(q[1])-q[0],np.array(q[2])-q[0]);cell=round(q[0][1]/P)-(1 if normal[1]>0 else 0);return q if y0<=cell<y1 else None
 lo=max(min(p[1] for p in q),y0*P);hi=min(max(p[1] for p in q),y1*P)
 return None if hi-lo<1e-9 else [[p[0],max(lo,min(hi,p[1])),p[2]] for p in q]
def mid(m):return int(m.rsplit('_',1)[1])+(12 if m.startswith('stone') else 0)
start=time.monotonic();master=read(O/'foundation_revised.master.json.gz');a=np.load(O/'foundation_arrays.npz');occ=a['occupancy'];mats=a['materials'];oldarrays=np.load(D/'image_derived_arrays.npz');t=time.monotonic();c=core.compile_master(master,{'pitch':P},cell_bounds={'min':[-48,0,-40],'max':[48,11,40]},max_candidate_cells=100000,max_output_cells=100000);sample=time.monotonic()-t;actual={(r[0],r[1],r[2]):mid(r[5]) for r in c['cells']};expected={(int(x-48),int(y),int(z-40)):int(mats[y,x,z]) for y,x,z in np.argwhere(occ[:11])};assert actual==expected;save(O/'foundation_patch.compiled.json.gz',c);t=time.monotonic();local=render_data.make_render_data(c);mesh=time.monotonic()-t;save(O/'foundation_patch.halo.render.json.gz',local);old=read(D/'diagnostic.render.json.gz');groups={};kept=clipped=0
for r,y0,y1 in [(old,10,112),(local,0,10)]:
 for g in r['groups']:
  for q in g['quads']:
   new=clip(q,y0,y1)
   if new is not None:groups.setdefault(g['material'],[]).append(new);kept+=int(new==q);clipped+=int(new!=q)
# Exact actual-cell exterior coverage on all six directions, including interface.
faces=np.full((6,*occ.shape),-1,np.int16);mapping=[1,0,2];offset=[48,0,40];duplicates=0
for material,qs in groups.items():
 for q in qs:
  grid=np.rint(np.asarray(q)/P).astype(int);assert np.max(np.abs(grid*P-q))<1e-9;normal=np.cross(grid[1]-grid[0],grid[2]-grid[0]);axis=int(np.argmax(abs(normal)));sign=1 if normal[axis]>0 else -1;owner=int(grid[0,axis])-(1 if sign>0 else 0);lo=grid.min(0);hi=grid.max(0);sl=[None]*3
  for k in range(3):sl[mapping[k]]=owner+offset[k] if k==axis else slice(int(lo[k]+offset[k]),int(hi[k]+offset[k]))
  view=faces[(2*axis+(sign>0),*sl)];duplicates+=int((view>=0).sum());faces[(2*axis+(sign>0),*sl)]=mid(material)
mismatch=0;unitfaces=0
for axis in range(3):
 k=mapping[axis]
 for sign in (-1,1):
  neigh=np.zeros_like(occ);dst=[slice(None)]*3;src=[slice(None)]*3
  if sign>0:dst[k]=slice(None,-1);src[k]=slice(1,None)
  else:dst[k]=slice(1,None);src[k]=slice(None,-1)
  neigh[tuple(dst)]=occ[tuple(src)];surface=occ&~neigh;wanted=np.where(surface,mats,-1);mismatch+=int((faces[2*axis+(sign>0)]!=wanted).sum());unitfaces+=int(surface.sum())
assert duplicates==0 and mismatch==0;(O/'proof_writer.lock').touch(exist_ok=True);n=sum(len(q) for q in groups.values());r={k:v for k,v in old.items() if k not in ['groups','quad_count','bounds','geometry','provenance']};r.update(source_id=c['source_id'],source_revision=c['source_revision'],master_hash=c['master_hash'],payload_hash=core.digest({'actual_unchanged_upper_payload':old['payload_hash'],'actual_bounded_patch':c['payload_hash'],'ownership_y':[0,10]}),materials=master['materials'],cell_count=int(occ.sum()),groups=[{'material':m,'quads':groups[m]} for m in sorted(groups)],quad_count=n,bounds={'min':[-6,0,-5],'max':[6,13.875,5]},geometry='Original upper common render + newly evaluated measured foundation ROI exterior; exact material unit-face comparison against original upper cells and actual bounded revised cells.',provenance={'original_render':ref(D/'diagnostic.render.json.gz'),'revised_master':ref(O/'foundation_revised.master.json.gz'),'core':ref(Path(core.__file__)),'mesher':ref(Path(render_data.mesh.__file__)),'exporter':ref(Path(render_data.__file__)),'driver':ref(Path(__file__)),'diagnostic_only':True,'production_gate_open':False});save(O/'foundation_repaired.render.json.gz',r)
report={'schema':'riverstone.image_foundation.bounded_composition.v1','technical_tests_pass':True,'diagnostic_only':True,'production_gate_open':False,'render':ref(O/'foundation_repaired.render.json.gz'),'source_contract':ref(O/'source_contract.json'),'compiled_patch':ref(O/'foundation_patch.compiled.json.gz'),'halo_render':ref(O/'foundation_patch.halo.render.json.gz'),'driver':ref(Path(__file__)),'core':ref(Path(core.__file__)),'original_render':ref(D/'diagnostic.render.json.gz'),'actual_local_cells':len(c['cells']),'revised_total_cells':int(occ.sum()),'added_cells':int(a['added'].sum()),'quad_count':n,'unit_faces_checked':unitfaces,'same_direction_duplicate_faces':duplicates,'exterior_material_face_mismatch':mismatch,'artificial_interface_caps':0,'upper_y_ge_1_125_occupancy_material_exact':bool(np.array_equal(occ[9:],oldarrays['occupancy'][9:]) and np.array_equal(mats[9:],oldarrays['materials'][9:])),'all_old_occupied_materials_unchanged':bool(np.array_equal(mats[oldarrays['occupancy']],oldarrays['materials'][oldarrays['occupancy']])),'sample_seconds':sample,'mesh_seconds':mesh,'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'unchanged_kept_quads':kept,'ownership_clipped_quads':clipped,'bounds':r['bounds'],'sampler_calls':1,'source_shapes_cropped':False};save(O/'verification.json',report);print(json.dumps(report),flush=True)
