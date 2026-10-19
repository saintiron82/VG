"""Exact local top-face coverage, overlap and height ledgers at measured contacts."""
import pathlib,json,math,importlib.util,sys,collections
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('diag',H/'diagnose_results.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);p=m.p;b=m.b;ROOT=m.ROOT

def area(poly):return abs(sum(a[0]*c[1]-c[0]*a[1]for a,c in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>2 else 0

def clip(poly,mask):
 if sum(a[0]*c[1]-c[0]*a[1]for a,c in zip(mask,mask[1:]+mask[:1]))<0:mask=list(reversed(mask))
 for a,c in zip(mask,mask[1:]+mask[:1]):
  old=poly;poly=[]
  if not old:break
  def side(q):return(c[0]-a[0])*(q[1]-a[1])-(c[1]-a[1])*(q[0]-a[0])
  for u,v in zip(old,old[1:]+old[:1]):
   su,sv=side(u),side(v);iu,iv=su>=0,sv>=0
   if iu:poly.append(u)
   if iu!=iv:
    t=su/(su-sv);poly.append([u[j]+t*(v[j]-u[j])for j in range(2)])
 return poly

def main():
 data=b.read(H/'prepared_runtime.json');partial=b.read(H/'evidence/contact_localization_final.json');out=[]
 for rid in ['ROAD:UPPER_CONTOUR','ROAD:MARKET_CONTOUR','ROAD:LOWER_CONTOUR','ROAD:NOBLE_RISE']:
  f=next(f for f in partial['findings']if f['route_id']==rid);hit=f['actual_contact'];point=hit['position'];route=next(r for r in data['routes']if r['id']==rid);target=hit['target'];center=hit['capsule_center'];vx,vz=target[0]-center[0],target[2]-center[2];ll=math.hypot(vx,vz);ux,uz=vx/ll,vz/ll;cx,cz=point[0],point[2];window=[[cx-1,cz-1],[cx+1,cz-1],[cx+1,cz+1],[cx-1,cz+1]];local=[];native=[]
  for pid in route['placement_ids']:
   asset=data['assets'][data['placements'][pid]['asset_key']]
   if asset.get('collision_format')!='actual_scene_triangles':continue
   g=b.read(ROOT/asset['render_path'])
   for face,t in zip(g['source_face_indices'],g['triangles']):
    bb=b.bounds(t)
    if not b.overlaps(bb,[cx-1,cz-1,cx+1,cz+1]):continue
    poly=[[v[0],v[2]]for v in t];clipped=clip(poly,window)
    if area(clipped)<1e-10:continue
    n=m.cross(m.sub(t[1],t[0]),m.sub(t[2],t[0]));length=math.sqrt(m.dot(n,n));local.append({'face':face,'triangle_godot_xyz_m':t,'clip_xz_m':clipped,'area_m2':area(clipped),'mathematical_normal_xyz':[v/length for v in n],'grade':math.hypot(n[0],n[2])/abs(n[1])})
  overlaps=[]
  for i,a in enumerate(local):
   for c in local[i+1:]:
    poly=clip(a['clip_xz_m'],c['clip_xz_m']);ar=area(poly)
    if ar<=1e-8:continue
    delta=[abs(p.y_at(a['triangle_godot_xyz_m'],x,z)-p.y_at(c['triangle_godot_xyz_m'],x,z))for x,z in poly];overlaps.append({'faces':[a['face'],c['face']],'area_m2':ar,'max_height_delta_m':max(delta),'polygon_xz_m':poly,'coplanar_within_1um':max(delta)<=1e-6})
  samples=[]
  for lateral in [-.3,0,.3]:
   for travel in [-.6,-.3,-.1,-.01,-.001,0,.001,.01,.1,.3,.6]:
    x=cx+ux*travel-uz*lateral;z=cz+uz*travel+ux*lateral;hits=[{'face':r['face'],'y_m':y}for r in local for y in [p.y_at(r['triangle_godot_xyz_m'],x,z)]if y is not None];samples.append({'lateral_m':lateral,'along_m':travel,'xz_m':[x,z],'scene_top_hits':hits,'height_range_m':max(q['y_m']for q in hits)-min(q['y_m']for q in hits)if hits else None})
  exactduplicates=[];seen={}
  for r in local:
   k=tuple(sorted(tuple(v)for v in r['triangle_godot_xyz_m']))
   if k in seen:exactduplicates.append([seen[k],r['face']])
   seen[k]=r['face']
  # Source vectors and actual tested XZ are identical; geometry can still have different profiles.
  inventory=b.read(H.parent/'primary_inventory/inventory.json');source=next(r for r in inventory['roads']if r['id']==rid.removeprefix('ROAD:'))
  path_equal=[[v[0],v[2]]for v in route['points']]==source['polyline_xz_m']
  record={'route_id':rid,'contact':hit,'source_path_xz_exactly_matches_tested':path_equal,'source_path_kind':source['kind'],'local_window_xz_m':window,'actual_contact_faces':f['candidate_faces_within_2cm'],'local_scene_top_faces':local,'max_local_scene_triangle_grade':max(r['grade']for r in local),'exact_duplicate_triangles':exactduplicates,'positive_area_overlaps':overlaps,'full_width_offset_height_samples':samples}
  if rid=='ROAD:NOBLE_RISE':record['native_step']={'asset':f['collider_asset'],'contact_face_refs':[r['source_face']for r in f['candidate_faces_within_2cm']],'observed_vertical_face_y_range_m':[15.5,16.0],'observed_world_x_m':-195.75685049999998,'observed_world_z_interval_m':[-249.05364175,-248.55364175],'interpretation':'Exact native service approach cap/riser intersects the tested public centreline; no house-scale or road relocation inference.'}
  out.append(record)
 result={'schema':'riverstone.primary_network_priority_diagnosis.v1','scene':data['sources']['scene'],'prepared':b.ref(H/'prepared_runtime.json'),'cases':out,'scope':'Actual contact-local two-metre square. Source grade functions or labels are not used to infer actual triangle continuity.'};b.write(H/'evidence/priority_diagnosis.json',result)
 print(json.dumps({'report':b.ref(H/'evidence/priority_diagnosis.json'),'cases':[{'id':r['route_id'],'max_grade':r['max_local_scene_triangle_grade'],'overlaps':len(r['positive_area_overlaps']),'duplicates':len(r['exact_duplicate_triangles']),'same_source_xz':r['source_path_xz_exactly_matches_tested']}for r in out]}))
if __name__=='__main__':main()
