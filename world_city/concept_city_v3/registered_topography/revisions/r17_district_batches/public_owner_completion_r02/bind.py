"""Bind finite institutional, water and repaired alley public owners."""
import json,math,time
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..public_dependency_review_r01 import review
HERE=Path(__file__).resolve().parent
OLD=a.HERE/'public_dependency_review_r01/actual_public_inputs_r01.json'
WATER=a.HERE/'public_owner_completion_r01/water_owner_binding.json'
RECOVERED=a.CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'
B17=a.HERE.parent/'public_corridors_r18/b17_local_alley_r01/physical_owners.json'
assert a.sha(B17)=='56f143e844d0a154df2e32c96e5e949425fc0df2e330bcef486934301c233a11'
def bind():
 old=json.loads(OLD.read_bytes());water={r['holding_id']:r for r in json.loads(WATER.read_bytes())['entries']};rec=json.loads(RECOVERED.read_bytes());owners=[]
 for kind in ['approaches','landings']:
  for i,t in enumerate(rec[kind]['triangles']):
   owners.append(dict(id='RECOVERED_ACTUAL:'+kind+':'+str(i),polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=a.common.plane(t['triangle_xyz_m']),source_kind='retained_rendered_institutional_top',source_json_pointer='/'+kind+'/triangles/'+str(i),source_triangle_sha256=a.canonical_sha(t['triangle_xyz_m'])))
 ix=index(owners);scene=json.loads(review.R04.read_bytes());tops=a.TriangleIndex(scene,[p for e in water.values() for p in e['remaining_polygons_xz_m']]);rows=[]
 for source in old['entries']:
  hid=source['holding_id']
  if hid not in water and hid not in ['BLOCK_005:R8_C003','BLOCK_017:R8_I004']:continue
  e=dict(source);regions=list(source['profile_regions']);missing=[];bound=[]
  if hid in water:
   w=water[hid];regions+=w['added_fixed_regions']
   for p in w['remaining_polygons_xz_m']:
    rem=[p]
    if hid=='BLOCK_008:R8_C003':
     candidates=[owners[i]for i in sorted(ix.candidates(p))]
    else:
     candidates=[dict(id=hid+':R04_RESIDUAL:'+str(r['triangle_index']),polygon_xz_m=r['intersection_polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],source_kind='actual_r04_top_excluded_from_primary_r18',source_material=r['material'],source_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'])for r in tops.covering(p)]
    for r in candidates:
     if not rem:break
     cuts=[]
     for q in rem:
      clip=a.clip(q,r['polygon_xz_m'])
      if clip and a.geo.polygon_area(clip)>1e-12:
       rr=dict(r,id=r['id']+':PART:'+str(len(bound)),polygon_xz_m=clip,gradient=math.hypot(*r['plane_y_xz_m'][:2]));bound.append(rr);cuts.append(clip)
     if cuts:rem=a.common.subtract(rem,cuts)
    missing+=rem
   regions+=bound
  elif hid=='BLOCK_017:R8_I004':
   replacements=json.loads(B17.read_bytes())['owners'];masks=[r['polygon_xz_m']for r in replacements];regions=[]
   for r in source['profile_regions']:
    for i,p in enumerate(a.common.subtract([r['polygon_xz_m']],masks)):regions.append(dict(r,id=r['id']+':RETAINED:'+str(i),polygon_xz_m=p))
    for s in replacements:
     q=a.clip(r['polygon_xz_m'],s['polygon_xz_m'])
     if q and a.geo.polygon_area(q)>1e-12:bound.append(dict(s,id=s['id']+':ENTRY_PART:'+str(len(bound)),polygon_xz_m=q,source_kind='sealed_b17_finite_alley_replacement',gradient=math.hypot(*s['plane_y_xz_m'][:2])))
   regions+=bound
  area=sum(a.geo.polygon_area(p)for p in missing)
  e.update(profile_regions=regions,remaining_polygons_xz_m=missing,uncovered_area_m2=area,added_source_regions=bound,status='SOURCE_COVERAGE_READY'if area<1e-7 else'HELD_FINITE_OWNER_GAP')
  rows.append(e);print(hid,'added',len(bound),'gap',area,'max grade',max(math.hypot(*r['plane_y_xz_m'][:2])for r in regions),flush=True)
 refs=[dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))for p in[OLD,WATER,RECOVERED,B17,review.R04]]
 write(HERE/'actual_public_inputs.json',dict(entries=rows,source_refs=refs,activation=False,policy='Every added height belongs to an exact recorded physical public surface. No inferred gap fill.'))
if __name__=='__main__':bind()
