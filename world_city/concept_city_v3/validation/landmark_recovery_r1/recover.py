"""Recover finite rendered profiles, never impersonating lost source hashes."""
import sys,json,pathlib,hashlib,math,collections
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as geo
CITY=ROOT/'world_city/concept_city_v3';SCENE=CITY/'evidence/visual_registered_common_r3/scene.json';AUDIT=SCENE.parent/'source_audit.json';CONTRACT=CITY/'registered_topography/revisions/r08_park_interface/contract.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def grad(t):
 a,b,c=t;dx1=b[0]-a[0];dz1=b[2]-a[2];dy1=b[1]-a[1];dx2=c[0]-a[0];dz2=c[2]-a[2];dy2=c[1]-a[1];det=dx1*dz2-dx2*dz1
 return math.hypot((dy1*dz2-dy2*dz1)/det,(dx1*dy2-dx2*dy1)/det)
scene=json.loads(SCENE.read_text());audit=json.loads(AUDIT.read_text());contract=json.loads(CONTRACT.read_text());n=audit['counts']['supplemental_preview_triangles'];road=scene['surfaces']['road'];assert len(road)%3==0
assert scene['terrain_contract']['landmark_approach_preview']==contract['landmark_approach_preview'];assert scene['terrain_contract']['landmark_public_landing_preview']==contract['landmark_public_landing_preview']
start=len(road)//3-n;rendered=[road[i:i+3] for i in range(start*3,len(road),3)]
landing=contract['landmark_public_landing_preview'];approach=contract['landmark_approach_preview'];masks=[];idx=geo._SpatialIndex(8)
for group in landing['source_records']:
 for i,r in enumerate(group['finite_owned_polygons']):
  p=r['poly'];rec={'owner_id':'RECOVERED_LANDMARK_PUBLIC:'+group['id']+':'+str(i),'group_id':group['id'],'road_id':r['road_id'],'polygon_xz_m':p,'kind':'landmark_public_hole','priority':9,'render_land':False};idx.add(len(masks),p);masks.append(rec)
centres={}
for g in approach['shared_boundaries']:
 points=[v for b in g['native'] for v in b['edge_xz_m']]+[b['a_xz_m'] for b in g['public']]
 centres[g['group_id']]=[sum(p[k] for p in points)/len(points) for k in (0,1)]
