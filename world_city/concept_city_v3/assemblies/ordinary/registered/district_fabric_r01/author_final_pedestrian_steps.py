"""Bounded fine native stone step skin over an accepted pedestrian profile."""
from . import geometry as g
from world_city.runtime_city.parts.author import Source
from world_city.concept_city_v3.assemblies.property.registered.r1.author import append_surface
from world_city.concept_city_v3.assemblies.landmarks.registered.build_audit import estimate_candidates
from world_city.concept_city_v3.assemblies.landmarks.registered.precinct_r06_whole.residual_completion_r01.noble_entry_batch_r02.author_regraded_native import refine_shared_xy_joins
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from .activate_backlands_subset import MaskIndex
import math,copy
OUT=g.HERE/'final_pedestrian_step_skins_r01'
PROFILE=a.HERE/'final_private_wedge_refinement_r01/BLOCK_001_R8_C003.json'

def run():
 OUT.mkdir(exist_ok=True);profile=g.load(PROFILE);res=profile['result'];assert res['status']=='PASSED_FINITE_TRIANGLE_GRADE' and res['maximum_gradient']<=.2500001
 tris=copy.deepcopy(res['triangles']);allpts=[v for t in tris for v in t['vertices_xyz_m']];x0=min(v[0]for v in allpts);x1=max(v[0]for v in allpts);z0=min(v[2]for v in allpts);z1=max(v[2]for v in allpts);floor=profile['candidate']['floor_y_m'];origin=[math.floor(x0),floor,math.floor(z0)];y0=min(v[1]for v in allpts)-.75;y1=max(v[1]for v in allpts)+.25
 s=Source('final_B001_C003_pedestrian_step_skin',[x0-origin[0]-.25,y0-floor,z0-origin[2]-.25],[x1-origin[0]+.25,y1-floor,z1-origin[2]+.25]);s.box('temporary_seed',[0,-.125,0],[.125,0,.125]);master=s.finish();master['components'][0]['operations']=[];master['metadata']={}
 for t in tris:
  for v in t['vertices_xyz_m']:v[1]+=.03125
 master=append_surface(master,dict(id='B001_C003_ACCEPTED_PEDESTRIAN_FIELD',triangulated_top_surface=tris),[origin[0],origin[2]],floor)
 ops,joins=refine_shared_xy_joins(master['components'][0]['operations'],tris);master['components'][0]['operations']=ops
 # Source-only column cuts preserve the exact private/public ownership. No
 # compiled cells or cached quads are altered after the common compiler.
 domain=profile['private_domain_polygons_xz_m'];mask=MaskIndex([dict(id='PRIVATE_PROFILE',polygon_xz_m=p)for p in domain]);pitch=.125;cuts=[]
 for ix in range(math.floor((x0-origin[0])/pitch)-2,math.ceil((x1-origin[0])/pitch)+2):
  for iz in range(math.floor((z0-origin[2])/pitch)-2,math.ceil((z1-origin[2])/pitch)+2):
   q=g.rect(origin[0]+ix*pitch,origin[2]+iz*pitch,origin[0]+(ix+1)*pitch,origin[2]+(iz+1)*pitch);hits=mask.hit([q]);inside=a.common.disjoint_union([h['polygon_xz_m']for h in hits]);missing=a.common.subtract([q],inside)
   if sum(g.geo.polygon_area(p)for p in missing)<=1e-10:continue
   # Only columns near some profile source prism need explicit removal.
   if not hits and not any(g.geo.intersection_area(q,p)>1e-10 for p in domain):
    cx=sum(p[0]for p in q)/4;cz=sum(p[1]for p in q)/4
    if not mask.hit([g.rect(cx-.3,cz-.3,cx+.3,cz+.3)]):continue
   cuts.append(q);master['components'][0]['operations'].append(dict(id='exact_private_column_boundary:'+str(len(cuts)),part='solid',action='cut',shape=dict(kind='extrusion',polygon=[[p[0]-origin[0],-(p[1]-origin[2])]for p in q],z_min=y0-floor,z_max=y1-floor),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
 master['id']='district_final_B001_C003_pedestrian_steps';master['revision']=1;master['metadata'].update(source_profile=g.ref(PROFILE),shared_native_source_join_refinement=joins,native_pitch_m=.125,native_sampling_top_bias_m=.03125,maximum_visible_tread_rise_m=.125,physical_collision_policy='Use the accepted continuous finite pedestrian field. Native step tops are visible and must be excluded from duplicate terrain; native side/bottom sections remain explicitly supported.',cart_access_claim=False,public_private_column_cuts=cuts,author=g.ref(__file__));master['provenance'].update(new_engine=False,cell_edits=False,shared_append_surface_author=g.ref(a.Path(append_surface.__code__.co_filename)))
 path=OUT/'masters'/f'{master["id"]}.json';g.write(path,master);estimate=estimate_candidates(master,.125);budget=dict(schema='riverstone.final_steps.native_budget.v1',sources=[dict(holding_id='BLOCK_001:R8_C003',master=g.ref(path),source_profile=g.ref(PROFILE),pose=dict(position_m=origin,yaw_rad=0.,scale=[1,1,1]),pitch_m=.125,estimate=estimate,candidate_cap=1000000,output_cap=100000)],summary=dict(new_unique_assemblies=1,serial_compile=True,candidate_cells=estimate['candidate_cells_exact_aabb_visits'],predicted_memory_mib=[60,220],new_engine=False,cell_edits=False),terrain_required=['Exact actual native downward/bottom sections at their local sampled levels.','Exclude each emitted native column from duplicate terrain tops; surrounding finite field remains intact.','Bind the original accepted continuous field as the walking collision surface with existing controller and no cart claim.']);g.write(OUT/'compile_budget.json',budget);print(budget['summary']);print(g.ref(OUT/'compile_budget.json'))
if __name__=='__main__':run()
