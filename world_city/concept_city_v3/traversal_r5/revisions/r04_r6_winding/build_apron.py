"""Finite collision-only restoration of actual flat native apron tops."""
import pathlib,json,hashlib,sys,math
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3';R02=H.parent/'r02';R03=H.parent/'r03_r6_merchant';A=CITY/'assemblies/waterworks/registered_bridge/south_approach_r02'
from world_city.runtime_city.checks import placement as g
read=lambda p:json.loads(pathlib.Path(p).read_bytes());sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def clean(p):
 out=[]
 for v in p:
  if not out or math.dist(out[-1],v)>1e-10:out.append(v)
 if len(out)>1 and math.dist(out[0],out[-1])<1e-10:out.pop()
 return out

def main():
 scene_path=CITY/'evidence/visual_registered_common_r6_winding_r01/scene.json';assert sha(scene_path)=='b755195c3d66be1101f62c5974427d29618b8199b8f6664edca5d81cd5fc558b'
 scene=read(scene_path);profile=read(A/'profile.json');b=profile['frame']['basis'];origin=profile['frame']['translation'];world=lambda v:[origin[i]+sum(b[i][j]*v[j] for j in range(3)) for i in range(3)];local=lambda v:[sum(b[j][i]*(v[j]-origin[j]) for j in range(3)) for i in range(3)]
 render_path=A/'cache/registered_south_approach_r02_visible_cover.render.json';render=read(render_path);saved=read(R02/'geometry/visible_upward_faces.json');assert sha(render_path)==saved['source']['sha256'];assert saved['frame']==profile['frame'];oldcontract=scene['collision_contracts'][0];assert oldcontract['add_triangles_world_xyz_m']==[t['triangle_xyz_m'] for t in profile['triangles']]
 flat=[]
 for gi,group in enumerate(render['groups']):
  for qi,q in enumerate(group['quads']):
   a,bv,c=q[:3];ny=(bv[2]-a[2])*(c[0]-a[0])-(bv[0]-a[0])*(c[2]-a[2])
   if ny>0 and all(abs(v[1]-1.25)<1e-10 for v in q):flat.append({'group_index':gi,'quad_index':qi,'y':1.25,'polygon_xz_m':[[v[0],v[2]] for v in q]})
 assert flat==[q for q in saved['local_upward_faces'] if abs(q['y']-1.25)<1e-10]
 profiles=[t['polygon_local_xz_m'] for t in profile['triangles']];pieces=[]
 for f in flat:
  remain=[f['polygon_xz_m']]
  for p in profiles:remain=[v for q in remain for v in g.convex_difference(q,p)]
  for p in remain:
   p=clean(p)
   if g.polygon_area(p)>1e-10:pieces.append({'native_group_index':f['group_index'],'native_quad_index':f['quad_index'],'polygon_local_xz_m':p,'polygon_world_xz_m':[[world([x,1.25,z])[i] for i in [0,2]] for x,z in p],'y_m':1.25})
 triangles=[]
 for r in pieces:
  p=r['polygon_local_xz_m']
  if g.signed_polygon_area(p)<0:p=list(reversed(p))
  for i in range(1,len(p)-1):
   tri=[world([x,1.25,z]) for x,z in [p[0],p[i],p[i+1]]]
   if g.polygon_area([[v[0],v[2]] for v in tri])>1e-10:triangles.append(tri)
 polys=[r['polygon_local_xz_m'] for r in pieces];area=sum(g.polygon_area(p) for p in polys);spill=sum(g.uncovered_area_by_union(p,[f['polygon_xz_m'] for f in flat],0) for p in polys);profile_overlap=sum(g.intersection_area(a,c) for a in polys for c in profiles);self_overlap=sum(g.intersection_area(a,c) for i,a in enumerate(polys) for c in polys[i+1:]);assert max(spill,profile_overlap,self_overlap)<1e-10
 diagnosis=read(R03/'diagnostic_miss_trace/evidence/southern_apron_diagnosis.json');regressions=[]
 for r in diagnosis['cases']:
  q=local(r['exact_miss']['center']);owners=[i for i,p in enumerate(polys) if g.point_in_convex_polygon([q[0],q[2]],p,0)];assert owners
  regressions.append({'route_id':r['route_id'],'previous_miss_center_xyz_m':r['exact_miss']['center'],'apron_piece_indices':owners,'expected_floor_y_m':1.25})
 # Exact overlap check against the actually displayed terrain faces near the finite apron.
 worldpolys=[r['polygon_world_xz_m'] for r in pieces];bb=[min(v[i] for p in worldpolys for v in p) for i in [0,1]]+[max(v[i] for p in worldpolys for v in p) for i in [0,1]];contacts=[]
 for mat,vertices in scene['surfaces'].items():
  if mat=='water':continue
  for i in range(0,len(vertices),3):
   tri=vertices[i:i+3]
   if max(v[0] for v in tri)<bb[0] or min(v[0] for v in tri)>bb[2] or max(v[2] for v in tri)<bb[1] or min(v[2] for v in tri)>bb[3]:continue
   if not all(abs(v[1]-1.25)<1e-8 for v in tri):continue
   p=[[v[0],v[2]] for v in tri]
   for j,q in enumerate(worldpolys):
    ar=g.intersection_area(p,q)
    if ar>1e-9:contacts.append({'material':mat,'triangle_index':i//3,'apron_piece':j,'area_m2':ar})
 assert not contacts,contacts
 proof_path=R02/'evidence/exact_bearing_audit.json';proof=read(proof_path);assert proof['status'].startswith('pass')
 payload={'schema':'riverstone.southern_native_flat_apron_collision.v1','status':'finite_native_geometry_candidate_pending_capsule','base_scene':ref(scene_path),'inputs':{'original_profile':ref(A/'profile.json'),'native_render':ref(render_path),'native_compiled':ref(A/'cache/registered_south_approach_r02_visible_cover.compiled.json'),'native_support_proof':ref(proof_path),'previous_failure':ref(R03/'diagnostic_miss_trace/evidence/southern_apron_diagnosis.json'),'builder':ref(pathlib.Path(__file__)),'polygon_helper':ref(ROOT/'world_city/runtime_city/checks/placement.py')},'collision_contract':{'id':'SOUTHERN_NATIVE_FLAT_TERMINAL_APRON','visual_owner':'BRIDGE_MAIN_RIVER:SOUTH_VISIBLE_GRADED_COVER','source_native_render':ref(render_path),'derivation':'Exact actual Y1.25 upward quads minus the eight finite continuous-profile polygons, with zero expansion. Direct Godot winding.','disable_native_mesh_collider_ids':[],'keep_native_mesh_collider_ids':[],'add_triangles_world_xyz_m':triangles,'native_flat_apron_pieces':pieces,'purpose':'Restore only supported native flat sampling apron top left uncovered by whole-cover collider disabling.'},'geometry_audit':{'area_m2':area,'pieces':len(pieces),'triangles':len(triangles),'native_top_spill_m2':spill,'continuous_profile_overlap_m2':profile_overlap,'self_overlap_m2':self_overlap,'actual_scene_coplanar_top_overlap':contacts,'visual_to_collision_max_abs_m':0.0,'original_eight_profile_triangles_unchanged':True,'native_visual_bytes_unchanged':True,'prior_exact_whole_column_support_proof':ref(proof_path)},'positive_point_regressions':regressions,'limits':['Only native Y1.25 flat apron tops are restored; the rest of the sampled cover stays non-colliding.','No controller or route change, no additional step-up, and no full-city or moving-span traversal guarantee.']}
 write(H/'supplemental_apron_contract.json',payload);print(json.dumps({'contract':ref(H/'supplemental_apron_contract.json'),'geometry_audit':payload['geometry_audit']},indent=2))
if __name__=='__main__':main()
