"""Seven finite fine-access skins over exact retained R7 estate infrastructure."""
from pathlib import Path
import sys,json,copy,time,collections,math
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
from author_native import estimate_candidates
OUT=Path(__file__).resolve().parent

def write(name,obj):p=OUT/name;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
def refine_internal_joins(skin, external):
 # Sloping independent prism normals leave tiny diagonal seams when sampled.
 # Expand only shared source triangle edges within the unchanged outer domain.
 # This is native source geometry, not an edit to compiled cells or a mesh.
 tris=external['triangulated_top_surface'];counts=collections.Counter()
 def key(a,c):return tuple(sorted(tuple(round(v,7)for v in p)for p in(a,c)))
 for t in tris:
  v=t['vertices_xyz_m']
  for a,c in zip(v,v[1:]+v[:1]):counts[key(a,c)]+=1
 result=copy.deepcopy(skin);refined=[]
 for j,op in enumerate(result):
  poly=op['shape']['polygon'];vs=tris[j]['vertices_xyz_m'];center=np.mean(poly,axis=0);lines=[];offsets=[]
  for k,(a,c)in enumerate(zip(poly,poly[1:]+poly[:1])):
   a=np.array(a);c=np.array(c);d=c-a;n=np.array([-d[1],d[0]])/np.linalg.norm(d)
   if np.dot(center-a,n)<0:n=-n
   off=.0625 if counts[key(vs[k],vs[(k+1)%len(vs)])]>1 else 0.
   lines.append((n,float(np.dot(n,a))-off));offsets.append(off)
  out=[]
  for k in range(len(poly)):
   n0,h0=lines[(k-1)%len(poly)];n1,h1=lines[k];out.append(np.linalg.solve(np.array([n0,n1]),[h0,h1]).tolist())
  op['shape']['polygon']=out;refined.append(dict(operation_id=op['id'],shared_edge_offsets_m=offsets,original_polygon=poly,refined_polygon=out))
 return result,refined

