"""Native material-only layer; frozen coarse volume remains authoritative."""
import os,resource,sys,json,gzip,hashlib,time
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
O=Path(__file__).resolve().parent;A=O.parent
sys.path.insert(0,str(A/'gallery_panel_repair_r01'))
from repair_common import (R,P,core,render_data,np,Image,sha,ref,read,baseline,value,
 partition_quad,faces,expected_faces,stream_render,hash_group_init,hash_quad)
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(110,)*2)
BASE=A/'roof_gallery_integration_r01/gallery_repaired_count_corrected.render.json.gz'
BASE_SHA='ecc62726f063ace31434d5266085c9a4416e1bd214f0b135dddaf1de362d930c'
SOURCE=R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
SOURCE_SHA='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93'
ROI=(1168,216,1240,288);LOW=(40,208,-148);HIGH=(112,280,-147)
CHUNKS=[{'id':f'chunk_{i:02d}','source_local_box':b,'owned_min':[112-b[2],280-b[3],-148],'owned_max':[112-b[0],280-b[1],-147]} for i,b in enumerate([(0,0,36,36),(36,0,72,36),(0,36,36,72),(36,36,72,72)])]
def save(name,v):
 p=O/name;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);b=json.dumps(v,separators=(',',':'),allow_nan=False).encode();p.write_bytes(gzip.compress(b,mtime=0) if str(p).endswith('.gz') else b);assert sum(q.stat().st_size for q in O.rglob('*') if q.is_file())<10_000_000;return ref(p)
def classify(c):
 r,g,b=np.moveaxis(c.astype(float),-1,0);lum=c.mean(2);yy,xx=np.indices(lum.shape);px=1168+xx;py=216+yy;frame=(px>=1176)&(px<1232)&(py>=220)&(py<278);pane=(px>=1184)&(px<1224)&(py>=228)&(py<270)&(b>r*1.05)&(g>r*1.1)&(lum>=20)&(lum<150);wood=frame&(r>=75)&(r-g>=12)&(g-b>=10)&(r>=1.3*b)&(lum>=55);light=~frame&(lum>=160)&((c.max(2).astype(int)-c.min(2).astype(int))<80);labels=np.zeros(lum.shape,np.uint8);labels[light]=1;labels[wood]=2;labels[pane]=3;return labels
def source():
 assert sha(SOURCE)==SOURCE_SHA
 return np.asarray(Image.open(SOURCE).convert('RGB'))[216:288,1168:1240].copy()
def rgbid(rgb):return 'native_rgb_'+''.join(f'{int(c):02x}' for c in rgb)
def inside(p,lo=LOW,hi=HIGH):return all(lo[a]<=p[a]<hi[a] for a in range(3))
def base_materials():
 # Rebuild only frozen palette metadata. Composition checks exact equality with
 # actual persisted base metadata, whose large groups precede the palette.
 m={}
 for path in [A/'foundation_repair_r01/foundation_revised.master.json.gz',A/'roof_repair_r05/roof_patch.master.json.gz',A/'gallery_panel_repair_r01/local_union.master.json.gz']:
  for name,color in read(path)['materials'].items():
   assert name not in m or m[name]==color;m[name]=color
 return m
def full_palette(crop):
 m=base_materials()
 for rgb in np.unique(crop.reshape(-1,3),axis=0):m[rgbid(rgb)]=rgbid(rgb)[11:]
 return m
def source_assignment(crop,labels):
 return {(111-int(x),279-int(y),-148):rgbid(crop[y,x]) for y,x in np.argwhere(labels>0)}
def source_samples(crop,labels,box):
 x0,y0,x1,y1=box
 return [{'source_xy':[1168+x,216+y],'rgb':crop[y,x].tolist(),'label':int(labels[y,x]),'material_id':rgbid(crop[y,x]),'state':'replace_existing_material_only' if labels[y,x] else 'unresolved_keep_existing'} for y in range(y0,y1) for x in range(x0,x1)]
def inherited(a,lo,hi,names):
 return {(x,y,z):names[value(a,(x,y,z))] for y in range(lo[1],hi[1]) for x in range(lo[0],hi[0]) for z in range(lo[2],hi[2]) if value(a,(x,y,z))>=0}
def expected(a,crop,labels,lo,hi):
 names=list(read(A/'foundation_repair_r01/foundation_revised.master.json.gz')['materials']);cells=inherited(a,lo,hi,names)
 for p,m in source_assignment(crop,labels).items():
  if inside(p,lo,hi):assert p in cells;cells[p]=m
 return cells
def make_master(chunk,a,crop,labels):
 lo=[x-1 for x in chunk['owned_min']];hi=[x+1 for x in chunk['owned_max']];materials=full_palette(crop);oldnames=list(read(A/'foundation_repair_r01/foundation_revised.master.json.gz')['materials']);ops=[]
 for y in range(lo[1],hi[1]):
  for x in range(lo[0],hi[0]):
   z=lo[2]
   while z<hi[2]:
    m=value(a,(x,y,z))
    if m<0:z+=1;continue
    z0=z;z+=1
    while z<hi[2] and value(a,(x,y,z))==m:z+=1
    ops.append({'id':f'inherited_x{x}_y{y}_z{z0}_{z}','part':'retained_body','action':'paint','material':oldnames[m],'shape':{'kind':'box','min':[x*P,y*P,z0*P],'max':[(x+1)*P,(y+1)*P,z*P]}})
 assignments=source_assignment(crop,labels)
 for p,m in sorted(assignments.items()):
  if inside(p,lo,hi):
   assert value(a,p)>=0;px=1279-p[0];py=495-p[1];lab=int(labels[py-216,px-1168]);ops.append({'id':f'source_BACK_x{px}_y{py}_label{lab}','part':f'appearance_owner_{lab}','action':'paint','material':m,'shape':{'kind':'box','min':[v*P for v in p],'max':[(v+1)*P for v in p]}})
 return {'schema':core.SCHEMA,'id':f'native_facade_exact_rgb_{chunk["id"]}','revision':1,'grid_origin':[0,0,0],'axes':{'up':'+Y','front':'+Z','right':'+X'},'materials':materials,'components':[{'id':'native_surface_plus_inherited_halo','parts':[{'id':p,'pivot':[0,0,0]} for p in ['retained_body','appearance_owner_1','appearance_owner_2','appearance_owner_3']],'operations':ops}],'instances':[{'id':'actual_BACK_surface','component':'native_surface_plus_inherited_halo'}],'assembly_cuts':[],'constraints':[{'id':'nonempty','kind':'nonempty'}],'metadata':{'base_render':ref(BASE),'source':ref(SOURCE),'contract':ref(A/'native_facade_plan_r01/first_window_contract_r02.json'),'source_roi':ROI,'source_samples_in_owned_chunk':source_samples(crop,labels,chunk['source_local_box']),'owned_bounds_native':{'min':chunk['owned_min'],'max':chunk['owned_max']},'halo_bounds_native':{'min':lo,'max':hi},'surface_pitch_m':P,'preserved_volume_pitch_m':.125,'surface_and_volume_pitch_independent':True,'occupancy_change_forbidden':True,'fixed_palette_ceiling':None,'exact_original_RGB':True,'unresolved_pixels_keep_old_material':True,'diagnostic_only':True,'production_gate_open':False}}
def compile_master(master):return core.compile_master(master,{'pitch':P},max_candidate_cells=10000,max_output_cells=6000)
def cellmap(c):return {tuple(r[:3]):r[5] for r in c['cells']}
