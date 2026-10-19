"""Finite precinct and merchant placements over the recovered r4 city.
Shared common masters/caches only. Components are provenance, not double-rendered.
"""
import copy,json,hashlib,collections
from pathlib import Path
from world_city.concept_city_v3.registered_integration.r4.assemble import sha,load,rel
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
PACKS=[('precinct_compounds','assemblies/landmarks/registered/precinct_r04/contact_repair_r01/resolved_placements.json'),('precinct_belts','assemblies/landmarks/registered/precinct_r04/boundary_belts/resolved_placements.json'),('merchant_compounds','assemblies/property/registered/merchant_block011/resolved_placements.json'),('abbey_guard','assemblies/landmarks/registered/precinct_r04/abbey_guard_r01/resolved_placements.json')]
def build(binding_path=None):
 src=HERE.parent/'r4/corrected_visual_candidate.json';out=copy.deepcopy(load(src));old_ids={p['id'] for p in out['common_instances']};read=[];replacement=[]
 def get(name,path):
  p=CITY/path;d=load(p);read.append({'name':name,'path':rel(p),'sha256':sha(p)});return d
 def add_asset(key,a):
  if 'source' in a:mp,mh,rp,rh=a['source']['path'],a['source']['sha256'],a['cache']['path'],a['cache']['sha256']
  else:mp,mh,rp,rh=a['master_path'],a['master_sha256'],a['render_path'],a['render_sha256']
  mp,rp=rel(mp),rel(rp);assert sha(ROOT/mp)==mh and sha(ROOT/rp)==rh
  rd=load(ROOT/rp);entry=dict(master_path=mp,master_sha256=mh,render_path=rp,render_sha256=rh,quad_count=rd['quad_count'],bounds=rd['bounds'],pitch_m=rd['pitch'])
  old=out['common_assets'].get(key);assert old is None or old['render_sha256']==rh,('asset key collision',key)
  out['common_assets'][key]=entry
 def add(name,d):
  assets=d['assets'];assets=assets.items() if isinstance(assets,dict) else ((a['id'],a) for a in assets)
  for k,a in assets:add_asset(k,a)
  removed=set(d.get('replaced_placement_ids',[]));assert removed<=old_ids,('Unknown retired source IDs',removed-old_ids)
  if removed:
   out['common_instances']=[p for p in out['common_instances'] if p['id'] not in removed]
   out['remove_proxy_ids']+=sorted(removed|{i+':support' for i in removed}|{i+':owned_foundation' for i in removed});out['access_overlay']['remove_path_ids']+=d.get('superseded_source_path_ids',[])
  for p in d['placements']:
   assert p.get('scale',[1,1,1])==[1,1,1]
   q={k:copy.deepcopy(p[k]) for k in ('id','asset_key','position_m','yaw_rad','palette_id','palette_override') if k in p};q.setdefault('yaw_rad',0);q.setdefault('palette_id','native_'+name);q.setdefault('palette_override',{});q.update(scale=[1,1,1],source_pack=name);out['common_instances'].append(q)
  replacement.append(dict(pack=name,render_instances=len(d['placements']),removed_ids=sorted(removed),component_instances_rendered=False))
 for name,path in PACKS:add(name,get(name,path))
 support=get('abbey_finite_bearing_support','registered_topography/revisions/r14_precinct_merchant/support/resolved_support.json');add('precinct_support',{'assets':{support['asset_key']:support},'placements':[dict(support,id='ABBEY_FINITE_BEARING_SUPPORT')]})
 merchant_support=get('merchant_finite_bearing_support','registered_topography/revisions/r14_precinct_merchant/support/resolved_merchant_support.json');add('merchant_support',{'assets':{merchant_support['asset_key']:merchant_support},'placements':[dict(merchant_support,id='MERCHANT_FINITE_BEARING_SUPPORT')]})
 for name,path in [('precinct_corrected_external_access','assemblies/landmarks/registered/precinct_r04/access_r02/exterior_access_proposal.json'),('merchant_terrain_handoff','assemblies/property/registered/merchant_block011/terrain_handoff.json')]:get(name,path)
 used={p['asset_key'] for p in out['common_instances']};out['common_assets']={k:a for k,a in out['common_assets'].items() if k in used};ids=[p['id'] for p in out['common_instances']];assert len(ids)==len(set(ids))
 for k in ('remove_proxy_ids','replace_plot_ids','replace_landmark_groups'):out[k]=sorted(set(out[k]))
 out['access_overlay']['remove_path_ids']=sorted(set(out['access_overlay']['remove_path_ids']))
 out['provenance']['input_packs']+=read;out['provenance']['r5_supersession_ledger']=replacement;out['provenance']['r5_parent_sha256']=sha(src)
 out['provenance']['r5_limits']=['Precinct additions occupy owned courts/gardens, not the entire unassigned city backland.','Seven merchant properties are court-served small-goods/service ranges: native1.0–1.5 m leaves are not cart doors.','No new full-city character, interior, navigation or hydraulic pass.','Finite native supports and terrain interfaces need actual visual inspection.']
 out.update(schema='riverstone.registered_integration.r5',status='draft_waiting_finite_r14_ground_binding')
 if binding_path:
  b=load(binding_path);p=ROOT/b['contract_path'];assert sha(p)==b['contract_sha256'];out['terrain_module']=b['module'];out['provenance']['input_packs'].append(dict(name='r14_finite_ground',path=rel(p),sha256=sha(p)));out['status']='native_exterior_candidate_pending_actual_review'
 else:out['terrain_module']='UNBOUND_R14_DO_NOT_RENDER'
 out['counts']=dict(collections.Counter(p['source_pack'] for p in out['common_instances']));out['counts'].update(instances=len(ids),unique_assets=len(used),unique_cached_quads=sum(a['quad_count'] for a in out['common_assets'].values()))
 return out
if __name__=='__main__':
 import sys
 d=build(Path(sys.argv[1]) if len(sys.argv)>1 else None);dest=HERE/('candidate.json' if len(sys.argv)>1 else 'draft_candidate.json');assert not dest.exists();dest.write_text(json.dumps(d,separators=(',',':'))+'\n');print(json.dumps(d['counts'],indent=2));print(sha(dest))
