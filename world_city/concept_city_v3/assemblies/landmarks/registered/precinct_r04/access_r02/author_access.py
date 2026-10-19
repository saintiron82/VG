"""Two-route source correction; frozen native geometry and original proposal stay intact."""
import sys,copy,math,json
from pathlib import Path
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from plan_coverage import *
from world_city.concept_city_v3.registered_topography.revisions.r13_precinct_interfaces import materials as terrain

def obstacles():
 plan=load(BASE/'coverage_plan.json');prod=load(BASE/'productive_frames.json');land=load(LAND);garden=load(GARDEN);obs=[]
 obs += [(f['placement_id'],f['polygon_xz_m'])for f in land['owned_floors']]
 obs += [(s['id'],s['polygon_xz_m'])for s in garden['sites']]
 obs += [(c['id'],c['requested_frame_xz_m'])for c in plan['compounds']]
 obs += [(f['id'],f['polygon_xz_m'])for f in prod['frames']]
 obs += [(p['id'],p['native_footprint_xz_m'])for p in load(BASE/'boundary_belts/preflight.json')['native_modules']]
 return obs
OBS=obstacles();INDEX=geo._SpatialIndex(16)
for i,(_,p)in enumerate(OBS):INDEX.add(i,p)

def polygons(points):return [geo.road_ribbon(a,b,1.8)for a,b in zip(points,points[1:])if math.dist(a,b)>1e-8],[circle(p,.9)for p in points[1:-1]]
def hits(points,owner='CLERGY_NORTH_ORCHARD'):
 rs,js=polygons(points);found=[]
 for p in rs+js:
  for i in INDEX.candidates(p):
   id,q=OBS[i]
   if id==owner:continue
   area=geo.intersection_area(p,q)
   if area>1e-6:found.append({'obstacle_id':id,'area_m2':area})
 return found

def sample(points,y,spacing=.4):
 rs,js=polygons(points);bad=[];count=0
 for a,b in zip(points,points[1:]):
  L=math.dist(a,b)
  if L<1e-8:continue
  n=max(1,math.ceil(L/spacing));nx=-(b[1]-a[1])/L*.9;nz=(b[0]-a[0])/L*.9
  for i in range(n+1):
   u=i/n
   for side in[-1,-.5,0,.5,1]:
    x=a[0]+u*(b[0]-a[0])+side*nx;z=a[1]+u*(b[1]-a[1])+side*nz;h=terrain.land_height_at(x,z);count+=1
    if abs(h-y)>1e-6:bad.append({'point_xyz_m':[x,h,z],'owner_id':terrain.owner_at(x,z)['owner_id']})
 for p in js:
  for x,z in p:
   h=terrain.land_height_at(x,z);count+=1
   if abs(h-y)>1e-6:bad.append({'point_xyz_m':[x,h,z],'owner_id':terrain.owner_at(x,z)['owner_id']})
 return {'samples':count,'nonlevel_samples':bad,'finished_y_m':y}

def main():
 old=load(BASE/'exterior_access_proposal.json');routes=copy.deepcopy(old['routes']);orch=next(r for r in routes if r['gate_id']=='CLERGY_NORTH_ORCHARD:main_gate');can=next(r for r in routes if r['gate_id']=='CLERGY_CANONS_CLOSE:main_gate');candidates=[]
 for i,p in enumerate(orch['polyline_xz_m'][:-4]):
  for j,q in enumerate(can['polyline_xz_m'][2:-1],2):
   if math.dist(p,q)>75:continue
   pts=orch['polyline_xz_m'][:i+1]+can['polyline_xz_m'][j:]
   if hits([p,q]):continue
   candidates.append((sum(math.dist(a,b)for a,b in zip(pts,pts[1:])),i,j,pts))
 selected=None
 for length,i,j,pts in sorted(candidates):
  if hits(pts):continue
  test=sample(pts,14)
  if not test['nonlevel_samples']:selected=(length,i,j,pts,test);break
 if not selected:raise RuntimeError('No full-width level source connection')
 length,i,j,pts,audit=selected;orch.update(polyline_xz_m=pts,ribbon_polygons_xz_m=polygons(pts)[0],join_polygons_xz_m=polygons(pts)[1],length_m=length,target=copy.deepcopy(can['target']),grade_policy='Fixed +14 source walk; full-width samples retain current terrain; destination uses the already-level canons recovered approach interior.',supersedes_route_id=orch['id'])
 print('clergy',length,'splice',i,j,'samples',audit['samples'],flush=True)
 # Publish the entire effective proposal to simplify consumers, with an explicit replacement list.
 doc=copy.deepcopy(old);doc.update(schema='riverstone.precinct.exterior_walk_source_proposal.v2',superseded_proposal=ref(BASE/'exterior_access_proposal.json'),author=ref(Path(__file__)),terrain_source=ref(Path(terrain.__file__)),routes=routes,replaced_route_ids=[orch['id']],recovery_note='Original route remains frozen; only the clergy orchard route is superseded. Abbey east orchard keeps its physical route and needs finite shoulder support.',full_width_independent_audit=False)
 write(OUT/'exterior_access_proposal.json',doc)
 write(OUT/'clergy_full_width_audit.json',{'source':ref(OUT/'exterior_access_proposal.json'),'terrain':ref(Path(terrain.__file__)),'changed_route_id':orch['id'],'splice_indices':[i,j],'body_and_boundary_hits':hits(pts),'sampling':audit,'target_owner':terrain.owner_at(*orch['target']['point_xz_m']),'limits':['Point/line sampling is bounded evidence; exact finite ownership and native controller remain independent gates.']})
 print('pack',ref(OUT/'exterior_access_proposal.json'),flush=True)
if __name__=='__main__':main()
