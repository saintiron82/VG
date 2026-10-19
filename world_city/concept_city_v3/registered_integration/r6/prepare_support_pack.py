"""Normalize the sealed R15 common native support records for scene placement."""
import copy,json
from . import apply_packs as a
PATH=a.CITY/'registered_topography/revisions/r15_merchant_local_patch/support_candidate/resolved_support.json'
HASH='abae7d11f7c1b09053cbcb95402b1715b0480528fce7d379e6a66412b7b1cf99'

def build():
 data=a.load(PATH,HASH);assets={};placements=[]
 for p in data['placements']:
  key=p['asset_key'];asset=a.asset_record(p)
  assert key not in assets;assets[key]=asset
  placements.append(dict(id='R15:'+p['native_owner_id']+':BEARING_SUPPORT',asset_key=key,position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=[1,1,1],palette_id='native_r15_support',palette_override={},property_id=p['property_id'],native_owner_id=p['native_owner_id']))
 assert len(assets)==len(placements)==15
 return dict(schema='riverstone.r6_normalized_support_pack.v1',status='hash_verified_native_support_candidate_requires_r15_ground',source=dict(path=a.rel(PATH),sha256=HASH),assets=assets,placements=placements,summary=data['summary'],source_limits=data['limitations'],terrain_approved=False)

if __name__=='__main__':
 d=build();dest=a.HERE/'merchant_support_pack.json';assert not dest.exists();dest.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(path=a.rel(dest),sha256=a.sha(dest),placements=len(d['placements']))))
