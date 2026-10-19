#!/usr/bin/env python3
"""Reconstruct every crop face and independently prove exhaustive local selection."""
import argparse,hashlib,json,pathlib,sys,math
sys.dont_write_bytecode=True
import numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(H))
import prepare as prep

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=pathlib.Path,required=True);ap.add_argument('--evidence',type=pathlib.Path,required=True);args=ap.parse_args();p=args.prepared.resolve();e=args.evidence.resolve();d=prep.read(p);request=prep.read(d['sources']['request']['path']);assert p.is_relative_to(H)and e.is_relative_to(H)
 for r in d['sources'].values():prep.resolve(r)
 for path,digest in d['implementation_hashes'].items():assert prep.sha(ROOT/path)==digest
 for a in d['assets'].values():assert prep.sha(ROOT/a['render_path'])==a['render_sha256']
 assert prep.sha(p.parent/'Traversal.gd')==prep.sha(prep.BASE/'Traversal.gd')
 assert prep.sha(p.parent/'RenderData.gd')==prep.sha(ROOT/'voxel_character/common/preview/RenderData.gd')
 scene=prep.read(d['sources']['base_scene']['path']);patch=prep.read(d['sources']['finite_patch']['path']);index=prep.read(d['sources']['visual_index']['path']);native_assets,native_instances,_=prep.compose_natives(scene,index,{})
 edits={(r['material'],r['triangle_index']):r['replacement_triangles_xyz_m']for r in patch['surface_edits']};removed=set(patch.get('removed_foundation_proxy_ids',[]));crops=[]
 for row in d['coverage']['collision_audit']:
  group=row['group'];key='SCENE:R9:GATE:'+group;geo=prep.read(ROOT/d['assets'][key]['render_path']);origin=d['placements'][key]['position_m'];bb=row['bounds_xz_m'];actual=[]
  assert len(geo['triangles'])==len(geo['source_face_indices'])
  for face,local in zip(geo['source_face_indices'],geo['triangles']):
   mat=face['material'];assert mat!='water'
   if 'appended_triangle_index'in face:
    i=face['appended_triangle_index'];tri=patch['appended_surfaces'][mat][i*3:i*3+3];ident=('append',mat,i,None)
   else:
    i=face['base_triangle_index'];j=face['replacement_index'];tri=scene['surfaces'][mat][i*3:i*3+3]if j is None else edits[(mat,i)][j];ident=('base',mat,i,j)
   world=[[v[k]+origin[k]for k in range(3)]for v in local];assert world==[tri[0],tri[2],tri[1]],(group,ident,'source triangle mismatch');actual.append(ident)
  expected=[]
  for mat,verts in scene['surfaces'].items():
   if mat=='water':continue
   arr=np.asarray(verts,dtype=np.float64).reshape(-1,3,3);mask=(arr[:,:,0].min(1)<=bb[2])&(arr[:,:,0].max(1)>=bb[0])&(arr[:,:,2].min(1)<=bb[3])&(arr[:,:,2].max(1)>=bb[1]);indices=set(map(int,np.nonzero(mask)[0]));indices.update(i for m,i in edits if m==mat)
   for i in sorted(indices):
    if(mat,i)in edits:
     for j,t in enumerate(edits[(mat,i)]):
      if prep.b.overlaps(prep.b.bounds(t),bb):expected.append(('base',mat,i,j))
    else:expected.append(('base',mat,i,None))
   del arr,mask
  for mat,verts in patch['appended_surfaces'].items():
   if mat=='water':continue
   for i in range(0,len(verts),3):
    if prep.b.overlaps(prep.b.bounds(verts[i:i+3]),bb):expected.append(('append',mat,i//3,None))
  assert set(actual)==set(expected)and len(actual)==len(expected),(group,'in-bounds source-face omission/duplication',len(actual),len(expected))
  native_expected=[]
  for item in native_instances:
   a=native_assets[item['asset_key']];bounds=a.get('bounds')or prep.read(ROOT/a['render_path'])['bounds']
   if not prep.b.overlaps(prep.b.instance_bounds(item,bounds),bb):continue
   native_expected.append(item['id']);record=d['placements'][item['id']]
   assert record['asset_key']==item['asset_key']and record['position_m']==item['position_m']and math.isclose(math.radians(record['yaw_deg']),item.get('yaw_rad',0),abs_tol=1e-14)
   if 'transform'in item:assert record['transform']==item['transform']
  assert set(native_expected)==set(row['native_ids'])and len(native_expected)==len(row['native_ids'])
  box_expected=[]
  for item in scene['boxes']:
   if item['id']in removed:continue
   bounds={'min':[-v/2 for v in item['size_m']],'max':[v/2 for v in item['size_m']]}
   if not prep.b.overlaps(prep.b.instance_bounds(item,bounds),bb):continue
   box_expected.append(item['id']);record=d['buildings'][item['id']];assert record['position_m']==item['position_m']and record['boxes']==[bounds]and record['yaw_rad']==item.get('yaw_rad',0)
  assert set(box_expected)==set(row['box_ids'])and len(box_expected)==len(row['box_ids'])
  margin=min(min(pt[0]-bb[0],pt[2]-bb[1],bb[2]-pt[0],bb[3]-pt[2])for r in d['routes']if r['group']==group for pt in r['points'])
  assert margin>math.hypot(request['cart_fixture']['width_m'],request['cart_fixture']['length_m'])/2+.05
  crops.append({'group':group,'whole_resolved_triangles':len(actual),'replacement_faces':sum(x[3]is not None for x in actual),'appended_faces':sum(x[0]=='append'for x in actual),'exact_native_instances':len(native_expected),'actual_boxes':len(box_expected),'minimum_waypoint_crop_margin_m':margin,'source_face_completeness':'pass','local_translation_exact':geo['local_origin_proof']['applied_world_roundtrip_error_m']==0})
 from audit_graph_authorship import verify
 producer_routes=verify(request)
 for r in request['routes']:
  if 'gate_frame_stations_longitudinal_lateral_m'in r:
   g=next(g for g in request['gates']if g['id']in r['source_road_ids']);c=g['opening_center_xyz_m'];f=g['travel_unit_xz'];t=[-f[1],f[0]]
   expected=[[c[0]+f[0]*a+t[0]*b,c[1],c[2]+f[1]*a+t[1]*b]for a,b in r['gate_frame_stations_longitudinal_lateral_m']];assert r['points']==expected,'Gate-frame probe derivation changed'
  else:assert r['points']==producer_routes[r['id']]['points'],'Producer full/junction path changed in QA'
 authored={r['id']:r for r in request['routes']}
 for r in d['routes']:
  if r['group']=='ISOLATED_CONTROL':continue
  reverse=r['id'].endswith('_REVERSE');name=r['id'][:-8]if reverse else r['id'];assert name in authored;expected=list(reversed(authored[name]['points']))if reverse else authored[name]['points'];assert r['points']==expected,'QA changed source route'
 results={};allpass=True
 for kind in ['capsule','cart']:
  path=e/(kind+'.json')
  if not path.exists():continue
  r=prep.read(path);assert r['prepared_sha256']==prep.sha(p);allpass&=r['status']=='pass'
  if kind=='capsule':assert {x['id']for x in r['routes']}=={x['id']for x in d['routes']}
  results[kind]={'path':str(path.relative_to(ROOT)),'sha256':prep.sha(path),'status':r['status'],'summary':r.get('summary'),'routes':[{'id':x['id'],'status':x['status'],'pass':x['pass'],'first_failure':x.get('first_failure'),'not_on_floor_frames':x.get('not_on_floor_frames'),'ground_ray_miss_frames':x.get('ground_ray_miss_frames'),'obstacle_contact_ids':x.get('obstacle_contact_ids'),'max_centerline_error_m':x.get('max_centerline_error_m')}for x in r['routes']]}
 report={'schema':'riverstone.r9.gate_runtime_evidence_audit.v1','status':'PASS'if allpass and set(results)=={'capsule'} else'RUNTIME_FAILURE_OR_PARTIAL_RETAINED','prepared':prep.ref(p),'source_identity_checks':'PASS','probe_authorship':'Every 0.25 m sample lies on the two exact public vectors within unchanged 50 um XZ / 20 mm height bounds; each branch is exactly 3 m; restored junction lies in all routes','full_source_face_parity':'PASS','native_composition_and_collider_completeness':'PASS','exact_authored_route_parity':'PASS','unchanged_capsule_controller_and_common_loader':True,'source_bound_crops':crops,'results':results,'limits':d['assumptions']}
 target=e/'audit.json';prep.write(target,report);print(json.dumps({'status':report['status'],'crops':len(crops),'triangles':sum(x['whole_resolved_triangles']for x in crops),'results':{k:{'status':v['status'],'summary':v['summary']}for k,v in results.items()}},indent=2))
if __name__=='__main__':main()
