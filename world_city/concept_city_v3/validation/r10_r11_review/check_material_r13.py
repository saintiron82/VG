"""Compare every material-region tile to the unchanged r10 geometric authority."""
import sys,json,pathlib,hashlib,math,collections,importlib
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r10_density_reservoir import author as prior
suffix='r13_precinct_interfaces';m=importlib.import_module('world_city.concept_city_v3.registered_topography.revisions.'+suffix+'.materials');g=prior.geo

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def area(p):
 if len(p)<3:return 0.
 a=p[0];return abs(sum((p[i][0]-a[0])*(p[i+1][1]-a[1])-(p[i][1]-a[1])*(p[i+1][0]-a[0]) for i in range(1,len(p)-1)))/2

def tidy(p):
 out=[]
 for q in p:
  if not out or math.dist(q,out[-1])>1e-12:out.append(q)
 if len(out)>1 and math.dist(out[0],out[-1])<=1e-12:out.pop()
 return out

def intersection(p,q):return g.convex_intersection(tidy(p),tidy(q))
def ix(ps,cell=4):
 v=g._SpatialIndex(cell)
 for i,p in enumerate(ps):v.add(i,p)
 return v

def uncovered(ps,qs):
 index=ix(qs);value=0
 for p in ps:
  parts=[tidy(p)]
  for i in index.candidates(p):parts=[tidy(t) for pp in parts for t in g.convex_difference(tidy(pp),tidy(qs[i])) if area(t)>1e-11]
  value+=sum(map(area,parts))
 return value

def partition(rs):
 ps=[r['polygon_xz_m'] for r in rs];index=ix(ps,2);return dict(records=len(rs),area_m2=sum(map(area,ps)),overlap_m2=sum(area(intersection(p,ps[j])) for i,p in enumerate(ps) for j in index.candidates(p) if j>i))

def identity(r):return (r['owner_id'],r['kind'],r.get('render_land',True),r.get('road_id'),r.get('profile_domain_id'))
allowed={'polygon_xz_m','material','material_change_only','material_region_id','ground_material_owner_id'}
def metadata(r):return json.dumps({k:v for k,v in r.items() if k not in allowed},sort_keys=True,separators=(',',':'))
inputs={};seals=[]
for a in (prior,m):
 d=pathlib.Path(a.__file__).parent;freeze=d/('material_freeze.json' if a is m else 'freeze_manifest.json');seal=json.loads(freeze.read_text());seals.append(str(freeze));inputs[str(freeze.relative_to(ROOT))]=sha(freeze)
 for f,h in seal['files'].items():assert sha(d/f)==h;inputs[str((d/f).relative_to(ROOT))]=h
regions=m.REGIONS;boxes=set()
for r in regions:
 p=r['polygon_xz_m']
 for x in range(math.floor(min(q[0] for q in p)/16)*16,math.floor(max(q[0] for q in p)/16)*16+1,16):
  for z in range(math.floor(min(q[1] for q in p)/16)*16,math.floor(max(q[1] for q in p)/16)*16+1,16):
   box=[[x,z],[x+16,z],[x+16,z+16],[x,z+16]]
   if area(intersection(p,box))>1e-9:boxes.add((x,z,x+16,z+16))
records=[];issues=[];height_max=0;owner_max=0;aliases={n:getattr(m,n) is getattr(prior,n) for n in ['source_surface_height_at','surface_height_at','height_at','land_height_at','road_height_at','path_height_at']};assert all(aliases.values())
for number,b in enumerate(sorted(boxes)):
 old=prior.surface_domains(b,False);new=m.surface_domains(b,False);oldparts=collections.defaultdict(list);newparts=collections.defaultdict(list);ometa={metadata(r) for r in old}
 for r in old:oldparts[identity(r)].append(r['polygon_xz_m'])
 for r in new:newparts[identity(r)].append(r['polygon_xz_m'])
 unknown=list(newparts.keys()-oldparts.keys());missing=list(oldparts.keys()-newparts.keys());changed=[]
 for key in oldparts.keys()&newparts.keys():
  delta=uncovered(oldparts[key],newparts[key])+uncovered(newparts[key],oldparts[key]);owner_max=max(owner_max,delta)
  if delta>1e-7:changed.append(dict(owner=key,symmetric_difference_m2=delta))
 metadata_errors=[];max_delta=0
 for r in new:
  if metadata(r) not in ometa:metadata_errors.append(r['owner_id']);continue
  if r.get('material_change_only'):assert m.eligible(r)
  p=r['polygon_xz_m'];q=[sum(v[k] for v in p)/len(p) for k in (0,1)];o=next((s for s in old if identity(s)==identity(r) and g.point_in_convex_polygon(q,tidy(s['polygon_xz_m']),1e-7)),None)
  if o is None:continue
  max_delta=max(max_delta,abs(m.source_surface_height_at(r,*q)-prior.source_surface_height_at(o,*q)))
 height_max=max(height_max,max_delta);before=partition(old);after=partition(new)
 row=dict(bounds=b,before=before,after=after,unknown_owner_ids=unknown,missing_owner_ids=missing,changed_owners=changed,metadata_errors=metadata_errors,max_height_delta_m=max_delta)
 records.append(row)
 if changed or unknown or missing or metadata_errors or abs(after['area_m2']-256)>1e-6 or after['overlap_m2']>1e-6 or max_delta>1e-9:issues.append(row)
 if number%25==0:print('TILE',number+1,'/',len(boxes),'issues',len(issues),flush=True)
for p,h in inputs.items():assert sha(ROOT/p)==h
report=dict(schema='riverstone.independent_material_geometry_equivalence.v1',status='fail_material_subdivision_changes_geometry' if issues else 'pass_finite_owner_and_height_preservation',candidate_revision=suffix,checker_sha256=sha(__file__),inputs=inputs,height_aliases=aliases,semantic_regions=len(regions),tile_count=len(boxes),maximum_owner_symmetric_difference_m2=owner_max,maximum_height_delta_m=height_max,issues=issues,tiles=records,limits=['All semantic-region16m tiles tested; no whole-city navigation claim.','Native B015 and southern cache checks remain in the separate hash-bound report.','No rendered triangle identity or same-plane material exporter claim.','Coincident consecutive/closing vertices are removed in the checker only; no terrain source is edited.'])
p=H/(suffix+'_material_'+sha(pathlib.Path(m.__file__))[:12]+'_'+sha(__file__)[:12]+'.json');p.write_text(json.dumps(report,indent=2)+'\n');print('REPORT',p,'STATUS',report['status'],'ISSUES',len(issues),flush=True)
