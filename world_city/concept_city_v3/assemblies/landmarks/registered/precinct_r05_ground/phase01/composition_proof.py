"""Finite domain proof for shared original indices and appended restoration."""
from prepare import *
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import frozen as f
from world_city.concept_city_v3.review_geometry import clean

def main():
 scene=f.load_scene();ground=load(HERE/'surface_patch.json');clergy=load(HERE.parent/'local_frame_r01/corner_repair_r01/terrain_patch/surface_patch.json');combined=load(HERE/'combined_clergy_ground_patch.json');pack=load(HERE/'resolved_placements.json');masks=load(HERE.parent/'local_frame_r01/corner_repair_r01/changed_masks.json');native=[r['polygon_xz_m']for r in pack['actual_bearing_footprints']]+[r['polygon_xz_m']for r in masks['add_actual_bearing_footprints']];nc=DomainCut([{'polygon_xz_m':p}for p in native]);g={(r['material'],r['triangle_index']):r for r in ground['surface_edits']};c={(r['material'],r['triangle_index']):r for r in clergy['surface_edits']};common=[]
 for key in sorted(set(g)&set(c)):
  tri=scene['surfaces'][key[0]][key[1]*3:key[1]*3+3];p=[[v[0],v[2]]for v in tri];assert geo.polygon_area(p)>1e-9
  removed=[]
  for patch in(c,g):
   remain=[[[v[0],v[2]]for v in t]for t in patch[key]['replacement_triangles_xyz_m']];removed.append(DomainCut([{'polygon_xz_m':q}for q in remain]).subtract(p))
  ar=sum(geo.intersection_area(a,b)for a in removed[0]for b in removed[1]);common.append({'material':key[0],'triangle_index':key[1],'removed_domain_overlap_m2':ar})
 gi=geo._SpatialIndex(8);gtris=[]
 for mat,verts in ground['appended_surfaces'].items():
  for k in range(0,len(verts),3):
   tri=verts[k:k+3];p=[[v[0],v[2]]for v in tri];gi.add(len(gtris),p);gtris.append((mat,p))
 double=0.;restored_cut=0.;restored_area=0.;maxone=0.;native_hit=0.
 for mat,verts in clergy['appended_surfaces'].items():
  for k in range(0,len(verts),3):
   tri=verts[k:k+3];p=[[v[0],v[2]]for v in tri];remain=nc.subtract(p);restored_cut+=geo.polygon_area(p)-sum(geo.polygon_area(q)for q in remain)
   for q in remain:
    restored_area+=geo.polygon_area(q)
    for i in gi.candidates(q):
     ar=geo.intersection_area(q,gtris[i][1]);double+=ar;maxone=max(maxone,ar)
 for mat,p in gtris:
  native_hit+=geo.polygon_area(p)-sum(geo.polygon_area(q)for q in nc.subtract(p))
 assert double<1e-6,(double,maxone)
 assert abs(native_hit)<1e-6,native_hit
 out={'combined_patch':ref(HERE/'combined_clergy_ground_patch.json'),'same_original_triangle_count':len(common),'shared_original_triangles':common,'total_removed_domain_overlap_m2':sum(r['removed_domain_overlap_m2']for r in common),'composition_method':'Intersect retained domains on each original plane. Productive appended terrain is cut against both new native ground bearings and corrected clergy bearings. Old-hole restoration is also cut against that combined native union.','clergy_restoration_cut_under_combined_native_m2':restored_cut,'remaining_clergy_restoration_area_m2':restored_area,'clergy_restoration_vs_productive_appended_overlap_m2':double,'maximum_single_appended_overlap_m2':maxone,'productive_appended_vs_combined_native_overlap_m2':native_hit,'passes':True};write(HERE/'composition_geometry_proof.json',out);print({k:v for k,v in out.items()if k!='shared_original_triangles'})
if __name__=='__main__':main()
