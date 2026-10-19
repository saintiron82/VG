"""Read-only operation coverage and existing peak-RSS audit. No cell sampling."""
import collections,gzip,hashlib,json,pathlib,resource,signal,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];U=HERE.parent;sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True;resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));signal.alarm(30)
from voxel_character.common import core
started=time.perf_counter();completed=set();stats=[]
for p in U.rglob('*.layered.stats.json'):
 s=json.loads(p.read_text());completed.add(s.get('asset_key'));stats.append({'asset_key':s.get('asset_key'),'max_rss_kib':s.get('max_rss_kib'),'elapsed_seconds':s.get('elapsed_seconds'),'path':str(p.relative_to(ROOT))})
catalogs=[('house',U/'house_extensions/generated/active_catalog.json'),('facility',U/'facility_roofs/activation_plan/all_72_layered_compile_catalog.v6.json')]
results=[]
for category,catalog in catalogs:
 for r in json.loads(catalog.read_text())['assets']:
  selected={'attached_native_row_0f0bbe769178b1','ordinary_r2_8c6ac6d806c93b','ordinary_r2_dd5975b033daae','registered_castle_west_residence','registered_castle_rear_residence','registered_monastery_monastic_church','registered_arcade_10'}
  if r.get('asset_key') not in selected or r.get('asset_key') in completed or not r.get('emitted_master_path'):continue
  p=ROOT/r['emitted_master_path'];data=p.read_bytes();master=json.loads(gzip.decompress(data) if p.suffix=='.gz' else data);components={c['id']:c for c in master['components']};instances={i['id']:i for i in master['instances']};transforms={}
  def resolve(key):
   if key not in transforms:
    i=instances[key];t=core.transform(i.get('transform'))
    if i.get('parent') is not None:t=core.compose(resolve(i['parent']),t)
    transforms[key]=t
   return transforms[key]
  counts=collections.Counter();eligible=0
  for i in instances.values():
   t=resolve(i['id'])
   for op in components[i['component']]['operations']:
    placement=core.compose(t,core.transform(op.get('transform'))) if op.get('transform') else t
    exact=all(sum(v!=0 for v in row)==1 and all(v in (0,1,-1) for v in row) for row in core.transpose(placement['basis']))
    kind=op['shape']['kind'];ok=kind in ('box','extrusion') and exact;counts[kind]+=1;eligible+=ok
  # Assembly cut operations use the same points_in optimization.
  for op in master.get('assembly_cuts',[]):
   basis=core.transform(op.get('transform'))['basis'];exact=all(sum(v!=0 for v in row)==1 and all(v in (0,1,-1) for v in row) for row in core.transpose(basis));kind=op['shape']['kind'];counts[kind]+=1;eligible+=kind in ('box','extrusion') and exact
  total=sum(counts.values());results.append({'category':category,'asset_key':r['asset_key'],'path':str(p.relative_to(ROOT)),'file_sha256':hashlib.sha256(data).hexdigest(),'catalog_sha_matches':hashlib.sha256(data).hexdigest()==r.get('emitted_master_sha256'),'operations':total,'eligible':eligible,'eligible_fraction':eligible/total if total else 0,'shapes':dict(counts)})
summary={}
for category in ('house','facility'):
 rows=[r for r in results if r['category']==category];n=sum(r['operations'] for r in rows);e=sum(r['eligible'] for r in rows);summary[category]={'representative_pending_assets_read':len(rows),'operations':n,'eligible_operations':e,'eligible_fraction':e/n if n else 0,'fallback_assets':[r['asset_key'] for r in rows if r['eligible']!=r['operations']]}
report={'summary':summary,'pending_assets':results,'highest_observed_existing_peak_rss':sorted(stats,key=lambda x:x.get('max_rss_kib') or 0,reverse=True)[:12],'elapsed_seconds':time.perf_counter()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'interpretation':'Representative subset, not an exhaustive pending-asset scan. Operation-count coverage only, not candidate-weighted or end-to-end speedup. Existing completed outputs were read but never recompiled.'}
(HERE/'support_coverage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('pending_assets','highest_observed_existing_peak_rss')},indent=2))
