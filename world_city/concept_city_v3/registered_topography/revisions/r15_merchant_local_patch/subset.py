"""Opt-in seven-property R6 candidate, preserving the other twelve R5 owners."""
import json,copy,math
from functools import lru_cache
from . import author as a, frozen as f
HERE=a.HERE/'subset_07';HERE.mkdir(exist_ok=True)
INDICES=(3,11,12,13,15,16,18)
PROPERTIES=[a.HANDOFF['properties'][i] for i in INDICES]
IDS={p['property_id'] for p in PROPERTIES}
ELIGIBILITY_PATH=a.ROOT/a.PACK['eligibility']['path']
if a.sha(ELIGIBILITY_PATH)!=a.PACK['eligibility']['sha256']:raise ValueError('Changed eligibility')
ELIGIBILITY=json.loads(ELIGIBILITY_PATH.read_bytes())
PROPERTY_SOURCES={p['id']:p for p in ELIGIBILITY['properties'] if p['id'] in IDS}
RETIRED=sorted({s for p in PROPERTY_SOURCES.values() for s in p['source_retired_native_ids']})
EXCLUDED=tuple(sorted(set(a.base.EXCLUDED)|set(RETIRED)))
PLATFORMS=[r for r in a.PLATFORMS if r['property_id'] in IDS]
GATES=[r for r in a.GATES if r['property_id'] in IDS]
HOLES=[r for r in a.NATIVE_HOLES if r['property_id'] in IDS]
NEW_MASKS=[r['polygon_xz_m'] for r in PLATFORMS+GATES]

@lru_cache(None)
def restoration_domains():
 out=[]
 for old in a.retired_owner_domains():
  if old['old_owner_id'].split(':')[0] not in RETIRED:continue
  for part in a.subtract([old['polygon_xz_m']],NEW_MASKS):
   b=f.bounds(part)
   for under in a.base.R04.prior._replacement_domains(part,b,EXCLUDED):
    p=a.polygon(under['polygon_xz_m'])
    if p:out.append(dict(id='SUBSET_RESTORE:'+str(len(out)),polygon_xz_m=p,retired_owner_id=old['old_owner_id'],retired_kind=old['old_kind'],underlying_record=under,walking_status='Retired doorway removed; nonwalking ground only.'))
 return out

def filtered_pack():
 p=copy.deepcopy(a.PACK)
 # Every property-scoped record is filtered. Whole-source manifests remain provenance.
 for k,v in list(p.items()):
  if isinstance(v,list) and v and isinstance(v[0],dict):
   fields=('property_id','id','owner_id','group_id','assembly_group_id')
   if any(key in v[0] for key in fields):p[k]=[x for x in v if any(str(x.get(key,''))==pid or str(x.get(key,'')).startswith(pid+':') for key in fields for pid in IDS)]
 p['replaced_placement_ids']=RETIRED
 p['superseded_native_access_ids']=sorted({s for x in PROPERTY_SOURCES.values() for s in x['superseded_native_access_ids']})
 p['superseded_source_path_ids']=sorted({s for x in PROPERTY_SOURCES.values() for s in x['superseded_source_path_ids']})
 keys={r['asset_key'] for r in p['placements']}
 if isinstance(p['assets'],dict):p['assets']={k:v for k,v in p['assets'].items() if k in keys}
 else:p['assets']=[r for r in p['assets'] if r.get('asset_key',r.get('key')) in keys]
 p['subset_binding']=dict(parent_pack_sha256=a.REFERENCES[list(a.REFERENCES)[2]],accepted_property_ids=sorted(IDS),source_indices=list(INDICES),inactive_property_ids=sorted({r['property_id'] for r in a.PLATFORMS}-IDS),inactive_original_ids=sorted(set(a.RETIRED)-set(RETIRED)))
 p['status']='SOURCE_ACCEPTED_SEVEN_PROPERTY_SUBSET_PENDING_SCENE_REVIEW';p['applied_to_scene']=False
 p['summary']=dict(property_count=len(IDS),rigid_placement_count=len(p['placements']),retired_original_count=len(RETIRED),native_hole_count=len(HOLES),actual_door_count=len(p['actual_doors']))
 return p

def filtered_support():
 src=a.CITY/'registered_integration/r6/merchant_support_pack.json'
 if a.sha(src)!='87db1e65f820e0b4bc8795bee70deb48bcc9e9c666eb3f869a2cf0c2b4c6487f':raise ValueError('Changed normalized support pack')
 p=json.loads(src.read_bytes());p['placements']=[r for r in p['placements'] if r['property_id'] in IDS]
 keys={r['asset_key'] for r in p['placements']}
 p['assets']={k:v for k,v in p['assets'].items() if k in keys} if isinstance(p['assets'],dict) else [r for r in p['assets'] if r.get('asset_key',r.get('key')) in keys]
 p['subset_binding']=dict(parent_pack_sha256=a.sha(src),accepted_property_ids=sorted(IDS));p['summary']=dict(placement_count=len(p['placements']),asset_count=len(p['assets']))
 return p
