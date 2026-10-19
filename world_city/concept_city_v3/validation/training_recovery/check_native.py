"""Fresh independent native/ownership audit of reconstructed training r09."""
import sys,json,pathlib,hashlib,math,collections,itertools,importlib
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
D=ROOT/'world_city/concept_city_v3/registered_topography/revisions/r09_training_access'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(pathlib.Path(p).relative_to(ROOT)),'sha256':sha(p)}
def area(p):
 if len(p)<3:return 0.
 a=p[0];return abs(sum((p[i][0]-a[0])*(p[i+1][1]-a[1])-(p[i][1]-a[1])*(p[i+1][0]-a[0]) for i in range(1,len(p)-1)))/2
pack=json.loads((D/'resolved_placements.json').read_text());assert sha(D/'resolved_placements.json')=='07bef5de4839b76eca2ed3d012bffeb70a1127a5e897edf9d7d1b02a1025effe'
seal=json.loads((D/'freeze_manifest.json').read_text());hashes=[]
for name,h in seal['files'].items():assert sha(D/name)==h;hashes.append(ref(D/name))
oldpath=ROOT/'world_city/concept_city_v3/assemblies/landscape/registered/training/resolved_placements.json';old=json.loads(oldpath.read_text());assert sha(oldpath)==pack['reconstruction']['source_pack_sha256']
for k in ['actual_doors','internal_routes','external_access_surfaces','gate_proposals','replacement_ledger']:assert pack[k]==old[k],k
assert {p['id']:p for p in pack['placements'] if not p['id'].startswith('TRAIN:r09:')}=={p['id']:p for p in old['placements'] if p['id']!='TRAIN:owned_ground'}
alltops=[];roles={};bijections=[]
for inst in pack['placements']:
 if not inst['id'].startswith('TRAIN:r09:'):continue
 role=inst['id'].rsplit(':',1)[1];a=pack['asset_manifest'][inst['asset_key']];rp=pathlib.Path(a['compiled_asset_ref']);cp=pathlib.Path(a['compiled_cells_path']);mp=pathlib.Path(a['master_path'])
 assert sha(rp)==a['render_sha256'] and sha(cp)==a['compiled_cells_sha256'] and sha(mp)==a['master_file_sha256']
 r=json.loads(rp.read_text());c=json.loads(cp.read_text());pitch=r['pitch'];o=r['grid_origin'];pos=inst['position_m'];cells={tuple(x[:3]) for x in c['cells']};assert len(cells)==len(c['cells']);expected=set();columns=collections.defaultdict(set)
 for x,y,z in cells:
  columns[(x,z)].add(y)
  for axis in range(3):
   for sign in [-1,1]:
    q=[x,y,z];q[axis]+=sign
    if tuple(q) not in cells:expected.add(((x,y,z),axis,sign))
 expected_count=len(expected);tops=[];bad=[]
 for gi,g in enumerate(r['groups']):
  for qi,q in enumerate(g['quads']):
   u=[q[1][k]-q[0][k] for k in range(3)];v=[q[2][k]-q[0][k] for k in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];axis=max(range(3),key=lambda k:abs(n[k]));sign=1 if n[axis]>0 else -1;axes=[k for k in range(3) if k!=axis]
   pts=[[int(round((p[k]-o[k])/pitch)) for k in range(3)] for p in q]
   assert max(abs(q[j][k]-(o[k]+pts[j][k]*pitch)) for j in range(4) for k in range(3))<1e-8
   for aa in range(min(p[axes[0]] for p in pts),max(p[axes[0]] for p in pts)):
    for bb in range(min(p[axes[1]] for p in pts),max(p[axes[1]] for p in pts)):
     xyz=[0,0,0];xyz[axis]=pts[0][axis]-(1 if sign>0 else 0);xyz[axes[0]]=aa;xyz[axes[1]]=bb;key=(tuple(xyz),axis,sign)
     if key not in expected:bad.append(key)
     else:expected.remove(key)
   if axis==1 and sign==1:tops.append({'polygon_xz_m':[[p[0]+pos[0],p[2]+pos[2]] for p in q],'y_m':q[0][1]+pos[1],'material':g['material']})
 assert not bad and not expected,(role,len(bad),len(expected));assert tops==inst['surface_ownership']['compiled_upward_faces']
 mask=next(m for m in pack['ownership_masks'] if m['owner_id']==inst['id']);assert mask==inst['surface_ownership']
 cols={}
 for (x,z),ys in columns.items():
  assert ys==set(range(min(ys),max(ys)+1)),'column void'
  cols[(x,z)]={'poly':[[pos[0]+o[0]+pitch*i,pos[2]+o[2]+pitch*k] for i,k in [(x,z),(x+1,z),(x+1,z+1),(x,z+1)]],'top':pos[1]+o[1]+pitch*(max(ys)+1),'bottom':pos[1]+o[1]+pitch*min(ys)}
 roles[role]={'tops':tops,'cols':cols,'pitch':pitch};alltops+=tops;bijections.append({'role':role,'cells':len(cells),'exterior_unit_faces':expected_count,'top_faces':len(tops),'render':ref(rp),'compiled':ref(cp),'source':ref(mp)})
