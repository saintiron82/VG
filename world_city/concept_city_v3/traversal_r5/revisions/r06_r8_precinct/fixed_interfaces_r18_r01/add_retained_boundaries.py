"""Exact existing-plane constraints at repair/retained-road overlap domains."""
import copy,hashlib,json,math,pathlib,sys,time
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3'
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def clean(p):
 out=[]
 for q in p:
  if not out or math.dist(out[-1],q)>1e-10:out.append(q)
 if len(out)>1 and math.dist(out[0],out[-1])<=1e-10:out.pop()
 return out if len(out)>=3 and a.geo.polygon_area(out)>1e-10 else []
def subtract(p,cut):return [q for s in a.geo.convex_difference(p,cut)if(q:=clean(s))]
def union_parts(parts):
 out=[];idx=a.geo._SpatialIndex(8)
 for raw in parts:
  todo=[clean(raw)];todo=[p for p in todo if p]
  for i in idx.candidates(raw):todo=[p for q in todo for p in subtract(q,out[i])]
  for p in todo:idx.add(len(out),p);out.append(p)
 return out

def main():
 start=time.monotonic();base=read(H/'fixed_interfaces.json');pp=H.parent/'public_corridor_priorities_r01/priorities.json';prior=read(pp);ss=H.parent/'network_batch_r01/evidence/summary.json';summary=read(ss);passed={r['road_id']for r in summary['road_corridor_results']if r['both_directions_pass']};rows=[]
 for pair in prior['full_width_shared_domains']:
  if pair['a_is_regeneration_candidate']==pair['b_is_regeneration_candidate']or not(set(pair['roads'])&passed):continue
  parts=union_parts([q['polygon_xz_m']for q in pair['raw_overlap_parts']]);rows.append({'roads':pair['roads'],'polygons_xz_m':parts})
 assert len(rows)==42
 scene=a.load_scene();windows=[p for r in rows for p in r['polygons_xz_m']];index=a.TriangleIndex(scene,windows)
 regions=[];checks=[];seen=set()
 for row in rows:
  masks=row['polygons_xz_m'];covered=[];missing=[];count=0;pairname='|'.join(row['roads'])
  for mi,p in enumerate(masks):
   hits=list(index.covering(p));cuts=[]
   for r in hits:
    poly=clean(r['intersection_polygon_xz_m'])
    if not poly:continue
    cuts.append(poly);key=(r['material'],r['triangle_index'],tuple(tuple(v)for v in poly))
    if key in seen:continue
    seen.add(key);count+=1;id='RETAINED_ROAD:'+pairname+':'+str(mi)+':'+r['material']+':'+str(r['triangle_index'])
    regions.append(dict(id=id,polygon_xz_m=poly,plane_y_xz_m=r['plane_y_xz_m'],kind='actual_retained_corridor_overlap',roads=row['roads'],triangle_xyz_m=r['vertices_xyz_m'],source=dict(path=str(a.SCENE_PATH.relative_to(ROOT)),material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256']),derivation='Exact convex traffic-overlap clipped to the preserved actual source triangle; heights use that same plane.'))
   rem=[p]
   for c in cuts:rem=[q for r in rem for q in subtract(r,c)]
   missing.extend(rem);covered.extend(cuts)
  expected=sum(a.geo.polygon_area(p)for p in masks);actual=sum(a.geo.polygon_area(p)for p in covered);gap=sum(a.geo.polygon_area(p)for p in missing)
  checks.append(dict(roads=row['roads'],exact_traffic_overlap_area_m2=expected,actual_source_covered_area_m2=actual,uncovered_area_m2=gap,positive_area_overlap_m2=max(0,actual+gap-expected),fixed_region_count=count,uncovered_polygons_xz_m=missing))
 base['regions']+=regions
 # Source accepted-runtime evidence is explicit rather than inferred from old active:false producer fields.
 extra=[pp,ss,a.SCENE_PATH,pathlib.Path(a.__file__),CITY/'traversal_r5/revisions/r04_r6_winding/freeze_manifest.json',CITY/'traversal_r5/revisions/r05_r7_working_ranges/freeze_initial_result.json',H/'fixed_interfaces.json',pathlib.Path(__file__)]
 base['sources']+=[ref(p)for p in extra];base['retained_corridor_review']={'road_pair_count':len(rows),'fixed_region_count':len(regions),'indexed_actual_triangles':len(index.rows),'checks':checks,'above_12_percent_regions':[{'id':r['id'],'grade':math.hypot(*r['plane_y_xz_m'][:2]),'source':r['source']}for r in regions if math.hypot(*r['plane_y_xz_m'][:2])>.12+1e-7], 'scope':'These exact retained-source planes are constraints, including any old steep face. Missing source is explicit; no floor is invented. Actual native/deck masks can explain some source-only holes and need separate owner accounting.'}
 base['fixed_gradient_review']['above_12_percent']+=base['retained_corridor_review']['above_12_percent_regions']
 base['fixed_gradient_review']['maximum']=max(base['fixed_gradient_review']['maximum'],max((math.hypot(*r['plane_y_xz_m'][:2])for r in regions),default=0))
 for src in base['sources']:assert sha(ROOT/src['path'])==src['sha256'],src['path']
 with(H/'fixed_interfaces_complete.json').open('x')as f:json.dump(base,f,separators=(',',':'),allow_nan=False);f.write('\n')
 report={'output':ref(H/'fixed_interfaces_complete.json'),'retained_pairs':len(rows),'new_regions':len(regions),'total_regions':len(base['regions']),'segments':len(base['segments']),'exclusions':len(base['exclusions']),'above12':len(base['retained_corridor_review']['above_12_percent_regions']),'max_grade':base['fixed_gradient_review']['maximum'],'source_missing_area_m2':sum(r['uncovered_area_m2']for r in checks),'source_overlap_area_m2':sum(r['positive_area_overlap_m2']for r in checks),'seconds':time.monotonic()-start}
 with(H/'extraction_report.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
