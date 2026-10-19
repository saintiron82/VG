"""Bounded plan-space accounting with conservative convex-cell area bounds."""
import sys,json,math,time,resource,collections
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5];sys.path.insert(0,str(ROOT))
from project_native import ref,sha,area
from world_city.concept_city_v3.registered_source.geometry import triangulate
from world_city.runtime_city.checks import placement as geo
CITY=ROOT/'world_city/concept_city_v3';PITCH=.5;BOUNDS=(-540,-540,540,660);NX=int((BOUNDS[2]-BOUNDS[0])/PITCH);NZ=int((BOUNDS[3]-BOUNDS[1])/PITCH);SHAPE=(NZ,NX)
def load(p):return json.loads(p.read_text())
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def empty():return [np.zeros(SHAPE,dtype=bool)for _ in range(3)]
def xform(p,inst):
 c=math.cos(inst['yaw_rad']);s=math.sin(inst['yaw_rad']);x,y,z=inst['position_m'];return [[x+c*q[0]+s*q[1],z-s*q[0]+c*q[1]]for q in p]
def add(layer,poly):
 if len(poly)<3 or geo.polygon_area(poly)<1e-10:return
 # Convex polygon/cell SAT. Polygon edge normals plus cell X/Z axes are complete.
 x0=max(0,math.floor((min(q[0]for q in poly)-BOUNDS[0])/PITCH));x1=min(NX,math.ceil((max(q[0]for q in poly)-BOUNDS[0])/PITCH));z0=max(0,math.floor((min(q[1]for q in poly)-BOUNDS[1])/PITCH));z1=min(NZ,math.ceil((max(q[1]for q in poly)-BOUNDS[1])/PITCH))
 if x0>=x1 or z0>=z1:return
 xs=BOUNDS[0]+(np.arange(x0,x1)+.5)*PITCH;zs=BOUNDS[1]+(np.arange(z0,z1)+.5)*PITCH;shape=(z1-z0,x1-x0);inside=np.ones(shape,bool);full=np.ones(shape,bool);touch=np.ones(shape,bool);sgn=1 if geo.signed_polygon_area(poly)>0 else -1
 for a,b in zip(poly,poly[1:]+poly[:1]):
  dx=b[0]-a[0];dz=b[1]-a[1];v=sgn*(dx*(zs[:,None]-a[1])-dz*(xs[None,:]-a[0]));r=PITCH*.5*(abs(dx)+abs(dz));inside &= v>=-1e-8;full &= v>=r-1e-8;touch &= v>=-r-1e-8
 for dst,src in zip(layer,(full,inside,touch)):dst[z0:z1,x0:x1]|=src

def layer_from(polys,concave=False):
 out=empty()
 for p in polys:
  for q in (triangulate(p)if concave else[p]):add(out,q)
 return out

def count(mask):return int(np.count_nonzero(mask))*PITCH*PITCH
def measure(layer,domain):
 return {'area_lower_bound_m2':count(layer[0]&domain[0]),'center_sample_area_m2':count(layer[1]&domain[1]),'area_upper_bound_m2':count(layer[2]&domain[2])}
def stats_mask(mask,domain):return count(mask&domain[1])

