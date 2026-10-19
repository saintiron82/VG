"""Separate low native boundary belts; existing precinct freeze stays unchanged."""
import sys,math,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from plan_coverage import ROOT,CITY,ref,write,load,geo,rect,triangulate,offset,DomainCut
from world_city.concept_city_v3.assemblies.landmarks.author import Assembly
from recovered_range_factory import estimate_candidates
BASE=HERE.parent

def main():
 plan=load(BASE/'coverage_plan.json');production=load(BASE/'productive_frames.json');routes=load(BASE/'exterior_access_proposal.json');wood=load(CITY/'assemblies/landscape/registered_woodland/resolved_placements.json');key='uf_r3_understory_d430ebbe68c49f';a=wood['assets'][key];print(a.keys());source=load(ROOT/a['master_path']);bounds=a['bounds'];obstacles=[r['polygon_xz_m']for r in plan['reserved_records']]+[c['requested_frame_xz_m']for c in plan['compounds']]+[f['polygon_xz_m']for f in production['frames']]
 for r in routes['routes']:obstacles += [offset(p,-1)for p in r['ribbon_polygons_xz_m']+r['join_polygons_xz_m']]
 index=geo._SpatialIndex(20)
 for i,p in enumerate(obstacles):index.add(i,p)
 records=[];preflight=[];rejections=[]
 for site in plan['sites']:
  poly=site['polygon_xz_m'];cx=sum(p[0]for p in poly)/len(poly);cz=sum(p[1]for p in poly)/len(poly);floor=14 if site['id']=='SITE_CLERGY'else 8;assembly=Assembly('boundary_belt_'+site['id'],[cx,cz],floor,poly);accepted=[]
  for edge,(p,q)in enumerate(zip(poly,poly[1:]+poly[:1])):
   length=math.dist(p,q);u=[(q[j]-p[j])/length for j in(0,1)];n=[-u[1],u[0]];mid=[(p[j]+q[j])/2 for j in(0,1)];inside=[mid[j]+n[j]for j in(0,1)]
   if not any(geo.point_in_convex_polygon(inside,t,0)for t in triangulate(poly)):n=[-n[0],-n[1]]
   count=max(1,int((length-8)/3.6));yaw=math.degrees(math.atan2(-u[1],u[0]))
   for i in range(count):
    t=4+(length-8)*(i+.5)/count;pos=[p[j]+u[j]*t+n[j]*5.5 for j in(0,1)];foot=geo.transformed_aabb_xz_m(bounds,[pos[0],floor,pos[1]],math.radians(yaw));expanded=offset(foot,-.25)
    covered=sum(geo.intersection_area(expanded,t)for t in triangulate(poly))
    hits=[j for j in index.candidates(expanded)if geo.positive_area_overlap(expanded,obstacles[j],0)]
    if abs(covered-geo.polygon_area(expanded))>1e-5 or hits:rejections.append({'site_id':site['id'],'edge':edge,'slot':i,'reason':'preserved route, body, plot or boundary clearance'});continue
    id=f'{site["id"]}:edge:{edge}:hedge:{i}';assembly.add(id,source,[pos[0]-cx,0,pos[1]-cz],yaw,purpose='continuous_low_productive_precinct_boundary_belt');accepted.append({'id':id,'edge_index':edge,'position_m':[pos[0],floor,pos[1]],'yaw_degrees':yaw,'native_footprint_xz_m':foot})
  s=assembly.finish();s['id']='registered_precinct_boundary_belt_'+site['id'].lower();s['provenance'].update(addon_author=ref(Path(__file__)),sealed_precinct_pack=ref(BASE/'resolved_placements.json'),native_understory_source=ref(ROOT/a['master_path']));s['extensions'].update(boundary_role='Intentional low green edge; all required access gaps cut by finite reservations.',native_plant_modules=accepted,existing_precinct_modified=False);path=HERE/'masters'/f"{s['id']}.json";write(path,s);estimate=estimate_candidates(s,.5);assert estimate['candidate_cells_exact_aabb_visits']<600000;preflight.append({'id':s['id'],'source':ref(path),'estimate':estimate,'position_m':[cx,floor,cz],'site_id':site['id'],'native_modules':len(accepted)});records+=accepted
 write(HERE/'preflight.json',{'schema':'riverstone.precinct.boundary_belt_preflight.v1','base_precinct_pack':ref(BASE/'resolved_placements.json'),'preserved_external_routes':ref(BASE/'exterior_access_proposal.json'),'sources':preflight,'native_modules':records,'rejections':rejections,'candidate_cap_each':600000,'output_cap_each':150000,'pitch_m':.5,'new_native_family':False,'actual_placed':False,'actual_viewed':False});print([(r['site_id'],r['native_modules'],r['estimate']['candidate_cells_exact_aabb_visits'])for r in preflight])
if __name__=='__main__':main()
