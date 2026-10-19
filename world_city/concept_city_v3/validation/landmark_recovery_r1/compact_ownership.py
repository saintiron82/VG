"""New recovery revision. Merge only exact shared-edge convex polygon unions."""
import json,pathlib,math,hashlib,collections
HERE=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def area(p):
 a=p[0];return abs(sum((p[i][0]-a[0])*(p[i+1][1]-a[1])-(p[i][1]-a[1])*(p[i+1][0]-a[0]) for i in range(1,len(p)-1)))/2

def hull(points):
 p=sorted(set(tuple(x) for x in points))
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 def side(seq):
  q=[]
  for x in seq:
   while len(q)>1 and cross(q[-2],q[-1],x)<=1e-13:q.pop()
   q.append(x)
  return q
 return [list(x) for x in side(p)[:-1]+side(p[::-1])[:-1]]

def compact(records):
 polys=[{'polygon_xz_m':r['polygon_xz_m'],'group_id':r['group_id'],'source_mask_ids':[r['owner_id']]} for r in records];rounds=[];excess=0.
 for step in range(24):
  index=collections.defaultdict(list)
  for i,r in enumerate(polys):
   p=r['polygon_xz_m']
   for a,b in zip(p,p[1:]+p[:1]):index[tuple(sorted([tuple(a),tuple(b)]))].append(i)
  used=set();out=[];merged=0
  for edge,ids in index.items():
   if len(ids)!=2:continue
   a,b=ids
   if a in used or b in used or polys[a]['group_id']!=polys[b]['group_id']:continue
   p,q=polys[a]['polygon_xz_m'],polys[b]['polygon_xz_m'];h=hull(p+q);delta=area(h)-area(p)-area(q)
   if abs(delta)>1e-11:continue
   used.update((a,b));merged+=1;excess+=max(0,delta)
   out.append({'polygon_xz_m':h,'group_id':polys[a]['group_id'],'source_mask_ids':polys[a]['source_mask_ids']+polys[b]['source_mask_ids']})
  out.extend(p for i,p in enumerate(polys) if i not in used);rounds.append({'before':len(polys),'merges':merged,'after':len(out)});polys=out
  if not merged:break
 return polys,rounds,excess
source=HERE/'recovered_rendered_profiles.json';d=json.loads(source.read_text());oldreport=json.loads((HERE/'recovery_report.json').read_text());polys,rounds,excess=compact(d['approaches']['masks'])
for i,r in enumerate(polys):r.update(owner_id='RECOVERED_COMPACT_RAMP:'+str(i),kind='landmark_ramp_hole',priority=18,render_land=False)
d['approaches']['masks']=polys;d['provenance']['compact_revision']={'previous_data_sha256':sha(source),'script_sha256':sha(pathlib.Path(__file__)),'method':'Only exact shared endpoint pairs; convex hull area equals component sum within 1e-11 m² per operation. No XY snapping or triangle height changes.','accumulated_positive_roundoff_area_m2':excess,'rounds':rounds}
d['limits'].append('Original public masks retain the baseline preview-filter micro-gap; explicit area ledger is in the recovery report. This is not a watertight collision claim.')
p=HERE/'recovered_rendered_profiles_r2.json';p.write_text(json.dumps(d,separators=(',',':'))+'\n')
ramp_tri_area=sum(area(t['polygon_xz_m']) for t in d['approaches']['triangles']);ramp_mask_area=sum(area(m['polygon_xz_m']) for m in polys);landing_tri_area=sum(area(t['polygon_xz_m']) for t in d['landings']['triangles']);landing_mask_area=sum(area(m['polygon_xz_m']) for m in d['landings']['masks'])
report=dict(oldreport);report.update(schema='riverstone.recovered_profiles.exact_render_comparison.r2',status='pass_exact_baseline_triangle_recovery_with_preserved_public_mask_residual',data={'path':str(p.relative_to(ROOT)),'sha256':sha(p)},previous_failed_strict_area_report_sha256=sha(HERE/'recovery_report.json'),compact_ramp_mask_count=len(polys),exact_rendered_triangle_arrays_unchanged=d['approaches']['triangles']==json.loads(source.read_text())['approaches']['triangles'] and d['landings']['triangles']==json.loads(source.read_text())['landings']['triangles'],robust_local_area_m2={'ramps_triangles':ramp_tri_area,'ramps_masks':ramp_mask_area,'landings_triangles':landing_tri_area,'landings_retained_masks':landing_mask_area},public_mask_minus_triangle_area_m2=landing_mask_area-landing_tri_area,ramp_compaction_area_delta_m2=ramp_mask_area-ramp_tri_area,compaction=d['provenance']['compact_revision'],ownership_status='Actual ramp triangle union compacted without XY snapping. Original 34 public masks preserved with measured tiny missing rendered area; no watertight claim.')
assert report['exact_rendered_triangle_arrays_unchanged'] and abs(ramp_mask_area-ramp_tri_area)<1e-7 and excess<1e-7
rp=HERE/'recovery_report_r2.json';rp.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','data','compact_ramp_mask_count','robust_local_area_m2','public_mask_minus_triangle_area_m2','ramp_compaction_area_delta_m2']},indent=2));print('REPORT_SHA',sha(rp))