def main():
 start=time.monotonic();candidate=load(HERE/'input/draft_candidate.json');proof=load(HERE/'asset_projection_proofs.json');plan=load(CITY/'registered_source/plan.json');assert candidate['source_plan_sha256']==sha(CITY/'registered_source/plan.json');assert proof['input']==ref(HERE/'input/draft_candidate.json');roof=empty();body=empty();roof_inst=[];body_inst=[];missing_body=[]
 for inst in candidate['common_instances']:
  assert inst.get('scale',[1,1,1])==[1,1,1];a=proof['assets'][inst['asset_key']];rp=a['roof_rectangles_local_xz_m'];bp=a.get('body_rectangles_local_xz_m')
  if rp:
   polys=[xform(p,inst)for p in rp]
   for p in polys:add(roof,p)
   roof_inst.append({'id':inst['id'],'source_pack':inst['source_pack'],'polygons':polys})
  if bp is not None:
   polys=[xform(p,inst)for p in bp]
   for p in polys:add(body,p)
   body_inst.append(inst['id'])
  elif rp:missing_body.append({'id':inst['id'],'source_pack':inst['source_pack'],'reason':a.get('body_proof',{}).get('status','outside_ordinary_body_scope')})
 print('native raster',len(roof_inst),'roof instances',len(body_inst),'body instances',flush=True)
 protected_polys=[r['polygon_xz_m'] for r in plan['spaces']]+[r['polygon_xz_m'] for r in plan['plots'] if r.get('land_use')=='enclosed_noble_compound']
 public_polys=[geo.road_ribbon(a,b,r['width_m']) for r in plan['roads'] for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]
 protected=layer_from(protected_polys,True);public=layer_from(public_polys)
 for k in range(3):protected[k]|=public[k]
 blocks=[];block_center=np.zeros(SHAPE,np.uint8)
 for index,b in enumerate(plan['blocks']):
  domain=layer_from([b['polygon_xz_m']],True);exact=geo.polygon_area(b['polygon_xz_m']);r=measure(roof,domain);s=measure(body,domain)
  for v in (r,s):v.update(coverage_center=v['center_sample_area_m2']/exact,coverage_lower=v['area_lower_bound_m2']/exact,coverage_upper=min(1,v['area_upper_bound_m2']/exact))
  available=[domain[0]&~protected[2],domain[1]&~protected[1],domain[2]&~protected[0]];available_area=count(available[1]);ar=measure(roof,available);ar.update(coverage_center=ar['center_sample_area_m2']/available_area if available_area else None,coverage_lower=ar['area_lower_bound_m2']/count(available[2]) if count(available[2]) else None,coverage_upper=min(1,ar['area_upper_bound_m2']/count(available[0])) if count(available[0]) else None)
  row={'block_id':b['id'],'district_id':b['district_id'],'exact_source_polygon_area_m2':exact,'raster_domain':{'lower_m2':count(domain[0]),'center_m2':count(domain[1]),'upper_m2':count(domain[2])},'native_roof_projection':r,'native_occupied_structural_body_projection':s,'body_definition':'Occupied structure at primary-floor +0.8…+1.8 m for ordinary/density/merchant instances only; hollow interiors remain empty. This is not enclosed building floor area.','unroofed_center_area_m2':count(domain[1]&~roof[1]),'reserved_institution_estate_lane_area_center_m2':count(domain[1]&protected[1]),'ordinary_review_domain':{'area_lower_bound_m2':count(available[0]),'center_sample_area_m2':available_area,'area_upper_bound_m2':count(available[2]),'native_roof_projection':ar,'unroofed_center_area_m2':count(available[1]&~roof[1]),'policy':'Subtract traced institutional/public spaces, noble estate plots and source traffic ribbons before ordinary-density review. Remaining backland can still contain intentional courts/working grounds; no automatic housing target.'},'priority_metric':'Large unroofed area and low roof fraction identify candidates for program review, not an automatic housing target.'};blocks.append(row);block_center[domain[1]]=index+1
 print('blocks',len(blocks),flush=True)
 # Precinct program geometry: exact native masks plus explicit finite reservations.
 precinct_base=HERE.parent/'precinct_r04';precinct_path=precinct_base/'contact_repair_r01/resolved_placements.json';precinct=load(precinct_path);garden_path=CITY/'assemblies/landscape/registered/resolved_placements.json';garden=load(garden_path);productive=load(precinct_base/'productive_frames.json');land_path=CITY/'assemblies/landmarks/registered/repairs/r02_connected_finials/resolved_placements.json';land=load(land_path);recovery_path=CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json';recovery=load(recovery_path);access_path=precinct_base/'access_r02/exterior_access_proposal.json';access=load(access_path);belt_path=precinct_base/'boundary_belts/preflight.json';belt=load(belt_path);program=load(precinct_base/'coverage_plan.json')
 categories=[('native_roof',roof,'Actual cached native roof geometry in fixed draft.'),('public_traffic_reservation',layer_from([geo.road_ribbon(a,b,r['width_m'])for r in plan['roads']for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]),'Registered source lane reservation; current terrain still owns its physical surface.'),('existing_garden_cemetery_orchard',layer_from([s['polygon_xz_m']for s in garden['sites']]),'Finite institutional garden/cemetery/orchard domains with native facilities, already in the draft; every square metre is not a solid object.'),('new_productive_plot',layer_from([f['polygon_xz_m']for f in productive['frames']]),'Five finite productive enclosures with actual native boundary/bed/tree assets; pending integrated view.'),('new_service_court',layer_from([f['polygon_xz_m']for f in precinct['owned_floors']if any(c['id']==f['placement_id']for c in program['compounds'])]),'Actual repaired upward native courtyard/building-floor quads; roofs take priority so covered interiors are excluded.'),('existing_native_floor_or_procession',layer_from([f['polygon_xz_m']for f in land['owned_floors']]+[m['polygon_xz_m']for m in recovery['approaches']['masks']+recovery['landings']['masks']]),'Finite old native floors and exact recovered rendered approach/landing surfaces; no recovered historical route-ID claim.'),('external_access_candidate',layer_from([p for r in access['routes']for p in r['ribbon_polygons_xz_m']+r['join_polygons_xz_m']]),'Explicit 1.8 m route reservations; physical terrain R14/controller acceptance remains separate.'),('native_low_boundary_belt',layer_from([r['native_footprint_xz_m']for r in belt['native_modules']]),'Actual native understory module footprints on preserved ground; no broad lawn completion claim.')]
 rows=[];classmap=np.zeros(SHAPE,np.uint8)
 for site in [s for s in plan['spaces']if s['id']in('SITE_CLERGY','SITE_MONASTERY')]:
  domain=layer_from([site['polygon_xz_m']],True);used=empty();assigned=[]
  for code,(name,layer,note)in enumerate(categories,1):
   lo=layer[0]&domain[0]&~used[2];ce=layer[1]&domain[1]&~used[1];hi=layer[2]&domain[2]&~used[0];assigned.append({'category':name,'area_lower_bound_m2':count(lo),'center_sample_area_m2':count(ce),'area_upper_bound_m2':count(hi),'status':note});classmap[ce]=code
   for i in range(3):used[i]|=layer[i]
  remaining={'area_lower_bound_m2':count(domain[0]&~used[2]),'center_sample_area_m2':count(domain[1]&~used[1]),'area_upper_bound_m2':count(domain[2]&~used[0]),'status':'No accounted roof/facility floor/program reservation in this classification. Remaining source functions do not count as implemented land.'};classmap[domain[1]&~used[1]]=9
  source_site=next(s for s in program['sites']if s['id']==site['id']);roles=collections.defaultdict(float)
  for r in source_site['remaining_subareas']:roles[r['function']]+=r['area_m2']
  exact=geo.polygon_area(site['polygon_xz_m']);rows.append({'site_id':site['id'],'exact_source_polygon_area_m2':exact,'raster_domain_center_m2':count(domain[1]),'classification_order':[r[0]for r in categories],'assigned_nonoverlapping_center_areas':assigned,'unresolved_native_land':remaining,'unresolved_fraction_center':remaining['center_sample_area_m2']/exact,'source_only_program_reservations_before_productive_fit_m2':dict(roles),'source_program_warning':'These original remainder roles overlap subsequent productive fit and are descriptive reservations, not additive implemented area.','failed_requested_productive_frames':productive['failed_frames']});assert abs(sum(r['center_sample_area_m2']for r in assigned)+remaining['center_sample_area_m2']-count(domain[1]))<1e-8
 print('precincts',[(r['site_id'],r['unresolved_fraction_center'])for r in rows],flush=True)
 ranking=sorted(blocks,key=lambda r:r['ordinary_review_domain']['unroofed_center_area_m2'],reverse=True);result={'schema':'riverstone.registered_city.coverage_accounting.v1','input_candidate_snapshot':ref(HERE/'input/draft_candidate.json'),'source_plan':ref(CITY/'registered_source/plan.json'),'native_projection_proofs':ref(HERE/'asset_projection_proofs.json'),'analyzer':ref(Path(__file__)),'status':'Source-bound draft geometry accounting; not actual runtime/view approval.','post_snapshot_ground_repair':{'effective_precinct_pack':ref(precinct_path),'mask_delta':ref(precinct_base/'contact_repair_r01/changed_masks.json'),'scope':'Roof quads and building components are byte-identical; only courtyard/boundary edge masks use the repaired version.'},'ground_inputs':[ref(p)for p in(garden_path,land_path,recovery_path,access_path,belt_path,precinct_base/'productive_frames.json',precinct_base/'coverage_plan.json')],'method':{'pitch_m':PITCH,'bounds_xz_m':BOUNDS,'cell_area_m2':PITCH*PITCH,'center_max_point_to_cell_corner_m':PITCH/math.sqrt(2),'interval_method':'Exact convex cell/polygon SAT. Lower counts a cell only when one union polygon contains the entire cell; upper counts all cells touched by any polygon. Domain intersections and category precedence propagate these conservative bounds. Shared internal decomposition edges can widen bounds.','roof_definition':proof['definitions']['roof'],'body_definition':proof['definitions']['body'],'no_cache_aabb_area_substitution':True,'no_concept_pixel_segmentation':True},'roof_classification_summary':proof['summary'],'counts':{'candidate_instances':len(candidate['common_instances']),'candidate_assets':len(candidate['common_assets']),'roof_instances':len(roof_inst),'body_supported_instances':len(body_inst),'ordinary_blocks':len(blocks)},'ordinary_blocks':blocks,'precincts':rows,'review_priority_largest_unroofed_blocks':[{'block_id':r['block_id'],'unroofed_center_area_m2':r['ordinary_review_domain']['unroofed_center_area_m2'],'roof_center_fraction':r['ordinary_review_domain']['native_roof_projection']['coverage_center'],'ordinary_review_domain_area_m2':r['ordinary_review_domain']['center_sample_area_m2']}for r in ranking],'roof_bearing_instances_outside_body_metric':missing_body,'limits':['No concept roof pixels were segmented; this is a world-plan accounting only.','Unroofed does not mean vacant: streets, courts, productive ground and purposeful open space require program review.','Native occupied body structure is not enclosed floor area or population capacity.','Raster intervals are conservative area bounds, not a claim of sub-cell exactness.','R5 snapshot is a draft; runtime visibility, terrain acceptance and final art remain separate.','One spring-intake stone cover remains unclassified and is not silently counted as roof; all 104 market canopies are included.'],'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};write(HERE/'coverage_accounting.json',result)
 np.savez_compressed(HERE/'plan_raster.npz',roof=roof[1],body=body[1],blocks=block_center,precinct_classes=classmap,pitch=PITCH,bounds=np.array(BOUNDS));print(ref(HERE/'coverage_accounting.json'),'seconds',result['seconds'],'rss',result['peak_rss_kib'])
if __name__=='__main__':main()
