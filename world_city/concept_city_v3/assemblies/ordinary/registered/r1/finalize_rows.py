"""Check actual common mesh boundaries and publish bounded replacement pack."""
import json,math
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
 pack={'schema':'riverstone.registered_density_replacement_pack.v1','status':'compiled_native_candidate_pending_terrain_and_capsule_review','source_plan_path':d['source_plan']['path'],'source_plan_sha256':d['source_plan']['sha256'],'baseline_native_pack':d['baseline_native_pack'],'candidate':ref(HERE/'candidate.json'),'compile_report':ref(HERE/'compile_report.json'),'actual_geometry_proof':ref(HERE/'actual_geometry_proof.json'),'replaced_placement_ids':d['replaced_placement_ids'],'superseded_old_path_ids':d['superseded_old_path_ids'],'source_block_id':d['block']['id'],'assets':assets,'placements':placements,'component_placements':d['placements'],'access_proposals':access,'courts':d['courts'],'court_paths':d['court_paths'],'summary':{**d['summary'],'count_unit':'Native building modules; physical entrances do not establish households.','physical_door_openings':len(access),'runtime_group_placements':len(placements),'new_common_assets':len(report['assets']),'new_common_quads':report['total_unique_quads'],'internal_render_faces':0,'compile_seconds':report['total_seconds'],'peak_rss_mib':report['peak_rss_mib']},'integration_rules':['Remove exactly replaced_placement_ids from the old ordinary pack before adding these16 group placements.','Do not also render component_placements; those records supply precise terrain/body/door ownership.','Use each asset at its native rigid pose. Closed-door interaction anchors remain distinct from public traversal.','No old plan, source cache or old evidence snapshot was changed.'],'limits':['Common union geometry exists; terrain ownership and capsule checks remain pending.','Roof silhouette accounting is native projection and plan-area coverage, not segmentation of the concept image.']};write(HERE/'resolved_placements.json',pack);print(json.dumps({'pack':ref(HERE/'resolved_placements.json'),'summary':pack['summary']},indent=2))
if __name__=='__main__':run()
