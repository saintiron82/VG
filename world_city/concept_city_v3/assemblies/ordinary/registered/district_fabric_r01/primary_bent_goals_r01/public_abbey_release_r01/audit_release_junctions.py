"""Bounded immutable abbey public-junction audit. No global or runtime certification."""
from pathlib import Path
import sys,json,math,time
O=Path(__file__).resolve().parent;B=O.parent;sys.path.insert(0,str(B/'abbey'))
from search_abbey import load,ref,b,geo,terrain,slab_rectangles,ROOT,SC,CAT
from upper_surface_support import Support,exact_subtract,exact_clip
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
terrain.common.subtract=exact_subtract

def write(n,d):(O/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def cap(p):
 rad=.3/math.cos(math.pi/32)
 return[[p[0]+rad*math.cos(2*math.pi*j/32),p[2]+rad*math.sin(2*math.pi*j/32)]for j in range(32)]
def short(a,c,d=2):
 length=math.hypot(a[0]-c[0],a[2]-c[2]);t=min(1,d/length)if length else 0
 return[c[i]+t*(a[i]-c[i])for i in range(3)]
def main():
 t=time.monotonic();scene=load(SC);doc=load(O/'public_chain_candidates.json');route=next(r for r in doc['routes']if r['id']=='GOAL:MARKET_TO_ABBEY');branch=load(B/'abbey/abbey_surface_snapped_profile.json');cases=[];ss=route['public_segment_slices']
 for i,(a,c)in enumerate(zip(ss,ss[1:])):
  if a['source_route_id']==c['source_route_id']:continue
  center=a['points_xyz_m'][1];pts=[short(a['points_xyz_m'][0],center),center,short(c['points_xyz_m'][1],center)];cases.append(dict(id=route['id']+':PUBLIC_JUNCTION:'+str(i),points_xyz_m=pts,source_segment_slices=[a,c]))
 center=branch['points_xyz_m'][0];out=branch['points_xyz_m'][min(3,len(branch['points_xyz_m'])-1)];cases.append(dict(id=route['id']+':PUBLIC_TO_BENT_BRANCH',points_xyz_m=[short(ss[-1]['points_xyz_m'][0],center),center,short(out,center)],source_segment_slices=[ss[-1]],branch=ref(B/'abbey/abbey_surface_snapped_profile.json')))
 pieces=[]
 for c in cases:
  c['ribbon_piece_ids']=[]
  for i,p in enumerate(b.ribbon([[q[0],q[2]]for q in c['points_xyz_m']],.6)):
   rid=c['id']+':STRIP:'+str(i);pieces.append(dict(id=rid,case_id=c['id'],kind='finite_incoming_or_outgoing_strip',polygon_xz_m=p));c['ribbon_piece_ids'].append(rid)
  rid=c['id']+':TURN_CAP';pieces.append(dict(id=rid,case_id=c['id'],kind='circumscribed_32gon_radius_0.3_m_turn_cap',polygon_xz_m=cap(c['points_xyz_m'][1])));c['ribbon_piece_ids'].append(rid)
 wins=[p['polygon_xz_m']for p in pieces];cache={};bindings=[];native={}
 for p in scene['common_instances']:
  a=scene['common_assets'][p['asset_key']];bb=a.get('bounds');py=p['position_m'][1]
  if bb is None:
   if a['render_path']not in cache:cache[a['render_path']]=load(ROOT/a['render_path'])
   bb=cache[a['render_path']]['bounds']
  wp=b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p)
  nearby=[c for c in cases if any(geo.intersection_area(wp,w['polygon_xz_m'])>1e-8 for w in pieces if w['case_id']==c['id'])]
  if not nearby:continue
  lo=min(v[1]for c in nearby for v in c['points_xyz_m']);hi=max(v[1]for c in nearby for v in c['points_xyz_m'])
  if bb['min'][1]+py>hi+2.2 or bb['max'][1]+py<lo-.5:continue
  if a['render_path']not in cache:cache[a['render_path']]=load(ROOT/a['render_path'])
  mesh=cache[a['render_path']];binding=dict(id=p['id'],asset_key=p['asset_key'],cache=dict(path=a['render_path'],sha256=a['render_sha256']),source=dict(path=a['master_path'],sha256=a['master_sha256']),position_m=p['position_m'],yaw_rad=p['yaw_rad'],actual_world_bounds_polygon_xz_m=wp)
  assert ref(ROOT/a['render_path'])==binding['cache']and ref(ROOT/a['master_path'])==binding['source'];bindings.append(binding);vs=[]
  for g in mesh['groups']:
   for q in g['quads']:
    if max(v[1]for v in q)-min(v[1]for v in q)>1e-8:continue
    fy=q[0][1]+py
    if not(lo-.5<=fy<=hi+.5):continue
    ny=(q[1][2]-q[0][2])*(q[2][0]-q[0][0])-(q[1][0]-q[0][0])*(q[2][2]-q[0][2])
    if ny<=0:continue
    poly=b.xform([[v[0],v[2]]for v in q],p)
    for tri in terrain.fan_upward([[x,fy,z]for x,z in poly]):vs.extend(tri)
  if vs:native['native:'+p['id']]=vs
 idx=Support(scene,wins,native);sides=SideIndex(scene,wins);owners=[];checks=[];contacts=[];boxes=[];higher=[];slabs={}
 for part in pieces:
  r=terrain.audit_polygon(idx,part['polygon_xz_m'],None,grade_limit=.12);checks.append(dict(**part,**r));fmin=min(q['min_y_m']for q in r['source_pieces']);fmax=max(q['max_y_m']for q in r['source_pieces'])
  for j,q in enumerate(r['source_pieces']):
   owner=dict(id=part['id']+':'+str(j),case_id=part['case_id'],polygon_xz_m=q['polygon_xz_m'],plane_y_xz_m=q['plane_y_xz_m']);owners.append(owner)
   for p in bindings:
    if geo.intersection_area(q['polygon_xz_m'],p['actual_world_bounds_polygon_xz_m'])<=1e-8:continue
    key=(p['id'],round(fmin,9),round(fmax,9))
    if key not in slabs:slabs[key]=[b.xform(v,p)for v in slab_rectangles(cache[p['cache']['path']],fmin-p['position_m'][1]+.01,fmax-p['position_m'][1]+2.2)]
    for bi,v in enumerate(slabs[key]):
     area=geo.intersection_area(q['polygon_xz_m'],v)
     if area>1e-8:contacts.append(dict(owner_id=owner['id'],case_id=part['case_id'],native_id=p['id'],body_piece=bi,area_m2=area))
   for box in scene['boxes']:
    x,y,z=box['position_m'];w,h,l=box['size_m']
    if y+h/2<=q['min_y_m']+.01 or y-h/2>=q['max_y_m']+2.2:continue
    v=b.xform(b.rect(-w/2,-l/2,w/2,l/2),box);area=geo.intersection_area(q['polygon_xz_m'],v)
    if area>1e-8:boxes.append(dict(owner_id=owner['id'],case_id=part['case_id'],box_id=box['id'],area_m2=area))
   for ri in idx.terrain.index.candidates(q['polygon_xz_m']):
    rr=idx.terrain.rows[ri]
    if max(v[1]for v in rr['vertices_xyz_m'])<=q['min_y_m']+1e-7:continue
    overlap=exact_clip.clip(q['polygon_xz_m'],rr['polygon_xz_m'])
    if len(overlap)<3 or geo.polygon_area(overlap)<=1e-8:continue
    delta=max(terrain.common.height(rr['plane_y_xz_m'],v)-terrain.common.height(q['plane_y_xz_m'],v)for v in overlap)
    if delta>1e-7:higher.append(dict(owner_id=owner['id'],case_id=part['case_id'],material=rr['material'],triangle_index=rr['triangle_index'],height_above_selected_floor_m=delta))
  print(part['id'],r['passes_existing_surface'],r['missing_area_m2'],r['max_actual_triangle_grade'],flush=True)
 bank=sides.audit(owners)
 for c in cases:
  rows=[r for r in checks if r['case_id']==c['id']];c['support_pass']=all(r['passes_existing_surface']for r in rows);c['max_actual_grade']=max(r['max_actual_triangle_grade']for r in rows);c['bank_contacts']=[r for r in bank['contacts']if r['owner_id'].startswith(c['id']+':')];c['native_contacts']=[r for r in contacts if r['case_id']==c['id']];c['explicit_box_contacts']=[r for r in boxes if r['case_id']==c['id']];c['higher_actual_surface_conflicts']=[r for r in higher if r['case_id']==c['id']];c['passed']=c['support_pass']and not(c['bank_contacts']or c['native_contacts']or c['explicit_box_contacts']or c['higher_actual_surface_conflicts'])
 out=dict(schema='riverstone.abbey_partial_public_junction_audit.v1',scene=ref(SC),source_candidates=ref(O/'public_chain_candidates.json'),helper=ref(B/'abbey/upper_surface_support.py'),width_m=.6,headroom_m=2.2,capsule_radius_m=.3,cases=cases,actual_native_bindings=bindings,support_checks=checks,retained_bank_checks=bank,status='PASS'if all(c['passed']for c in cases)else'RETAINED_PUBLIC_JUNCTION_INCIDENTS_RUNTIME_REPLAY_REQUIRED',summary=dict(cases=len(cases),passed_cases=sum(c['passed']for c in cases),native_contacts=len(contacts),explicit_box_contacts=len(boxes),bank_contacts=len(bank['contacts']),higher_surface_conflicts=len(higher),seconds=time.monotonic()-t),limits=['Finite junction turn/strip/cap audit only. No global terrain certification.','Existing source incidents are retained without suppression or geometry changes.','Unchanged-controller full-chain bidirectional replay remains required.'])
 write('public_abbey_junction_audit.json',out);print(json.dumps(out['summary']),out['status'],flush=True)
if __name__=='__main__':main()