index=geo._SpatialIndex(4)
for i,f in enumerate(alltops):index.add(i,f['polygon_xz_m'])
uncovered=0.
for p in pack['external_access_surfaces'][0]['polygon_regions_xz_m']:
 parts=[p]
 for i in index.candidates(p):parts=[q for current in parts for q in geo.convex_difference(current,alltops[i]['polygon_xz_m']) if area(q)>1e-11]
 uncovered+=sum(area(q) for q in parts)
overlap=sum(area(geo.convex_intersection(f['polygon_xz_m'],c['polygon_xz_m'])) for f in roles['fine']['tops'] for c in roles['coarse']['tops'])
cols=roles['fine']['cols'];risers=[];boundary=[]
for (x,z),c in cols.items():
 for dx,dz in [(1,0),(0,1)]:
  if (x+dx,z+dz) in cols:risers.append(abs(c['top']-cols[(x+dx,z+dz)]['top']))
 for (dx,dz),j in [((0,-1),0),((1,0),1),((0,1),2),((-1,0),3)]:
  if (x+dx,z+dz) not in cols:boundary.append({'a':c['poly'][j],'b':c['poly'][(j+1)%4],'y':c['top']})
# Import only the consumer API, never the author's native geometry audit.
review=importlib.import_module('world_city.concept_city_v3.registered_topography.revisions.r09_training_access.review');under=review.prior.prior
burial=[];owners_bad=[]
for c in cols.values():
 points=c['poly']+[[sum(p[k] for p in c['poly'])/4 for k in (0,1)]]
 for p in points:burial.append(under.land_height_at(*p)-c['bottom'])
 p=points[-1];r=review.owner_at(*p);y=review.surface_height_at(r,*p)
 if r['kind']!='r09_training_native_hole' or abs(y-c['top'])>1e-8:owners_bad.append({'point':p,'expected':c['top'],'owner':r,'actual_y':y})
public_edges=[]
for e in boundary:
 m=[(e['a'][k]+e['b'][k])/2 for k in (0,1)];r=under.owner_at(*m)
 if r['kind']=='road' and r['road_id']=='CASTLE_APPROACH':
  pts=[[(1-t)*e['a'][k]+t*e['b'][k] for k in (0,1)] for t in [0,.25,.5,.75,1]]
  public_edges.append(dict(e,steps=[e['y']-under.road_height_at('CASTLE_APPROACH',*p) for p in pts]))
for f in pack['actual_public_surface_overrides']:
 p=[sum(v[k] for v in f['polygon_xz_m'])/len(f['polygon_xz_m']) for k in (0,1)];r=review.owner_at(*p)
 if r['kind']!='r09_training_native_hole' or abs(review.surface_height_at(r,*p)-f['actual_compiled_top_y_m'])>1e-8:owners_bad.append({'public':f,'owner':r})
roads=[r for r in under._owners() if r['kind']=='road'];ri=geo._SpatialIndex(16)
for i,r in enumerate(roads):ri.add(i,r['polygon_xz_m'])
expected_public=[]
for fi,f in enumerate(alltops):
 for i in ri.candidates(f['polygon_xz_m']):
  p=geo.convex_intersection(f['polygon_xz_m'],roads[i]['polygon_xz_m'])
  if area(p)>1e-8:expected_public.append({'face':fi,'road_id':roads[i]['road_id'],'poly':p,'y':f['y_m']})
