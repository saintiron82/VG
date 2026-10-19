"""Independent bounded audit; writes only beside this file. No author/build run."""
from pathlib import Path
import hashlib,json,math
HERE=Path(__file__).resolve().parent
R=next(p for p in HERE.parents if (p/'world_city').is_dir())
U=R/'world_city/concept_city_v3/near_detail_r01/city_upgrade'
D=R/'world_city/concept_city_v3/playable_detail_r01'
N=U/'native_access_detail_r01'
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(name,data): (HERE/name).write_text(json.dumps(data,indent=2)+'\n')
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def rectangle_overlap(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
runtime=read(D/'native_access_catalog.json');plan_path=R/runtime['source_plan_path'];cat_path=R/runtime['module_catalog_path'];plan=read(plan_path);cat=read(cat_path);index=read(D/'generated/tile_r01/index.json');mods={m['id']:m for m in cat['modules']}
paths=[D/'CityWorldAccessDetail.gd',D/'RoadSurfaceSource.gd',U/'road_surfaces/RoadSurfaceSource.gd',D/'near_catalog.json',D/'validation/detail_cases.json',D/'character/runtime/LilyController.gd',D/'CityWorldRoadDetail.gd',D/'CityWorld.gd',D/'SurfacePatchMesh.gd',D/'RenderData.gd',D/'native_access_catalog.json',D/'generated/tile_r01/index.json',N/'source_policy.json',N/'author_native_access.py',N/'build_native_modules.py',plan_path,cat_path,U/'surface_modules/edge_trims/author_edge_trims.py',U/'surface_modules/author_surfaces.py']
module_rows=[]
for m in cat['modules']:
 mp=R/m['master_path'];rp=R/m['render_path'];paths.extend([mp,rp]);r=read(rp);quads=[q for g in r['groups'] for q in g['quads']];w,h=m['trim']['width_m'],m['trim']['height_m'];bad=0
 for q in quads:
  n=cross(sub(q[1],q[0]),sub(q[2],q[0]));n2=cross(sub(q[2],q[0]),sub(q[3],q[0]));bad+=not(sum(a*b for a,b in zip(n,n2))>0 and sum(abs(v)>1e-10 for v in n)==1)
 tests={'render_sha':sha(rp)==m['render_sha256'],'master_sha':sha(mp)==m['master_sha256'],'quad_count':len(quads)==m['quads'],'finite_vertices':all(math.isfinite(v) for q in quads for p in q for v in p),'within_exact_trim_and_offset':all(-1e-7<=p[0]<=w+1e-7 and -1e-7<=p[1]<=h+1e-7 and -.0375001<=p[2]<=1e-7 for q in quads for p in q),'axis_aligned_non_crossing_quads':bad==0,'no_declared_holes':not read(mp).get('holes',[])}
 module_rows.append({'id':m['id'],'tests':tests,'all_pass':all(tests.values())})
rows=[];probes=[]
for a in plan['assets']:
 key=a['asset_key'];src=index['common_assets'][key];mp=R/a['source_master_path'];rp=R/a['source_render_path'];paths.extend([mp,rp]);r=read(rp);faces={(f['group_index'],f['quad_index']):f for f in a['faces']};tests={};checks=[]
 tests['original_source_sha']=sha(mp)==a['source_master_sha256']==src['master_sha256'] and sha(rp)==a['source_render_sha256']==src['render_sha256']
 tests['exact_retained_face_refs']=all(r['groups'][gi]['material']==a['rule']['material'] and r['groups'][gi]['quads'][qi]==f['quad'] and digest(f['quad'])==f['quad_sha256'] for (gi,qi),f in faces.items())
 tests['source_quad_perimeter_winding']=all(cross(sub(f['quad'][1],f['quad'][0]),sub(f['quad'][2],f['quad'][0]))[1]>0 and cross(sub(f['quad'][2],f['quad'][0]),sub(f['quad'][3],f['quad'][0]))[1]>0 for f in faces.values())
 tests['rigid_normal_transform']=all(p['transform']['basis']==[[1,0,0],[0,0,1],[0,-1,0]] for p in a['placements'])
 tests['placement_inside_source_face']=True;tests['source_normal_offset']=True;tests['module_trim_matches_placement']=True
 for p in a['placements']:
  f=faces[tuple(p['source_face_ref'])];b=p['bounds_uv_m'];frect=[v*.0125 for v in f['rect_uv_integer_cells']];m=mods[p['module_key']];tr=p['transform']['translation']
  tests['placement_inside_source_face'] &= frect[0]-1e-7<=b[0]<b[2]<=frect[2]+1e-7 and frect[1]-1e-7<=b[1]<b[3]<=frect[3]+1e-7 and p['source_face_sha256']==f['quad_sha256']
  tests['source_normal_offset'] &= abs(tr[1]-f['plane_y_m']-.0375)<1e-7 and abs(tr[0]-b[0])<1e-7 and abs(tr[2]+b[1])<1e-7
  tests['module_trim_matches_placement'] &= abs(m['trim']['width_m']-(b[2]-b[0]))<1e-7 and abs(m['trim']['height_m']-(b[3]-b[1]))<1e-7
 overlap=sum(rectangle_overlap(p['bounds_uv_m'],q['bounds_uv_m']) for i,p in enumerate(a['placements']) for q in a['placements'][i+1:] if abs(p['source_plane_y_m']-q['source_plane_y_m'])<1e-7)
 tests['no_coplanar_patch_overlap']=overlap<1e-8
 tests['no_collision_request']=a['existing_collision_unchanged'] and all(not p['collision_changed'] for p in a['placements'])
 uncovered=[];sampling=[]
 for gi,g in enumerate(r['groups']):
  if g['material']!=a['rule']['material']:continue
  for qi,q in enumerate(g['quads']):
   n=cross(sub(q[1],q[0]),sub(q[2],q[0]))
   if n[1]<=0 or abs(n[0])+abs(n[2])>1e-7:continue
   lo=[min(p[i] for p in q) for i in range(3)];hi=[max(p[i] for p in q) for i in range(3)]
   if (gi,qi) not in faces:uncovered.append({'source_face':[gi,qi],'bounds':[lo,hi],'reason':'Not selected by declared bearing ownership; original face remains.'})
   # Exact original material top faces, including intentionally excluded landings/guard tops.
   for fx,fz,label in [(.5,.5,'center'),(.1,.1,'inset'),(.1,.9,'inset'),(.9,.1,'inset'),(.9,.9,'inset')]:sampling.append({'name':f'face_{gi}_{qi}_{label}_{fx}_{fz}','kind':'selected_face' if (gi,qi) in faces else 'excluded_original_face','local':[lo[0]+fx*(hi[0]-lo[0]),lo[1],lo[2]+fz*(hi[2]-lo[2])]})
 if 'stair' in key:
  # Contract explicitly binds local central walking prism [x -1.2..1.2,z 0..11.4].
  contract=next(c for c in index['collision_contracts'] if c.get('native_placement_id')=='PHASE02:real_neighborhood_stair:0')
  for x in [-.6,0,.6]:
   for j in range(123):
    z=-.4+j*.1;y=0 if z<=1.2 else min(1.95,(z-1.2)*.5) if z<=6.3 else min(3.9,1.95+(z-6.3)*.5)
    sampling.append({'name':f'contract_route_{x}_{j}','kind':'connection' if z<0 or z>11.4 else 'contract_route','local':[x,y,z]})
 else:
  # Deck main face is x -5..5; extend .5m outside each original endpoint for contact observations.
  for z in [-1,0,1]:
   for j in range(111):sampling.append({'name':f'deck_route_{z}_{j}','kind':'connection' if j<5 or j>105 else 'deck_route','local':[-5.5+j*.1,0,z]})
 rows.append({'asset':key,'selected_faces':len(faces),'placements':len(a['placements']),'tests':tests,'all_pass':all(tests.values()),'coplanar_overlap_m2':overlap,'unselected_original_up_faces':uncovered,'physics_probe_count':len(sampling)})
 probes.append({'asset_key':key,'probes':sampling})
# Include binding and touched input fingerprints for reproducibility.
bindings={'source_plan_sha':sha(plan_path)==runtime['source_plan_sha256']==cat['source_plan_sha256'],'module_catalog_sha':sha(cat_path)==runtime['module_catalog_sha256'],'source_index_sha':sha(D/'generated/tile_r01/index.json')==runtime['source_city_index_sha256']==plan['source_city_index_sha256']}
save('input_fingerprints.json',{str(p.relative_to(R)):sha(p) for p in sorted(set(paths))})
save('support_probes.json',probes)
save('static_geometry.json',{'all_pass':all(bindings.values()) and all(m['all_pass'] for m in module_rows) and all(a['all_pass'] for a in rows),'bindings':bindings,'modules':module_rows,'assets':rows,'scope':'Exact current source and all 75 module quads/202 placements. No voxel compiler rerun, no source mutation. Godot mesh winding and original physics support are independently checked in scene_support.gd.'})
print(json.dumps({'bindings':bindings,'module_count':len(module_rows),'module_pass':all(m['all_pass'] for m in module_rows),'assets':[{k:v for k,v in a.items() if k!='unselected_original_up_faces'} for a in rows]}))
