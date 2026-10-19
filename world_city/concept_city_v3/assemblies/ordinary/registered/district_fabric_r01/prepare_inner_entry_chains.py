"""Explicit court-to-gate centerlines inside the already selected finite domains."""
from . import geometry as g
from .activate_backlands_subset import MaskIndex
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
import math
OUT=g.HERE/'final_inner_entry_chains_r01'
def area(ps):return sum(g.geo.polygon_area(q)for q in ps)
def run():
 prep=g.HERE/'final_source_preparation_r01/native_owner_replacements.json';rows=[]
 for r in g.load(prep)['records']:
  h=r['replacement_holding'];hid=r['holding_id'];ends={tuple(d['polyline_xyz_m'][-1][::2])for d in r['replacement_door_routes']};assert len(ends)==1;anchor=list(next(iter(ends)));gate=h['gate_position_xz_m'];seams=h['shared_inner_seams_xz_m']
  if seams:
   seam=seams[0]['endpoints_xz_m'];mid=[sum(v[k]for v in seam)/2 for k in [0,1]];line=[anchor,mid,gate];width=1.5;profile_width=math.dist(*seam)
  else:
   p=a.HERE/'entry_continuation_r01/source_refit_profiles_r03/BLOCK_003_R8_C003_2.json';line=g.load(p)['candidate']['internal_court_link_xz_m'];width=1.5;profile_width=3.5;assert math.dist(line[0],anchor)<1e-8
  polys=g.ribbons(line,width);domain=h['flat_owner_polygons_xz_m']+h['profile_domain_polygons_xz_m'];missing=area(a.common.subtract(polys,domain));obs=[q for p in r['replacement_native_placements']for q in p['native_walking_obstacles_xz_m']];hits=MaskIndex([dict(id=str(i),polygon_xz_m=q)for i,q in enumerate(obs)]).hit(polys)
  row=dict(id=hid+':INNER_GRADED_ENTRY',holding_id=hid,polyline_xz_m=line,width_m=width,selected_full_profile_width_at_inner_seam_m=profile_width,polygons_xz_m=polys,start_flat_floor_y_m=h['floor_y_m'],start_xz_m=anchor,end_gate_xz_m=gate,height_policy='Lift centerline on the selected exact flat/profile triangles; never assign the entire chain the court datum.',source_preparation=g.ref(prep),selected_candidate=r['selected_candidate'],missing_selected_physical_domain_m2=missing,native_contacts=hits,passes=missing<1e-7 and not hits)
  rows.append(row);print(hid,missing,len(hits),flush=True)
 OUT.mkdir(exist_ok=True);g.write(OUT/'handoff.json',dict(schema='riverstone.explicit_inner_entry_chains.v1',source_preparation=g.ref(prep),records=rows,passed=all(r['passes']for r in rows),author=g.ref(__file__),physical_policy='These are named centerline traversals of the existing finite surface owner, not additional terrain or route grading. The supplied width is an interior pedestrian test band; the complete selected finite profile retains its full source width.'))
 print(g.ref(OUT/'handoff.json'))
if __name__=='__main__':run()
