"""Check actual common mesh boundaries and publish bounded replacement pack."""
import json,math,sys,copy
from pathlib import Path
from .compile_rows import inverse,pose
from world_city.concept_city_v3.assemblies.ordinary.resolve_cached import ROOFS
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/"validation"))
from check_landmark_access_candidate import slab_rectangles,transform
from .author_density import HERE,ROOT,ref,write
from voxel_character.common import core

def face_bijection(c,r):
 pitch=r['pitch'];cells={tuple(row[:3]) for row in c['cells']};faces=set()
 for p in cells:
  for axis in range(3):
   for sign in(-1,1):
    q=list(p);q[axis]+=sign
    if tuple(q) not in cells:faces.add((*p,axis,sign))
 count=len(faces);bad=0
 for g in r['groups']:
  for quad in g['quads']:
   pts=[[int(round(v/pitch)) for v in q] for q in quad];u=[quad[1][k]-quad[0][k] for k in range(3)];v=[quad[2][k]-quad[1][k] for k in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];axis=max(range(3),key=lambda k:abs(n[k]));sign=1 if n[axis]>0 else -1;other=[k for k in range(3) if k!=axis];plane=pts[0][axis]
   for a in range(min(p[other[0]] for p in pts),max(p[other[0]] for p in pts)):
    for b in range(min(p[other[1]] for p in pts),max(p[other[1]] for p in pts)):
     p=[0,0,0];p[axis]=plane-1 if sign>0 else plane;p[other[0]]=a;p[other[1]]=b;key=(*p,axis,sign)
     if key in faces:faces.remove(key)
     else:bad+=1
 assert not bad and not faces,(bad,len(faces));return {'actual_exterior_unit_faces':count,'missing_unit_faces':len(faces),'duplicate_or_internal_unit_faces':bad}

