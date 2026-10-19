"""Original common core + common greedy mesher, exact bounded diagnostic slabs.

Full43k-run master is unchanged. cell_bounds limits evaluation only. Artificial
slab caps cannot survive ownership clipping because each slab includes1-cell
source halo. No sampler or mesher is reimplemented here.
"""
import argparse,fcntl,gzip,hashlib,json,os,resource,shutil,sys,time
from pathlib import Path
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(ROOT))
from voxel_character.common import core,render_data
HERE=Path(__file__).resolve().parent;PITCH=.125;H=HERE.parents[1]/'house_rules'
# Resolve the shared original budget reader without mutating its contract.
H=ROOT/'world_city/concept_city_v3/near_detail_r01/city_upgrade/house_rules';sys.path.insert(0,str(H));from output_reservations_v3 import ReservationBook
cfg=json.load(open(H/'shared_output_budget.v2.json'));book=ReservationBook(ROOT/cfg['book_path'],ROOT,[ROOT/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)}
def load(p):return json.loads(gzip.decompress(Path(p).read_bytes()) if str(p).endswith('.gz') else Path(p).read_bytes())
def guard(additional=0):
 owned=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file());status=book.inspect()
 assert owned+additional<=20_000_000,'Diagnostic20MB cap'
 assert status['reserved_total_bytes']+20_000_000<=350_000_000,'Shared350MB+explicit diagnostic reservation cap'
 assert status['disk_free_after_active_caps_bytes']-20_000_000>=1073741824,'Minimum1GiB spare after all caps'
 return status

def save(path,obj):
 data=json.dumps(obj,separators=(',',':'),allow_nan=False).encode();raw=gzip.compress(data,mtime=0) if str(path).endswith('.gz') else data;guard(len(raw));assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp');tmp.write_bytes(raw);tmp.replace(path)

def owned_quad(q,y0,y1):
 # Source coordinates are multiples of pitch; preserve vertex winding.
 if max(p[1] for p in q)-min(p[1] for p in q)<1e-9:
  a=[q[1][j]-q[0][j] for j in range(3)];b=[q[2][j]-q[0][j] for j in range(3)];normal_y=a[2]*b[0]-a[0]*b[2];cell_y=round(q[0][1]/PITCH)-(1 if normal_y>0 else 0)
  return q if y0<=cell_y<y1 else None
 lo=max(min(p[1] for p in q),y0*PITCH);hi=min(max(p[1] for p in q),y1*PITCH)
 if hi-lo<1e-9:return None
 return [[p[0],max(lo,min(hi,p[1])),p[2]] for p in q]

def run(max_slabs,seconds):
 start=time.monotonic();guard();arrays=np.load(HERE/'image_derived_arrays.npz');occ=arrays['occupancy'];mats=arrays['materials'];master=load(HERE/'image_derived.master.json.gz');identity={'master':ref(HERE/'image_derived.master.json.gz'),'arrays':ref(HERE/'image_derived_arrays.npz'),'core':ref(core.__file__),'renderer':ref(render_data.__file__),'mesher':ref(render_data.mesh.__file__),'driver':ref(__file__),'pitch':PITCH,'source_shapes_cropped':False};signature=core.digest(identity);done=[];new=0
 for k,y0 in enumerate(range(0,112,4)):
  y1=min(112,y0+4);cp=HERE/'slabs'/f'{k:03d}.compiled.json.gz';rp=HERE/'slabs'/f'{k:03d}.render.json.gz';sp=HERE/'slabs'/f'{k:03d}.stats.json'
  if sp.exists():
   s=load(sp);assert s['signature']==signature and s['compiled']['sha256']==sha(cp) and s['render']['sha256']==sha(rp);done.append(s);continue
  if max_slabs and new>=max_slabs:break
  if time.monotonic()-start>seconds-6:break
  t=time.monotonic();compiled=core.compile_master(master,{'pitch':PITCH},cell_bounds={'min':[-48,max(0,y0-1),-40],'max':[48,min(112,y1+1),40]},max_candidate_cells=150000,max_output_cells=100000);tc=time.monotonic()
  owned=[r for r in compiled['cells'] if y0<=r[1]<y1];expected={(int(xx-48),int(yy+y0),int(zz-40)):int(mats[yy+y0,xx,zz]) for yy,xx,zz in np.argwhere(occ[y0:y1])};actual={(r[0],r[1],r[2]):int(r[5].split('_')[1]) for r in owned};assert actual==expected,'Actual common cell positions/materials differ from image-derived source runs'
  render=render_data.make_render_data(compiled);tm=time.monotonic();groups=[]
  for g in render['groups']:
   qs=[v for q in g['quads'] if (v:=owned_quad(q,y0,y1)) is not None]
   if qs:groups.append({'material':g['material'],'quads':qs})
  render['groups']=groups;render['quad_count']=sum(len(g['quads']) for g in groups);render['ownership']={'cell_y_min':y0,'cell_y_max':y1,'halo_cells':1,'only_original_exterior_faces':True};save(cp,compiled);save(rp,render)
  s={'slab':k,'y_cells':[y0,y1],'signature':signature,'identity':identity,'compiled':ref(cp),'render':ref(rp),'owned_cell_count':len(owned),'owned_cells_hash':core.digest(owned),'quads':render['quad_count'],'common_sample_seconds':tc-t,'common_mesh_seconds':tm-tc,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'exact_mask_source_cell_match':True};save(sp,s);done.append(s);new+=1;print(json.dumps({'slab':k,'sample_seconds':s['common_sample_seconds'],'mesh_seconds':s['common_mesh_seconds'],'total_seconds':s['elapsed_seconds'],'peak_rss_kib':s['peak_rss_kib'],'owned_cells':len(owned),'quads':s['quads']}),flush=True)
  assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<256*1024,'256MiB peak target exceeded; pause rather than silently increase'
  del compiled,render,owned,expected,actual
 result={'signature':signature,'identity':identity,'complete':len(done)==28,'slabs':len(done),'new_slabs':new,'session_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'all_owned_cell_count':sum(s['owned_cell_count'] for s in done),'all_common_cell_matches':all(s['exact_mask_source_cell_match'] for s in done),'all_quad_count':sum(s['quads'] for s in done),'budget':guard()};target=HERE/'sessions'/f'session_{len(list((HERE/"sessions").glob("*.json"))) if (HERE/"sessions").exists() else 0:03d}.json';save(target,result);print(json.dumps({k:result[k] for k in ['complete','slabs','new_slabs','session_seconds','peak_rss_kib','all_owned_cell_count','all_quad_count']}),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--max-slabs',type=int,default=0);p.add_argument('--seconds',type=float,default=120);q=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,384*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(180,180));lock=open(HERE/'diagnostic_writer.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(q.max_slabs,q.seconds)
