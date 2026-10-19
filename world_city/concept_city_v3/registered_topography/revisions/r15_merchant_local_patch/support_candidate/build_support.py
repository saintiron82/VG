"""Bounded R15 support candidates; common compiler only; no scene activation."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import hashlib,json,math,time,resource,itertools
from collections import Counter,defaultdict
from pathlib import Path
from functools import lru_cache
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import author as a
from voxel_character.common import coordinate_planes,core,render_data
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
HERE=Path(__file__).resolve().parent
PITCH=.5; BURIAL=.5; TOTAL_CAP=100000; PER_ASSET_CAP=20000
CONTRACT_SHA='f4cc65e37809887ee616369b5d9a3a86bd346e28e77ad2d0c641f498dc9a1cdf'
POSES={p['id']:p for p in a.PACK['placements']}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
 assert Path(p).resolve().is_relative_to(HERE)
 with Path(p).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def area(poly):return a.geo.polygon_area(poly)
def clip(p,q):return a.polygon(a.geo.convex_intersection(p,q))
def bounds(p):
 x,z=zip(*p);return [min(x),min(z),max(x),max(z)]
def local(pose,p):
 c,s=math.cos(pose['yaw_rad']),math.sin(pose['yaw_rad']);x,z=p[0]-pose['position_m'][0],p[1]-pose['position_m'][2]
 return [c*x-s*z,s*x+c*z]
def world(pose,p):
 c,s=math.cos(pose['yaw_rad']),math.sin(pose['yaw_rad']);x,z=p
 return [pose['position_m'][0]+c*x+s*z,pose['position_m'][2]-s*x+c*z]
def cells_2d(p):
 x0,z0,x1,z1=bounds(p)
 for x in range(math.floor(x0/PITCH+1e-8),math.ceil(x1/PITCH-1e-8)):
  for z in range(math.floor(z0/PITCH+1e-8),math.ceil(z1/PITCH-1e-8)):
   cell=[[x*PITCH,z*PITCH],[(x+1)*PITCH,z*PITCH],[(x+1)*PITCH,(z+1)*PITCH],[x*PITCH,(z+1)*PITCH]]
   if clip(p,cell):yield x,z

def effective_domains(poly):
 """Exact current owner domains, with the same retirement expansion as R15."""
 x0,z0,x1,z1=bounds(poly);out=[]
 for ix in range(math.floor(x0/16),math.floor(x1/16)+1):
  for iz in range(math.floor(z0/16),math.floor(z1/16)+1):
   b=[16*ix,16*iz,16*(ix+1),16*(iz+1)]
   tile=clip(poly,a.base.R04.old.rect(b))
   if not tile:continue
   for r in a.base.surface_domains(b,conform=False):
    q=clip(tile,r['polygon_xz_m'])
    if not q:continue
    if a.base.R04.prior.is_excluded(r,a.EXCLUDED):
     replacements=a.base.R04.prior._replacement_domains(q,b,a.EXCLUDED)
     out.extend(a.base.insert(replacements,b))
    else:out.append(dict(r,polygon_xz_m=q))
 assert abs(sum(area(r['polygon_xz_m']) for r in out)-area(poly))<1e-5
 for r in out:
  assert r['kind'] in ('ground','terrace'),('Unexpected effective owner',r['kind'],r['owner_id'])
  p=r['polygon_xz_m'];c=[sum(v[k] for v in p)/len(p) for k in(0,1)]
  assert abs(a.effective_source_height(*c)-a.base.source_surface_height_at(r,*c))<1e-8
 return out

@lru_cache(maxsize=100000)
def ground_y(x,z):
 return a.base.source_surface_height_at(dict(kind='ground',owner_id='BASE_GROUND'),x,z)

def lipschitz_proof():
 b=a.base.R04.base
 water=max(math.hypot(abs(y1-y0)/math.dist(p,q),.06) for w in b.WATERS for p,q,y0,y1 in zip(w['polyline_xz_m'],w['polyline_xz_m'][1:],w['levels_m'],w['levels_m'][1:]))
 value=max(.12,b.ROAD_GRADE,water,math.hypot(.0035,.06),.08)
 assert value<=.120000001
 return dict(constant_m_per_m=value,road_cones_and_area_plateaus=.1,terrace_cones=.12,waterbank_max_gradient=water,riverbank_max_gradient=math.hypot(.0035,.06),reservoir_bank=.08,rule='A maximum of L-Lipschitz fields remains L-Lipschitz. Segment projection is nonexpansive; head and lateral-distance derivatives are orthogonal. Ground source is max of these bounded fields. Terrace source is constant.',sample_cover_radius_m=PITCH/math.sqrt(2),source_module_sha256=sha(b.__file__))

def native_bottom_columns(pose):
 path=Path(pose['compiled_asset_ref']);assert sha(path)==pose['render_sha256']
 data=json.loads(path.read_text());assert data['pitch']==PITCH and data['grid_origin']==[0,0,0]
 cols=set();faces=[]
 for gi,g in enumerate(data['groups']):
  for qi,q in enumerate(g['quads']):
   u=[q[1][i]-q[0][i] for i in range(3)];v=[q[2][i]-q[0][i] for i in range(3)]
   ny=u[2]*v[0]-u[0]*v[2]
   if ny< -1e-9 and all(abs(v[1])<1e-9 for v in q):
    p=[[v[0],v[2]] for v in q];cols.update(cells_2d(p));faces.append(dict(group_index=gi,quad_index=qi,area_m2=area(p)))
 return cols,faces

def master(group):
 ops=[]
 for r in group['regions']:
  ops.append(dict(id='foundation_'+r['region_id'].rsplit(':',1)[1],part='solid',action='paint',material='stone',shape=dict(kind='extrusion',polygon=[[x,-z] for x,z in r['local_polygon_xz_m']],z_min=r['local_bottom_y_m'],z_max=0.),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
 return dict(schema='riverstone.voxel.master.v1',id=group['asset_key'],revision=15,axes=dict(up='+Y',front='+Z',right='+X'),grid_origin=[0,0,0],materials={'stone':'7e8075'},components=[dict(id='support',parts=[dict(id='solid',pivot=[0,0,0])],operations=ops)],instances=[dict(id='support',component='support')],metadata=dict(source_contract_sha256=CONTRACT_SHA,owner_id=group['native_owner_id'],native_render_sha256=group['native_render_sha256'],position_m=group['position_m'],yaw_rad=group['yaw_rad'],support_top_local_y_m=0.,support_top_world_y_m=group['top_y_m'],native_plinth_bottom_world_y_m=group['top_y_m'],policy='Exact native half-metre sampled columns only. No platform fill, native edits, floor edits, or scene activation.'))

def conflict_proof(regions):
 protected=[]
 for r in a.base.R04._owners():
  if r['kind'] in ('road','water_hole','replacement_road','port_tie','bridge_hole'):protected.append(r)
 for r in a.base.OWNERS:protected.append(r)
 # All current R14 owners are checked; original road collars are not traffic lanes.
 idx=a.geo._SpatialIndex(16)
 for i,r in enumerate(protected):idx.add(i,r['polygon_xz_m'])
 hits=[]
 for r in regions:
  for i in idx.candidates(r['polygon_xz_m']):
   q=clip(r['polygon_xz_m'],protected[i]['polygon_xz_m'])
   if q and area(q)>1e-7:hits.append(dict(region_id=r['id'],owner_id=protected[i]['owner_id'],kind=protected[i]['kind'],area_m2=area(q)))
 assert not hits,hits
 return dict(protected_polygons=len(protected),tested_support_regions=len(regions),positive_area_conflicts=hits,water_and_public_road_overlap_m2=0.,policy='Exact positive-area polygon intersections; support footprints cannot spill beyond the native contact columns.')

def preflight():
 start=time.monotonic();assert sha(a.HERE/'source_contract.json')==CONTRACT_SHA
 contract=json.loads((a.HERE/'source_contract.json').read_text());L=lipschitz_proof();rows=[];groups={};mismatch=[];maxgrid=0.;domain_kinds=Counter();native_proofs=[];reqs=contract['support_requirements'];selected=[]
 for i,r in enumerate(reqs):
  pose=POSES[r['id'].rsplit(':',1)[0]];p=[local(pose,q) for q in r['polygon_xz_m']]
  err=max(abs(v/PITCH-round(v/PITCH)) for q in p for v in q);maxgrid=max(maxgrid,err);assert err<1e-7
  p=[[round(v/PITCH)*PITCH for v in q] for q in p];doms=effective_domains(r['polygon_xz_m']);proof=[];min_sample=math.inf;lower=math.inf
  for d in doms:
   domain_kinds[d['kind']]+=1;q=[local(pose,v) for v in d['polygon_xz_m']]
   if d['kind']=='terrace':sample=bound=d['floor_y_m'];n=1
   else:
    vals=[ground_y(*world(pose,[(x+.5)*PITCH,(z+.5)*PITCH])) for x,z in cells_2d(q)]
    sample=min(vals);bound=max(1.,sample-L['constant_m_per_m']*L['sample_cover_radius_m']);n=len(vals)
   min_sample=min(min_sample,sample);lower=min(lower,bound)
   proof.append(dict(owner_id=d['owner_id'],kind=d['kind'],polygon_xz_m=d['polygon_xz_m'],area_m2=area(d['polygon_xz_m']),samples=n,minimum_record_field_sample_y_m=sample,certified_lower_y_m=bound))
  # Include all original source corners/centroids in screened minima.
  exact_samples=[a.effective_source_height(*q) for q in r['polygon_xz_m']+[[sum(v[k] for v in r['polygon_xz_m'])/len(r['polygon_xz_m']) for k in(0,1)]]]
  min_sample=min(min_sample,*exact_samples)
  selected_flag=r['required'] or min_sample<r['bottom_y_m']-1e-7
  uncertain=not selected_flag and lower<r['bottom_y_m']-1e-7
  record=dict(region_id=r['id'],property_id=r['property_id'],native_owner_id=pose['id'],original_required=r['required'],selected=selected_flag,unresolved_gap_bound=uncertain,local_polygon_xz_m=p,world_polygon_xz_m=r['polygon_xz_m'],native_top_y_m=r['bottom_y_m'],minimum_sample_y_m=min_sample,certified_lower_y_m=lower,source_domain_proof=proof)
  rows.append(record)
  if selected_flag:
   selected.append(r);local_bottom=math.floor((lower-BURIAL-r['bottom_y_m'])/PITCH+1e-10)*PITCH
   record.update(local_bottom_y_m=local_bottom,bottom_world_y_m=r['bottom_y_m']+local_bottom,certified_minimum_burial_m=lower-r['bottom_y_m']-local_bottom)
   assert abs(pose['position_m'][1]-r['bottom_y_m'])<1e-9
   if pose['id'] not in groups:
    group=dict(asset_key='r15_native_support_'+hashlib.sha256(pose['id'].encode()).hexdigest()[:12],native_owner_id=pose['id'],property_id=r['property_id'],native_render_sha256=pose['render_sha256'],native_render_path=str(Path(pose['compiled_asset_ref']).relative_to(a.ROOT)),position_m=pose['position_m'],yaw_rad=pose['yaw_rad'],scale=[1,1,1],pitch_m=PITCH,top_y_m=r['bottom_y_m'],regions=[])
    groups[pose['id']]=group
   groups[pose['id']]['regions'].append(record)
  if (i+1)%25==0:print('preflight regions',i+1,'elapsed',round(time.monotonic()-start,1),flush=True)
 for pose_id,g in groups.items():
  native_cols,faces=native_bottom_columns(POSES[pose_id]);want=set(c for r in g['regions'] for c in cells_2d(r['local_polygon_xz_m']))
  assert want<=native_cols
  g['native_contact_proof']=dict(native_bottom_face_count=len(faces),native_bottom_columns=len(native_cols),support_columns=len(want),unsupported_top_columns=0,support_area_m2=len(want)*PITCH**2,actual_bottom_face_refs=faces)
  budget=candidate_budget(master(g),PITCH);g['candidate_budget']=budget['exact_candidate_visits_without_cell_sampling'];assert g['candidate_budget']<=PER_ASSET_CAP
 total=sum(g['candidate_budget'] for g in groups.values());assert total<=TOTAL_CAP
 conflicts=conflict_proof(selected)
 out=dict(schema='riverstone.r15_support.preflight.v1',status='PREFLIGHT_ONLY_AWAIT_BOUNDED_COMPILE_APPROVAL',active=False,source_contract_sha256=CONTRACT_SHA,source_pack_sha256=a.REFERENCES['assemblies/property/registered/merchant_fabric_r02/resolved_placements.json'],source_author_sha256=sha(a.HERE/'author.py'),compiler_sources={str(Path(m.__file__).relative_to(a.ROOT)):sha(m.__file__) for m in(coordinate_planes,core,render_data)},retired_native_ids=list(a.RETIRED),all_native_regions=len(rows),original_required_regions=sum(r['required'] for r in reqs),selected_regions=len(selected),selected_holdings=len(set(r['property_id'] for r in selected)),groups=list(groups.values()),regions=rows,additional_selected_regions=[r['region_id'] for r in rows if r['selected'] and not r['original_required']],unresolved_regions=[r['region_id'] for r in rows if r['unresolved_gap_bound']],maximum_native_grid_error= maxgrid,source_domain_kinds=domain_kinds,ground_lipschitz_proof=L,conflicts=conflicts,exact_candidate_visits=total,hard_total_candidate_cap=TOTAL_CAP,hard_per_asset_candidate_cap=PER_ASSET_CAP,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,elapsed_s=time.monotonic()-start)
 write(HERE/'preflight.json',out)
 print(json.dumps({k:v for k,v in out.items() if k not in ('groups','regions','compiler_sources','retired_native_ids')},indent=2));return out

def compile_all():
 p=json.loads((HERE/'preflight.json').read_text());assert sha(a.HERE/'source_contract.json')==CONTRACT_SHA
 assert not p['unresolved_regions'],p['unresolved_regions']
 total=0;rows=[];start=time.monotonic()
 for g in p['groups']:
  m=master(g);budget=candidate_budget(m,PITCH)['exact_candidate_visits_without_cell_sampling'];assert budget==g['candidate_budget'];assert total+budget<=TOTAL_CAP
  mp=HERE/(g['asset_key']+'.master.json');cp=HERE/(g['asset_key']+'.compiled.json');rp=HERE/(g['asset_key']+'.render.json');write(mp,m)
  c=coordinate_planes.compile_master(m,{'pitch':PITCH},max_candidate_cells=PER_ASSET_CAP,max_output_cells=PER_ASSET_CAP);assert c['valid'];assert c['candidate_cells']==budget
  r=render_data.make_render_data(c);write(cp,c);write(rp,r);total+=c['candidate_cells']
  row=dict(asset_key=g['asset_key'],property_id=g['property_id'],native_owner_id=g['native_owner_id'],position_m=g['position_m'],yaw_rad=g['yaw_rad'],scale=[1,1,1],pitch_m=PITCH,top_y_m=g['top_y_m'],source=dict(path=str(mp.relative_to(a.ROOT)),sha256=sha(mp)),compiled=dict(path=str(cp.relative_to(a.ROOT)),sha256=sha(cp)),cache=dict(path=str(rp.relative_to(a.ROOT)),sha256=sha(rp)),native_render_sha256=g['native_render_sha256'],native_render_path=g['native_render_path'],candidate_visits=c['candidate_cells'],cell_count=r['cell_count'],quad_count=r['quad_count'],bounds_local_m=r['bounds'],ownership_regions=[dict(region_id=v['region_id'],polygon_xz_m=v['world_polygon_xz_m'],local_polygon_xz_m=v['local_polygon_xz_m'],bottom_y_m=v['bottom_world_y_m'],top_y_m=g['top_y_m'],certified_minimum_burial_m=v['certified_minimum_burial_m']) for v in g['regions']],contact_proof=g['native_contact_proof'])
  rows.append(row);print('compiled',g['asset_key'],c['candidate_cells'],r['quad_count'],flush=True)
 out=dict(schema='riverstone.r15_merchant_native_support.resolved.v1',status='BOUNDED_CANDIDATE_AWAIT_SCENE_AND_FULL_INTERFACE_ACCEPTANCE',active=False,source_contract_sha256=CONTRACT_SHA,preflight=dict(path=str((HERE/'preflight.json').relative_to(a.ROOT)),sha256=sha(HERE/'preflight.json')),source_pack_sha256=p['source_pack_sha256'],builder_sha256=sha(__file__),compiler_sources=p['compiler_sources'],placements=rows,summary=dict(properties=p['selected_holdings'],runtime_support_groups=len(rows),native_regions=p['selected_regions'],candidate_visits=total,hard_total_candidate_cap=TOTAL_CAP,cell_count=sum(r['cell_count'] for r in rows),quad_count=sum(r['quad_count'] for r in rows),support_area_m2=sum(r['contact_proof']['support_area_m2'] for r in rows),minimum_certified_burial_m=min(v['certified_minimum_burial_m'] for r in rows for v in r['ownership_regions']),elapsed_s=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),limitations=['Support solids only; terrain and retained R5 geometry are not altered.','Full-scene native/terrain clipping, final skin/side treatment, visual approval and capsule/cart traversal remain outside this candidate.','Common support top contact faces remain buried against native plinths; no cross-mesh hidden-face culling is claimed.'])
 write(HERE/'resolved_support.json',out);print(json.dumps(out['summary'],indent=2));return out
if __name__=='__main__':compile_all() if '--compile' in sys.argv else preflight()