assert len(expected_public)==len(pack['actual_public_surface_overrides'])
remaining_public=list(enumerate(pack['actual_public_surface_overrides']))
for e in expected_public:
 matches=[(i,f) for i,f in remaining_public if f['compiled_face_index']==e['face'] and f['road_id']==e['road_id'] and abs(area(f['polygon_xz_m'])-area(e['poly']))<1e-8 and abs(area(geo.convex_intersection(f['polygon_xz_m'],e['poly']))-area(e['poly']))<1e-8 and abs(f['actual_compiled_top_y_m']-e['y'])<1e-8]
 assert matches,'missing public clip'
 remaining_public.remove(matches[0])
assert not remaining_public
public_multiset=collections.Counter((f['compiled_face_index'],f['road_id'],f['actual_compiled_top_y_m'],tuple(sorted(map(tuple,f['polygon_xz_m'])))) for f in pack['actual_public_surface_overrides'])
public_duplicate_records=sum(n-1 for n in public_multiset.values())
bounds=[-272,-155,-254,-149];records=review.surface_domains(bounds,False);partition_area=sum(area(r['polygon_xz_m']) for r in records);pi=geo._SpatialIndex(2)
for i,r in enumerate(records):pi.add(i,r['polygon_xz_m'])
double=sum(area(geo.convex_intersection(r['polygon_xz_m'],records[j]['polygon_xz_m'])) for i,r in enumerate(records) for j in pi.candidates(r['polygon_xz_m']) if j>i)
stale=[r['owner_id'] for r in records if review.stale(r)]
assert uncovered<1e-7 and overlap<1e-7 and max(risers)<=.125+1e-8 and min(burial)>=.25-1e-8 and not owners_bad and abs(partition_area-108)<1e-7 and double<1e-7 and not stale
for name,h in seal['files'].items():assert sha(D/name)==h,'sealed source changed during independent audit'
report={'schema':'riverstone.reconstructed_training.independent_native_owner_review.v1','status':'pass_bounded_native_and_owner_checks_traversal_pending','pack':ref(D/'resolved_placements.json'),'seal':ref(D/'freeze_manifest.json'),'contract':ref(D/'contract.json'),'checker':ref(pathlib.Path(__file__)),'sealed_files':hashes,'native_face_bijections':bijections,'source_uncovered_area_m2':uncovered,'coarse_fine_top_overlap_m2':overlap,'fine_columns':len(cols),'fine_area_m2':len(cols)*roles['fine']['pitch']**2,'fine_native_levels_m':sorted(set(c['top'] for c in cols.values())),'max_neighbor_riser_m':max(risers),'min_native_depth_m':min(c['top']-c['bottom'] for c in cols.values()),'minimum_burial_all_column_centres_and_corners_m':min(burial),'public_clip_count':len(expected_public),'unique_public_clip_count':len(public_multiset),'redundant_public_clip_records':public_duplicate_records,'public_boundary_segments':len(public_edges),'max_public_boundary_step_m':max(abs(s) for e in public_edges for s in e['steps']),'fine_and_public_owner_sample_errors':owners_bad,'bounded_partition':{'bounds':bounds,'record_count':len(records),'expected_area_m2':108,'sum_area_m2':partition_area,'double_overlap_m2':double,'stale_owners':stale},'unchanged_doors':len(pack['actual_doors']),'unchanged_routes':len(pack['internal_routes']),'limits':['Actual0.125m stair risers and up to0.070887m public-edge step persist; generic no-step capsule/cart approval absent.','Recovered native shell is0.5m; lost92fb6fc8 hash is not reused.','Original landmark source reservation reference in inherited pack metadata remains unavailable; the current consumer is separately bound to recovered rendered profiles9a47eab7.','The public co-ownership ledger has a redundant clip; the consumer partition is checked separately rather than counting its raw sum as union area.','Only the108m² ownership fixture was exhaustively partition-checked; full-city ownership is not approved.']}
p=HERE/('training_'+sha(D/'resolved_placements.json')[:12]+'_'+sha(pathlib.Path(__file__))[:12]+'.json');p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sealed_files','native_face_bijections','public_edges','limits']},indent=2));print('REPORT',p)
