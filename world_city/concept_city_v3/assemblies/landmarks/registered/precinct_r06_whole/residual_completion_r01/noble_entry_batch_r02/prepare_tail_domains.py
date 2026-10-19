"""Bounded source-domain input for seven public-priority private terminal solves."""
from pathlib import Path
import sys,json,math,argparse
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
OUT=Path(__file__).resolve().parent;OLD=OUT.with_name('noble_entry_batch_r01');R18=CITY/'registered_topography/revisions/public_corridors_r18'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default='tail_solve_inputs.json');ap.add_argument('--e2-depth',type=float,default=8.);args=ap.parse_args()
 pack=load(OLD/'resolved_native_candidate.json');public=load(R18/'finite_field_candidate_r07_native_bound.json')['records'];ix=geo._SpatialIndex(8)
 for i,r in enumerate(public):ix.add(i,r['polygon_xz_m'])
 rows=[]
 for owner in pack['owners']:
  eid=owner['owner_id'];profile=load(OLD/f'geometry/{eid}_physical_top.json');ext=owner['source_external_profile'];points=profile['route_points_xz_m'];seam=np.array(points[-2]);d=seam-np.array(points[-3]);d=d/np.linalg.norm(d);n=np.array([-d[1],d[0]])
  def rect(s0,s1,w):return [(seam+d*s+n*t).tolist()for s,t in[(s0,-w),(s1,-w),(s1,w),(s0,w)]]
  depth=args.e2_depth if eid=='E2'else 8.;window=rect(-depth,.85,2.1);inner=rect(-depth-.05,-depth+.000001,2.1);domain=[]
  # Keep the authored source footprint finite; the native raster fringe will
  # be retired and its exact outside remainder separately restored.
  for region in ext['polygon_regions_xz_m']:
   for tri in b.triangulate(region):
    q=fg.clip(tri,window)
    if q:domain.extend(fg.subtract([q],domain))
  localpublic=[public[i]for i in sorted(ix.candidates(window))if fg.clip(public[i]['polygon_xz_m'],window)]
  private=fg.subtract(domain,[r['polygon_xz_m']for r in localpublic]);fixed=[]
  for r in profile['top_pieces']:
   q=fg.clip(r['polygon_xz_m'],inner)
   if q:fixed.append(dict(id='INNER:'+str(len(fixed)),polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],kind='unchanged_private_inner_profile'))
  fixed +=[dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],kind='fixed_public_priority')for r in localpublic]
  rows.append(dict(owner_id=eid,window_polygon_xz_m=window,source_domain_polygons_xz_m=domain,private_domain_polygons_xz_m=private,fixed_regions=fixed,target_profile=ref(OLD/f'geometry/{eid}_physical_top.json'),source_profile=ext,public_record_ids=[r['id']for r in localpublic],public_records=localpublic,domain_area_m2=sum(fg.area(q)for q in private),seam_xz_m=seam.tolist(),direction_xz=d.tolist(),original_source_inner_offset_m=-depth))
 out=dict(schema='riverstone.noble.finite_tail_input.v1',source_public=ref(R18/'finite_field_candidate_r07_native_bound.json'),source_native=ref(OLD/'resolved_native_candidate.json'),owners=rows,policy='Canonical public full width and planes fixed; unchanged private profile at -8m; no retained base changes; runtime pending')
 p=OUT/args.output;p.write_text(json.dumps(out,indent=2)+'\n');print(ref(p));print([(r['owner_id'],r['domain_area_m2'],len(r['private_domain_polygons_xz_m']),len(r['fixed_regions']))for r in rows])
if __name__=='__main__':main()