out={'schema':'riverstone.recovered_rendered_landmark_profiles.r1','provenance':{'kind':'Exact rendered triangle extraction from hash-bound archived r3 scene; not original author JSON reconstruction.','scene':ref(SCENE),'source_audit':ref(AUDIT),'r08_contract':ref(CONTRACT),'builder':ref(CITY/'evidence/visual_registered_common_r3/source_snapshot/world_city/concept_city_v3/build_blockout.py'),'r08_author':ref(CITY/'evidence/visual_registered_common_r3/source_snapshot/world_city/concept_city_v3/registered_topography/revisions/r08_park_interface/author.py'),'extractor':ref(pathlib.Path(__file__)),'road_triangle_suffix_start_index':start,'road_triangle_suffix_count':n,'recovery_rule':'The frozen builder emits supplemental domains after all regular road surfaces. r08 emits approaches then landings. No later road faces are appended in exact-ownership mode.','lost_source_sha256':[approach['source_sha256'],landing['source_sha256']],'old_hashes_not_reused':True},'approaches':{'triangles':[],'masks':[],'shared_boundaries':approach['shared_boundaries'],'historical_declared_route_count':approach['route_count'],'missing_routes':approach['missing_routes']},'landings':{'triangles':[],'masks':masks,'retained_source_records':landing['source_records']},'limits':['Rendered finite XYZ profiles only. Support depths cannot be recovered from visible top faces.','Ramp ownership is the exact recovered rendered triangle union; original 239 broader mask records and route-to-triangle IDs are missing.','Native capsule movement, general road gradients, approach support and scene-wide access remain unverified.','The rear monastery chapel route remains explicitly missing.','Original pre-weld and welded author JSON bytes/hashes were not recovered.']}
ambiguous=[];grades={'approaches':[],'landings':[]};groupcounts=collections.Counter();areas=collections.defaultdict(float);firstlanding=None
for i,t in enumerate(rendered):
 p=[[v[0],v[2]] for v in t];centroid=[sum(v[k] for v in p)/3 for k in (0,1)];hits=[]
 for j in idx.candidates(p):
  m=masks[j]
  if all(geo.point_in_convex_polygon(q,m['polygon_xz_m'],1e-7) for q in p):hits.append(m['group_id'])
 hits=sorted(set(hits))
 if len(hits)>1:ambiguous.append({'index':i,'groups':hits})
 kind='landings' if hits else 'approaches';gid=hits[0] if hits else min(centres,key=lambda g:math.dist(centroid,centres[g]));g=grad(t)
 rec={'owner_id':'RECOVERED_R3_'+kind.upper()+':'+str(i),'group_id':gid,'triangle_xyz_m':t,'polygon_xz_m':p,'source_grade':g,'rendered_source_index':{'material':'road','triangle_index':start+i},'support_status':'unverified_visible_top_only'}
 out[kind]['triangles'].append(rec);grades[kind].append(g);groupcounts[(kind,gid)]+=1;areas[kind]+=geo.polygon_area(p)
 if hits:
  if firstlanding is None:firstlanding=i
 else:
  if firstlanding is not None:ambiguous.append({'index':i,'issue':'approach_triangle_after_landing_suffix'})
  out['approaches']['masks'].append({'owner_id':rec['owner_id']+':MASK','group_id':gid,'polygon_xz_m':p,'kind':'landmark_ramp_hole','priority':18,'render_land':False})
assert not ambiguous,ambiguous[:5]
# Export exact XYZ without rounding or re-evaluation. Every saved vertex equals its
# identified source triplet; current heights are never taken from a fresh author.
DATA=HERE/'recovered_rendered_profiles.json';DATA.write_text(json.dumps(out,separators=(',',':'))+'\n')
reloaded=json.loads(DATA.read_text());mismatch=[]
for kind in ('approaches','landings'):
 for t in reloaded[kind]['triangles']:
  i=t['rendered_source_index']['triangle_index'];
  if t['triangle_xyz_m']!=road[i*3:i*3+3]:mismatch.append(t['owner_id'])
# All retained public masks must have their full positive area represented. The
# partitioned landing faces are summed and checked against the original mask sum.
landing_area=sum(geo.polygon_area(x['polygon_xz_m']) for x in masks)
report={'schema':'riverstone.recovered_profiles.exact_render_comparison.v1','status':'pass_exact_rendered_profiles_only' if not mismatch and abs(landing_area-areas['landings'])<1e-6 else 'FAIL','data':ref(DATA),'sources':out['provenance'],'triangle_counts':{k:len(out[k]['triangles']) for k in ('approaches','landings')},'group_counts':{':'.join(k):v for k,v in groupcounts.items()},'area_m2':dict(areas),'retained_public_mask_area_m2':landing_area,'public_mask_minus_triangle_area_m2':landing_area-areas['landings'],'maximum_triangle_grade':{k:max(v) for k,v in grades.items()},'triangle_grade_over_12_percent':{k:sum(g>.12000001 for g in v) for k,v in grades.items()},'exact_source_xyz_mismatches':mismatch,'rendered_omission_relative_to_historical_authored_triangle_count':approach['triangle_count']+landing['triangle_count']-n,'first_landing_suffix_index':firstlanding,'route_identity_status':'Only group identity recovered; original individual route-to-triangle association absent.','broad_ramp_mask_status':'Original mask bytes missing; recovery cuts only actual recovered triangle polygons. No equivalence of broader cuts claimed.','support_status':'unverified; not inferable from top-surface render','limits':out['limits']}
p=HERE/'recovery_report.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('sources','limits')},indent=2));print('DATA',sha(DATA),'REPORT',sha(p))
