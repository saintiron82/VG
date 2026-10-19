"""Resumable measured small batches, frozen source masks -> common geometry.
Completed module records are immutable and exact-input pinned. R03 explicitly excludes joint-only degenerate tiny tips; no validator relaxation. R02 adds an exact convex-owner containment shortcut before the identical union oracle; original r01 records remain explicitly recognized. New artifacts
use the already supported deterministic gzip JSON transport, not a new format.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,importlib.util,json,os,resource,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
q=load('e7_mask_prepare',H/'prepare.py');p=q.p;a=q.a;b=q.b;R=q.R;N=q.N;P=q.P
crop=load('frozen_common_crop',N/'expansion_r06/training_partial_crop_r01/build.py')
rio=load('frozen_gzip_transport',b.U/'facility_openings/batch_r01/sampler_v2/reserved_io_r02.py')
LIMIT=8*1024*1024;TOTAL_SECONDS=240
CACHES=[N/'expansion_r04/combined/module_catalog_r03_plus_r04.json',N/'expansion_r04/extrusion_support_r01/modules/catalog.json',N/'expansion_r04/extrusion_support_r02/modules/catalog.json',N/'expansion_r05/first_e7_e1/modules/catalog.json']
def trimkey(seed,trim):return (seed,trim['width_m'],trim['height_m'],*trim['offset_m'])
def geometry_bytes():return sum(f.stat().st_size for f in (H/'modules').glob('*.gz'))
def read(path):return json.loads(gzip.decompress(Path(path).read_bytes())if str(path).endswith('.gz')else Path(path).read_bytes())
def specification():
 masks=q.read(H/'prepared_masks.json');known={};cachedeps={}
 for cp in CACHES:
  cachedeps[str(cp.relative_to(R))]=q.sha(cp)
  for row in read(cp)['modules']:
   if row['kind']=='paving':known[trimkey(row['seed'],row['trim'])]=row
 demands={};placements=[]
 for g in masks['grids']:
  x,y,z,w=g['bbox_cells_xy'];trim={'width_m':(z-x)*P,'height_m':(w-y)*P,'offset_m':[x*P,y*P]};cached=known.get(trimkey(g['seed'],trim))if g['rectangular']else None
  token=cached['id']if cached else 'paving_mask_'+str(g['seed'])+'_'+g['mask_sha256'][:16]
  if token not in demands:demands[token]={'id':token,'seed':g['seed'],'cached':copy.deepcopy(cached),'mask_sha256':g['mask_sha256'],'allowed_cell_runs_xy':g['allowed_cell_runs_xy'],'forbidden_cell_runs_xy':g['forbidden_cell_runs_xy'],'example_grid':g['grid_xy_m']}
  offset=trim['offset_m']if cached else [0,0];placements.append({'grid':g,'module_key':token,'module_offset_xy_m':offset})
 return masks,demands,placements,cachedeps

def validate_source_runs(g,asset):
 owners=[q.e.fp(o['polygon_uv_m'])for o in asset['source_polygon_owners']if o['operation']in g['source_owner_ids']];source=read(R/asset['source_render_path']);quads=[q.e.fp([[v[0],-v[2]]for v in source['groups'][gi]['quads'][qi]])for gi,qi in g['source_face_refs']];cuts=[q.e.fp(c['polygon_uv_m'])for c in asset['source_component_cuts']if not(c['y_interval_m'][1]<0 or c['y_interval_m'][0]>.0375)];xv=q.coords(g['grid_xy_m'][0])[0];yv=q.coords(g['grid_xy_m'][1])[0]
 for x,y,z,w in g['allowed_cell_runs_xy']:
  rect=[xv[x],yv[y],xv[z],yv[w]];subject=p.rectpoly(rect)
  assert any(p.rect_in(rect,p.lines(poly))for poly in owners) or q.e.exact_union(subject,owners)==0
  assert q.e.exact_union(subject,quads)==0
  assert all(q.ad.intersection_area(subject,cut)==0 for cut in cuts)
 return {'all_pass':True,'whole_row_runs':len(g['allowed_cell_runs_xy']),'horizontal_cells':g['safe_cell_count'],'source_quad_union_outside_area_m2':0,'source_walk_union_outside_area_m2':0,'original_cut_positive_overlap_area_m2':0}

def batch(count):
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));assert 1<=count<=16
 masks,demands,places,cachedeps=specification();assert all(q.sha(R/f)==v for f,v in masks['source_dependencies'].items());asset=next(r for r in q.read(q.PLAN)['assets']if r['asset_key']==q.KEY);bygrid={tuple(g['grid_xy_m']):g for g in masks['grids']};prior=list((H/'batches').glob('batch_*.json'));spent=30+sum(read(f)['elapsed_seconds']for f in prior);assert spent<TOTAL_SECONDS,'240 s cumulative compile/verification allowance exhausted';deadline=start+min(27,TOTAL_SECONDS-spent);safe=read(b.U/'surface_modules/inputs/safe_offset_rules.v1.json');safe['trim']={'width_m':1.0,'height_m':1.0,'offset_m':[0.0,0.0]};identity={'prepared_masks':q.ref(H/'prepared_masks.json'),'author':q.ref(Path(__file__)),'common_crop':q.ref(Path(crop.__file__)),'gzip_encoder':q.ref(Path(rio.__file__))};completed=[];skipped=0;largest=0
 for ident,d in demands.items():
  if d['cached']:continue
  record=H/'module_records'/(ident+'.json')
  excluded=H/'excluded_modules'/(ident+'.json')
  if excluded.exists():
   old=read(excluded);assert old['mask_sha256']==d['mask_sha256'] and old['reason']=='COMMON_PAVING_TOP_ABSENT_JOINT_ONLY';continue
  if record.exists():
   old=read(record);assert {k:v for k,v in old['identity'].items()if k!='author'}=={k:v for k,v in identity.items()if k!='author'} and old['identity']['author'] in [q.ref(H/'author.py'),q.ref(H/'author_r02.py'),identity['author']] and old['mask_sha256']==d['mask_sha256'];assert all(q.sha(R/old['module'][k+'_path'])==old['module'][k+'_sha256']for k in ['master','render']);skipped+=1;continue
  if len(completed)>=count or time.monotonic()+max(2,largest*1.5)>deadline:break
  before=time.monotonic();g=bygrid[tuple(d['example_grid'])];source_proof=validate_source_runs(g,asset)
  try:m,c,r,checks=crop.compile_conservative_crop(safe,d['seed'],d['allowed_cell_runs_xy'],d['forbidden_cell_runs_xy'])
  except ValueError as exc:
   if str(exc)!='paving must have exact top Z=0':raise
   q.save(excluded,{'reason':'COMMON_PAVING_TOP_ABSENT_JOINT_ONLY','mask_sha256':d['mask_sha256'],'grid_xy_m':g['grid_xy_m'],'safe_cell_count':g['safe_cell_count'],'safe_area_m2':g['safe_cell_count']*P*P,'source_proof':source_proof,'identity':identity,'candidate_geometry_written':False});print(json.dumps({'excluded':ident,'cells':g['safe_cell_count']}),flush=True);continue
  boundary=crop.exterior_proof(c,r);mp=H/'modules'/(ident+'.master.json.gz');rp=H/'modules'/(ident+'.render.json.gz');mb=rio.encoded(mp,m);rb=rio.encoded(rp,r);rawm=a.common.payload(m);rawr=a.common.payload(r);assert gzip.decompress(mb)==rawm and gzip.decompress(rb)==rawr;assert geometry_bytes()+len(mb)+len(rb)<LIMIT,'8 MiB geometry cap reached before writing';a.common.write_exact(mp,mb);a.common.write_exact(rp,rb)
  module={'id':ident,'kind':'paving','seed':d['seed'],'trim':copy.deepcopy(safe['trim']),'master_path':str(mp.relative_to(R)),'master_sha256':q.sha(mp),'render_path':str(rp.relative_to(R)),'render_sha256':q.sha(rp),'decoded_master_sha256':hashlib.sha256(rawm).hexdigest(),'decoded_render_sha256':hashlib.sha256(rawr).hexdigest(),'payload_hash':c['payload_hash'],'cells':len(c['cells']),'quads':r['quad_count'],'checks':checks,'source_support_mask_sha256':d['mask_sha256'],'transport':'existing_gzip_json','uncompressed_geometry_bytes':len(rawm)+len(rawr)}
  result={'all_pass':True,'identity':identity,'mask_sha256':d['mask_sha256'],'module':module,'source_proof':source_proof,'closed_boundary':boundary,'compressed_geometry_bytes':len(mb)+len(rb),'elapsed_seconds':time.monotonic()-before};q.save(record,result);completed.append(ident);largest=max(largest,result['elapsed_seconds']);print(json.dumps({'completed_new':len(completed),'id':ident,'elapsed_seconds':time.monotonic()-start,'total_geometry_bytes':geometry_bytes()}),flush=True)
 new=[d for d in demands.values()if not d['cached']];done=[d for d in new if(H/'module_records'/(d['id']+'.json')).exists()or(H/'excluded_modules'/(d['id']+'.json')).exists()];duration=time.monotonic()-start;assert duration<30 and spent+duration<TOTAL_SECONDS and geometry_bytes()<LIMIT
 report={'status':'COMPLETE'if len(done)==len(new)else 'BOUNDED_BATCH_COMPLETE_MORE_REMAIN','all_written_modules_valid':True,'whole_candidate_complete':len(done)==len(new),'new_modules_this_batch':len(completed),'new_modules_done':len(done),'new_modules_required':len(new),'cached_unique_modules':sum(bool(d['cached'])for d in demands.values()),'cached_grid_placements':sum(bool(demands[r['module_key']]['cached'])for r in places),'elapsed_seconds':duration,'cumulative_batch_seconds':spent+duration,'failed_batch_charged_seconds':30,'hard_process_seconds':30,'cumulative_limit_seconds':TOTAL_SECONDS,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'geometry_bytes':geometry_bytes(),'geometry_limit_bytes':LIMIT,'immutable_completed_skipped':skipped,'completed_ids':completed,'identity':identity};q.save(H/'batches'/('batch_%03d.json'%(len(prior)+1)),report);print(json.dumps(report),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--count',type=int,default=16);args=ap.parse_args();batch(args.count)
