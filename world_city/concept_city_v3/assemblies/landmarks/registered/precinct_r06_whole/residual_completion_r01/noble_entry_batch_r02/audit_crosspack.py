"""Exact fine-native and walking-profile partition checks against phase02."""
from build_ground_patch import *
OUT=Path(__file__).resolve().parent

def main():
 pack=load(OUT/'resolved_native_candidate.json');ground=load(OUT/'native_ground_candidate_audit.json');routes=load(OUT/'runtime_routes.json');phasepath=CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json';phase=load(phasepath);phasefoot=[]
 for p in phase['placements']:
  # Actual native occupied projections, never the placement AABB.
  mesh=load(ROOT/p['cache']['path']);ys=[v[1]for g in mesh['groups']for q in g['quads']for v in q];local=slab_rectangles(mesh,min(ys)-.001,max(ys)+.001)
  for q in local:phasefoot.append(dict(id=p['id'],polygon_xz_m=b.xform(q,p)))
 pi=geo._SpatialIndex(8)
 for i,r in enumerate(phasefoot):pi.add(i,r['polygon_xz_m'])
 checks=[]
 for route in routes['routes']:
  eid=route['owner_id'];native=[r['polygon_xz_m']for r in ground['new_native_undersides']if r['native_id']==route['native_fine_id']];polys=native+b.ribbon(route['polyline_xz_m'],2);contacts=[]
  for q in polys:
   for i in pi.candidates(q):
    pp=geo.convex_intersection(q,phasefoot[i]['polygon_xz_m']);a=geo.polygon_area(pp)
    if a>1e-7:contacts.append(dict(id=phasefoot[i]['id'],area_m2=a,polygon_xz_m=pp))
  tops=load(ROOT/route['physical_top']['path'])['top_pieces'];ix=geo._SpatialIndex(4);overlaps=[];maxarea=0
  for i,r in enumerate(tops):
   q=r['polygon_xz_m']
   for j in ix.candidates(q):
    pp=geo.convex_intersection(q,tops[j]['polygon_xz_m']);a=geo.polygon_area(pp);maxarea=max(maxarea,a)
    if a>1e-7:overlaps.append(dict(first=j,second=i,area_m2=a))
   ix.add(i,q)
  checks.append(dict(owner_id=eid,phase02_contacts=contacts,physical_top_positive_area_overlaps=overlaps,maximum_pair_overlap_area_m2=maxarea,pass_=not contacts and not overlaps));print(eid,'crosspack',checks[-1]['pass_'],len(contacts),len(overlaps),maxarea,flush=True)
 out=dict(status='PASS_EXACT_PHASE02_AND_PHYSICAL_TOP_PARTITION'if all(r['pass_']for r in checks)else'HELD_CROSSPACK_FAILURE',native_pack=ref(OUT/'resolved_native_candidate.json'),phase02_pack=ref(phasepath),collision_contracts=ref(OUT/'collision_contracts.json'),checks=checks);write('phase02_and_physical_partition_audit.json',out)
if __name__=='__main__':main()