def run():
 d=json.loads((HERE/'candidate.json').read_text());pre=json.loads((HERE/'compile_preflight.json').read_text());report=json.loads((HERE/'compile_report.json').read_text());members={p['id']:p for p in d['placements']};assets=report['assets'].copy();proofs=[];placements=[]
 assert pre['candidate']==ref(HERE/'candidate.json')
 for key,a in report['assets'].items():
  c=json.loads((ROOT/a['compiled_path']).read_text());r=json.loads((ROOT/a['render_path']).read_text());assert c['valid'] and core.digest(c['cells'])==c['payload_hash']==r['payload_hash'];proofs.append({'asset_key':key,'compiled':ref(ROOT/a['compiled_path']),'render':ref(ROOT/a['render_path']),**face_bijection(c,r)})
 for inst in pre['placements']:
  if inst['kind']=='existing_single_cache':
   p=inst['placement'].copy();assets[p['asset_key']]=d['assets'][p['asset_key']];p['id']=inst['group_id'];p['source_member_ids']=inst['source_member_ids'];placements.append(p);continue
  ps=[members[k] for k in inst['source_member_ids']];placements.append({'id':inst['group_id'],'asset_key':inst['variant_key'],'position_m':inst['position_m'],'yaw_rad':inst['yaw_rad'],'transform':inst['transform'],'scale':[1,1,1],'source_member_ids':inst['source_member_ids'],'source_block_id':d['block']['id'],'source_district_id':'D_POOR','source_plot_id':inst['group_id'],'pad_floor_y_m':2.5,'actual_body_footprint_polygons_xz_m':[p['actual_body_footprint_xz_m'] for p in ps],'actual_outer_footprint_polygons_xz_m':[p['actual_outer_footprint_xz_m'] for p in ps],'actual_entrance_ids':[i for p in ps for i in p['actual_entrance_ids']],'footprint_policy':'Use exact component polygon union; the group AABB is not occupied ground.','assembly_group_id':inst['group_id'],'native_union_verified':True})
 access=[]
 for p in d['access_proposals']:
  q=p.copy();q['physical_opening_only']=True;q['population_or_household_inference']=False;q['facade_side']='+Z_front';q['access_role']='source_primary_front_interaction' if q['id'].endswith(':0') else 'secondary_front_opening_use_unassigned';q['portal_status']='closed exterior native door; no through-interior public route claim';access.append(q)
 proof={'schema':'riverstone.native_row_actual_mesh_proof.v1','candidate':ref(HERE/'candidate.json'),'compile_report':ref(HERE/'compile_report.json'),'assets':proofs,'all_face_bijections_pass':True,'internal_render_unit_faces':sum(p['duplicate_or_internal_unit_faces'] for p in proofs),'missing_render_unit_faces':sum(p['missing_unit_faces'] for p in proofs),'limits':['Actual native source and common union mesh proof only; no capsule or finished-ground promotion.','Physical door anchors do not establish household counts or traversable interiors.']};write(HERE/'actual_geometry_proof.json',proof)
 pack={'schema':'riverstone.registered_density_replacement_pack.v1','status':'compiled_native_candidate_pending_terrain_and_capsule_review','source_plan_path':d['source_plan']['path'],'source_plan_sha256':d['source_plan']['sha256'],'baseline_native_pack':d['baseline_native_pack'],'candidate':ref(HERE/'candidate.json'),'compile_report':ref(HERE/'compile_report.json'),'actual_geometry_proof':ref(HERE/'actual_geometry_proof.json'),'replaced_placement_ids':d['replaced_placement_ids'],'superseded_old_path_ids':d['superseded_old_path_ids'],'source_block_id':d['block']['id'],'assets':assets,'placements':placements,'component_placements':d['placements'],'access_proposals':access,'courts':d['courts'],'court_paths':d['court_paths'],'summary':{**d['summary'],'count_unit':'Native building modules; physical entrances do not establish households.','physical_door_openings':len(access),'runtime_group_placements':len(placements),'new_common_assets':len(report['assets']),'new_common_quads':report['total_unique_quads'],'internal_render_faces':0,'compile_seconds':report['total_seconds'],'peak_rss_mib':report['peak_rss_mib']},'integration_rules':['Remove exactly replaced_placement_ids from the old ordinary pack before adding these16 group placements.','Do not also render component_placements; those records supply precise terrain/body/door ownership.','Use each asset at its native rigid pose. Closed-door interaction anchors remain distinct from public traversal.','No old plan, source cache or old evidence snapshot was changed.'],'limits':['Common union geometry exists; terrain ownership and capsule checks remain pending.','Roof silhouette accounting is native projection and plan-area coverage, not segmentation of the concept image.']}

 # Recover exact runtime-door and native foundation records, never a group AABB.
 renders={k:json.loads((ROOT/a['render_path']).read_text()) for k,a in assets.items()};group_by_member={mid:p for p in placements for mid in p['source_member_ids']}
 for j,p in enumerate(placements):
  palette='clay_red' if j%5==0 else 'slate_gray' if j%5==3 else 'wood_brown'
  p.update(compiled_asset_ref=str(ROOT/assets[p['asset_key']]['render_path']),render_sha256=assets[p['asset_key']]['render_sha256'],palette_id=palette,palette_override=dict(zip(('slate','slate_light','slate_dark','slate_worn'),ROOFS[palette])))
 for door in access:
  p=group_by_member[door['source_mass_id']];local=core.apply(inverse(pose(p)),door['actual_door_xyz_m']);x,y,z=local;proof=[]
  for gi,group in enumerate(renders[p['asset_key']]['groups']):
   if group['material'] not in ('door','door_dark'):continue
   for qi,q in enumerate(group['quads']):
    lo=[min(v[i] for v in q) for i in range(3)];hi=[max(v[i] for v in q) for i in range(3)]
    if abs(hi[2]-lo[2])<1e-8 and abs(lo[2]-z)<1e-6 and lo[0]-1e-6<=x<=hi[0]+1e-6 and abs(lo[1]-y)<1e-6 and hi[1]>=y+1-1e-6:proof.append(dict(group_index=gi,quad_index=qi,vertices_local_m=q))
  assert proof,(door['id'],local)
  door.update(actual_runtime_group_id=p['id'],actual_runtime_door_local_xyz_m=local,actual_cached_threshold_evidence=proof,render_sha256=p['render_sha256'])
 masks=[]
 for p in placements:
  floor=2.5-p['position_m'][1];polys=[transform(poly,p) for poly in slab_rectangles(renders[p['asset_key']],floor-.01,floor-.001)];assert polys
  masks.append(dict(owner_id=p['id'],kind='actual_native_foundation_at_threshold_floor',floor_y_m=2.5,terrain_exclusion_regions_xz_m=polys,terrain_exclusion_union_required=True,render_sha256=p['render_sha256'],foundation_embed_m=floor))
 grounds=json.loads((HERE/'owned_grounds.json').read_text())
 pack.update(source_block_id='BLOCK_015',source_subarea_id='BLOCK_015_EAST',ownership_masks=masks,ground_source=ref(HERE/'owned_grounds.json'),ground_ownership_records=grounds['grounds'],ground_service_paths=grounds['paths'],retained_public_surface_regions=next(x for x in grounds['ownership_ledger'] if x['category']=='retained_public_streets'),runtime_ready=False,applied_to_scene=False,recovery_provenance={'kind':'Reconstructed from restored version 5 baseline and retained bounded specs after executor loss. New checks and seals required.','lost_prior_pack_sha256':'ebb45cfd6faf403eb5c6a56b346354f99959780ed8e8ff7df5cea0cb721f9e79','prior_bytes_restored':False,'density_and_module_counts_reproduced':True},status='reconstructed_native_base_with_one_known_canal_route_pending_separate_addendum')
 pack['integration_rules']=['Replace exactly the 37 old IDs and add only the 10 group placements.','Do not render component_placements alongside groups.','Apply route_repair_01 addendum before any access promotion.','Exact water and public surface ownership retain priority; no canal fill.','Rear-ground records are source intents, not compiled facilities.']
 write(HERE/'resolved_placements.json',pack);print(json.dumps({'pack':ref(HERE/'resolved_placements.json'),'summary':pack['summary'],'foundation_regions':sum(len(m['terrain_exclusion_regions_xz_m']) for m in masks)},indent=2))

if __name__=='__main__':run()
