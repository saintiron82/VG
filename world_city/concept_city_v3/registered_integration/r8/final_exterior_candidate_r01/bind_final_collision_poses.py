"""Exact schema/pose adapters, followed by all-contract actual-native preflight."""
import copy,json,pathlib
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a
from world_city.concept_city_v3.registered_integration.r8.promotion import palette_catalog,resolve_palettes,explicit_retirements
from world_city.concept_city_v3.registered_integration.r8.runtime_contracts import append_collision_contracts
D=pathlib.Path(__file__).resolve().parent
ref=lambda p:dict(path=a.rel(p),sha256=a.sha(p))
read=lambda r:a.load(a.ROOT/r['path'],r['sha256'])
def main():
 bp=D/'whole_city_activation_r02/activation_binding.json';b=a.load(bp);base=read(b['base_scene']);s={k:base[k]for k in ('common_instances','common_assets','boxes','surfaces')};s['collision_contracts']=copy.deepcopy(base.get('collision_contracts',[]));catalog=palette_catalog(s)
 for r in b['packs']:
  p=read(r);p,_=resolve_palettes(p,catalog);s,_=a.apply_pack(s,p,r['name'],dict(path=r['path'],sha256=r['sha256']),extra_retire_ids=explicit_retirements(p))
  if p.get('collision_contracts'):s['collision_contracts']+=copy.deepcopy(p['collision_contracts'])
 by={p['id']:p for p in s['common_instances']};out=D/'whole_city_activation_r03';assert not out.exists();out.mkdir();changes=[]
 for i,pid in [(10,'BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED'),(12,'BRIDGE_MAIN_RIVER:PORT_VISIBLE_APPROACH_R01')]:
  previous=b['collision_contracts'][i];old=read(previous);c=copy.deepcopy(old);p=by[pid];ass=s['common_assets'][p['asset_key']]
  c['native_placement_id']=pid;c['replacement_transform']={k:p[k]for k in('position_m','yaw_rad')};c['native_source']=dict(path=ass['render_path'],sha256=ass['render_sha256']);c['integration_source_contract']=previous;c['integration_pose_binding']='Exact current native placement/cache; source collision triangles remain value-identical.'
  if i==10:
   cp=a.CITY/'assemblies/waterworks/registered_bridge/port_guard_opening_r01/compatibility_audit.json';audit=a.load(cp);assert audit['fixed_span_geometry_unchanged']and audit['port_profile_and_collision_contract_unchanged'];c['native_successor_compatibility']=ref(cp)
   assert old['native_pose']['translation']==p['position_m']
  else:c['native_and_ownership_activation_pending']=False
  assert c['add_triangles_world_xyz_m']==old['add_triangles_world_xyz_m']and c['disable_native_mesh_collider_ids']==old['disable_native_mesh_collider_ids']
  q=out/f'contract_{i:02d}.json';q.write_text(json.dumps(c,separators=(',',':'))+'\n');b['collision_contracts'][i]=ref(q);changes.append(dict(index=i,previous=previous,current=ref(q),triangles_unchanged=True,disable_ids_unchanged=True,native_placement_id=pid))
 result=append_collision_contracts(s,[read(r)for r in b['collision_contracts']]);report=dict(status='PASS_ALL_CURRENT_NATIVE_CONTRACTS',source_binding=ref(bp),contracts=len(b['collision_contracts']),scene_contracts=len(result['collision_contracts']),native_instances=len(s['common_instances']),changes=changes,geometry_changed=False)
 q=out/'contract_preflight.json';q.write_text(json.dumps(report,indent=2)+'\n');b['evidence'].append(ref(q));q=out/'activation_binding.json';q.write_text(json.dumps(b,indent=2)+'\n');print(ref(q),report['contracts'],flush=True)
if __name__=='__main__':main()
