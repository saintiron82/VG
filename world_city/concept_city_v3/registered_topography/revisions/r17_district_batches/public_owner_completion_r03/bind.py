"""Current physical-source precedence, with exact signed finite clipping."""
import json,math
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..final_profile_audit_r01.exact_clip import clip,difference
HERE=Path(__file__).resolve().parent
OLD=a.HERE/'public_owner_completion_r02/actual_public_inputs.json'
WATER=a.HERE/'public_owner_completion_r01/water_owner_binding.json'
CURRENT=a.HERE.parent/'public_corridors_r18/finite_field_candidate_r07_native_bound.json'
RECOVERED=a.CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'
def cut(ps,masks):
 for mask in masks:
  ps=[v for p in ps for v in difference(p,mask)]
 return ps
def run():
 old=json.loads(OLD.read_bytes());water={e['holding_id']:e for e in json.loads(WATER.read_bytes())['entries']};cur=json.loads(CURRENT.read_bytes())['records'];ci=index(cur);rec=json.loads(RECOVERED.read_bytes());rr=[]
 for kind in ['approaches','landings']:
  for i,t in enumerate(rec[kind]['triangles']):rr.append(dict(id='RECOVERED:'+kind+':'+str(i),polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=a.common.plane(t['triangle_xyz_m']),source_kind='retained_actual_institutional_top',source_triangle_sha256=a.canonical_sha(t['triangle_xyz_m']),source_json_pointer='/'+kind+'/triangles/'+str(i)))
 ri=index(rr);out=[]
 for e in old['entries']:
  if e['holding_id']=='BLOCK_017:R8_I004':out.append(e);continue
  hid=e['holding_id'];regions=[];miss=[]
  # Current R18 planes replace all superseded original-source top portions.
  for r in e['profile_regions']:
   if r.get('source_kind')in ['actual_common_native_traffic_top','exact_water_approach_field']:regions.append(r);continue
   rem=[r['polygon_xz_m']]
   for i in sorted(ci.candidates(r['polygon_xz_m'])):
    s=cur[i];q=clip(r['polygon_xz_m'],s['polygon_xz_m'])
    if a.geo.polygon_area(q)>1e-12:
     regions.append(dict(id=s['id']+':ENTRY:'+str(len(regions)),polygon_xz_m=q,plane_y_xz_m=s['plane_y_xz_m'],source_kind='current_r07_public_field',source_record_id=s['id'],gradient=math.hypot(*s['plane_y_xz_m'][:2])));rem=cut(rem,[s['polygon_xz_m']])
   for j,p in enumerate(rem):regions.append(dict(r,id=r['id']+':OUTSIDE_CURRENT:'+str(j),polygon_xz_m=p))
  for p in e['remaining_polygons_xz_m']:
   rem=[p]
   for i in sorted(ri.candidates(p)):
    s=rr[i];parts=[clip(q,s['polygon_xz_m'])for q in rem];parts=[q for q in parts if a.geo.polygon_area(q)>1e-12]
    if parts:
     for q in parts:regions.append(dict(s,id=s['id']+':RESIDUAL:'+str(len(regions)),polygon_xz_m=q))
     rem=cut(rem,[s['polygon_xz_m']])
   miss+=rem
  # Rebuild exact original B005 residual requests directly on current field.
  if hid.startswith('BLOCK_005:') and hid in water:
   residual=water[hid]['remaining_polygons_xz_m'];regions=[dict(r,polygon_xz_m=q,id=r['id']+':REMAINDER:'+str(j))for r in regions for j,q in enumerate(cut([r['polygon_xz_m']],residual))]
   for p in residual:
    rem=[p]
    for i in sorted(ci.candidates(p)):
     s=cur[i];q=clip(p,s['polygon_xz_m'])
     if a.geo.polygon_area(q)>1e-12:
      regions.append(dict(id=s['id']+':RECOVERED_REQUEST:'+str(len(regions)),polygon_xz_m=q,plane_y_xz_m=s['plane_y_xz_m'],source_record_id=s['id'],source_kind='current_r07_public_field'));rem=cut(rem,[s['polygon_xz_m']])
    miss+=rem
  area=sum(a.geo.polygon_area(p)for p in miss)
  row=dict(e,profile_regions=regions,remaining_polygons_xz_m=miss,uncovered_area_m2=area,status='SOURCE_COVERAGE_READY'if area<1e-7 else'HELD_FINITE_OWNER_GAP');out.append(row);print(hid,len(regions),'gap',area,flush=True)
 write(HERE/'actual_public_inputs.json',dict(entries=out,source_refs=[dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))for p in[OLD,WATER,CURRENT,RECOVERED]],activation=False,policy='Current R07 finite public planes supersede any earlier R04 plane in the same footprint. Native water deck and approach fields have exact independent ownership. Signed half-plane clipping has no absolute short-edge containment expansion.'))
if __name__=='__main__':run()
