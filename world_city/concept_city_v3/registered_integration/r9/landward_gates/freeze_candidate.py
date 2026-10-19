"""Freeze source-bound gate inputs. Refuse to overwrite previous QA candidates."""
import json,hashlib,shutil,sys,subprocess,platform,math
from pathlib import Path
H=Path(__file__).parent;ROOT=H.parents[4];SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):
 with p.open('x')as f:json.dump(d,f,separators=(',',':'));f.write('\n')
def main():
 out=H/(sys.argv[1]if len(sys.argv)>1 else 'candidate_r01')
 if '--retessellate-west-apron'in sys.argv:subprocess.run([sys.executable,'-m','world_city.concept_city_v3.registered_integration.r9.landward_gates.retessellate_west_apron'],check=True)
 for route in read(H/'routes.json')['routes']:
  peak=max(abs(b[1]-a[1])/math.hypot(b[0]-a[0],b[2]-a[2])for a,b in zip(route['points'],route['points'][1:]));assert peak<=.100001,('New full-route grade preflight',route['id'],peak)
 subprocess.run([sys.executable,'-m','world_city.concept_city_v3.registered_integration.r9.landward_gates.canonicalize_road_vertices'],check=True)
 subprocess.run([sys.executable,'-m','world_city.concept_city_v3.registered_integration.r9.landward_gates.audit_ribbon_topology','.'],check=True)
 topology=read(H/'float32_ribbon_topology_audit.json');assert topology['status']=='PASS',('Public road topology regression failed',topology['status'])
 preflight=H/(out.name+'_before_freeze_float32.json')
 subprocess.run([sys.executable,str(H.parent/'gate_runtime_validation/validate_float32.py'),'--patch',str(H/'surface_patch.json'),'--report',str(preflight)],check=True)
 out.mkdir();shutil.copyfile(preflight,out/'float32_preflight.json')
 for name in ['surface_patch.json','ground_ownership.json','routes.json','farm_pack.json','source_tests.json','float32_filter_report.json','float32_ribbon_topology_audit.json','road_vertex_canonicalization.json']:
  shutil.copyfile(H/name,out/name)
 if '--retessellate-west-apron'in sys.argv:shutil.copyfile(H/'coplanar_retriangulation.json',out/'coplanar_retriangulation.json')
 for name in ['pack.json','bridge_pack.json']:
  shutil.copyfile(H/'native_pack'/name,out/('gate_pack.json'if name=='pack.json'else name))
 oldindex=H.parent/'integration_r02_camera/index.json';index=read(oldindex)
 rows=read(H.parent/'landmarks/attachment_ledger.json')['rows'];walls=['FORT_CURTAIN_12_0_05','FORT_CURTAIN_26_0_00'];upper=[r for r in rows if r['native_parent_id']in walls]
 write(out/'upper_retirement_pack.json',dict(schema='riverstone.city.visual_addendum.v1',base_scene_sha256=SHA,common_assets={},add_instances=[],remove_instance_ids=[r['id']for r in upper]))
 for name in ['gate_pack.json','bridge_pack.json','farm_pack.json','upper_retirement_pack.json']:index['packs'].append(ref(out/name))
 write(out/'index.json',index)
 data=read(out/'routes.json');data.update(schema='riverstone.r9.gate_runtime_request.v1',finite_patch=ref(out/'surface_patch.json'),visual_index=ref(out/'index.json'),collision_margin_m=8,producer_sources={'ownership':ref(out/'ground_ownership.json'),'gate_geometry_tests':ref(H/'native_pack/test_results.json'),'bridge_geometry_tests':ref(H/'native_pack/bridge_test_results.json')})
 for r in data['routes']:
  r['gate_id']=r['group']+'_GATE_PUBLIC_CORRIDOR';r['public_access']='public_pedestrian_and_cart_candidate';r['design_clear_width_m']=6.;r['points'][r['gate_waypoint_index']]=next(g['opening_center_xyz_m']for g in data['gates']if g['id']==r['gate_id'])
 planpath=ROOT/'world_city/concept_city_v3/registered_source/plan.json';plan=read(planpath)
 from .build_corridors import Ground,xz
 from world_city.runtime_city.checks import placement as geo
 patch=read(out/'surface_patch.json');newground=Ground([dict(material=m,triangle_index=i//3,triangle=vs[i:i+3])for m,vs in patch['appended_surfaces'].items()for i in range(0,len(vs),3)]);oldground=Ground(read(H/'local_source_faces.json'));bridge=next(o['polygon_xz_m']for o in patch['ownership']if o['id']=='EAST_NATIVE_CANAL_BRIDGE')
 def support(v):
  q=xz(v)
  if geo.point_in_convex_polygon(q,bridge,1e-7):y=3.
  else:
   try:y=newground.at(q)
   except ValueError:y=oldground.at(q)
  return [v[0],y,v[2]]

 for side,rid,indices in [('WEST','CASTLE_APPROACH',range(18,23)),('EAST','EAST_WALL_SERVICE',range(3,14))]:
  road=next(r for r in plan['roads']if r['id']==rid)
  data['routes'].append(dict(id=side+'_EXISTING_PUBLIC_JUNCTION_THROUGH',group=side,points=[support(road['resolved_world_xyz_m'][i])for i in indices],source_original_points=[road['resolved_world_xyz_m'][i]for i in indices],source_road_ids=[rid],source_plan=ref(planpath),source_station_indices=list(indices),design_clear_width_m=road['width_m'],test_scope='Existing road through affected finite-replacement junction; rerun both directions rather than inherit old results.',public_access='existing_public_road_junction',cart_test=True))
 data['cart_fixture']=read(H.parent/'gate_runtime_validation/INPUT_CONTRACT.json')['cart_fixture'];data['negative_controls']=[]
 # routes.json is already a mutable provisional copy within this not-yet-frozen directory.
 (out/'routes.json').unlink();write(out/'routes.json',data)
 original={p['id']:p for p in read(H/'base_context.json')['common_instances']};ledger=[];base_ref=ref(ROOT/'world_city/concept_city_v3/evidence/r8_final110_runtime_r01/scene.json')
 for name in ['gate_pack.json','farm_pack.json']:
  for pid in read(out/name)['remove_instance_ids']:ledger.append(dict(id=pid,source=base_ref,original_instance=original[pid],reason='Replaced bounded public gateway corridor'if name=='gate_pack.json'else 'Road and farm ownership intersects existing woodland collider'))
 landmarks=read(H.parent/'landmarks/pack.json');added={p['id']:p for p in landmarks['add_instances']}
 for r in upper:ledger.append(dict(id=r['id'],source=ref(H.parent/'landmarks/pack.json'),original_instance=added[r['id']],attachment_record=r,reason='Retired curtain parent replaced by real gate aperture'))
 write(out/'retirement_ledger.json',dict(base_scene_sha256=SHA,records=ledger))
 snapshot=out/'source_snapshot';snapshot.mkdir()
 producer_files=['build_corridors.py','filter_float32.py','freeze_candidate.py','check_candidates.py','check_support.py','audit_revision.py','actual_profile_audit.py','audit_lane_surfaces.py','audit_native_boundaries.py','audit_ribbon_topology.py','canonicalize_road_vertices.py','retessellate_west_apron.py','inspect_surfaces.py','native_pack/author.py','native_pack/author_bridge.py']
 copied=[]
 for name in producer_files:
  src=H/name;dst=snapshot/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);copied.append(dict(original=ref(src),snapshot=ref(dst)))
 import numpy
 components={}
 for packname in ['gate_pack.json','bridge_pack.json','farm_pack.json']:
  for key,asset in read(out/packname).get('common_assets',{}).items():components[key]={k:asset[k]for k in ['master_path','master_sha256','render_path','render_sha256']if k in asset}
 manifest=dict(schema='riverstone.landward_gate.producer_snapshot.v1',candidate=out.name,python=sys.version,platform=platform.platform(),numpy=numpy.__version__,producer_files=copied,inputs={'base_scene':data['base_scene'],'source_plan':ref(planpath),'base_context':ref(H/'base_context.json'),'local_source_faces':ref(H/'local_source_faces.json'),'asset_bounds':ref(H/'asset_bounds.json'),'placement_geometry':ref(ROOT/'world_city/runtime_city/checks/placement.py'),'finite_geometry':ref(ROOT/'world_city/concept_city_v3/review_geometry.py'),'source_geometry':ref(ROOT/'world_city/concept_city_v3/registered_source/geometry.py')},component_sources=components,commands=['python -m world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors','python -m world_city.concept_city_v3.registered_integration.r9.landward_gates.filter_float32','python -m world_city.concept_city_v3.registered_integration.r9.landward_gates.freeze_candidate '+' '.join(sys.argv[1:])],ownership='Only bounded new landward_gates files; old candidates immutable')
 write(snapshot/'manifest.json',manifest)
 write(out/'FROZEN.json',dict(producer_snapshot=ref(snapshot/'manifest.json'),status='IMMUTABLE_SOURCE_CANDIDATE_RUNTIME_PENDING',parent_index=ref(oldindex),files={p.name:sha(p)for p in sorted(out.glob('*.json'))},count_retired=len(ledger)))
 print(out);print(json.dumps(ref(out/'routes.json')))
if __name__=='__main__':main()
