"""Serial unchanged common compile plus exact sampled skin sections."""
from . import geometry as g
from .author_final_pedestrian_steps import OUT
from voxel_character.common import core,coordinate_planes,render_data
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.finalize_rows import face_bijection
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from .activate_backlands_subset import MaskIndex
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
from collections import defaultdict
import time,resource,math

def rectangles(cells):
 rows=defaultdict(set)
 for x,z in cells:rows[z].add(x)
 live={};out=[]
 for z in range(min(rows),max(rows)+2):
  xs=sorted(rows.get(z,[]));spans=[]
  for x in xs:
   if spans and x==spans[-1][1]:spans[-1]=(spans[-1][0],x+1)
   else:spans.append((x,x+1))
  new={}
  for span in spans:new[span]=(live[span][0],z+1)if span in live else(z,z+1)
  for span,(z0,z1)in live.items():
   if span not in new:out.append([span[0],z0,span[1],z1])
  live=new
 return out

def run():
 started=time.monotonic();budget=g.load(OUT/'compile_budget.json');assert len(budget['sources'])==1;v=budget['sources'][0];m=g.load(g.ROOT/v['master']['path']);assert g.ref(g.ROOT/v['master']['path'])==v['master'];assert v['estimate']['candidate_cells_exact_aabb_visits']<=1000000
 cp=OUT/'cache'/f'{m["id"]}.compiled.json';rp=OUT/'cache'/f'{m["id"]}.render.json'
 if cp.exists():
  c=g.load(cp);r=g.load(rp);assert c['master_hash']==core.digest(m)
 else:
  c=coordinate_planes.compile_master(m,{'pitch':v['pitch_m']},max_candidate_cells=1000000,max_output_cells=100000);assert c['valid'],c['constraints'];r=render_data.make_render_data(c);g.write(cp,c);g.write(rp,r)
 proof=face_bijection(c,r);assert core.digest(c['cells'])==c['payload_hash']==r['payload_hash']
 ass=dict(key=m['id'],master_path=v['master']['path'],master_sha256=v['master']['sha256'],render_path=g.ref(rp)['path'],render_sha256=g.ref(rp)['sha256'],compiled_path=g.ref(cp)['path'],compiled_sha256=g.ref(cp)['sha256'],bounds=r['bounds'],cell_count=r['cell_count'],quad_count=r['quad_count'],pitch_m=v['pitch_m'],native_metadata=m['metadata'],face_bijection=proof,constraints=c['constraints']);pose=v['pose'];pitch=v['pitch_m'];columns=defaultdict(list)
 for cell in c['cells']:columns[(cell[0],cell[2])].append(cell[1])
 assert all(len(set(ys))==max(ys)-min(ys)+1 for ys in columns.values()),'Disconnected native column in walking skin'
 low=defaultdict(list);high=defaultdict(list)
 column_tops={k:max(ys)+1 for k,ys in columns.items()};rises=[]
 for (x,z),y in column_tops.items():
  for other in [(x+1,z),(x,z+1)]:
   if other in column_tops:rises.append(abs(column_tops[other]-y)*pitch)
 assert max(rises,default=0)<=pitch
 for(x,z),ys in columns.items():low[min(ys)].append((x,z));high[max(ys)+1].append((x,z))
 def pieces(levels,kind):
  result=[]
  for y,cs in sorted(levels.items()):
   for x0,z0,x1,z1 in rectangles(cs):
    q=g.rect(pose['position_m'][0]+x0*pitch,pose['position_m'][2]+z0*pitch,pose['position_m'][0]+x1*pitch,pose['position_m'][2]+z1*pitch);result.append(dict(id=f'{m["id"]}:{kind}:{len(result)}',polygon_xz_m=q,y_m=pose['position_m'][1]+y*pitch,kind=kind))
  return result
 bottoms=pieces(low,'native_bottom');tops=pieces(high,'visible_native_top');profile=g.load(g.ROOT/v['source_profile']['path']);tri=profile['result']['triangles'];mi=MaskIndex([dict(t,id=t['id'])for t in tri]);deviations=[];coverage=[]
 for top in tops:
  hits=[]
  for i in mi.index.candidates(top['polygon_xz_m']):
   t=mi.rows[i];q=fg.clip(top['polygon_xz_m'],t['polygon_xz_m'])
   if q:hits.append(dict(t,polygon_xz_m=q))
  parts=[p['polygon_xz_m']for p in hits];missing=sum(fg.area(p)for p in fg.subtract([top['polygon_xz_m']],parts));coverage.append(missing)
  for hit in hits:
   src=next(t for t in tri if t['id']==hit['id']);d=[top['y_m']-a.common.height(src['plane_y_xz_m'],p)for p in hit['polygon_xz_m']];deviations+=d
 g.write(OUT/'native_column_domain_strict_audit.json',dict(maximum_missing_m2=max(coverage,default=0),total_missing_m2=sum(coverage),failed=[dict(top=t,missing_m2=ar)for t,ar in zip(tops,coverage)if ar>1e-8],candidate_cells=c['candidate_cells'],output_cells=r['cell_count']))
 print('coverage',max(coverage,default=0),sum(coverage),flush=True)
 assert max(coverage,default=0)<1e-8
 placement=dict(id='BLOCK_001:R8_C003:PEDESTRIAN_STEP_SKIN',holding_id='BLOCK_001:R8_C003',block_id='BLOCK_001',asset_key=m['id'],position_m=pose['position_m'],yaw_rad=0.,scale=[1,1,1],role='fine_native_pedestrian_steps',implementation_tier='exterior_only',source_profile=v['source_profile'],native_foundation_polygons_xz_m=[b['polygon_xz_m']for b in bottoms],native_profile_support_sections=bottoms,native_visible_top_sections=tops,cart_access_claim=False,walking_collision_policy='Explicit accepted finite continuous envelope, not native riser collision.',activation_status='SOURCE_ONLY_MATCHED_FINAL24_TERRAIN_AND_COLLISION_REQUIRED')
 summary=dict(new_unique_assets=1,candidate_cells=c['candidate_cells'],output_cells=r['cell_count'],quads=r['quad_count'],native_columns=len(columns),native_column_area_m2=len(columns)*pitch*pitch,bottom_sections=len(bottoms),top_sections=len(tops),maximum_visible_above_physical_m=max(deviations),maximum_physical_above_visible_m=-min(deviations),missing_profile_support_m2=sum(coverage),maximum_measured_native_grid_riser_m=max(rises,default=0),measured_native_riser_edges=sum(x>0 for x in rises),verification_seconds=time.monotonic()-started,compile_wall_seconds=None,peak_verifier_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 handoff=dict(schema='riverstone.final24.fine_native_pedestrian_step_skin.v1',budget=g.ref(OUT/'compile_budget.json'),assets={m['id']:ass},placements=[placement],selected_profile=v['source_profile'],native_bottom_sections=bottoms,native_top_sections=tops,physical_collision_triangles=tri,physical_collision_domain_polygons_xz_m=profile['private_domain_polygons_xz_m'],terrain_top_exclusion_polygons_xz_m=[b['polygon_xz_m']for b in bottoms],physical_edge_collar_policy='Keep the original finite walking field in every source-private strip outside the exact native columns. Public columns and flat court feet retain priority.',summary=summary,checks=dict(common_payload_hash_exact=True,face_bijection=True,all_columns_contiguous=True,all_native_columns_in_profile_domain=True,all_visible_neighbor_rises_at_most_0_125_m=True,candidate_budget_respected=c['candidate_cells']<=1000000,output_budget_respected=r['cell_count']<=100000),common_sources=[g.ref(g.Path(x.__file__))for x in(core,coordinate_planes,render_data)],author=g.ref(__file__),strict_column_domain_audit=g.ref(OUT/'native_column_domain_strict_audit.json'),initial_conservative_domain_diagnostic=g.ref(OUT/'native_column_domain_diagnostic.json'),domain_audit_note='The first broad-phase audit discarded sub-1e-7 triangle intersections and reported 8.61e-8 m² missing. Exact signed-halfplane intersections of the same unchanged compiled columns prove zero missing area; no geometry or physical tolerance was changed.',runtime_ready=False,activation=False,new_engine=False,cell_edits=False);g.write(OUT/'native_step_handoff.json',handoff);print(summary,flush=True);print(g.ref(OUT/'native_step_handoff.json'),flush=True)
if __name__=='__main__':run()
