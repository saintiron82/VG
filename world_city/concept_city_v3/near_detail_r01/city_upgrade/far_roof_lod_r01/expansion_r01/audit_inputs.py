from input_contract import *
from collections import Counter,defaultdict
import resource,time
start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
idx=load(C/'playable_r01/generated/tile_r01/index.json')['common_assets'];mapping=load(U/'surface_mapping/material_surface_map.v1.json')['assets'];near=load(C/'playable_detail_r01/near_catalog.json')['assets'];rows=[];families=defaultdict(Counter)
for key,source in sorted(idx.items()):
 m=load(R/source['master_path']);r=inspect(key,mapping[key],source,m)
 row={k:v for k,v in r.items()if k not in ['raw_solids','canonical_solids','source_operations','cut_exclusion_proofs','canonical_group_suppression_proof']}
 if r['status']=='SUPPORTED_INPUT_UNBUILT':row.update(raw_solids=len(r['raw_solids']),canonical_solids=len(r['canonical_solids']),cut_exclusion_proofs=len(r['cut_exclusion_proofs']))
 row['has_completed_near_entry']=key in near;row['placement_count']=mapping[key].get('placement_count',0);row['categories']=mapping[key].get('category_counts',{})
 for cat in row['categories']:families[cat][row['status']]+=1
 rows.append(row)
report={'schema':'riverstone.source_roof_lod_eligibility.v1','scope':'All 304 indexed common assets. Input eligibility only; no all-assets surface/visual acceptance claim.','counts':dict(Counter(r['status']for r in rows)),'category_counts':{k:dict(v)for k,v in sorted(families.items())},'near_asset_counts':dict(Counter(r['status']for r in rows if r['has_completed_near_entry'])),'rows':rows,'sources':[ref(C/'playable_r01/generated/tile_r01/index.json'),ref(U/'surface_mapping/material_surface_map.v1.json'),ref(Path(__file__)),ref(H/'input_contract.py'),ref(P/'source_surface_adapter.py')],'seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'outputs_mutate_runtime':False}
write(H/'eligibility_inventory.json',report)
print(json.dumps({k:report[k]for k in ['counts','near_asset_counts','seconds','max_rss_kib']}))
