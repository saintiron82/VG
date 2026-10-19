"""Preserve initial draft; bind bridge deck spawn to actual native tops instead of riverbed."""
import pathlib,json,hashlib,math,importlib.util,sys,copy
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prep',H/'prepare_batch.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
b=p.b;ROOT=p.ROOT

def main():
 src=H/'prepared.json';d=b.read(src);assert b.sha(src)=='50b27307b885f032ccda9a2444adaa5de4b0b938db78be6aef715c7ba43a78d0'
 scene=b.read(p.SCENE);tr=scene['bridge_mechanism']['bridge_to_world'];A=tr['basis'];o=tr['translation'];cache={};changed=[]
 def local(v):return [sum(A[k][i]*(v[k]-o[k])for k in range(3))for i in range(3)]
 def tops(pid,x,z):
  placement=d['placements'][pid];asset=d['assets'][placement['asset_key']]
  if pid not in cache:
   data=b.read(ROOT/asset['render_path']);out=[]
   if asset.get('collision_format')in ['source_grade_proxy_triangles','actual_scene_triangles']:
    # Direct Godot order has downward mathematical cross product for upward faces.
    for t in data['triangles']:
     w=[b.transform(v,placement)for v in t];a,c,e=w;ny=(c[2]-a[2])*(e[0]-a[0])-(c[0]-a[0])*(e[2]-a[2])
     if ny< -1e-9:out.append(w)
   else:
    for g in data['groups']:
     for q in g['quads']:
      w=[b.transform(v,placement)for v in q];a,c,e=w[:3];ny=(c[2]-a[2])*(e[0]-a[0])-(c[0]-a[0])*(e[2]-a[2])
      if ny>1e-9:out.extend([[w[0],w[1],w[2]],[w[0],w[2],w[3]]])
   cache[pid]=[(b.bounds(t),t)for t in out]
  return [v for bb,t in cache[pid]if p.covers(bb,x,z)for v in [p.y_at(t,x,z)]if v is not None]
 for r in d['routes']:
  if not any(s in r['id']for s in ['ROAD:MAIN_BRIDGE','ROAD:PORT_BRIDGE_TIE','ROAD:SOUTH_COUNTRY_ROAD','BRIDGE_CLOSED','NEGATIVE_BARRIER']):continue
  for i,v in enumerate(r['points']):
   lo=local(v)
   if not(-72.000001<=lo[0]<=75 and abs(lo[2])<=7):continue
   hits=[]
   for pid in r['placement_ids']:
    if not(pid.startswith('BRIDGE_') or pid.startswith('CONTRACT:SOUTHERN')):continue
    hits.extend((y,pid)for y in tops(pid,v[0],v[2])if y>=0)
   if hits:
    y,pid=min(hits,key=lambda q:abs(q[0]-(4.25 if abs(lo[0])<=15 else max(1.25,v[1]))))
    if y!=v[1]:changed.append({'route_id':r['id'],'vertex_index':i,'old_xyz_m':list(v),'new_xyz_m':[v[0],y,v[2]],'actual_owner':pid})
    v[1]=y
  r['minimum_allowed_feet_y_m']=min(v[1]for v in r['points'])-2
 # One exact left barrier centre-gap tested from both directions. The draft's shared
 # collision group already had these two vectors, but its second ID implied the right side.
 for r in d['routes']:
  if r['id']=='NEGATIVE_BARRIER_CENTER_GAP_-1':r['id']='NEGATIVE_BARRIER_CENTER_GAP_LEFT'
  elif r['id']=='NEGATIVE_BARRIER_CENTER_GAP_1':r['id']='NEGATIVE_BARRIER_CENTER_GAP_LEFT_REVERSE'
  if r['id'].startswith('NEGATIVE_BARRIER'):r['test_scope']='Static ROAD_SECURED left barrier centre gap, both directions, actual native panel collision. Right barrier and live operations remain separate.'
 d['sources']['preflight_draft']=b.ref(src);d['sources']['control_source']=b.ref(p.BASE/'revisions/r04_r6_winding/prepared.json');d['implementation_hashes'][str(pathlib.Path(__file__).resolve().relative_to(ROOT))]=b.sha(pathlib.Path(__file__).resolve())
 for r in d['routes']:
  r['length_m']=sum(math.dist(a,c)for a,c in zip(r['points'],r['points'][1:]))
 d['coverage']['static_bridge_spawn_verified_from_native_deck']=True
 b.write(H/'evidence/preflight_correction.json',{'status':'corrected_before_runtime','draft':b.ref(src),'bridge_height_rebindings':changed,'barrier_label_correction':'The draft shared group contained a left-barrier forward/reverse pair; corrected IDs explicitly identify that pair. No right-barrier result is claimed.','geometry_and_controller_unchanged':True})
 b.write(H/'prepared_checked.json',d);print(json.dumps({'prepared':b.ref(H/'prepared_checked.json'),'cases':len(d['routes']),'actual_native_height_corrections':len(changed)}))
if __name__=='__main__':main()
