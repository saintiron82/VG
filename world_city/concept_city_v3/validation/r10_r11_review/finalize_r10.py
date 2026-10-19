import sys,json,pathlib,hashlib,math
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r10_density_reservoir import author as a
g=a.geo

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(pathlib.Path(p).relative_to(ROOT)),sha256=sha(p))
def area(p):
 if len(p)<3:return 0.
 o=p[0];return abs(sum((p[i][0]-o[0])*(p[i+1][1]-o[1])-(p[i][1]-o[1])*(p[i+1][0]-o[0]) for i in range(1,len(p)-1)))/2

def tidy(p):
 out=[]
 for q in p:
  if not out or math.dist(q,out[-1])>1e-12:out.append(q)
 if len(out)>1 and math.dist(out[0],out[-1])<=1e-12:out.pop()
 return out

def partition(rs,b):
 ix=g._SpatialIndex(2)
 for i,r in enumerate(rs):ix.add(i,r['polygon_xz_m'])
 double=sum(area(g.convex_intersection(tidy(r['polygon_xz_m']),tidy(rs[j]['polygon_xz_m']))) for i,r in enumerate(rs) for j in ix.candidates(r['polygon_xz_m']) if j>i)
 return dict(bounds=b,records=len(rs),area_m2=sum(area(r['polygon_xz_m']) for r in rs),pairwise_overlap_m2=double)
inputs=[]
for d in [a.HERE,a.HERE.parent/'r11_ground_materials']:
 seal=json.loads((d/'freeze_manifest.json').read_text());inputs.append(ref(d/'freeze_manifest.json'))
 for f,h in seal['files'].items():assert sha(d/f)==h;inputs.append(ref(d/f))
density=json.loads(a.DENSITY_PATH.read_text());inputs.append(ref(a.DENSITY_PATH));assert sha(a.DENSITY_PATH)==a.DENSITY_SHA
for asset in density['assets'].values():
 for kind in ['render','master','compiled']:
  if kind+'_path' in asset:p=ROOT/asset[kind+'_path'];assert sha(p)==asset[kind+'_sha256'];inputs.append(ref(p))
for f in [a.SOUTH_PATH,ROOT/a.SOUTH['native_bridge']['path'],ROOT/a.SOUTH['native_bridge']['render_path'],H/'check_r11_failed.py',H/'run.log',H/'south_progress.json',H/'b015_progress.json',H/'partition_failure_320_304.json',H/'partition_gap_320_304.json',H/'isolate_partition.py',H/'measure_partition_gap.py']:inputs.append(ref(f))
C=ROOT/'world_city/concept_city_v3';candidate=C/'registered_integration/r4/material_candidate.json';assert sha(candidate)=='2684871a3e975fdbabe287e435b84f8952e57e7e43489b98b46259011924be53';inputs.append(ref(candidate))
s=json.loads((H/'south_progress.json').read_text());b=json.loads((H/'b015_progress.json').read_text());gap=json.loads((H/'partition_gap_320_304.json').read_text());failure=json.loads((H/'partition_failure_320_304.json').read_text())
bs=sorted({tuple(t['bounds']) for t in s['partitions']+b['partitions']});rows=[]
for i,box in enumerate(bs):
 rs=a.surface_domains(box,False);row=partition(rs,box);rows.append(row)
 assert abs(row['area_m2']-256)<1e-6 and row['pairwise_overlap_m2']<1e-6,row
 if i%20==0:print('R10 partition',i+1,'/',len(bs),flush=True)
assert not b['route_errors'] and s['full_width_source_uncovered_m2']==0 and s['maximum_native_seam_error_m']==0
assert gap['uncovered_area_m2']>0.02 and failure['versions']['r11']['pairwise_overlap_m2']>0.7
for f in inputs:assert sha(ROOT/f['path'])==f['sha256']
report=dict(schema='riverstone.independent_r10_native_and_r11_hold.v1',status='r10_bounded_native_and_south_pass_r11_material_subdivision_failed',checker=ref(__file__),inputs=inputs,south=s,b015=b,r10_consumer_partitions=rows,r10_max_area_error_m2=max(abs(r['area_m2']-256) for r in rows),r10_max_pairwise_overlap_m2=max(r['pairwise_overlap_m2'] for r in rows),r11_failure=dict(bounds=gap['bounds'],uncovered_area_m2=gap['uncovered_area_m2'],pairwise_overlap_m2=failure['versions']['r11']['pairwise_overlap_m2'],evidence=ref(H/'partition_failure_320_304.json'),gap_evidence=ref(H/'partition_gap_320_304.json')),retained_r09_caveat=dict(raw_clips=40,unique_clips=39,consumer_duplicate_floor=False,actual_tread_m=.125,maximum_public_edge_step_m=.07088698012788086),limits=['No capsule/cart, full-city navigation or runtime collision claim.','Six southern road surfaces are source/preview triangles; common terrain compile remains pending.','Southern side cut/fill height differences reach0.63612m; no sideways passage or complete retaining-face support approval.','Off-city country-road endpoint is explicit; countryside continuation and painted southern barbican absent.','B015 closed native doors are interaction thresholds, not certified interior passages; slab clearance covers its native groups.','The r11 material subdivision changes actual finite ownership despite unchanged height functions; hold this promotion until a separately audited repair.','Recovered landmark public mask retains1.46416e-6m² known preview-filter residual.'])
p=H/('bound_r10_'+sha(a.HERE/'contract.json')[:12]+'_r11_hold.json');p.write_text(json.dumps(report,indent=2)+'\n');print('REPORT',p,flush=True)
