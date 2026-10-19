#!/usr/bin/env python3
"""Read-only point-predicate replay of existing source definitions; no compilation."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
import json,gzip,csv,math,itertools,collections,time,sys,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;A=O.parent;ROOT=next(p for p in A.parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(ROOT))
from voxel_character.common import core
P=.03125
def read(p):
 with gzip.open(p,'rt') if str(p).endswith('.gz') else open(p) as f:return json.load(f)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 t=time.monotonic();cpu=time.process_time();src=O/'authored_footprint_backing.csv';pins={str(src.relative_to(ROOT)):sha(src),str(Path(core.__file__).relative_to(ROOT)):sha(Path(core.__file__))};rows=list(csv.DictReader(src.open()));queries=[];masters={};prepared={};opsbyid={}
 for rev in ['roof_repair_r02','roof_repair_r03']:
  p=A/rev/'roof_patch.master.json.gz';pins[str(p.relative_to(ROOT))]=sha(p);m=read(p);assert len(m['instances'])==1 and 'transform' not in m['instances'][0];masters[rev]=m;prepared[rev]=[]
  for c in m['components']:
   for op in c['operations']:
    shape=core.prepare_shape(op['shape'],P);placement=core.transform(op.get('transform'));lo,hi=core.shape_bounds(shape);cs=[core.apply(placement,q) for q in itertools.product(*zip(lo,hi))];wl=[min(q[k] for q in cs) for k in range(3)];wh=[max(q[k] for q in cs) for k in range(3)];prepared[rev].append((op,shape,placement,wl,wh));opsbyid[op['id']]=(shape,placement)
 for r in rows:
  x=int(r['grid_x']);z=int(r['grid_z']);fid=r['expected_tile'];rev='roof_repair_r03' if fid.startswith('shadow_extension_') else 'roof_repair_r02';ytop=float(r['analytic_tile_top_world_y']);y=math.floor(ytop/P-.5-1e-8);p=[(n+.5)*P for n in [x,y,z]];shape,placement=opsbyid[fid]
  assert core.contains(shape,core.inverse(placement,p),epsilon=P*core.EPS), (fid,p)
  current=None;events=[];expected_seen=False;overwritten_by=None;erased_by=None
  for op,shape,placement,lo,hi in prepared[rev]:
   if not all(lo[k]-1e-10<=p[k]<=hi[k]+1e-10 for k in range(3)):continue
   if not core.contains(shape,core.inverse(placement,p),epsilon=P*core.EPS):continue
   if op['action']=='paint':
    if current and current['feature']==fid and op['id']!=fid:overwritten_by=op['id']
    current={'instance':masters[rev]['instances'][0]['id'],'component':masters[rev]['components'][0]['id'],'part':op['part'],'material':op['material'],'feature':op['id']};events.append({'action':'paint','operation':op['id']});expected_seen|=op['id']==fid
   elif current is not None and core.selector_matches(op.get('selector',{}),current):
    if expected_seen:erased_by=op['id']
    events.append({'action':'cut','operation':op['id'],'removed_feature':current['feature']});current=None
  final=current['feature'] if current else None
  queries.append({'point_grid_xyz':[x,y,z],'world_center':p,'expected_source_tile':fid,'source_revision':rev,'distance_band':r['distance_band'],'whole_XZ_cell_inside':r['whole_XZ_cell_inside']=='True','analytic_expected_contains':True,'expected_paint_seen':expected_seen,'later_overwriting_feature':overwritten_by,'later_erasing_cut':erased_by,'ordered_source_final_feature':final,'events':events})
 look={(q['source_revision'],tuple(q['point_grid_xyz'])):q for q in queries}
 for rev in masters:
  path=A/rev/'compile.json';pins[str(path.relative_to(ROOT))]=sha(path);comp=read(path);records=[r['compiled'] for r in comp['chunks']] if rev.endswith('02') else [comp['delta']]
  for rec in records:
   p=ROOT/rec['path'];pins[str(p.relative_to(ROOT))]=sha(p);assert pins[str(p.relative_to(ROOT))]==rec['sha256'];d=read(p)
   for row in d['cells']:
    q=look.get((rev,tuple(row[:3])))
    if q is not None:q['cached_compiled_feature']=row[6]
 for q in queries:q.setdefault('cached_compiled_feature',None)
 mismatches=[q for q in queries if q['cached_compiled_feature']!=q['ordered_source_final_feature']];assert not mismatches
 causes=collections.Counter('later_neighbor_overpaint_then_feature_cut' if q['later_overwriting_feature'] and q['later_erasing_cut'] and q['ordered_source_final_feature'] is None else 'other' for q in queries)
 report={'schema':'riverstone.roof.source_order_point_audit.r1','source_dependencies':pins,'scope':'One analytically source-contained upper lattice-center witness per 1781 current backing XZ columns inside authored footprint. Read-only point predicate queries, not a cell sampler or compiler.','query_count':len(queries),'cause_counts':dict(causes),'all_analytic_expected_contains':all(q['analytic_expected_contains'] for q in queries),'all_expected_paints_seen':all(q['expected_paint_seen'] for q in queries),'ordered_source_final_exactly_matches_cached_compiled_feature':not mismatches,'by_boundary_distance':dict(collections.Counter(q['distance_band'] for q in queries)),'examples':queries[:3]+[q for q in queries if q['distance_band']=='>2P'],'sampler_calls':0,'compiler_calls':0,'geometry_changes':0,'all_pinned_inputs_unchanged':all(sha(ROOT/k)==v for k,v in pins.items()),'elapsed_seconds':time.monotonic()-t,'cpu_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 assert report['all_pinned_inputs_unchanged'];(O/'source_ordering_witnesses.json').write_text(json.dumps({'queries':queries},separators=(',',':'))+'\n');(O/'source_ordering_audit.json').write_text(json.dumps(report,indent=2)+'\n');assert sum(p.stat().st_size for p in O.iterdir() if p.is_file())<2*1024**2;print(json.dumps({k:v for k,v in report.items() if k not in ['source_dependencies','examples']},indent=2))
if __name__=='__main__':main()
