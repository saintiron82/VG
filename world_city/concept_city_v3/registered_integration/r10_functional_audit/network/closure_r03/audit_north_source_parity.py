"""Carry-forward source parity for the already certified northern turn crop."""
import json,pathlib,hashlib,math,numpy as np
O=pathlib.Path(__file__).resolve().parent;N=O.parent;ROOT=N.parents[4];read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def resolve(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==r['sha256'];return p
sel=ROOT/'world_city/concept_city_v3/traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04/selected_all493_bound_r02.json';s=read(sel);id='JOIN:NORTH_WATERKEEPER:-1:NORTH_BACK_LANE:82:INTERIOR:A';r=next(r for r in s['routes']if r['id']==id);floor=s['placements'][r['placement_ids'][0]];asset=s['assets'][floor['asset_key']];gp=resolve({'path':asset['render_path'],'sha256':asset['render_sha256']});geo=read(gp);faces={tuple(x)for x in geo['source_face_indices']};boxes=geo['corridor_boxes_xz_m'];I=N.parent/'integration_r04';index=read(I/'index.json');patch=read(I/'surface_patch.json');assert index['base_scene_sha256']==s['sources']['scene']['sha256']==patch['base_scene_sha256'];sources=[ref(sel),ref(gp),ref(I/'index.json'),ref(I/'surface_patch.json')]
def overlaps(a,b):return a[0]<=b[2]and a[2]>=b[0]and a[1]<=b[3]and a[3]>=b[1]
def bbox(t):
 q=np.array(t);return[q[:,0].min(),q[:,2].min(),q[:,0].max(),q[:,2].max()]
changed_faces=[x for x in patch['surface_edits']if(x['material'],x['triangle_index'])in faces];appended=[]
for mat,verts in patch['appended_surfaces'].items():
 if mat=='water':continue
 for i in range(0,len(verts),3):
  if any(overlaps(bbox(verts[i:i+3]),b)for b in boxes):appended.append([mat,i//3])
ids=set(r['placement_ids'][1:]);removed=[];replaced=[];entering=[];base_scene=read(resolve(s['sources']['scene']));assets=base_scene['common_assets'];del base_scene
for ent in index['packs']:
 p=resolve(ent);sources.append(ref(p));pack=read(p);assets.update(pack.get('common_assets',{}));removed.extend(id for id in pack.get('remove_instance_ids',[])if id in ids);replaced.extend(x['id']for x in pack.get('replace_instances',[])if x['id']in ids)
 for item in pack.get('add_instances',[])+[dict(x,position_m=x['expected_position_m'],yaw_rad=x.get('expected_yaw_rad',0))for x in pack.get('replace_instances',[])]:
  a=assets[item['asset_key']];b=a.get('bounds')
  if not b:
   rp=resolve({'path':a['render_path'],'sha256':a['render_sha256']});b=read(rp)['bounds']
  v=np.array([[x,0,z]for x in[b['min'][0],b['max'][0]]for z in[b['min'][2],b['max'][2]]]);yaw=item.get('yaw_rad',0);c=math.cos(yaw);sn=math.sin(yaw);q=v@np.array([[c,0,-sn],[0,1,0],[sn,0,c]])+item['position_m']
  if any(overlaps(bbox(q),bb)for bb in boxes):entering.append(item['id'])
removed_boxes=sorted(set(r['building_ids']).intersection(patch.get('removed_foundation_proxy_ids',[])))
for pid in ids:
 a=s['assets'][s['placements'][pid]['asset_key']];resolve({'path':a['render_path'],'sha256':a['render_sha256']})
assert not any([changed_faces,appended,removed,replaced,entering,removed_boxes]),(len(changed_faces),appended,removed,replaced,entering,removed_boxes)
report={'schema':'riverstone.r10.north_certificate_source_carryforward.v1','status':'PASS','route_id':id,'base_scene_sha256':s['sources']['scene']['sha256'],'retained_exact_floor_triangles':len(faces),'retained_native_instance_ids':sorted(ids),'retained_box_ids':r['building_ids'],'surface_faces_replaced_in_crop':0,'appended_support_triangles_in_crop':0,'native_instances_removed_or_replaced_in_crop':0,'new_or_relocated_native_bounds_entering_crop':0,'foundation_boxes_removed_in_crop':0,'crop_boxes_xz_m':boxes,'sources':sources,'limits':['Existing positive runtime remains the original bound r8 certificate. This report proves its collision neighborhood survives final composition without edited/added source primitives; it is not a new runtime run.','Graph attachment source endpoints satisfy50um XZ/20mm Y. Sparse interior graph heights are not overwritten.']};(O/'north_source_parity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in['status','retained_exact_floor_triangles','retained_native_instance_ids','native_instances_removed_or_replaced_in_crop']},indent=2))