def main():
 started=time.monotonic();projection=load(BASE/'actual_native_projection.json');originalpack=load(CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json');caproot=CITY/'assemblies/property/registered/public_lane_repairs_r01';caps={r['property_id']:r for r in load(caproot/'source_candidates.json')['records']};capcolumns={r['property_id']:r['candidate_columns']for r in load(caproot/'baseline/cap_columns.json')['records']};assets=[];placements=[];ownerrows=[]
 for eid in ['E1','E2','E3','E4','E5','E6','E7']:
  old=next(p for p in projection['instances']if p['id']==eid+':registered_r1:infrastructure');actual=projection['assets'][old['asset_key']];source=load(ROOT/actual['source']['path']);assert sha(ROOT/actual['source']['path'])==actual['source']['sha256'];latest=copy.deepcopy(source);capops=[]
  if eid in caps:
   record=caps[eid];assert record['original_master']==actual['source'];latest=load(ROOT/record['source_master']['path']);capops=latest['components'][0]['operations'][len(source['components'][0]['operations']):];assert all(o['id'].startswith('public_lane_access_skin_cut_')for o in capops)
  ops=source['components'][0]['operations'];skin=[o for o in ops if o['id'].startswith('r1_access_skin_')];baseops=[o for o in ops if not o['id'].startswith('r1_access_skin_')];assert skin;localassets=[];external=next(r for r in originalpack['external_access_surfaces']if r['property_id']==eid);skin,joinledger=refine_internal_joins(skin,external)
  for role,pitch in [('retained_base',.5),('fine_access',.125)]:
   master=copy.deepcopy(source);master['id']='registered_precinct_noble_entry_r01_'+eid.lower()+'_'+role;master['revision']=1;master['components'][0]['operations']=copy.deepcopy(baseops if role=='retained_base'else skin+capops);master.setdefault('metadata',{}).update(derived_from_actual_R7=actual['source'],native_pitch_m=pitch,author=ref(Path(__file__)),repair_role=role,mesh_scaling=False,runtime_ready=False,preserved_later_cap_source=caps[eid]['source_master']if eid in caps else None)
   if role=='fine_access':
    source_ys=[v[1]-old['position_m'][1]for t in external['triangulated_top_surface']for v in t['vertices_xyz_m']];cutlow=min(source_ys)-.75;cuthigh=max(source_ys)+.25
    master['metadata']['internal_source_triangle_join_refinement']=joinledger
    base=load(ROOT/localassets[0]['cache']['path']);full=roof_rectangles(base,{g['material']for g in base['groups']})[0];coords=[q for poly in external['polygon_regions_xz_m']for q in poly];px,py,pz=old['position_m'];clip=b.rect(min(q[0]for q in coords)-px-.25,min(q[1]for q in coords)-pz-.25,max(q[0]for q in coords)-px+.25,max(q[1]for q in coords)-pz+.25);cuts=[]
    for q in full:
     q=geo.convex_intersection(q,clip)
     if geo.polygon_area(q)<1e-8:continue
     cuts.append(q);master['components'][0]['operations'].append(dict(id='retained_base_native_exclusion:'+str(len(cuts)),part='solid',action='cut',shape=dict(kind='extrusion',polygon=[[v[0],-v[1]]for v in q],z_min=cutlow,z_max=cuthigh),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
    master['metadata']['retained_base_actual_native_exclusions_local_xz_m']=cuts
    # Oblique .5 m skin thickness must not leave a low outer fringe beyond
    # the actual top domain. Keep only source-domain vertical columns.
    source_top=[[[v[0]-px,v[1]-pz]for v in poly]for region in external['polygon_regions_xz_m']for poly in b.triangulate(region)]
    outside=terrain.common.subtract([clip],source_top)
    for oi,q in enumerate(outside):
     master['components'][0]['operations'].append(dict(id='source_top_vertical_boundary_cut:'+str(oi),part='solid',action='cut',shape=dict(kind='extrusion',polygon=[[v[0],-v[1]]for v in q],z_min=cutlow,z_max=cuthigh),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
    master['metadata']['source_top_vertical_boundary_cuts_local_xz_m']=outside
    # The prior approved cuts identify exact 0.5 m public columns. A finer
    # source compiler must retire the entire access-only skin in those same
    # columns, rather than leave partial upper skin layers above the old cut.
    for ci,col in enumerate(capcolumns.get(eid,[])):
     q=[[v[0]-px,-(v[1]-pz)]for v in col['polygon_xz_m']]
     master['components'][0]['operations'].append(dict(id='public_lane_full_access_column_cut:'+str(ci),part='solid',action='cut',shape=dict(kind='extrusion',polygon=q,z_min=cutlow,z_max=cuthigh),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
    master['metadata']['full_access_only_public_column_cut_source']=ref(caproot/'baseline/cap_columns.json')if eid in capcolumns else None
    master['metadata']['full_access_only_public_column_cut_count']=len(capcolumns.get(eid,[]))
   sr=write('masters/'+master['id']+'.json',master);estimate=estimate_candidates(master,pitch);visits=estimate['candidate_cells_exact_aabb_visits'];assert visits<5000000,(eid,role,visits);preflight=write('preflight/'+eid+'_'+role+'.json',dict(source=sr,pitch_m=pitch,estimate=estimate,actual_source=actual['source'],actual_cache=actual['cache'],later_cap_cuts=caps.get(eid),common_dependencies=[ref(ROOT/'voxel_character/common/coordinate_planes.py'),ref(ROOT/'voxel_character/common/render_data.py'),ref(ROOT/'voxel_character/common/core.py')]))
   print('compile',eid,role,visits,flush=True);compiled=coordinate_planes.compile_master(master,{'pitch':pitch},max_candidate_cells=5000000,max_output_cells=400000);assert compiled['valid'];mesh=render_data.make_render_data(compiled);cr=write('cache/'+master['id']+'.render.json',mesh);a=dict(id=master['id'],property_id=eid,role=role,source=sr,cache=cr,pitch_m=pitch,master_hash=core.digest(master),candidate_cells=compiled['candidate_cells'],output_cells=len(compiled['cells']),preflight=preflight);assets.append(a);localassets.append(a);placements.append(dict(id='R06_NOBLE_ENTRY_R01:'+eid+':'+role,owner_id=eid,asset_key=a['id'],source=sr,cache=cr,position_m=old['position_m'],yaw_rad=old['yaw_rad'],scale=[1,1,1],role=role))
  ownerrows.append(dict(owner_id=eid,replaces_native_instance_id=old['id'],actual_R7_source=actual['source'],actual_R7_cache=actual['cache'],retained_non_access_operation_count=len(baseops),external_skin_operation_count=len(skin),later_cap_cut_count=len(capops),later_cap_source=caps[eid]['source_master']if eid in caps else None,original_public_endpoint=external['public_lane_endpoint'],source_external_profile=external,status='FINITE_NATIVE_CANDIDATE_PENDING_FULL_SOURCE_GROUND_COLLISION_AND_RUNTIME_CLOSURE'))
 out=dict(schema='riverstone.precinct.noble_entry_batch.v1',status='NATIVE_CANDIDATE_NOT_APPLIED',assets=assets,placements=placements,owners=ownerrows,replacement_ledger=dict(existing_native_placements_removed=[r['replaces_native_instance_id']for r in ownerrows]),sources=dict(actual_native_projection=ref(BASE/'actual_native_projection.json'),original_source_profiles=ref(CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json'),actual_internal_route_acceptance=ref(ROOT/'world_city/concept_city_v3/assemblies/ordinary/registered/district_fabric_r01/noble_internal_route_review_r01/internal_route_acceptance.json'),later_public_lane_caps=ref(caproot/'source_candidates.json')),summary=dict(owners=7,placements=len(placements),candidate_cells=sum(a['candidate_cells']for a in assets),output_cells=sum(a['output_cells']for a in assets),seconds=time.monotonic()-started),activation=False,runtime_ready=False);write('resolved_native_candidate.json',out);print(out['summary'],flush=True)
if __name__=='__main__':main()
